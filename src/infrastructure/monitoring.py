"""
EasyPay Payment Gateway - Monitoring Infrastructure
"""
import logging
import os
import sys
from typing import Dict, Any

import structlog
from prometheus_client import Counter, Histogram, Gauge, Info

# Prometheus metrics
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

PAYMENT_COUNT = Counter(
    'easypay_payments_total',
    'Total payments processed',
    ['status', 'currency']
)

PAYMENT_AMOUNT = Histogram(
    'easypay_payment_amount',
    'Payment amounts',
    ['currency']
)

ACTIVE_CONNECTIONS = Gauge(
    'easypay_active_connections',
    'Number of active connections'
)

DATABASE_CONNECTIONS = Gauge(
    'easypay_database_connections',
    'Number of database connections'
)

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

APPLICATION_INFO = Info(
    'easypay_application_info',
    'Application information'
)

# Set application info
APPLICATION_INFO.info({
    'version': '0.1.0',
    'name': 'EasyPay Payment Gateway',
    'environment': os.getenv('ENVIRONMENT', 'development')
})


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


def get_metrics() -> Dict[str, Any]:
    """
    Get current metrics for monitoring.
    
    Returns:
        Dict containing current metrics
    """
    return {
        "request_count": REQUEST_COUNT._value.sum(),
        "request_duration": REQUEST_DURATION._sum._value.sum(),
        "payment_count": PAYMENT_COUNT._value.sum(),
        "payment_amount": PAYMENT_AMOUNT._sum._value.sum(),
        "active_connections": ACTIVE_CONNECTIONS._value._value,
        "database_connections": DATABASE_CONNECTIONS._value._value,
        "cache_hits": CACHE_HITS._value.sum(),
        "cache_misses": CACHE_MISSES._value.sum(),
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
