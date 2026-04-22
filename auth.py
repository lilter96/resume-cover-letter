#!/usr/bin/env python3
"""
Authentication and user management for Resume Generator.

Author: Generated for ML project
Date: 2025-08-22
"""

import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from models import User, CreditTransaction, get_db
import json

class AuthManager:
    """Handle user authentication and session management."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24 * 7  # 7 days
    
    def hash_password(self, password: str) -> str:
        """Hash password with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        try:
            salt, stored_hash = hashed.split(':')
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return password_hash.hex() == stored_hash
        except:
            return False
    
    def create_access_token(self, user_id: str) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return user_id."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload.get("user_id")
        except jwt.ExpiredSignatureError:
            return None
        except (jwt.InvalidTokenError, jwt.InvalidSignatureError, jwt.DecodeError):
            return None

class UserManager:
    """Handle user operations and credits."""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth = auth_manager
    
    def register_user(self, db: Session, email: str, password: str, name: str,
                     phone: str = None, location: str = None) -> Dict:
        """Register a new user."""
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return {"success": False, "message": "Email already registered"}
        
        # Create new user
        password_hash = self.auth.hash_password(password)
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            phone=phone,
            location=location,
            credits=3,  # Free credits for new users
            auth_provider='local'
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create welcome credit transaction
        credit_transaction = CreditTransaction(
            user_id=user.id,
            transaction_type="bonus",
            credits_amount=3,
            description="Welcome bonus - 3 free generations"
        )
        db.add(credit_transaction)
        db.commit()
        
        # Create access token
        token = self.auth.create_access_token(user.id)
        
        return {
            "success": True,
            "message": "User registered successfully",
            "token": token,
            "user": self.user_to_dict(user)
        }
    
    def register_or_login_google_user(self, db: Session, google_user_data: Dict) -> Dict:
        """Register or login user via Google OAuth."""
        email = google_user_data.get('email')
        google_id = google_user_data.get('google_id')
        name = google_user_data.get('name')
        picture = google_user_data.get('picture')
        verified_email = google_user_data.get('verified_email', False)
        
        if not email or not google_id:
            return {"success": False, "message": "Invalid Google user data"}
        
        # Check if user exists by email or Google ID
        existing_user = db.query(User).filter(
            (User.email == email) | (User.google_id == google_id)
        ).first()
        
        if existing_user:
            # Update existing user with Google data if needed
            if not existing_user.google_id:
                existing_user.google_id = google_id
                existing_user.auth_provider = 'google'
            
            if picture and not existing_user.profile_picture:
                existing_user.profile_picture = picture
            
            if verified_email:
                existing_user.is_verified = True
            
            # Update last login
            existing_user.last_login = datetime.utcnow()
            db.commit()
            
            # Create access token
            token = self.auth.create_access_token(existing_user.id)
            
            return {
                "success": True,
                "message": "Google login successful",
                "token": token,
                "user": self.user_to_dict(existing_user)
            }
        
        else:
            # Create new user from Google data
            user = User(
                email=email,
                name=name,
                google_id=google_id,
                profile_picture=picture,
                auth_provider='google',
                is_verified=verified_email,
                credits=3  # Free credits for new users
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Create welcome credit transaction
            credit_transaction = CreditTransaction(
                user_id=user.id,
                transaction_type="bonus",
                credits_amount=3,
                description="Welcome bonus - 3 free generations (Google signup)"
            )
            db.add(credit_transaction)
            db.commit()
            
            # Create access token
            token = self.auth.create_access_token(user.id)
            
            return {
                "success": True,
                "message": "Google account registered successfully",
                "token": token,
                "user": self.user_to_dict(user)
            }
    
    def register_or_login_telegram_user(self, db: Session, telegram_user_data: Dict) -> Dict:
        """Register or login user via Telegram Login Widget."""
        telegram_id = telegram_user_data.get('telegram_id')
        name = telegram_user_data.get('name')
        email = telegram_user_data.get('email')  # synthetic: {id}@telegram.user
        photo_url = telegram_user_data.get('photo_url')
        telegram_username = telegram_user_data.get('telegram_username')

        if not telegram_id:
            return {"success": False, "message": "Invalid Telegram user data"}

        existing_user = db.query(User).filter(
            (User.telegram_id == telegram_id) | (User.email == email)
        ).first()

        if existing_user:
            if not existing_user.telegram_id:
                existing_user.telegram_id = telegram_id
                existing_user.auth_provider = 'telegram'
            if telegram_username:
                existing_user.telegram_username = telegram_username
            if photo_url and not existing_user.profile_picture:
                existing_user.profile_picture = photo_url
            existing_user.last_login = datetime.utcnow()
            db.commit()

            token = self.auth.create_access_token(existing_user.id)
            return {
                "success": True,
                "message": "Telegram login successful",
                "token": token,
                "user": self.user_to_dict(existing_user)
            }

        user = User(
            email=email,
            name=name,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            profile_picture=photo_url,
            auth_provider='telegram',
            is_verified=True,
            credits=3
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        credit_transaction = CreditTransaction(
            user_id=user.id,
            transaction_type="bonus",
            credits_amount=3,
            description="Welcome bonus - 3 free generations (Telegram signup)"
        )
        db.add(credit_transaction)
        db.commit()

        token = self.auth.create_access_token(user.id)
        return {
            "success": True,
            "message": "Telegram account registered successfully",
            "token": token,
            "user": self.user_to_dict(user)
        }

    def login_user(self, db: Session, email: str, password: str) -> Dict:
        """Login user."""
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return {"success": False, "message": "Invalid email or password"}
        
        # Check if user has a password (local auth) or is OAuth user
        if user.password_hash is None:
            return {"success": False, "message": "This account uses Google login. Please use 'Continue with Google' button."}
        
        if not self.auth.verify_password(password, user.password_hash):
            return {"success": False, "message": "Invalid email or password"}
        
        if not user.is_active:
            return {"success": False, "message": "Account is deactivated"}
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create access token
        token = self.auth.create_access_token(user.id)
        
        return {
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": self.user_to_dict(user)
        }
    
    def get_user_by_token(self, db: Session, token: str) -> Optional[User]:
        """Get user by JWT token."""
        user_id = self.auth.verify_token(token)
        if not user_id:
            return None
        
        return db.query(User).filter(User.id == user_id).first()
    
    def update_user_profile(self, db: Session, user_id: str, profile_data: Dict) -> Dict:
        """Update user profile."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        # Update allowed fields
        allowed_fields = [
            'name', 'phone', 'location', 'experience_years', 'current_position',
            'education', 'achievements', 'github'
        ]
        
        for field in allowed_fields:
            if field in profile_data:
                if field == 'key_skills' and isinstance(profile_data[field], list):
                    setattr(user, field, json.dumps(profile_data[field]))
                else:
                    setattr(user, field, profile_data[field])
        
        user.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": self.user_to_dict(user)
        }
    
    def use_credits(self, db: Session, user_id: str, credits_amount: int = 1,
                   description: str = "Document generation") -> Dict:
        """Use user credits."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        # Admin users have unlimited generations
        if user.is_admin:
            user.total_generations += 1
            db.commit()
            return {
                "success": True,
                "message": f"Admin generation (unlimited)",
                "remaining_credits": "∞"
            }
        
        if user.credits < credits_amount:
            return {"success": False, "message": "Insufficient credits"}
        
        # Deduct credits for regular users
        user.credits -= credits_amount
        user.total_generations += 1
        
        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type="usage",
            credits_amount=-credits_amount,
            description=description
        )
        
        db.add(transaction)
        db.commit()
        
        return {
            "success": True,
            "message": f"Used {credits_amount} credits",
            "remaining_credits": user.credits
        }
    
    def add_credits(self, db: Session, user_id: str, credits_amount: int, 
                   payment_method: str = None, payment_id: str = None, 
                   amount_paid: float = None) -> Dict:
        """Add credits to user account."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        # Add credits
        user.credits += credits_amount
        
        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type="purchase",
            credits_amount=credits_amount,
            description=f"Purchased {credits_amount} credits",
            payment_method=payment_method,
            payment_id=payment_id,
            amount_paid=amount_paid
        )
        
        db.add(transaction)
        db.commit()
        
        return {
            "success": True,
            "message": f"Added {credits_amount} credits",
            "total_credits": user.credits
        }
    
    def user_to_dict(self, user: User) -> Dict:
        """Convert user object to dictionary."""
        key_skills = []
        if user.key_skills:
            try:
                key_skills = json.loads(user.key_skills)
            except:
                key_skills = []
        
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "location": user.location,
            "experience_years": user.experience_years,
            "current_position": user.current_position,
            "key_skills": key_skills,
            "education": user.education,
            "achievements": user.achievements,
            "github": user.github,
            "profile_picture": getattr(user, 'profile_picture', None),
            "auth_provider": getattr(user, 'auth_provider', 'local'),
            "is_verified": getattr(user, 'is_verified', False),
            "credits": "∞" if user.is_admin else user.credits,
            "is_admin": user.is_admin,
            "total_generations": user.total_generations,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }