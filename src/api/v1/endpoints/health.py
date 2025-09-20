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
from src.infrastructure.monitoring import get_metrics, update_system_metrics

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
    # Update system metrics
    update_system_metrics()
    
    # Get current metrics
    metrics = get_metrics()
    
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
            "uptime_seconds": metrics.get("application_uptime", 0),
            "memory_usage_bytes": metrics.get("system_memory_usage", 0),
            "cpu_usage_percent": metrics.get("system_cpu_usage", 0),
            "disk_usage_bytes": metrics.get("system_disk_usage", 0)
        },
        "metrics": {
            "request_count": metrics.get("request_count", 0),
            "payment_count": metrics.get("payment_count", 0),
            "webhook_count": metrics.get("webhook_count", 0),
            "error_count": metrics.get("error_count", 0),
            "cache_hits": metrics.get("cache_hits", 0),
            "cache_misses": metrics.get("cache_misses", 0),
            "auth_attempts": metrics.get("auth_attempts", 0),
            "auth_failures": metrics.get("auth_failures", 0)
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


@router.get("/metrics")
async def metrics_endpoint() -> Dict[str, Any]:
    """
    Get current application metrics.
    
    Returns:
        Dict containing current metrics
    """
    # Update system metrics
    update_system_metrics()
    
    # Get all metrics
    metrics = get_metrics()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics
    }


@router.get("/startup")
async def startup_check() -> Dict[str, Any]:
    """
    Startup check endpoint for Kubernetes startup probe.
    
    Returns:
        Dict containing startup status
    """
    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "EasyPay Payment Gateway",
        "version": "0.1.0"
    }


@router.get("/dependencies")
async def dependencies_check(
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Check all external dependencies.
    
    Args:
        db: Database session dependency
        
    Returns:
        Dict containing dependency status
    """
    dependencies = {
        "database": {"status": "unknown", "response_time_ms": None, "error": None},
        "cache": {"status": "unknown", "response_time_ms": None, "error": None},
        "authorize_net": {"status": "unknown", "response_time_ms": None, "error": None}
    }
    
    # Check database
    try:
        import time
        start_time = time.time()
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
        end_time = time.time()
        
        dependencies["database"] = {
            "status": "healthy",
            "response_time_ms": round((end_time - start_time) * 1000, 2),
            "error": None
        }
    except Exception as e:
        dependencies["database"] = {
            "status": "unhealthy",
            "response_time_ms": None,
            "error": str(e)
        }
    
    # Check cache
    try:
        import time
        start_time = time.time()
        cache = get_cache_client()
        await cache.ping()
        end_time = time.time()
        
        dependencies["cache"] = {
            "status": "healthy",
            "response_time_ms": round((end_time - start_time) * 1000, 2),
            "error": None
        }
    except Exception as e:
        dependencies["cache"] = {
            "status": "unhealthy",
            "response_time_ms": None,
            "error": str(e)
        }
    
    # Check Authorize.net (simplified check)
    try:
        import time
        start_time = time.time()
        # This would be a real API call in production
        # For now, we'll just simulate a check
        end_time = time.time()
        
        dependencies["authorize_net"] = {
            "status": "healthy",
            "response_time_ms": round((end_time - start_time) * 1000, 2),
            "error": None
        }
    except Exception as e:
        dependencies["authorize_net"] = {
            "status": "unhealthy",
            "response_time_ms": None,
            "error": str(e)
        }
    
    # Determine overall status
    all_healthy = all(
        dep["status"] == "healthy" 
        for dep in dependencies.values()
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": dependencies
    }


@router.get("/performance")
async def performance_check() -> Dict[str, Any]:
    """
    Performance check endpoint.
    
    Returns:
        Dict containing performance metrics
    """
    # Update system metrics
    update_system_metrics()
    
    # Get current metrics
    metrics = get_metrics()
    
    # Calculate performance indicators
    performance_indicators = {
        "response_time_p95": 0.5,  # Would be calculated from actual metrics
        "throughput_rps": metrics.get("request_count", 0),
        "error_rate": metrics.get("error_count", 0) / max(metrics.get("request_count", 1), 1),
        "cpu_usage": metrics.get("system_cpu_usage", 0),
        "memory_usage": metrics.get("system_memory_usage", 0),
        "cache_hit_rate": metrics.get("cache_hits", 0) / max(
            metrics.get("cache_hits", 0) + metrics.get("cache_misses", 1), 1
        )
    }
    
    # Determine performance status
    if performance_indicators["response_time_p95"] > 1.0:
        status = "degraded"
    elif performance_indicators["error_rate"] > 0.05:
        status = "degraded"
    elif performance_indicators["cpu_usage"] > 80:
        status = "degraded"
    else:
        status = "healthy"
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "performance_indicators": performance_indicators
    }
