"""
EasyPay Payment Gateway - Enhanced Logging Configuration
"""
import logging
import os
import sys
import json
from typing import Dict, Any, Optional
from datetime import datetime

import structlog
from pythonjsonlogger import jsonlogger


class CorrelationIDProcessor:
    """Processor to add correlation IDs to log records."""
    
    def __init__(self):
        self.correlation_id = None
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set the correlation ID for the current context."""
        self.correlation_id = correlation_id
    
    def __call__(self, logger, method_name, event_dict):
        """Add correlation ID to log record."""
        if self.correlation_id:
            event_dict['correlation_id'] = self.correlation_id
        return event_dict


class SecurityFilterProcessor:
    """Processor to filter sensitive information from logs."""
    
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'key', 'card_number', 'cvv', 'ssn',
        'api_key', 'private_key', 'authorization', 'bearer'
    }
    
    def __call__(self, logger, method_name, event_dict):
        """Filter sensitive fields from log record."""
        filtered_dict = {}
        for key, value in event_dict.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                filtered_dict[key] = '[REDACTED]'
            else:
                filtered_dict[key] = value
        return filtered_dict


class BusinessContextProcessor:
    """Processor to add business context to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        """Add business context to log record."""
        # Add timestamp if not present
        if 'timestamp' not in event_dict:
            event_dict['timestamp'] = datetime.utcnow().isoformat()
        
        # Add service information
        event_dict['service'] = 'easypay-payment-gateway'
        event_dict['version'] = '0.1.0'
        event_dict['environment'] = os.getenv('ENVIRONMENT', 'development')
        
        return event_dict


class PerformanceProcessor:
    """Processor to add performance metrics to log records."""
    
    def __call__(self, logger, method_name, event_dict):
        """Add performance metrics to log record."""
        # Add performance context if available
        if 'duration' in event_dict:
            duration = event_dict['duration']
            if duration > 1.0:
                event_dict['performance_level'] = 'slow'
            elif duration > 0.5:
                event_dict['performance_level'] = 'medium'
            else:
                event_dict['performance_level'] = 'fast'
        
        return event_dict


def setup_enhanced_logging() -> logging.Logger:
    """
    Set up enhanced structured logging with security filtering and business context.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Configure structlog with enhanced processors
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            SecurityFilterProcessor(),
            BusinessContextProcessor(),
            PerformanceProcessor(),
            CorrelationIDProcessor(),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json")
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    
    # Set formatter based on configuration
    if log_format.lower() == "json":
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            json_ensure_ascii=False
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler for persistent logging
    log_file = os.getenv("LOG_FILE", "logs/easypay.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Create application logger
    app_logger = structlog.get_logger("easypay")
    
    return app_logger


class LogAggregator:
    """Log aggregator for centralized logging."""
    
    def __init__(self):
        self.logs = []
        self.max_logs = int(os.getenv("MAX_LOG_ENTRIES", "1000"))
    
    def add_log(self, log_entry: Dict[str, Any]) -> None:
        """Add a log entry to the aggregator."""
        self.logs.append(log_entry)
        
        # Keep only the most recent logs
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
    
    def get_logs(
        self,
        level: Optional[str] = None,
        service: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """Get filtered logs from the aggregator."""
        filtered_logs = self.logs
        
        if level:
            filtered_logs = [log for log in filtered_logs if log.get('level') == level]
        
        if service:
            filtered_logs = [log for log in filtered_logs if log.get('service') == service]
        
        if start_time:
            filtered_logs = [
                log for log in filtered_logs 
                if datetime.fromisoformat(log.get('timestamp', '')) >= start_time
            ]
        
        if end_time:
            filtered_logs = [
                log for log in filtered_logs 
                if datetime.fromisoformat(log.get('timestamp', '')) <= end_time
            ]
        
        return filtered_logs[-limit:]
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get log statistics."""
        if not self.logs:
            return {"total_logs": 0}
        
        levels = {}
        services = {}
        
        for log in self.logs:
            level = log.get('level', 'unknown')
            service = log.get('service', 'unknown')
            
            levels[level] = levels.get(level, 0) + 1
            services[service] = services.get(service, 0) + 1
        
        return {
            "total_logs": len(self.logs),
            "levels": levels,
            "services": services,
            "oldest_log": self.logs[0].get('timestamp') if self.logs else None,
            "newest_log": self.logs[-1].get('timestamp') if self.logs else None
        }


class AuditLogger:
    """Specialized logger for audit events."""
    
    def __init__(self):
        self.logger = structlog.get_logger("easypay.audit")
    
    def log_payment_event(
        self,
        event_type: str,
        payment_id: str,
        amount: float,
        currency: str,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log payment-related audit events."""
        self.logger.info(
            "Payment audit event",
            event_type=event_type,
            payment_id=payment_id,
            amount=amount,
            currency=currency,
            user_id=user_id,
            correlation_id=correlation_id,
            audit_category="payment"
        )
    
    def log_auth_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        method: str = "api_key",
        success: bool = True,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log authentication-related audit events."""
        self.logger.info(
            "Authentication audit event",
            event_type=event_type,
            user_id=user_id,
            method=method,
            success=success,
            correlation_id=correlation_id,
            audit_category="authentication"
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str = "medium",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log security-related audit events."""
        self.logger.warning(
            "Security audit event",
            event_type=event_type,
            severity=severity,
            details=details or {},
            correlation_id=correlation_id,
            audit_category="security"
        )
    
    def log_admin_event(
        self,
        event_type: str,
        admin_user_id: str,
        target_resource: Optional[str] = None,
        action: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """Log admin-related audit events."""
        self.logger.info(
            "Admin audit event",
            event_type=event_type,
            admin_user_id=admin_user_id,
            target_resource=target_resource,
            action=action,
            correlation_id=correlation_id,
            audit_category="admin"
        )


# Global instances
log_aggregator = LogAggregator()
audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """Get the audit logger instance."""
    return audit_logger


def get_log_aggregator() -> LogAggregator:
    """Get the log aggregator instance."""
    return log_aggregator
