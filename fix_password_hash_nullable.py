#!/usr/bin/env python3
"""
Fix password_hash column to allow NULL values for OAuth users.
"""

import sqlite3
import os

def fix_password_hash_nullable():
    """Make password_hash column nullable for OAuth users."""
    db_path = "resume_generator.db"
    
    if not os.path.exists(db_path):
        print("Database file not found.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔧 Making password_hash column nullable for OAuth users...")
        
        # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
        # First, get the current table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        # Create new table with nullable password_hash
        cursor.execute("""
        CREATE TABLE users_new (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,  -- Now nullable
            name TEXT NOT NULL,
            phone TEXT,
            location TEXT,
            experience_years TEXT,
            current_position TEXT,
            key_skills TEXT,
            education TEXT,
            achievements TEXT,
            github TEXT,
            google_id TEXT UNIQUE,
            profile_picture TEXT,
            auth_provider TEXT DEFAULT 'local',
            credits INTEGER DEFAULT 3,
            total_generations INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME,
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 0,
            is_admin BOOLEAN DEFAULT 0
        )
        """)
        
        # Copy data from old table to new table
        cursor.execute("""
        INSERT INTO users_new 
        SELECT id, email, password_hash, name, phone, location, experience_years, 
               current_position, key_skills, education, achievements, github,
               google_id, profile_picture, auth_provider, credits, total_generations,
               created_at, updated_at, last_login, is_active, is_verified, is_admin
        FROM users
        """)
        
        # Drop old table and rename new table
        cursor.execute("DROP TABLE users")
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        
        # Recreate indexes
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL")
        
        conn.commit()
        print("✅ Successfully made password_hash nullable!")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_password_hash_nullable()