#!/usr/bin/env bash
# Migrate SQLite nakamadb → Postgres (asyncpg URL).
# Usage:
#   DATABASE_URL=postgresql+asyncpg://nakama:pass@localhost:5432/nakama \
#   SQLITE_PATH=./data/nakamadb.sqlite \
#   ./deploy/migrate_sqlite_to_postgres.sh
set -euo pipefail

APP_DIR="${NAKAMA_APP_DIR:-/home/ubuntu/projects/nakama}"
SQLITE_PATH="${SQLITE_PATH:-$APP_DIR/data/nakamadb.sqlite}"
DATABASE_URL="${DATABASE_URL:-}"
if [[ -z "$DATABASE_URL" ]]; then
  echo "DATABASE_URL required (postgresql+asyncpg://...)" >&2
  exit 1
fi
if [[ ! -f "$SQLITE_PATH" ]]; then
  echo "SQLite file missing: $SQLITE_PATH (will only ensure Postgres schema)" >&2
fi

cd "$APP_DIR"
python3 - <<'PY'
import asyncio
import os
import sqlite3
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base, ReadingHistory, User, dispose_engine, get_database_url, init_db

sqlite_path = Path(os.environ.get("SQLITE_PATH", "data/nakamadb.sqlite"))
pg_url = os.environ["DATABASE_URL"]
print("postgres:", pg_url.split("@")[-1] if "@" in pg_url else pg_url)
print("sqlite:", sqlite_path, "exists=", sqlite_path.exists())

async def main() -> None:
    # Ensure schema on Postgres
    engine = create_async_engine(pg_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    users = []
    history = []
    if sqlite_path.exists():
        con = sqlite3.connect(str(sqlite_path))
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        try:
            users = [dict(r) for r in cur.execute("SELECT * FROM users")]
        except sqlite3.Error as e:
            print("users table:", e)
        try:
            history = [dict(r) for r in cur.execute("SELECT * FROM reading_history")]
        except sqlite3.Error as e:
            print("history table:", e)
        con.close()

    async with factory() as session:
        # Upsert users by username
        existing_users = {
            u.username: u
            for u in (await session.execute(select(User))).scalars().all()
        }
        id_map: dict[int, int] = {}
        for u in users:
            uname = u["username"]
            if uname in existing_users:
                id_map[int(u["id"])] = int(existing_users[uname].id)
                continue
            nu = User(username=uname, password_hash=u["password_hash"])
            session.add(nu)
            await session.flush()
            id_map[int(u["id"])] = int(nu.id)
        await session.commit()

        # Insert history if empty-ish
        existing_hist = (await session.execute(select(ReadingHistory.id))).scalars().all()
        if existing_hist:
            print(f"postgres already has {len(existing_hist)} history rows; skip history copy")
        else:
            for h in history:
                old_uid = int(h["user_id"])
                new_uid = id_map.get(old_uid)
                if not new_uid:
                    continue
                session.add(
                    ReadingHistory(
                        user_id=new_uid,
                        source=h["source"],
                        content_id=h["content_id"],
                        content_type=h["content_type"],
                        chapter_id=h["chapter_id"],
                    )
                )
            await session.commit()
            print(f"migrated users={len(users)} history={len(history)}")

    # counts
    async with factory() as session:
        uc = (await session.execute(text("select count(*) from users"))).scalar()
        hc = (await session.execute(text("select count(*) from reading_history"))).scalar()
        print(f"postgres counts users={uc} history={hc}")
    await engine.dispose()

asyncio.run(main())
PY
