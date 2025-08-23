#!/usr/bin/env python3
"""
Middleware for Resume Generator Application

Includes:
- Metrics collection middleware
- Request/response logging
- Error tracking
- Performance monitoring

Author: Generated for ML project
Date: 2025-08-23
"""

import time
import json
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from metrics import metrics_collector, track_http_metrics, track_error_metrics
from prometheus_client import CONTENT_TYPE_LATEST

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics and performance data"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timing
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = request.url.path
        
        # Normalize endpoint for metrics (remove IDs, etc.)
        endpoint = self._normalize_endpoint(path)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Track metrics
            track_http_metrics(method, endpoint, response.status_code, duration)
            
            # Log request
            self._log_request(request, response, duration)
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration = time.time() - start_time
            
            # Track error metrics
            track_error_metrics("http_error", endpoint)
            track_http_metrics(method, endpoint, 500, duration)
            
            # Log error
            logger.error(f"Request failed: {method} {path} - {str(e)}")
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics grouping"""
        # Remove query parameters
        path = path.split('?')[0]
        
        # Replace common ID patterns
        import re
        
        # Replace UUIDs
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Replace order IDs (alphanumeric)
        path = re.sub(r'/[a-zA-Z0-9]{10,}', '/{id}', path)
        
        return path
    
    def _log_request(self, request: Request, response: Response, duration: float):
        """Log request details in structured format"""
        
        # Extract user info if available
        user_id = None
        if hasattr(request.state, 'user'):
            user_id = getattr(request.state.user, 'id', None)
        
        log_data = {
            "timestamp": time.time(),
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration": round(duration, 3),
            "user_id": user_id,
            "user_agent": request.headers.get("user-agent"),
            "ip": request.client.host if request.client else None,
            "endpoint": self._normalize_endpoint(str(request.url.path))
        }
        
        # Log as JSON for structured logging
        logger.info(json.dumps(log_data))

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to serve Prometheus metrics"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/metrics":
            # Serve Prometheus metrics
            from prometheus_client import generate_latest
            metrics_data = generate_latest()
            
            return Response(
                content=metrics_data,
                media_type=CONTENT_TYPE_LATEST
            )
        else:
            return await call_next(request)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced logging middleware for production"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
        # Create logs directory
        import os
        os.makedirs('logs', exist_ok=True)
        
        # Setup file handler for application logs
        self.app_logger = logging.getLogger('resume_generator')
        self.app_logger.setLevel(logging.INFO)
        
        # File handler for application logs
        app_handler = logging.FileHandler('logs/app.log')
        app_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.app_logger.addHandler(app_handler)
        
        # File handler for access logs
        self.access_logger = logging.getLogger('access')
        self.access_logger.setLevel(logging.INFO)
        
        access_handler = logging.FileHandler('logs/access.log')
        access_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s'
        ))
        self.access_logger.addHandler(access_handler)
        
        # File handler for error logs
        self.error_logger = logging.getLogger('errors')
        self.error_logger.setLevel(logging.ERROR)
        
        error_handler = logging.FileHandler('logs/error.log')
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.error_logger.addHandler(error_handler)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log access
            self._log_access(request, response, duration)
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            self._log_error(request, e, duration)
            
            raise
    
    def _log_access(self, request: Request, response: Response, duration: float):
        """Log access in Apache Common Log Format"""
        
        client_ip = request.client.host if request.client else "-"
        method = request.method
        path = str(request.url)
        status = response.status_code
        size = response.headers.get("content-length", "-")
        user_agent = request.headers.get("user-agent", "-")
        
        log_line = f'{client_ip} - - [{time.strftime("%d/%b/%Y:%H:%M:%S %z")}] ' \
                  f'"{method} {path} HTTP/1.1" {status} {size} ' \
                  f'"-" "{user_agent}" {duration:.3f}'
        
        self.access_logger.info(log_line)
    
    def _log_error(self, request: Request, error: Exception, duration: float):
        """Log error details"""
        
        error_data = {
            "timestamp": time.time(),
            "method": request.method,
            "path": str(request.url.path),
            "error": str(error),
            "error_type": type(error).__name__,
            "duration": duration,
            "ip": request.client.host if request.client else None
        }
        
        self.error_logger.error(json.dumps(error_data))

def setup_middleware(app):
    """Setup all middleware for the application"""
    
    # Add middleware in reverse order (last added = first executed)
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    
    logger.info("Middleware setup complete")