"""
EasyPay Payment Gateway - Error Management API Endpoints

This module provides API endpoints for error management including:
- Error reporting and monitoring
- Dead letter queue management
- Circuit breaker status
- Graceful shutdown control
- Error recovery operations
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field

from src.infrastructure.error_recovery import (
    error_recovery_manager, graceful_shutdown_manager, error_reporting_service
)
from src.infrastructure.dead_letter_queue import dead_letter_queue_service, DeadLetterQueueAPI
from src.infrastructure.circuit_breaker_service import circuit_breaker_service
from src.infrastructure.error_reporting import ErrorReportingAPI, ErrorSeverity, AlertType
from src.core.exceptions import EasyPayException
from src.api.v1.middleware.auth import require_admin_read, require_admin_write

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/error-management", tags=["error-management"])

# Initialize API services
dlq_api = DeadLetterQueueAPI(dead_letter_queue_service)
error_api = ErrorReportingAPI(error_reporting_service)


# Request/Response Models
class ErrorReportRequest(BaseModel):
    """Request model for error reporting."""
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    severity: ErrorSeverity = Field(..., description="Error severity")
    request_id: Optional[str] = Field(None, description="Request ID")
    user_id: Optional[str] = Field(None, description="User ID")
    endpoint: Optional[str] = Field(None, description="API endpoint")
    method: Optional[str] = Field(None, description="HTTP method")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status model."""
    name: str
    state: str
    failure_count: int
    success_count: int
    success_rate: float
    metrics: Dict[str, Any]


class ShutdownStatus(BaseModel):
    """Shutdown status model."""
    is_shutting_down: bool
    current_phase: Optional[str]
    health_check_enabled: bool
    active_connections: int
    background_tasks: int
    registered_handlers: int
    metrics: Dict[str, Any]


# Error Recovery Endpoints
@router.get("/recovery/status")
async def get_recovery_status(
    auth_context: dict = Depends(require_admin_read)
) -> Dict[str, Any]:
    """Get error recovery system status."""
    try:
        return {
            "status": "operational",
            "error_statistics": error_recovery_manager.get_error_statistics(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get recovery status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recovery status")


@router.post("/recovery/report-error")
async def report_error(
    request: ErrorReportRequest,
    auth_context: dict = Depends(require_admin_write)
) -> Dict[str, Any]:
    """Report an error to the error recovery system."""
    try:
        # Create a mock exception for reporting
        class MockError(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.__class__.__name__ = request.error_type
        
        error = MockError(request.error_message)
        
        # Report the error
        error_id = await error_reporting_service.report_error(
            error=error,
            severity=request.severity,
            request_id=request.request_id,
            user_id=request.user_id,
            endpoint=request.endpoint,
            method=request.method,
            context=request.context
        )
        
        return {
            "error_id": error_id,
            "status": "reported",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to report error: {e}")
        raise HTTPException(status_code=500, detail="Failed to report error")


# Dead Letter Queue Endpoints
@router.get("/dead-letter-queue/status")
async def get_dead_letter_queue_status(
    auth_context: dict = Depends(require_admin_read)
) -> Dict[str, Any]:
    """Get dead letter queue status."""
    try:
        return await dlq_api.get_queue_status()
    except Exception as e:
        logger.error(f"Failed to get dead letter queue status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dead letter queue status")


@router.get("/dead-letter-queue/messages")
async def get_dead_letter_messages(
    auth_context: dict = Depends(require_admin_read),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of messages to return")
) -> List[Dict[str, Any]]:
    """Get dead letter queue messages."""
    try:
        messages = await dead_letter_queue_service.get_pending_messages(limit=limit)
        return [
            {
                "id": msg.id,
                "created_at": msg.created_at.isoformat(),
                "retry_count": msg.retry_count,
                "max_retries": msg.max_retries,
                "status": msg.status.value,
                "next_retry_at": msg.next_retry_at.isoformat() if msg.next_retry_at else None,
                "last_error": msg.last_error,
                "metadata": msg.metadata
            }
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"Failed to get dead letter messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dead letter messages")


@router.get("/dead-letter-queue/messages/{message_id}")
async def get_dead_letter_message(
    message_id: str,
    auth_context: dict = Depends(require_admin_read)
) -> Dict[str, Any]:
    """Get a specific dead letter queue message."""
    try:
        message = await dlq_api.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        return message
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dead letter message: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dead letter message")


@router.post("/dead-letter-queue/messages/{message_id}/retry")
async def retry_dead_letter_message(
    message_id: str,
    auth_context: dict = Depends(require_admin_write)
) -> Dict[str, Any]:
    """Retry a dead letter queue message."""
    try:
        return await dlq_api.retry_message(message_id)
    except Exception as e:
        logger.error(f"Failed to retry dead letter message: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry dead letter message")


@router.delete("/dead-letter-queue/messages/{message_id}")
async def delete_dead_letter_message(
    message_id: str,
    auth_context: dict = Depends(require_admin_write)
) -> Dict[str, Any]:
    """Delete a dead letter queue message."""
    try:
        return await dlq_api.delete_message(message_id)
    except Exception as e:
        logger.error(f"Failed to delete dead letter message: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete dead letter message")


@router.post("/dead-letter-queue/cleanup")
async def cleanup_dead_letter_queue(
    auth_context: dict = Depends(require_admin_write)
) -> Dict[str, Any]:
    """Clean up expired dead letter queue messages."""
    try:
        return await dlq_api.cleanup_expired()
    except Exception as e:
        logger.error(f"Failed to cleanup dead letter queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup dead letter queue")


# Circuit Breaker Endpoints
@router.get("/circuit-breakers")
async def get_circuit_breakers(
    auth_context: dict = Depends(require_admin_read)
) -> List[CircuitBreakerStatus]:
    """Get all circuit breakers status."""
    try:
        metrics = circuit_breaker_service.get_all_metrics()
        return [
            CircuitBreakerStatus(
                name=name,
                state=data["state"],
                failure_count=data["failure_count"],
                success_count=data["success_count"],
                success_rate=data["success_rate"],
                metrics=data["metrics"]
            )
            for name, data in metrics.items()
        ]
    except Exception as e:
        logger.error(f"Failed to get circuit breakers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breakers")


@router.get("/circuit-breakers/{service_name}")
async def get_circuit_breaker(
    service_name: str,
    auth_context: dict = Depends(require_admin_read)
) -> CircuitBreakerStatus:
    """Get specific circuit breaker status."""
    try:
        circuit_breaker = circuit_breaker_service.get_circuit_breaker(service_name)
        if not circuit_breaker:
            raise HTTPException(status_code=404, detail="Circuit breaker not found")
        
        metrics = circuit_breaker.get_metrics()
        return CircuitBreakerStatus(
            name=service_name,
            state=metrics["state"],
            failure_count=metrics["failure_count"],
            success_count=metrics["success_count"],
            success_rate=metrics["success_rate"],
            metrics=metrics["metrics"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get circuit breaker: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit breaker")


@router.post("/circuit-breakers/{service_name}/reset")
async def reset_circuit_breaker(
    service_name: str,
    auth_context: dict = Depends(require_admin_write)
) -> Dict[str, Any]:
    """Reset a circuit breaker."""
    try:
        success = circuit_breaker_service.reset_circuit_breaker(service_name)
        if not success:
            raise HTTPException(status_code=404, detail="Circuit breaker not found")
        
        return {
            "service_name": service_name,
            "reset": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breaker")


@router.get("/circuit-breakers/healthy")
async def get_healthy_services(
    auth_context: dict = Depends(require_admin_read)
) -> Dict[str, Any]:
    """Get list of healthy services."""
    try:
        healthy_services = circuit_breaker_service.get_healthy_services()
        unhealthy_services = circuit_breaker_service.get_unhealthy_services()
        
        return {
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "total_services": len(healthy_services) + len(unhealthy_services),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get healthy services: {e}")
        raise HTTPException(status_code=500, detail="Failed to get healthy services")


# Graceful Shutdown Endpoints
@router.get("/shutdown/status")
async def get_shutdown_status(
    auth_context: dict = Depends(require_admin_read)
) -> ShutdownStatus:
    """Get graceful shutdown status."""
    try:
        status_data = graceful_shutdown_manager.get_shutdown_status()
        return ShutdownStatus(**status_data)
    except Exception as e:
        logger.error(f"Failed to get shutdown status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get shutdown status")


@router.post("/shutdown/initiate")
async def initiate_shutdown(
    auth_context: dict = Depends(require_admin_write)
) -> Dict[str, Any]:
    """Initiate graceful shutdown."""
    try:
        if graceful_shutdown_manager.is_shutting_down:
            return {
                "status": "already_shutting_down",
                "message": "Shutdown already in progress",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Start shutdown in background
        asyncio.create_task(graceful_shutdown_manager.shutdown())
        
        return {
            "status": "shutdown_initiated",
            "message": "Graceful shutdown initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to initiate shutdown: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate shutdown")


# Error Reporting Endpoints
@router.get("/errors/dashboard")
async def get_error_dashboard(
    auth_context: dict = Depends(require_admin_read)
) -> Dict[str, Any]:
    """Get error dashboard data."""
    try:
        return await error_api.get_error_dashboard()
    except Exception as e:
        logger.error(f"Failed to get error dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error dashboard")


@router.get("/errors")
async def get_error_reports(
    auth_context: dict = Depends(require_admin_read),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of errors to return"),
    severity: Optional[ErrorSeverity] = Query(None, description="Filter by severity"),
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status")
) -> List[Dict[str, Any]]:
    """Get error reports with filtering."""
    try:
        return error_reporting_service.get_error_reports(
            limit=limit,
            severity=severity,
            error_type=error_type,
            resolved=resolved
        )
    except Exception as e:
        logger.error(f"Failed to get error reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error reports")


@router.get("/errors/{error_id}")
async def get_error_details(
    error_id: str,
    auth_context: dict = Depends(require_admin_read)
) -> Dict[str, Any]:
    """Get detailed error information."""
    try:
        error_details = await error_api.get_error_details(error_id)
        if not error_details:
            raise HTTPException(status_code=404, detail="Error not found")
        return error_details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get error details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error details")


@router.post("/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    auth_context: dict = Depends(require_admin_write)
) -> Dict[str, Any]:
    """Resolve an error."""
    try:
        return await error_api.resolve_error(error_id)
    except Exception as e:
        logger.error(f"Failed to resolve error: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve error")


@router.get("/alerts")
async def get_alerts(
    auth_context: dict = Depends(require_admin_read),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of alerts to return"),
    alert_type: Optional[AlertType] = Query(None, description="Filter by alert type"),
    severity: Optional[ErrorSeverity] = Query(None, description="Filter by severity"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status")
) -> List[Dict[str, Any]]:
    """Get alerts with filtering."""
    try:
        return error_reporting_service.get_alerts(
            limit=limit,
            alert_type=alert_type,
            severity=severity,
            resolved=resolved
        )
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    auth_context: dict = Depends(require_admin_write)
) -> Dict[str, Any]:
    """Resolve an alert."""
    try:
        return await error_reporting_service.resolve_alert(alert_id)
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve alert")


@router.get("/errors/metrics")
async def get_error_metrics(
    auth_context: dict = Depends(require_admin_read)
) -> Dict[str, Any]:
    """Get error metrics."""
    try:
        return error_reporting_service.get_error_metrics()
    except Exception as e:
        logger.error(f"Failed to get error metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error metrics")


@router.get("/errors/trends")
async def get_error_trends(
    auth_context: dict = Depends(require_admin_read),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze")
) -> Dict[str, Any]:
    """Get error trends over time."""
    try:
        return error_reporting_service.get_error_trends(hours=hours)
    except Exception as e:
        logger.error(f"Failed to get error trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error trends")


# Health Check Endpoint
@router.get("/health")
async def error_management_health() -> Dict[str, Any]:
    """Health check for error management system."""
    try:
        return {
            "status": "healthy",
            "components": {
                "error_recovery": "operational",
                "dead_letter_queue": "operational",
                "circuit_breakers": "operational",
                "graceful_shutdown": "operational",
                "error_reporting": "operational"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error management health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
