#!/usr/bin/env python3
"""
Production Metrics Collection for Resume Generator

Comprehensive metrics collection including:
- LLM usage and costs
- Daily Active Users (DAU)
- Revenue tracking
- Performance metrics
- Error tracking
- Business KPIs

Author: Generated for ML project
Date: 2025-08-23
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from models import User, Generation, CreditTransaction, PaymentOrder, StripePaymentOrder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus Metrics
# =================

# Application Info
app_info = Info('resume_generator_app', 'Resume Generator Application Information')
app_info.info({
    'version': '2.0.0',
    'environment': 'production',
    'service': 'resume_generator'
})

# User Metrics
total_users = Gauge('resume_generator_users_total', 'Total number of registered users')
active_users_daily = Gauge('resume_generator_users_active_daily', 'Daily active users')
active_users_weekly = Gauge('resume_generator_users_active_weekly', 'Weekly active users')
active_users_monthly = Gauge('resume_generator_users_active_monthly', 'Monthly active users')
new_users_daily = Gauge('resume_generator_users_new_daily', 'New users registered today')

# Generation Metrics
generations_total = Counter('resume_generator_generations_total', 'Total document generations', ['user_type', 'status'])
generations_daily = Gauge('resume_generator_generations_daily', 'Daily document generations')
generation_duration = Histogram('resume_generator_generation_duration_seconds', 'Time taken to generate documents')

# LLM Usage Metrics
llm_requests_total = Counter('resume_generator_llm_requests_total', 'Total LLM API requests', ['model', 'type', 'status'])
llm_tokens_total = Counter('resume_generator_llm_tokens_total', 'Total LLM tokens used', ['model', 'type'])
llm_cost_total = Counter('resume_generator_llm_cost_usd_total', 'Total LLM costs in USD', ['model', 'type'])
llm_response_time = Histogram('resume_generator_llm_response_time_seconds', 'LLM API response time', ['model', 'type'])

# Credit System Metrics
credits_issued_total = Counter('resume_generator_credits_issued_total', 'Total credits issued', ['source'])
credits_used_total = Counter('resume_generator_credits_used_total', 'Total credits used', ['user_type'])
credits_balance_total = Gauge('resume_generator_credits_balance_total', 'Total credits balance across all users')

# Payment Metrics
revenue_total = Counter('resume_generator_revenue_usd_total', 'Total revenue in USD', ['payment_method'])
payments_total = Counter('resume_generator_payments_total', 'Total payments', ['payment_method', 'status'])
payment_processing_time = Histogram('resume_generator_payment_processing_seconds', 'Payment processing time', ['payment_method'])

# Error Metrics
errors_total = Counter('resume_generator_errors_total', 'Total application errors', ['type', 'endpoint'])
http_requests_total = Counter('resume_generator_http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
http_request_duration = Histogram('resume_generator_http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# Business KPIs
conversion_rate = Gauge('resume_generator_conversion_rate', 'User to paying customer conversion rate')
average_revenue_per_user = Gauge('resume_generator_arpu_usd', 'Average revenue per user in USD')
customer_lifetime_value = Gauge('resume_generator_clv_usd', 'Customer lifetime value in USD')

@dataclass
class MetricsSnapshot:
    """Snapshot of current metrics for reporting"""
    timestamp: datetime
    total_users: int
    dau: int
    wau: int
    mau: int
    total_generations: int
    daily_generations: int
    total_revenue: float
    daily_revenue: float
    llm_costs: float
    daily_llm_costs: float
    conversion_rate: float
    arpu: float

class MetricsCollector:
    """Centralized metrics collection and reporting"""
    
    def __init__(self):
        self.start_time = time.time()
        logger.info("Metrics collector initialized")
    
    def collect_all_metrics(self, db: Session) -> MetricsSnapshot:
        """Collect all metrics and update Prometheus gauges"""
        try:
            now = datetime.utcnow()
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # User Metrics
            total_users_count = db.query(User).count()
            total_users.set(total_users_count)
            
            # Daily Active Users (users who generated documents today)
            dau_count = db.query(func.count(func.distinct(Generation.user_id))).filter(
                func.date(Generation.created_at) == today
            ).scalar() or 0
            active_users_daily.set(dau_count)
            
            # Weekly Active Users
            wau_count = db.query(func.count(func.distinct(Generation.user_id))).filter(
                Generation.created_at >= week_ago
            ).scalar() or 0
            active_users_weekly.set(wau_count)
            
            # Monthly Active Users
            mau_count = db.query(func.count(func.distinct(Generation.user_id))).filter(
                Generation.created_at >= month_ago
            ).scalar() or 0
            active_users_monthly.set(mau_count)
            
            # New users today
            new_users_count = db.query(User).filter(
                func.date(User.created_at) == today
            ).count()
            new_users_daily.set(new_users_count)
            
            # Generation Metrics
            total_generations_count = db.query(Generation).count()
            daily_generations_count = db.query(Generation).filter(
                func.date(Generation.created_at) == today
            ).count()
            generations_daily.set(daily_generations_count)
            
            # Credit Metrics
            total_credits = db.query(func.sum(User.credits)).scalar() or 0
            credits_balance_total.set(total_credits)
            
            # Revenue Metrics
            # Crypto payments
            crypto_revenue = db.query(func.sum(PaymentOrder.usd_amount)).filter(
                PaymentOrder.status == 'completed'
            ).scalar() or 0
            
            # Stripe payments
            stripe_revenue = db.query(func.sum(StripePaymentOrder.usd_amount)).filter(
                StripePaymentOrder.status == 'completed'
            ).scalar() or 0
            
            total_revenue_amount = crypto_revenue + stripe_revenue
            
            # Daily revenue
            daily_crypto_revenue = db.query(func.sum(PaymentOrder.usd_amount)).filter(
                and_(
                    PaymentOrder.status == 'completed',
                    func.date(PaymentOrder.created_at) == today
                )
            ).scalar() or 0
            
            daily_stripe_revenue = db.query(func.sum(StripePaymentOrder.usd_amount)).filter(
                and_(
                    StripePaymentOrder.status == 'completed',
                    func.date(StripePaymentOrder.created_at) == today
                )
            ).scalar() or 0
            
            daily_revenue_amount = daily_crypto_revenue + daily_stripe_revenue
            
            # Business KPIs
            paying_customers = db.query(func.count(func.distinct(PaymentOrder.user_id))).filter(
                PaymentOrder.status == 'completed'
            ).scalar() or 0
            
            paying_customers += db.query(func.count(func.distinct(StripePaymentOrder.user_id))).filter(
                StripePaymentOrder.status == 'completed'
            ).scalar() or 0
            
            conv_rate = (paying_customers / total_users_count * 100) if total_users_count > 0 else 0
            conversion_rate.set(conv_rate)
            
            arpu_value = total_revenue_amount / total_users_count if total_users_count > 0 else 0
            average_revenue_per_user.set(arpu_value)
            
            # Create snapshot
            snapshot = MetricsSnapshot(
                timestamp=now,
                total_users=total_users_count,
                dau=dau_count,
                wau=wau_count,
                mau=mau_count,
                total_generations=total_generations_count,
                daily_generations=daily_generations_count,
                total_revenue=total_revenue_amount,
                daily_revenue=daily_revenue_amount,
                llm_costs=0.0,  # Will be updated by LLM tracking
                daily_llm_costs=0.0,
                conversion_rate=conv_rate,
                arpu=arpu_value
            )
            
            logger.info(f"Metrics collected: DAU={dau_count}, Revenue=${total_revenue_amount:.2f}, Users={total_users_count}")
            return snapshot
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            errors_total.labels(type='metrics_collection', endpoint='internal').inc()
            raise
    
    def track_llm_request(self, model: str, request_type: str, tokens_used: int, 
                         cost_usd: float, response_time: float, success: bool = True):
        """Track LLM API usage"""
        status = 'success' if success else 'error'
        
        llm_requests_total.labels(model=model, type=request_type, status=status).inc()
        llm_tokens_total.labels(model=model, type=request_type).inc(tokens_used)
        llm_cost_total.labels(model=model, type=request_type).inc(cost_usd)
        llm_response_time.labels(model=model, type=request_type).observe(response_time)
        
        logger.info(f"LLM request tracked: {model} {request_type} - {tokens_used} tokens, ${cost_usd:.4f}, {response_time:.2f}s")
    
    def track_generation(self, user_type: str, duration: float, success: bool = True):
        """Track document generation"""
        status = 'success' if success else 'error'
        
        generations_total.labels(user_type=user_type, status=status).inc()
        if success:
            generation_duration.observe(duration)
        
        logger.info(f"Generation tracked: {user_type} - {duration:.2f}s, {status}")
    
    def track_payment(self, payment_method: str, amount_usd: float, 
                     processing_time: float, success: bool = True):
        """Track payment processing"""
        status = 'success' if success else 'error'
        
        payments_total.labels(payment_method=payment_method, status=status).inc()
        if success:
            revenue_total.labels(payment_method=payment_method).inc(amount_usd)
            payment_processing_time.labels(payment_method=payment_method).observe(processing_time)
        
        logger.info(f"Payment tracked: {payment_method} - ${amount_usd:.2f}, {processing_time:.2f}s, {status}")
    
    def track_credit_transaction(self, transaction_type: str, amount: int, user_type: str = 'regular'):
        """Track credit transactions"""
        if transaction_type in ['purchase', 'bonus']:
            credits_issued_total.labels(source=transaction_type).inc(amount)
        elif transaction_type == 'usage':
            credits_used_total.labels(user_type=user_type).inc(amount)
        
        logger.info(f"Credit transaction tracked: {transaction_type} - {amount} credits, {user_type}")
    
    def track_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Track HTTP requests"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
        http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def track_error(self, error_type: str, endpoint: str):
        """Track application errors"""
        errors_total.labels(type=error_type, endpoint=endpoint).inc()
        logger.error(f"Error tracked: {error_type} at {endpoint}")
    
    def get_metrics_export(self) -> str:
        """Get Prometheus metrics in text format"""
        return generate_latest()

# Global metrics collector instance
metrics_collector = MetricsCollector()

# Utility functions for easy access
def track_llm_usage(model: str, request_type: str, tokens: int, cost: float, response_time: float, success: bool = True):
    """Convenience function to track LLM usage"""
    metrics_collector.track_llm_request(model, request_type, tokens, cost, response_time, success)

def track_generation_metrics(user_type: str, duration: float, success: bool = True):
    """Convenience function to track generation metrics"""
    metrics_collector.track_generation(user_type, duration, success)

def track_payment_metrics(payment_method: str, amount: float, processing_time: float, success: bool = True):
    """Convenience function to track payment metrics"""
    metrics_collector.track_payment(payment_method, amount, processing_time, success)

def track_credit_metrics(transaction_type: str, amount: int, user_type: str = 'regular'):
    """Convenience function to track credit metrics"""
    metrics_collector.track_credit_transaction(transaction_type, amount, user_type)

def track_http_metrics(method: str, endpoint: str, status_code: int, duration: float):
    """Convenience function to track HTTP metrics"""
    metrics_collector.track_http_request(method, endpoint, status_code, duration)

def track_error_metrics(error_type: str, endpoint: str):
    """Convenience function to track errors"""
    metrics_collector.track_error(error_type, endpoint)