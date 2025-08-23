#!/usr/bin/env python3
"""
Migrate database to add admin functionality.

Author: Generated for ML project
Date: 2025-08-23
"""

import sqlite3
import os
from models import create_tables

def migrate_database():
    """Add is_admin column to existing database."""
    
    db_path = "resume_generator.db"
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if is_admin column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_admin' not in columns:
            print("🔄 Adding is_admin column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
            conn.commit()
            print("✅ Successfully added is_admin column")
        else:
            print("✅ is_admin column already exists")
        
        conn.close()
        
        # Recreate tables to ensure all new tables exist
        print("🔄 Creating any missing tables...")
        create_tables()
        print("✅ Database migration complete!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error migrating database: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Migrating Database for Admin Functionality")
    print("=" * 50)
    
    success = migrate_database()
    
    if success:
        print("\n✅ Database migration successful!")
        print("📝 You can now create admin users")
    else:
        print("\n❌ Database migration failed")