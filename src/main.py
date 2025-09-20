"""
EasyPay Payment Gateway - Main Application
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from src.core.exceptions import EasyPayException
from src.infrastructure.database import init_database
from src.infrastructure.cache import init_cache
from src.api.v1.endpoints import health, payments, admin, auth, version
from src.infrastructure.monitoring import setup_logging

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# Configure logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting EasyPay Payment Gateway...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize cache
        await init_cache()
        logger.info("Cache initialized successfully")
        
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
            "description": "Health check endpoints for monitoring and load balancers"
        },
        {
            "name": "authentication",
            "description": "API key management, JWT token generation, and authentication"
        },
        {
            "name": "payments",
            "description": "Payment processing, refunds, cancellations, and transaction management"
        },
        {
            "name": "admin",
            "description": "Administrative endpoints for system management"
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

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure based on environment
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
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration": duration,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    return response


# Global exception handler
@app.exception_handler(EasyPayException)
async def easypay_exception_handler(request: Request, exc: EasyPayException):
    """Handle EasyPay-specific exceptions."""
    logger.error(f"EasyPay exception: {exc.message}", extra={"error_code": exc.error_code})
    
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


# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(version.router, prefix="/api/v1", tags=["version"])


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
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


def main():
    """Main entry point for the application."""
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
