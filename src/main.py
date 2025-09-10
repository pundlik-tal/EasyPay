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
from src.api.v1.endpoints import health, payments
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
    description="A modern payment gateway system built with FastAPI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
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
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])


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
