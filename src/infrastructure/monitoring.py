"""
EasyPay Payment Gateway - Monitoring Infrastructure
"""
import logging
import os
import sys
import time
import psutil
from typing import Dict, Any
from datetime import datetime

import structlog
from prometheus_client import Counter, Histogram, Gauge, Info, Summary

# HTTP Metrics
REQUEST_COUNT = Counter(
    'easypay_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'easypay_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

REQUEST_SIZE = Histogram(
    'easypay_http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

RESPONSE_SIZE = Histogram(
    'easypay_http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint']
)

# Payment Metrics
PAYMENT_COUNT = Counter(
    'easypay_payments_total',
    'Total payments processed',
    ['status', 'currency', 'payment_method']
)

PAYMENT_AMOUNT = Histogram(
    'easypay_payment_amount',
    'Payment amounts',
    ['currency']
)

PAYMENT_PROCESSING_TIME = Summary(
    'easypay_payment_processing_seconds',
    'Payment processing time in seconds',
    ['status']
)

# Webhook Metrics
WEBHOOK_COUNT = Counter(
    'easypay_webhooks_total',
    'Total webhooks processed',
    ['event_type', 'status', 'source']
)

WEBHOOK_DELIVERY_TIME = Histogram(
    'easypay_webhook_delivery_seconds',
    'Webhook delivery time in seconds',
    ['event_type', 'status']
)

WEBHOOK_RETRY_COUNT = Counter(
    'easypay_webhook_retries_total',
    'Total webhook retries',
    ['event_type', 'retry_attempt']
)

# Authentication Metrics
AUTH_ATTEMPTS = Counter(
    'easypay_auth_attempts_total',
    'Total authentication attempts',
    ['method', 'status']
)

AUTH_FAILURES = Counter(
    'easypay_auth_failures_total',
    'Total authentication failures',
    ['method', 'reason']
)

# Database Metrics
DATABASE_CONNECTIONS = Gauge(
    'easypay_database_connections',
    'Number of database connections'
)

DATABASE_QUERY_DURATION = Histogram(
    'easypay_database_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table']
)

DATABASE_ERRORS = Counter(
    'easypay_database_errors_total',
    'Total database errors',
    ['operation', 'error_type']
)

# Cache Metrics
CACHE_HITS = Counter(
    'easypay_cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

CACHE_MISSES = Counter(
    'easypay_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

CACHE_OPERATION_DURATION = Histogram(
    'easypay_cache_operation_duration_seconds',
    'Cache operation duration in seconds',
    ['operation', 'cache_type']
)

# System Metrics
SYSTEM_CPU_USAGE = Gauge(
    'easypay_system_cpu_usage_percent',
    'System CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'easypay_system_memory_usage_bytes',
    'System memory usage in bytes'
)

SYSTEM_DISK_USAGE = Gauge(
    'easypay_system_disk_usage_bytes',
    'System disk usage in bytes',
    ['device']
)

# Application Metrics
ACTIVE_CONNECTIONS = Gauge(
    'easypay_active_connections',
    'Number of active connections'
)

APPLICATION_UPTIME = Gauge(
    'easypay_application_uptime_seconds',
    'Application uptime in seconds'
)

APPLICATION_INFO = Info(
    'easypay_application_info',
    'Application information'
)

# Error Metrics
ERROR_COUNT = Counter(
    'easypay_errors_total',
    'Total application errors',
    ['error_type', 'severity']
)

# Business Metrics
REVENUE_TOTAL = Counter(
    'easypay_revenue_total',
    'Total revenue processed',
    ['currency']
)

FRAUD_DETECTIONS = Counter(
    'easypay_fraud_detections_total',
    'Total fraud detections',
    ['fraud_type', 'severity']
)

CHARGEBACK_COUNT = Counter(
    'easypay_chargebacks_total',
    'Total chargebacks',
    ['reason', 'status']
)

# Set application info
APPLICATION_INFO.info({
    'version': '0.1.0',
    'name': 'EasyPay Payment Gateway',
    'environment': os.getenv('ENVIRONMENT', 'development'),
    'build_date': datetime.utcnow().isoformat(),
    'python_version': sys.version,
    'platform': os.name
})

# Track application start time for uptime calculation
_APP_START_TIME = time.time()


def setup_logging() -> logging.Logger:
    """
    Set up structured logging with appropriate configuration.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
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
        formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create application logger
    app_logger = structlog.get_logger("easypay")
    
    return app_logger


def update_system_metrics() -> None:
    """Update system metrics with current values."""
    try:
        # Update CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        SYSTEM_CPU_USAGE.set(cpu_percent)
        
        # Update memory usage
        memory = psutil.virtual_memory()
        SYSTEM_MEMORY_USAGE.set(memory.used)
        
        # Update disk usage
        disk_usage = psutil.disk_usage('/')
        SYSTEM_DISK_USAGE.labels(device='/').set(disk_usage.used)
        
        # Update application uptime
        uptime = time.time() - _APP_START_TIME
        APPLICATION_UPTIME.set(uptime)
        
    except Exception as e:
        # Log error but don't fail
        logger = structlog.get_logger("easypay.monitoring")
        logger.error("Failed to update system metrics", error=str(e))


def get_metrics() -> Dict[str, Any]:
    """
    Get current metrics for monitoring.
    
    Returns:
        Dict containing current metrics
    """
    # Update system metrics before returning
    update_system_metrics()
    
    return {
        "request_count": REQUEST_COUNT._value.sum(),
        "request_duration": REQUEST_DURATION._sum._value.sum(),
        "payment_count": PAYMENT_COUNT._value.sum(),
        "payment_amount": PAYMENT_AMOUNT._sum._value.sum(),
        "webhook_count": WEBHOOK_COUNT._value.sum(),
        "auth_attempts": AUTH_ATTEMPTS._value.sum(),
        "auth_failures": AUTH_FAILURES._value.sum(),
        "database_errors": DATABASE_ERRORS._value.sum(),
        "cache_hits": CACHE_HITS._value.sum(),
        "cache_misses": CACHE_MISSES._value.sum(),
        "error_count": ERROR_COUNT._value.sum(),
        "revenue_total": REVENUE_TOTAL._value.sum(),
        "fraud_detections": FRAUD_DETECTIONS._value.sum(),
        "chargeback_count": CHARGEBACK_COUNT._value.sum(),
        "active_connections": ACTIVE_CONNECTIONS._value._value,
        "database_connections": DATABASE_CONNECTIONS._value._value,
        "system_cpu_usage": SYSTEM_CPU_USAGE._value._value,
        "system_memory_usage": SYSTEM_MEMORY_USAGE._value._value,
        "application_uptime": APPLICATION_UPTIME._value._value,
    }


class MetricsCollector:
    """Metrics collector for custom metrics."""
    
    def __init__(self):
        self.custom_metrics = {}
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None) -> None:
        """
        Increment a custom counter metric.
        
        Args:
            name: Metric name
            labels: Optional labels for the metric
        """
        if name not in self.custom_metrics:
            self.custom_metrics[name] = Counter(
                f'easypay_{name}_total',
                f'Total {name}',
                list(labels.keys()) if labels else []
            )
        
        if labels:
            self.custom_metrics[name].labels(**labels).inc()
        else:
            self.custom_metrics[name].inc()
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """
        Set a custom gauge metric.
        
        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels for the metric
        """
        if name not in self.custom_metrics:
            self.custom_metrics[name] = Gauge(
                f'easypay_{name}',
                f'{name} value',
                list(labels.keys()) if labels else []
            )
        
        if labels:
            self.custom_metrics[name].labels(**labels).set(value)
        else:
            self.custom_metrics[name].set(value)
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """
        Observe a custom histogram metric.
        
        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels for the metric
        """
        if name not in self.custom_metrics:
            self.custom_metrics[name] = Histogram(
                f'easypay_{name}',
                f'{name} distribution',
                list(labels.keys()) if labels else []
            )
        
        if labels:
            self.custom_metrics[name].labels(**labels).observe(value)
        else:
            self.custom_metrics[name].observe(value)


# Global metrics collector instance
metrics_collector = MetricsCollector()
