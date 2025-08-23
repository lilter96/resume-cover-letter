#!/usr/bin/env python3
"""
Create admin user with infinite generations.

Author: Generated for ML project
Date: 2025-08-23
"""

from models import create_tables, get_db, User
from auth import AuthManager, UserManager
import os
from dotenv import load_dotenv

load_dotenv()

def create_admin_user():
    """Create an admin user with infinite generations."""
    
    # Initialize services
    auth_manager = AuthManager(secret_key=os.getenv('SECRET_KEY', 'your-secret-key-here'))
    user_manager = UserManager(auth_manager)
    
    # Create database tables if they don't exist
    create_tables()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Admin user details
        admin_email = "admin@resumegen.pro"
        admin_password = "admin123"
        admin_name = "Admin User"
        
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            print(f"✅ Admin user already exists: {admin_email}")
            if not existing_admin.is_admin:
                existing_admin.is_admin = True
                existing_admin.credits = 999999  # Set high number for display
                db.commit()
                print("✅ Updated existing user to admin status")
            return existing_admin
        
        # Create admin user
        password_hash = auth_manager.hash_password(admin_password)
        admin_user = User(
            email=admin_email,
            password_hash=password_hash,
            name=admin_name,
            phone="+1-555-ADMIN",
            location="Admin Location",
            experience_years="10+",
            current_position="System Administrator",
            education="Computer Science",
            achievements="Full system access and unlimited generations",
            github="https://github.com/admin",
            credits=999999,  # High number for display (actual logic uses is_admin flag)
            is_admin=True,
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("🎉 Admin user created successfully!")
        print(f"📧 Email: {admin_email}")
        print(f"🔑 Password: {admin_password}")
        print(f"👤 Name: {admin_name}")
        print(f"⚡ Credits: ∞ (Unlimited)")
        print(f"🔧 Admin Status: True")
        
        return admin_user
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Creating Admin User for Resume Generator")
    print("=" * 50)
    
    admin = create_admin_user()
    
    if admin:
        print("\n✅ Admin user setup complete!")
        print("\n📝 Login Instructions:")
        print("1. Go to http://localhost:8000/login")
        print("2. Use email: admin@resumegen.pro")
        print("3. Use password: admin123")
        print("4. Enjoy unlimited generations! ∞")
    else:
        print("\n❌ Failed to create admin user")