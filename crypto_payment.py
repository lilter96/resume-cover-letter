#!/usr/bin/env python3
"""
Cryptocurrency payment service for USDT TRC20 payments.

Author: Generated for ML project
Date: 2025-08-22
"""

import os
import json
import time
import uuid
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy.orm import Session

from models import PaymentOrder, CryptoWallet, PricingPlan, CreditTransaction, User
from dotenv import load_dotenv

load_dotenv()

class CryptoPaymentService:
    """Service for handling USDT TRC20 payments."""
    
    def __init__(self):
        # TRON API endpoints
        self.tron_api_url = "https://api.trongrid.io"
        self.tronscan_api_url = "https://apilist.tronscanapi.com/api"
        
        # Default wallet address (should be set in environment)
        self.default_wallet = os.getenv('USDT_TRC20_WALLET', 'TYASr5UV6HEcXatwdFQT4k7DgZuyDu1ZvH')
        
        # USDT TRC20 contract address
        self.usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
        # Pricing configuration
        self.credit_price_usd = float(os.getenv('CREDIT_PRICE_USD', '0.50'))  # $0.50 per credit
        
    def get_usdt_price(self) -> float:
        """Get current USDT price in USD (should be ~1.0)."""
        try:
            # Using CoinGecko API for USDT price
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return float(data.get('tether', {}).get('usd', 1.0))
        except Exception as e:
            print(f"Error fetching USDT price: {e}")
        
        return 1.0  # Fallback to 1 USD = 1 USDT
    
    def get_pricing_plans(self, db: Session) -> List[Dict]:
        """Get available pricing plans."""
        plans = db.query(PricingPlan).filter(PricingPlan.is_active == True).order_by(PricingPlan.sort_order).all()
        
        if not plans:
            # Create default plans if none exist
            default_plans = [
                {"name": "Starter", "credits": 10, "usd_price": 4.99, "bonus_credits": 0, "sort_order": 1},
                {"name": "Professional", "credits": 25, "usd_price": 9.99, "bonus_credits": 5, "sort_order": 2},
                {"name": "Enterprise", "credits": 50, "usd_price": 19.99, "bonus_credits": 15, "sort_order": 3},
                {"name": "Ultimate", "credits": 100, "usd_price": 34.99, "bonus_credits": 35, "sort_order": 4}
            ]
            
            for plan_data in default_plans:
                plan = PricingPlan(**plan_data)
                db.add(plan)
            
            db.commit()
            plans = db.query(PricingPlan).filter(PricingPlan.is_active == True).order_by(PricingPlan.sort_order).all()
        
        usdt_price = self.get_usdt_price()
        
        result = []
        for plan in plans:
            total_credits = plan.credits + plan.bonus_credits
            usdt_amount = round(plan.usd_price / usdt_price, 2)
            
            result.append({
                "id": plan.id,
                "name": plan.name,
                "credits": plan.credits,
                "bonus_credits": plan.bonus_credits,
                "total_credits": total_credits,
                "usd_price": plan.usd_price,
                "usdt_price": usdt_amount,
                "savings": f"{round((total_credits * self.credit_price_usd - plan.usd_price) / (total_credits * self.credit_price_usd) * 100)}%" if total_credits * self.credit_price_usd > plan.usd_price else "0%"
            })
        
        return result
    
    def create_payment_order(self, db: Session, user_id: str, plan_id: str) -> Dict:
        """Create a new payment order."""
        try:
            # Get pricing plan
            plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id, PricingPlan.is_active == True).first()
            if not plan:
                return {"success": False, "message": "Invalid pricing plan"}
            
            # Get wallet address
            wallet = db.query(CryptoWallet).filter(
                CryptoWallet.currency == "USDT",
                CryptoWallet.network == "TRC20",
                CryptoWallet.is_active == True
            ).first()
            
            if not wallet:
                # Create default wallet if none exists
                wallet = CryptoWallet(
                    currency="USDT",
                    network="TRC20",
                    address=self.default_wallet
                )
                db.add(wallet)
                db.commit()
            
            # Calculate amounts
            usdt_price = self.get_usdt_price()
            usdt_amount = round(plan.usd_price / usdt_price, 2)
            total_credits = plan.credits + plan.bonus_credits
            
            # Generate order ID
            order_id = f"ORDER_{int(time.time())}_{uuid.uuid4().hex[:8].upper()}"
            
            # Create payment order
            payment_order = PaymentOrder(
                user_id=user_id,
                order_id=order_id,
                credits_amount=total_credits,
                usdt_amount=usdt_amount,
                usd_amount=plan.usd_price,
                wallet_address=wallet.address,
                expires_at=datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
            )
            
            db.add(payment_order)
            db.commit()
            
            return {
                "success": True,
                "order": {
                    "order_id": order_id,
                    "credits_amount": total_credits,
                    "usdt_amount": usdt_amount,
                    "usd_amount": plan.usd_price,
                    "wallet_address": wallet.address,
                    "expires_at": payment_order.expires_at.isoformat(),
                    "plan_name": plan.name
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error creating payment order: {str(e)}"}
    
    def check_payment_status(self, db: Session, order_id: str) -> Dict:
        """Check if payment has been received for an order."""
        try:
            order = db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
            if not order:
                return {"success": False, "message": "Order not found"}
            
            if order.status == "paid":
                return {"success": True, "status": "paid", "payment_hash": order.payment_hash}
            
            # Check expiration with some tolerance
            current_time = datetime.utcnow()
            if order.status == "expired" or current_time > order.expires_at:
                if order.status != "expired":
                    order.status = "expired"
                    db.commit()
                return {"success": True, "status": "expired"}
            
            # Check for payments to the wallet address
            payments = self.get_recent_payments(order.wallet_address, order.usdt_amount, order.created_at)
            
            for payment in payments:
                if payment['amount'] >= order.usdt_amount:
                    # Payment found! Process it
                    return self.process_payment(db, order, payment['hash'])
            
            return {"success": True, "status": "pending"}
            
        except Exception as e:
            return {"success": False, "message": f"Error checking payment: {str(e)}"}
    
    def get_recent_payments(self, wallet_address: str, min_amount: float, since: datetime) -> List[Dict]:
        """Get recent USDT TRC20 payments to a wallet address."""
        try:
            # Convert datetime to timestamp
            since_timestamp = int(since.timestamp() * 1000)
            
            # Get transactions from TronScan API
            url = f"{self.tronscan_api_url}/token_trc20/transfers"
            params = {
                "contract_address": self.usdt_contract,
                "toAddress": wallet_address,
                "start_timestamp": since_timestamp,
                "limit": 50
            }
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code != 200:
                return []
            
            data = response.json()
            payments = []
            
            for tx in data.get('token_transfers', []):
                amount_raw = int(tx.get('quant', 0))
                amount_usdt = amount_raw / 1000000  # USDT has 6 decimals
                
                if amount_usdt >= min_amount:
                    payments.append({
                        'hash': tx.get('transaction_id'),
                        'amount': amount_usdt,
                        'timestamp': tx.get('block_ts'),
                        'from_address': tx.get('from_address')
                    })
            
            return payments
            
        except Exception as e:
            print(f"Error fetching payments: {e}")
            return []
    
    def process_payment(self, db: Session, order: PaymentOrder, payment_hash: str) -> Dict:
        """Process a confirmed payment."""
        try:
            # Update order status
            order.status = "paid"
            order.payment_hash = payment_hash
            order.paid_at = datetime.utcnow()
            
            # Add credits to user
            user = db.query(User).filter(User.id == order.user_id).first()
            if user:
                user.credits += order.credits_amount
                
                # Create credit transaction record
                transaction = CreditTransaction(
                    user_id=order.user_id,
                    transaction_type="purchase",
                    credits_amount=order.credits_amount,
                    description=f"Credit purchase - Order {order.order_id}",
                    payment_method="USDT_TRC20",
                    payment_id=payment_hash,
                    amount_paid=order.usdt_amount,
                    currency="USDT"
                )
                db.add(transaction)
            
            db.commit()
            
            return {
                "success": True,
                "status": "paid",
                "payment_hash": payment_hash,
                "credits_added": order.credits_amount
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error processing payment: {str(e)}"}
    
    def get_order_status(self, db: Session, order_id: str) -> Dict:
        """Get order status and details."""
        try:
            order = db.query(PaymentOrder).filter(PaymentOrder.order_id == order_id).first()
            if not order:
                return {"success": False, "message": "Order not found"}
            
            # Check if expired
            if order.status == "pending" and datetime.utcnow() > order.expires_at:
                order.status = "expired"
                db.commit()
            
            current_time = datetime.utcnow()
            return {
                "success": True,
                "order": {
                    "order_id": order.order_id,
                    "status": order.status,
                    "credits_amount": order.credits_amount,
                    "usdt_amount": order.usdt_amount,
                    "usd_amount": order.usd_amount,
                    "wallet_address": order.wallet_address,
                    "payment_hash": order.payment_hash,
                    "expires_at": order.expires_at.isoformat(),
                    "created_at": order.created_at.isoformat(),
                    "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                    "time_remaining": max(0, int((order.expires_at - current_time).total_seconds())) if order.status == "pending" else 0
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error getting order status: {str(e)}"}