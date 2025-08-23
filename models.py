#!/usr/bin/env python3
"""
Database models for Resume Generator application.

Author: Generated for ML project
Date: 2025-08-22
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """User model for authentication and credits management."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)  # Nullable for OAuth users
    name = Column(String, nullable=False)
    phone = Column(String)
    location = Column(String)
    experience_years = Column(String)
    current_position = Column(String)
    key_skills = Column(Text)  # JSON string
    education = Column(String)
    achievements = Column(Text)
    github = Column(String)
    
    # OAuth fields
    google_id = Column(String, unique=True, nullable=True)  # Google OAuth ID
    profile_picture = Column(String, nullable=True)  # Profile picture URL
    auth_provider = Column(String, default='local')  # 'local', 'google'
    
    # Credits system
    credits = Column(Integer, default=3)  # Free credits for new users
    total_generations = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)  # Admin users have unlimited generations

class Generation(Base):
    """Track document generations for users."""
    __tablename__ = "generations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    
    # Vacancy information
    vacancy_url = Column(String, nullable=False)
    vacancy_title = Column(String)
    company = Column(String)
    vacancy_data = Column(Text)  # JSON string of full vacancy data
    
    # Generated documents
    resume_text = Column(Text)
    cover_letter_text = Column(Text)
    
    # Generation details
    language = Column(String, default='en')  # 'en' or 'ru'
    credits_used = Column(Integer, default=1)
    generation_time = Column(Float)  # Time taken in seconds
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # File paths
    folder_path = Column(String)

class CreditTransaction(Base):
    """Track credit purchases and usage."""
    __tablename__ = "credit_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    
    # Transaction details
    transaction_type = Column(String, nullable=False)  # 'purchase', 'usage', 'bonus'
    credits_amount = Column(Integer, nullable=False)  # Positive for add, negative for use
    description = Column(String)
    
    # Payment details (for purchases)
    payment_method = Column(String)
    payment_id = Column(String)
    amount_paid = Column(Float)
    currency = Column(String, default='USD')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

class PaymentOrder(Base):
    """Track cryptocurrency payment orders."""
    __tablename__ = "payment_orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    order_id = Column(String, unique=True, nullable=False, index=True)
    
    # Purchase details
    credits_amount = Column(Integer, nullable=False)  # Number of credits to purchase
    usdt_amount = Column(Float, nullable=False)  # USDT amount to pay
    usd_amount = Column(Float, nullable=False)  # USD equivalent at time of order
    
    # Payment details
    wallet_address = Column(String, nullable=False)  # Our USDT TRC20 wallet
    status = Column(String, default="pending")  # pending, paid, expired, cancelled
    payment_hash = Column(String)  # Transaction hash when paid
    
    # Timestamps
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime)

class StripePaymentOrder(Base):
    """Track Stripe payment orders."""
    __tablename__ = "stripe_payment_orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    order_id = Column(String, unique=True, nullable=False, index=True)
    
    # Purchase details
    credits_amount = Column(Integer, nullable=False)  # Number of credits to purchase
    usd_amount = Column(Float, nullable=False)  # USD amount to pay
    
    # Stripe details
    stripe_payment_intent_id = Column(String, unique=True, nullable=False)
    stripe_client_secret = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, succeeded, failed, cancelled
    
    # Payment details
    payment_method_id = Column(String)  # Stripe payment method ID
    receipt_url = Column(String)  # Stripe receipt URL
    
    # Timestamps
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime)

class CryptoWallet(Base):
    """Store cryptocurrency wallet addresses for payments."""
    __tablename__ = "crypto_wallets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    currency = Column(String, nullable=False)  # "USDT"
    network = Column(String, nullable=False)  # "TRC20"
    address = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PricingPlan(Base):
    """Store pricing plans for credit purchases."""
    __tablename__ = "pricing_plans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # "Starter", "Professional", "Enterprise"
    credits = Column(Integer, nullable=False)  # Number of credits
    usd_price = Column(Float, nullable=False)  # Price in USD
    bonus_credits = Column(Integer, default=0)  # Bonus credits for this plan
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
DATABASE_URL = "sqlite:///./resume_generator.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()