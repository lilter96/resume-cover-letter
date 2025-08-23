#!/usr/bin/env python3
"""
Database migration script to add Google OAuth fields to existing users table.
"""

import sqlite3
import os

def migrate_database():
    """Add OAuth fields to the users table."""
    db_path = "resume_generator.db"
    
    if not os.path.exists(db_path):
        print("Database file not found. Creating new database with OAuth support.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if OAuth columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        oauth_columns = ['google_id', 'profile_picture', 'auth_provider']
        missing_columns = [col for col in oauth_columns if col not in columns]
        
        if not missing_columns:
            print("✅ OAuth columns already exist in the database.")
            return
        
        print(f"📝 Adding missing OAuth columns: {missing_columns}")
        
        # Add missing OAuth columns
        if 'google_id' in missing_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
            print("✅ Added google_id column")
        
        if 'profile_picture' in missing_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN profile_picture TEXT")
            print("✅ Added profile_picture column")
        
        if 'auth_provider' in missing_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'")
            print("✅ Added auth_provider column")
        
        # Update existing users to have 'local' auth provider
        cursor.execute("UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL")
        
        # Make password_hash nullable for OAuth users (SQLite doesn't support modifying column constraints directly)
        # This is handled in the model definition
        
        # Create unique index on google_id
        try:
            cursor.execute("CREATE UNIQUE INDEX idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL")
            print("✅ Created unique index on google_id")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                print("ℹ️ Unique index on google_id already exists")
            else:
                raise
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()