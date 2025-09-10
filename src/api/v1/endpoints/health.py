"""
EasyPay Payment Gateway - Health Check Endpoints
"""
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.infrastructure.cache import get_cache_client

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        Dict containing health status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "EasyPay Payment Gateway",
        "version": "0.1.0"
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """
    Readiness check endpoint that verifies all dependencies.
    
    Args:
        db: Database session dependency
        
    Returns:
        Dict containing readiness status and dependency checks
        
    Raises:
        HTTPException: If any dependency is not ready
    """
    checks = {
        "database": False,
        "cache": False,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check database connection
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        checks["database"] = True
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database not ready: {str(e)}"
        )
    
    # Check cache connection
    try:
        cache = get_cache_client()
        await cache.ping()
        checks["cache"] = True
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cache not ready: {str(e)}"
        )
    
    # Check if all dependencies are ready
    if not all(checks[key] for key in ["database", "cache"]):
        raise HTTPException(
            status_code=503,
            detail="Service not ready"
        )
    
    checks["status"] = "ready"
    return checks


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check endpoint for Kubernetes.
    
    Returns:
        Dict containing liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Detailed health check with comprehensive system information.
    
    Args:
        db: Database session dependency
        
    Returns:
        Dict containing detailed health information
    """
    health_info = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "EasyPay Payment Gateway",
        "version": "0.1.0",
        "dependencies": {
            "database": {"status": "unknown", "response_time_ms": None},
            "cache": {"status": "unknown", "response_time_ms": None}
        },
        "system": {
            "uptime": "unknown",  # Would need to track start time
            "memory_usage": "unknown",  # Would need psutil
            "cpu_usage": "unknown"  # Would need psutil
        }
    }
    
    # Check database with timing
    try:
        import time
        start_time = time.time()
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        end_time = time.time()
        
        health_info["dependencies"]["database"] = {
            "status": "healthy",
            "response_time_ms": round((end_time - start_time) * 1000, 2)
        }
    except Exception as e:
        health_info["dependencies"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_info["status"] = "degraded"
    
    # Check cache with timing
    try:
        import time
        start_time = time.time()
        cache = get_cache_client()
        await cache.ping()
        end_time = time.time()
        
        health_info["dependencies"]["cache"] = {
            "status": "healthy",
            "response_time_ms": round((end_time - start_time) * 1000, 2)
        }
    except Exception as e:
        health_info["dependencies"]["cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_info["status"] = "degraded"
    
    return health_info
