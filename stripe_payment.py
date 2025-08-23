#!/usr/bin/env python3
"""
Stripe payment service for production-ready credit card payments.

Author: Generated for ML project
Date: 2025-08-22
"""

import os
import json
import time
import uuid
import stripe
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from sqlalchemy.orm import Session

from models import StripePaymentOrder, PricingPlan, CreditTransaction, User
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StripePaymentService:
    """Service for handling Stripe credit card payments."""
    
    def __init__(self):
        # Initialize Stripe with API keys
        self.stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
        self.stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        self.stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if not self.stripe_secret_key:
            raise ValueError("STRIPE_SECRET_KEY environment variable is required")
        
        stripe.api_key = self.stripe_secret_key
        
        # Payment configuration
        self.currency = 'usd'
        self.payment_method_types = ['card']
        self.automatic_payment_methods = {'enabled': True}
        
        # Business information for receipts
        self.business_name = os.getenv('BUSINESS_NAME', 'Resume Generator Pro')
        self.business_url = os.getenv('BUSINESS_URL', 'https://resumegen.pro')
        self.support_email = os.getenv('SUPPORT_EMAIL', 'support@resumegen.pro')
        
    def get_pricing_plans(self, db: Session) -> List[Dict]:
        """Get available pricing plans for Stripe payments."""
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
        
        result = []
        for plan in plans:
            total_credits = plan.credits + plan.bonus_credits
            
            result.append({
                "id": plan.id,
                "name": plan.name,
                "credits": plan.credits,
                "bonus_credits": plan.bonus_credits,
                "total_credits": total_credits,
                "usd_price": plan.usd_price,
                "price_per_credit": round(plan.usd_price / total_credits, 2),
                "savings_percent": round((total_credits * 0.50 - plan.usd_price) / (total_credits * 0.50) * 100) if total_credits * 0.50 > plan.usd_price else 0
            })
        
        return result
    
    def create_payment_intent(self, db: Session, user_id: str, plan_id: str) -> Dict:
        """Create a Stripe Payment Intent for a credit purchase."""
        try:
            # Get pricing plan
            plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id, PricingPlan.is_active == True).first()
            if not plan:
                return {"success": False, "message": "Invalid pricing plan"}
            
            # Get user for metadata
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Calculate amounts
            total_credits = plan.credits + plan.bonus_credits
            amount_cents = int(plan.usd_price * 100)  # Stripe uses cents
            
            # Generate order ID
            order_id = f"STRIPE_{int(time.time())}_{uuid.uuid4().hex[:8].upper()}"
            
            # Create Stripe Payment Intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=self.currency,
                payment_method_types=self.payment_method_types,
                automatic_payment_methods=self.automatic_payment_methods,
                metadata={
                    'order_id': order_id,
                    'user_id': user_id,
                    'user_email': user.email,
                    'plan_name': plan.name,
                    'credits_amount': total_credits,
                    'business_name': self.business_name
                },
                description=f"{plan.name} Plan - {total_credits} Credits",
                receipt_email=user.email,
                statement_descriptor=self.business_name[:22],  # Max 22 chars for statement
            )
            
            # Create payment order in database
            stripe_order = StripePaymentOrder(
                user_id=user_id,
                order_id=order_id,
                credits_amount=total_credits,
                usd_amount=plan.usd_price,
                stripe_payment_intent_id=payment_intent.id,
                stripe_client_secret=payment_intent.client_secret,
                expires_at=datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
            )
            
            db.add(stripe_order)
            db.commit()
            
            logger.info(f"Created Stripe payment intent {payment_intent.id} for user {user_id}")
            
            return {
                "success": True,
                "order": {
                    "order_id": order_id,
                    "credits_amount": total_credits,
                    "usd_amount": plan.usd_price,
                    "client_secret": payment_intent.client_secret,
                    "payment_intent_id": payment_intent.id,
                    "expires_at": stripe_order.expires_at.isoformat(),
                    "plan_name": plan.name
                },
                "stripe_publishable_key": self.stripe_publishable_key
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            return {"success": False, "message": f"Payment service error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error creating Stripe payment intent: {str(e)}")
            return {"success": False, "message": f"Error creating payment: {str(e)}"}
    
    def handle_webhook(self, payload: bytes, signature: str, db: Session) -> Dict:
        """Handle Stripe webhook events."""
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.stripe_webhook_secret
            )
            
            logger.info(f"Received Stripe webhook: {event['type']}")
            
            # Handle different event types
            if event['type'] == 'payment_intent.succeeded':
                return self._handle_payment_succeeded(event['data']['object'], db)
            elif event['type'] == 'payment_intent.payment_failed':
                return self._handle_payment_failed(event['data']['object'], db)
            elif event['type'] == 'payment_intent.canceled':
                return self._handle_payment_canceled(event['data']['object'], db)
            else:
                logger.info(f"Unhandled webhook event type: {event['type']}")
                return {"success": True, "message": "Event received but not processed"}
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return {"success": False, "message": "Invalid signature"}
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return {"success": False, "message": f"Webhook error: {str(e)}"}
    
    def _handle_payment_succeeded(self, payment_intent: Dict, db: Session) -> Dict:
        """Handle successful payment."""
        try:
            order_id = payment_intent['metadata'].get('order_id')
            if not order_id:
                logger.error("No order_id in payment_intent metadata")
                return {"success": False, "message": "Missing order_id"}
            
            # Find the order
            order = db.query(StripePaymentOrder).filter(
                StripePaymentOrder.stripe_payment_intent_id == payment_intent['id']
            ).first()
            
            if not order:
                logger.error(f"Order not found for payment_intent {payment_intent['id']}")
                return {"success": False, "message": "Order not found"}
            
            if order.status == "succeeded":
                logger.info(f"Order {order_id} already processed")
                return {"success": True, "message": "Already processed"}
            
            # Update order status
            order.status = "succeeded"
            order.paid_at = datetime.utcnow()
            order.receipt_url = payment_intent.get('charges', {}).get('data', [{}])[0].get('receipt_url')
            
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
                    payment_method="STRIPE",
                    payment_id=payment_intent['id'],
                    amount_paid=order.usd_amount,
                    currency="USD"
                )
                db.add(transaction)
                
                logger.info(f"Added {order.credits_amount} credits to user {user.email}")
            
            db.commit()
            
            return {
                "success": True,
                "message": "Payment processed successfully",
                "credits_added": order.credits_amount
            }
            
        except Exception as e:
            logger.error(f"Error processing successful payment: {str(e)}")
            db.rollback()
            return {"success": False, "message": f"Error processing payment: {str(e)}"}
    
    def _handle_payment_failed(self, payment_intent: Dict, db: Session) -> Dict:
        """Handle failed payment."""
        try:
            order = db.query(StripePaymentOrder).filter(
                StripePaymentOrder.stripe_payment_intent_id == payment_intent['id']
            ).first()
            
            if order:
                order.status = "failed"
                db.commit()
                logger.info(f"Marked order {order.order_id} as failed")
            
            return {"success": True, "message": "Payment failure recorded"}
            
        except Exception as e:
            logger.error(f"Error handling payment failure: {str(e)}")
            return {"success": False, "message": f"Error handling failure: {str(e)}"}
    
    def _handle_payment_canceled(self, payment_intent: Dict, db: Session) -> Dict:
        """Handle canceled payment."""
        try:
            order = db.query(StripePaymentOrder).filter(
                StripePaymentOrder.stripe_payment_intent_id == payment_intent['id']
            ).first()
            
            if order:
                order.status = "cancelled"
                db.commit()
                logger.info(f"Marked order {order.order_id} as cancelled")
            
            return {"success": True, "message": "Payment cancellation recorded"}
            
        except Exception as e:
            logger.error(f"Error handling payment cancellation: {str(e)}")
            return {"success": False, "message": f"Error handling cancellation: {str(e)}"}
    
    def get_payment_status(self, db: Session, order_id: str) -> Dict:
        """Get payment status for an order."""
        try:
            order = db.query(StripePaymentOrder).filter(StripePaymentOrder.order_id == order_id).first()
            if not order:
                return {"success": False, "message": "Order not found"}
            
            # Check if expired
            if order.status == "pending" and datetime.utcnow() > order.expires_at:
                order.status = "expired"
                db.commit()
            
            # Get latest status from Stripe
            try:
                payment_intent = stripe.PaymentIntent.retrieve(order.stripe_payment_intent_id)
                stripe_status = payment_intent.status
                
                # Update local status if needed
                if stripe_status == "succeeded" and order.status != "succeeded":
                    self._handle_payment_succeeded(payment_intent, db)
                elif stripe_status == "canceled" and order.status != "cancelled":
                    order.status = "cancelled"
                    db.commit()
                elif stripe_status in ["requires_payment_method", "requires_confirmation"] and order.status == "pending":
                    order.status = "processing"
                    db.commit()
                    
            except stripe.error.StripeError as e:
                logger.error(f"Error retrieving payment intent from Stripe: {str(e)}")
            
            current_time = datetime.utcnow()
            return {
                "success": True,
                "order": {
                    "order_id": order.order_id,
                    "status": order.status,
                    "credits_amount": order.credits_amount,
                    "usd_amount": order.usd_amount,
                    "payment_intent_id": order.stripe_payment_intent_id,
                    "receipt_url": order.receipt_url,
                    "expires_at": order.expires_at.isoformat(),
                    "created_at": order.created_at.isoformat(),
                    "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                    "time_remaining": max(0, int((order.expires_at - current_time).total_seconds())) if order.status == "pending" else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            return {"success": False, "message": f"Error getting payment status: {str(e)}"}
    
    def cancel_payment(self, db: Session, order_id: str, user_id: str) -> Dict:
        """Cancel a pending payment."""
        try:
            order = db.query(StripePaymentOrder).filter(
                StripePaymentOrder.order_id == order_id,
                StripePaymentOrder.user_id == user_id
            ).first()
            
            if not order:
                return {"success": False, "message": "Order not found"}
            
            if order.status != "pending":
                return {"success": False, "message": f"Cannot cancel order with status: {order.status}"}
            
            # Cancel the payment intent in Stripe
            try:
                stripe.PaymentIntent.cancel(order.stripe_payment_intent_id)
                order.status = "cancelled"
                db.commit()
                
                logger.info(f"Cancelled payment intent {order.stripe_payment_intent_id}")
                return {"success": True, "message": "Payment cancelled successfully"}
                
            except stripe.error.StripeError as e:
                logger.error(f"Error cancelling Stripe payment intent: {str(e)}")
                return {"success": False, "message": f"Error cancelling payment: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Error cancelling payment: {str(e)}")
            return {"success": False, "message": f"Error cancelling payment: {str(e)}"}
    
    def get_user_payment_history(self, db: Session, user_id: str, limit: int = 10) -> Dict:
        """Get user's payment history."""
        try:
            orders = db.query(StripePaymentOrder).filter(
                StripePaymentOrder.user_id == user_id
            ).order_by(StripePaymentOrder.created_at.desc()).limit(limit).all()
            
            history = []
            for order in orders:
                history.append({
                    "order_id": order.order_id,
                    "status": order.status,
                    "credits_amount": order.credits_amount,
                    "usd_amount": order.usd_amount,
                    "created_at": order.created_at.isoformat(),
                    "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                    "receipt_url": order.receipt_url
                })
            
            return {"success": True, "history": history}
            
        except Exception as e:
            logger.error(f"Error getting payment history: {str(e)}")
            return {"success": False, "message": f"Error getting payment history: {str(e)}"}