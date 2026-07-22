#!/usr/bin/env python3
"""Add SourceMeta to all source adapters that don't have one yet."""
import re, sys
from pathlib import Path

PROJECT = Path("/home/ubuntu/projects/nakama")
SOURCES = PROJECT / "app" / "sources"

# Sources already done (have 'meta = SourceMeta')
DONE = {"bacakomik", "kiryuu", "otakudesu", "meionovels", "anichin"}

META_TEMPLATE = '''    meta = SourceMeta(
        version="{today}",
        verified_on="{today}",
        base_url_pattern="{pattern}",
        selectors=[{selectors}],
        alt_domains=[{alt_domains}],
        notes="{notes}",
    )'''

from datetime import date
today = date.today().isoformat()

# Metadata per source
DATA = {
    "komiku": {"base_url": "https://komiku.id", "kind": "comic",
        "selectors": [".daftar .bge a", ".bge", ".chlist a"],
        "alt_domains": ["komiku.org", "komiku.com"], "notes": "Classic Indo comic aggregator"},
    "komikcast": {"base_url": "https://komikcast.com", "kind": "comic",
        "selectors": [".bsx a", ".listupd .bs", ".eplister a"],
        "alt_domains": ["komikcast03.com", "komikcast.me"], "notes": "komikcast6 theme; uses Appwrite auth"},
    "komikindo": {"base_url": "https://komikindo.id", "kind": "comic",
        "selectors": [".bsx a", ".listupd .bs", ".eplister a"],
        "alt_domains": ["komikindo.ch", "komikindo.co"], "notes": "komikcast6 theme; shared with komikcast"},
    "mangadex": {"base_url": "https://mangadex.org", "kind": "comic",
        "selectors": ["api.mangadex.org/manga", "api.mangadex.org/chapter"],
        "alt_domains": [], "notes": "Official MangaDex API (v5)"},
    "shinigami": {"base_url": "https://api.shngm.io", "kind": "comic",
        "selectors": ["/api/manga/list", "/api/manga/detail", "/api/chapter"],
        "alt_domains": ["shinigami.asia", "shinigami.id"], "notes": "Shinigami API; has auth; domain rotates"},
    "samehadaku": {"base_url": "https://samehadaku.li", "kind": "anime",
        "selectors": [".venz", ".detpost", ".eps", ".episodelist"],
        "alt_domains": ["samehadaku.how", "samehadaku.care"], "notes": "JS-rendered episodes; CF-protected"},
    "anilist": {"base_url": "https://graphql.anilist.co", "kind": "anime",
        "selectors": ["GraphQL Page.media", "GraphQL Media.search"],
        "alt_domains": [], "notes": "AniList GraphQL API; no HTML scraping"},
    "jikan": {"base_url": "https://api.jikan.moe/v4", "kind": "anime",
        "selectors": ["/anime", "/anime/{id}", "/anime/{id}/episodes"],
        "alt_domains": [], "notes": "Jikan v4 REST API; MyAnimeList proxy; rate-limited"},
    "sakuranovel": {"base_url": "https://sakuranovel.id", "kind": "novel",
        "selectors": [".listupd .bs", ".bixbox .bxcl a", ".chapter-content"],
        "alt_domains": ["sakuranovel.cc", "sakuranovel.me"], "notes": "CF-protected; uses FlareSolverr"},
    "novelbin": {"base_url": "https://www.novelbin.cc", "kind": "novel",
        "selectors": [".col-novel-main .novel-item", ".chr-c", "#chr-content"],
        "alt_domains": ["novelbin.com", "novelbin.net"], "notes": "NovelBin; English novel source"},
    "novelfull": {"base_url": "https://novelfull.com", "kind": "novel",
        "selectors": [".col-truyen-main .row", ".list-chapter a", "#chapter-content"],
        "alt_domains": ["novelfull.net"], "notes": "NovelFull; CF-protected; uses FlareSolverr"},
}


def main():
    added = 0
    for name, info in DATA.items():
        target = SOURCES / f"{name}.py"
        if not target.exists():
            print(f"SKIP {name}: file not found", file=sys.stderr)
            continue
        content = target.read_text()
        if "meta = SourceMeta" in content:
            print(f"SKIP {name}: already has meta")
            continue

        # Find import line to add
        if "from .source_meta import SourceMeta" not in content:
            # Add import after the last "from .base import" or similar
            content = content.replace(
                "from .base import ComicSource, SourceError",
                "from .base import ComicSource, SourceError\nfrom .source_meta import SourceMeta",
            )
            content = content.replace(
                "from .base import AnimeSource, SourceError",
                "from .base import AnimeSource, SourceError\nfrom .source_meta import SourceMeta",
            )
            content = content.replace(
                "from .base import NovelSource, SourceError",
                "from .base import NovelSource, SourceError\nfrom .source_meta import SourceMeta",
            )

        sel_str = ", ".join(f'"{s}"' for s in info["selectors"])
        alt_str = ", ".join(f'"{d}"' for d in info["alt_domains"])

        meta_block = META_TEMPLATE.format(
            today=today, pattern=info["base_url"],
            selectors=sel_str, alt_domains=alt_str, notes=info["notes"],
        )

        # Insert meta block after the name + base_url lines
        if "meta = SourceMeta" not in content:
            # Find "name = ..." followed by "base_url = ..." 
            name_pattern = rf'(\s+name\s*=\s*"{name}".*\n)(\s+base_url.*\n)'
            repl = rf'\1{meta_block}\n\2'
            new_content = re.sub(name_pattern, repl, content, count=1)
            if new_content == content:
                # Fallback: just insert after name line
                name_pattern = rf'(\s+name\s*=\s*"{name}".*\n)'
                repl = rf'\1{meta_block}\n'
                new_content = re.sub(name_pattern, repl, content, count=1)
            if new_content != content:
                content = new_content
                added += 1
                target.write_text(content)
                print(f"OK {name} ({info['kind']}): {info['base_url']}")
            else:
                print(f"FAIL {name}: could not find name pattern. First 5 lines:", file=sys.stderr)
                # Show context
                for line in content.split('\n')[:10]:
                    print(f"  {line}", file=sys.stderr)
        else:
            print(f"OK {name}: already present")

    print(f"\nAdded meta to {added} sources")


if __name__ == "__main__":
    main()