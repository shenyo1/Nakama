"""Add plan + is_admin columns to users table (v2.7.3 migration).

Run inside nakama-db container:
    docker exec -i nakama-db psql -U nakama -d nakama < migrations/002_add_plan_admin.sql

Idempotent: uses IF NOT EXISTS so it's safe to re-run.
"""

-- Add plan column (default 'free')
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(32) NOT NULL DEFAULT 'free';

-- Add is_admin column (default false)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;

-- Backfill: any existing user with no plan value gets 'free'
UPDATE users SET plan = 'free' WHERE plan IS NULL OR plan = '';

-- Index for fast admin lookups (partial — only admins)
CREATE INDEX IF NOT EXISTS ix_users_is_admin ON users(is_admin) WHERE is_admin = true;

-- Grant shenyo1 unlimited plan + admin privileges + email confirmed
UPDATE users
SET plan = 'unlimited',
    is_admin = true,
    email_confirmed = true
WHERE username = 'shenyo1';

-- Verify
SELECT id, username, email, plan, is_admin, email_confirmed FROM users WHERE username = 'shenyo1';
