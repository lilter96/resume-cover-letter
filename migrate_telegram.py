#!/usr/bin/env python3
"""Migration: add telegram_id and telegram_username columns to users table."""

import sqlite3
import os

DB_PATH = os.getenv('DATABASE_URL', './resume_generator.db').replace('sqlite:///', '')


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    existing = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}

    if 'telegram_id' not in existing:
        cursor.execute("ALTER TABLE users ADD COLUMN telegram_id TEXT")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_telegram_id ON users (telegram_id)")
        print("Added telegram_id column")
    else:
        print("telegram_id column already exists")

    if 'telegram_username' not in existing:
        cursor.execute("ALTER TABLE users ADD COLUMN telegram_username TEXT")
        print("Added telegram_username column")
    else:
        print("telegram_username column already exists")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == '__main__':
    migrate()
