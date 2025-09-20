"""
EasyPay Payment Gateway - Error Reporting Service

This module provides comprehensive error reporting and monitoring including:
- Error aggregation and analysis
- Alert generation
- Error metrics and statistics
- Integration with monitoring systems
- Error trend analysis
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque

from src.core.exceptions import EasyPayException

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Alert types."""
    ERROR_RATE = "error_rate"
    ERROR_SPIKE = "error_spike"
    SERVICE_DOWN = "service_down"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    DEAD_LETTER_QUEUE_FULL = "dead_letter_queue_full"
    PERFORMANCE_DEGRADATION = "performance_degradation"


@dataclass
class ErrorReport:
    """Error report structure."""
    id: str
    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class Alert:
    """Alert structure."""
    id: str
    type: AlertType
    severity: ErrorSeverity
    message: str
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorMetrics:
    """Error metrics."""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_endpoint: Dict[str, int] = field(default_factory=dict)
    error_rate_per_minute: float = 0.0
    error_rate_per_hour: float = 0.0
    average_resolution_time: Optional[float] = None
    critical_errors: int = 0
    unresolved_errors: int = 0


class ErrorReportingService:
    """Service for error reporting and analysis."""
    
    def __init__(self, max_reports: int = 10000, alert_threshold: int = 10):
        self.max_reports = max_reports
        self.alert_threshold = alert_threshold
        
        # Storage
        self.error_reports: deque = deque(maxlen=max_reports)
        self.alerts: List[Alert] = []
        self.error_patterns: Dict[str, int] = defaultdict(int)
        
        # Metrics
        self.metrics = ErrorMetrics()
        self.error_rate_window = deque(maxlen=60)  # Last 60 minutes
        self.hourly_error_counts = deque(maxlen=24)  # Last 24 hours
        
        # Alert handlers
        self.alert_handlers: List[Callable[[Alert], None]] = []
        
        # Configuration
        self.alert_config = {
            AlertType.ERROR_RATE: {"threshold": 10, "window_minutes": 5},
            AlertType.ERROR_SPIKE: {"threshold": 50, "window_minutes": 1},
            AlertType.SERVICE_DOWN: {"threshold": 1, "window_minutes": 1},
            AlertType.CIRCUIT_BREAKER_OPEN: {"threshold": 1, "window_minutes": 1},
            AlertType.DEAD_LETTER_QUEUE_FULL: {"threshold": 1, "window_minutes": 1},
            AlertType.PERFORMANCE_DEGRADATION: {"threshold": 5, "window_minutes": 5}
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def report_error(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Report an error."""
        error_id = f"err_{int(time.time())}_{len(self.error_reports)}"
        
        # Extract error information
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = None
        
        if isinstance(error, Exception):
            import traceback
            stack_trace = traceback.format_exc()
        
        # Create error report
        report = ErrorReport(
            id=error_id,
            timestamp=datetime.utcnow(),
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            request_id=request_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            stack_trace=stack_trace,
            context=context or {}
        )
        
        # Store report
        self.error_reports.append(report)
        
        # Update metrics
        await self._update_metrics(report)
        
        # Check for alerts
        await self._check_alerts(report)
        
        # Log based on severity
        self._log_error(report)
        
        return error_id
    
    async def _update_metrics(self, report: ErrorReport):
        """Update error metrics."""
        # Update counters
        self.metrics.total_errors += 1
        self.metrics.errors_by_type[report.error_type] = self.metrics.errors_by_type.get(report.error_type, 0) + 1
        self.metrics.errors_by_severity[report.severity.value] = self.metrics.errors_by_severity.get(report.severity.value, 0) + 1
        
        if report.endpoint:
            self.metrics.errors_by_endpoint[report.endpoint] = self.metrics.errors_by_endpoint.get(report.endpoint, 0) + 1
        
        if report.severity == ErrorSeverity.CRITICAL:
            self.metrics.critical_errors += 1
        
        if not report.resolved:
            self.metrics.unresolved_errors += 1
        
        # Update error rate
        current_time = datetime.utcnow()
        self.error_rate_window.append(current_time)
        
        # Calculate error rate per minute
        minute_ago = current_time - timedelta(minutes=1)
        recent_errors = sum(1 for t in self.error_rate_window if t > minute_ago)
        self.metrics.error_rate_per_minute = recent_errors
        
        # Calculate error rate per hour
        hour_ago = current_time - timedelta(hours=1)
        hourly_errors = sum(1 for t in self.error_rate_window if t > hour_ago)
        self.metrics.error_rate_per_hour = hourly_errors
        
        # Update hourly counts
        if len(self.hourly_error_counts) == 0 or self.hourly_error_counts[-1][0] != current_time.hour:
            self.hourly_error_counts.append((current_time.hour, 1))
        else:
            hour, count = self.hourly_error_counts[-1]
            self.hourly_error_counts[-1] = (hour, count + 1)
    
    async def _check_alerts(self, report: ErrorReport):
        """Check if error should trigger alerts."""
        current_time = datetime.utcnow()
        
        # Check error rate alert
        if self.metrics.error_rate_per_minute > self.alert_config[AlertType.ERROR_RATE]["threshold"]:
            await self._create_alert(
                AlertType.ERROR_RATE,
                ErrorSeverity.HIGH,
                f"High error rate detected: {self.metrics.error_rate_per_minute} errors/minute",
                {"error_rate": self.metrics.error_rate_per_minute}
            )
        
        # Check error spike alert
        if self.metrics.error_rate_per_minute > self.alert_config[AlertType.ERROR_SPIKE]["threshold"]:
            await self._create_alert(
                AlertType.ERROR_SPIKE,
                ErrorSeverity.CRITICAL,
                f"Error spike detected: {self.metrics.error_rate_per_minute} errors/minute",
                {"error_rate": self.metrics.error_rate_per_minute}
            )
        
        # Check critical error alert
        if report.severity == ErrorSeverity.CRITICAL:
            await self._create_alert(
                AlertType.SERVICE_DOWN,
                ErrorSeverity.CRITICAL,
                f"Critical error: {report.error_message}",
                {"error_id": report.id, "error_type": report.error_type}
            )
    
    async def _create_alert(
        self,
        alert_type: AlertType,
        severity: ErrorSeverity,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create an alert."""
        alert_id = f"alert_{int(time.time())}_{len(self.alerts)}"
        
        alert = Alert(
            id=alert_id,
            type=alert_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        
        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")
        
        self.logger.warning(f"Alert created: {alert_type.value} - {message}")
    
    def _log_error(self, report: ErrorReport):
        """Log error based on severity."""
        log_message = f"Error {report.id}: {report.error_type} - {report.error_message}"
        
        if report.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif report.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif report.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler."""
        self.alert_handlers.append(handler)
    
    def remove_alert_handler(self, handler: Callable[[Alert], None]):
        """Remove an alert handler."""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)
    
    async def resolve_error(self, error_id: str) -> bool:
        """Mark an error as resolved."""
        for report in self.error_reports:
            if report.id == error_id:
                report.resolved = True
                report.resolution_time = datetime.utcnow()
                
                # Update metrics
                self.metrics.unresolved_errors = max(0, self.metrics.unresolved_errors - 1)
                
                # Calculate resolution time
                if report.resolution_time and report.timestamp:
                    resolution_time = (report.resolution_time - report.timestamp).total_seconds()
                    if self.metrics.average_resolution_time is None:
                        self.metrics.average_resolution_time = resolution_time
                    else:
                        self.metrics.average_resolution_time = (
                            self.metrics.average_resolution_time + resolution_time
                        ) / 2
                
                self.logger.info(f"Error {error_id} resolved")
                return True
        
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolution_time = datetime.utcnow()
                self.logger.info(f"Alert {alert_id} resolved")
                return True
        
        return False
    
    def get_error_reports(
        self,
        limit: int = 100,
        severity: Optional[ErrorSeverity] = None,
        error_type: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get error reports with filtering."""
        reports = list(self.error_reports)
        
        # Apply filters
        if severity:
            reports = [r for r in reports if r.severity == severity]
        
        if error_type:
            reports = [r for r in reports if r.error_type == error_type]
        
        if resolved is not None:
            reports = [r for r in reports if r.resolved == resolved]
        
        # Sort by timestamp (newest first)
        reports.sort(key=lambda r: r.timestamp, reverse=True)
        
        # Limit results
        reports = reports[:limit]
        
        # Convert to dict
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "error_type": r.error_type,
                "error_message": r.error_message,
                "severity": r.severity.value,
                "request_id": r.request_id,
                "user_id": r.user_id,
                "endpoint": r.endpoint,
                "method": r.method,
                "resolved": r.resolved,
                "resolution_time": r.resolution_time.isoformat() if r.resolution_time else None,
                "context": r.context
            }
            for r in reports
        ]
    
    def get_alerts(
        self,
        limit: int = 50,
        alert_type: Optional[AlertType] = None,
        severity: Optional[ErrorSeverity] = None,
        resolved: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get alerts with filtering."""
        alerts = list(self.alerts)
        
        # Apply filters
        if alert_type:
            alerts = [a for a in alerts if a.type == alert_type]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        # Limit results
        alerts = alerts[:limit]
        
        # Convert to dict
        return [
            {
                "id": a.id,
                "type": a.type.value,
                "severity": a.severity.value,
                "message": a.message,
                "timestamp": a.timestamp.isoformat(),
                "resolved": a.resolved,
                "resolution_time": a.resolution_time.isoformat() if a.resolution_time else None,
                "metadata": a.metadata
            }
            for a in alerts
        ]
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error metrics."""
        return {
            "total_errors": self.metrics.total_errors,
            "errors_by_type": dict(self.metrics.errors_by_type),
            "errors_by_severity": dict(self.metrics.errors_by_severity),
            "errors_by_endpoint": dict(self.metrics.errors_by_endpoint),
            "error_rate_per_minute": self.metrics.error_rate_per_minute,
            "error_rate_per_hour": self.metrics.error_rate_per_hour,
            "average_resolution_time": self.metrics.average_resolution_time,
            "critical_errors": self.metrics.critical_errors,
            "unresolved_errors": self.metrics.unresolved_errors,
            "total_alerts": len(self.alerts),
            "unresolved_alerts": len([a for a in self.alerts if not a.resolved])
        }
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get error trends over time."""
        current_time = datetime.utcnow()
        start_time = current_time - timedelta(hours=hours)
        
        # Filter reports by time range
        recent_reports = [
            r for r in self.error_reports
            if r.timestamp >= start_time
        ]
        
        # Group by hour
        hourly_counts = defaultdict(int)
        for report in recent_reports:
            hour_key = report.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_counts[hour_key] += 1
        
        # Group by severity
        severity_counts = defaultdict(int)
        for report in recent_reports:
            severity_counts[report.severity.value] += 1
        
        # Group by error type
        type_counts = defaultdict(int)
        for report in recent_reports:
            type_counts[report.error_type] += 1
        
        return {
            "time_range_hours": hours,
            "total_errors": len(recent_reports),
            "hourly_distribution": dict(hourly_counts),
            "severity_distribution": dict(severity_counts),
            "type_distribution": dict(type_counts),
            "trend_direction": self._calculate_trend_direction(recent_reports)
        }
    
    def _calculate_trend_direction(self, reports: List[ErrorReport]) -> str:
        """Calculate error trend direction."""
        if len(reports) < 2:
            return "stable"
        
        # Compare first half vs second half
        mid_point = len(reports) // 2
        first_half = reports[:mid_point]
        second_half = reports[mid_point:]
        
        first_half_count = len(first_half)
        second_half_count = len(second_half)
        
        if second_half_count > first_half_count * 1.2:
            return "increasing"
        elif second_half_count < first_half_count * 0.8:
            return "decreasing"
        else:
            return "stable"


class ErrorReportingAPI:
    """API endpoints for error reporting management."""
    
    def __init__(self, error_service: ErrorReportingService):
        self.error_service = error_service
        self.logger = logging.getLogger(__name__)
    
    async def get_error_dashboard(self) -> Dict[str, Any]:
        """Get error dashboard data."""
        return {
            "metrics": self.error_service.get_error_metrics(),
            "recent_errors": self.error_service.get_error_reports(limit=20),
            "recent_alerts": self.error_service.get_alerts(limit=10),
            "trends": self.error_service.get_error_trends(hours=24)
        }
    
    async def get_error_details(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed error information."""
        reports = self.error_service.get_error_reports(limit=1000)
        for report in reports:
            if report["id"] == error_id:
                return report
        return None
    
    async def resolve_error(self, error_id: str) -> Dict[str, Any]:
        """Resolve an error."""
        success = await self.error_service.resolve_error(error_id)
        return {
            "error_id": error_id,
            "resolved": success,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def resolve_alert(self, alert_id: str) -> Dict[str, Any]:
        """Resolve an alert."""
        success = await self.error_service.resolve_alert(alert_id)
        return {
            "alert_id": alert_id,
            "resolved": success,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global error reporting service instance
error_reporting_service = ErrorReportingService()


def get_error_reporting_service() -> ErrorReportingService:
    """Get the global error reporting service."""
    return error_reporting_service
