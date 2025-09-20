"""
EasyPay Payment Gateway - Test Main Application with Authentication
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest
from starlette.responses import Response

from src.core.exceptions import EasyPayException
from src.infrastructure.metrics import get_request_count, get_request_duration

# Get Prometheus metrics
REQUEST_COUNT = get_request_count()
REQUEST_DURATION = get_request_duration()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting EasyPay Payment Gateway (Test Version)...")
    
    try:
        logger.info("EasyPay Payment Gateway started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start EasyPay Payment Gateway: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down EasyPay Payment Gateway...")
    logger.info("EasyPay Payment Gateway shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="EasyPay Payment Gateway",
    description="""
    ## EasyPay Payment Gateway API
    
    A modern, secure payment gateway system built with FastAPI that provides:
    
    ### Core Features
    - **Payment Processing**: Charge credit cards, process refunds, and manage transactions
    - **Authentication**: API key management with JWT tokens and role-based access control
    - **Webhook Handling**: Process Authorize.net webhooks for real-time payment updates
    - **Monitoring**: Health checks, metrics, and comprehensive logging
    
    ### Authentication
    All API endpoints require authentication using either:
    - **API Keys**: Direct API key authentication for server-to-server communication
    - **JWT Tokens**: Token-based authentication for web applications
    
    ### Rate Limiting
    - Default: 100 requests/minute, 1000/hour, 10000/day
    - Configurable per API key
    - IP-based whitelisting and blacklisting support
    
    ### Error Handling
    All errors follow a consistent format with error codes, messages, and timestamps.
    
    ### Support
    For API support, please contact: support@easypay.com
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "EasyPay Support",
        "email": "support@easypay.com",
        "url": "https://docs.easypay.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "https://api.easypay.com",
            "description": "Production server"
        },
        {
            "url": "https://api-sandbox.easypay.com", 
            "description": "Sandbox server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ],
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints"
        },
        {
            "name": "authentication",
            "description": "Authentication and API key management"
        },
        {
            "name": "payments",
            "description": "Payment processing operations"
        },
        {
            "name": "webhooks",
            "description": "Webhook management"
        },
        {
            "name": "admin",
            "description": "Administrative operations"
        }
    ]
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing information."""
    import time
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
    )
    
    return response


# Global exception handler
@app.exception_handler(EasyPayException)
async def easypay_exception_handler(request: Request, exc: EasyPayException):
    """Handle EasyPay-specific exceptions."""
    logger.error(f"EasyPay exception: {exc.message}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.error_type,
                "code": exc.error_code,
                "message": exc.message,
                "request_id": getattr(request.state, "request_id", None)
            },
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_error",
                "code": "unexpected_error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None)
            },
            "timestamp": None
        }
    )


# Health check endpoints
@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "service": "EasyPay Payment Gateway"
    }


@app.get("/health/ready", tags=["health"])
async def readiness():
    """Readiness check endpoint."""
    return {
        "ready": True,
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/health/live", tags=["health"])
async def liveness():
    """Liveness check endpoint."""
    return {
        "alive": True,
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/health/detailed", tags=["health"])
async def detailed_health():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "service": "EasyPay Payment Gateway",
        "components": {
            "database": "healthy",
            "cache": "healthy",
            "external_services": "healthy"
        },
        "metrics": {
            "uptime": "0s",
            "requests_total": 0,
            "error_rate": 0.0
        }
    }


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "EasyPay Payment Gateway",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


# API endpoints
@app.get("/api/v1/version", tags=["admin"])
async def get_version():
    """Get API version information."""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "build_date": "2024-01-01T00:00:00Z",
        "environment": "development"
    }


# Authentication endpoints (simplified for testing)
@app.post("/api/v1/auth/api-keys", tags=["authentication"])
async def create_api_key():
    """Create a new API key for testing."""
    return {
        "id": "ak_test_123456789",
        "key_id": "ak_test_123456789",
        "key_secret": "sk_test_abcdef123456789",
        "name": "Test API Key",
        "description": "API key for testing payments",
        "permissions": ["payments:read", "payments:write"],
        "expires_at": None,
        "created_at": "2024-01-01T00:00:00Z"
    }


@app.get("/api/v1/auth/api-keys", tags=["authentication"])
async def list_api_keys():
    """List API keys."""
    return {
        "api_keys": [
            {
                "id": "ak_test_123456789",
                "key_id": "ak_test_123456789",
                "name": "Test API Key",
                "description": "API key for testing payments",
                "status": "active",
                "permissions": ["payments:read", "payments:write"],
                "created_at": "2024-01-01T00:00:00Z"
            }
        ],
        "total": 1,
        "page": 1,
        "per_page": 20
    }


@app.post("/api/v1/auth/tokens", tags=["authentication"])
async def generate_tokens():
    """Generate JWT tokens using API key credentials."""
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh_token",
        "token_type": "bearer",
        "expires_in": 3600
    }


# Payment endpoints (simplified for testing)
@app.get("/api/v1/payments", tags=["payments"])
async def list_payments():
    """List payments (simplified)."""
    return {
        "payments": [],
        "total": 0,
        "page": 1,
        "per_page": 20
    }


@app.post("/api/v1/payments", tags=["payments"])
async def create_payment(payment_data: dict):
    """Create a payment (simplified)."""
    return {
        "id": "pay_123456789",
        "status": "pending",
        "amount": {
            "value": str(payment_data.get("amount", "10.00")),
            "currency": payment_data.get("currency", "USD")
        },
        "customer_id": payment_data.get("customer_id"),
        "customer_email": payment_data.get("customer_email"),
        "customer_name": payment_data.get("customer_name"),
        "description": payment_data.get("description"),
        "metadata": payment_data.get("metadata"),
        "is_test": payment_data.get("is_test", True),
        "created_at": "2024-01-01T00:00:00Z"
    }


@app.get("/api/v1/payments/{payment_id}", tags=["payments"])
async def get_payment(payment_id: str):
    """Get payment by ID."""
    return {
        "id": payment_id,
        "status": "completed",
        "amount": {
            "value": "10.00",
            "currency": "USD"
        },
        "created_at": "2024-01-01T00:00:00Z"
    }


@app.post("/api/v1/payments/{payment_id}/refund", tags=["payments"])
async def refund_payment(payment_id: str):
    """Refund a payment."""
    return {
        "id": payment_id,
        "status": "refunded",
        "amount": {
            "value": "10.00",
            "currency": "USD"
        },
        "refunded_at": "2024-01-01T00:00:00Z"
    }


def main():
    """Main entry point for the application."""
    import uvicorn
    
    uvicorn.run(
        "src.main_test:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
