"""
EasyPay Payment Gateway - Prometheus Metrics
"""
from prometheus_client import Counter, Histogram, CollectorRegistry, REGISTRY
import threading

# Thread lock to ensure metrics are only created once
_metrics_lock = threading.Lock()
_metrics_initialized = False

# Global metrics variables
REQUEST_COUNT = None
REQUEST_DURATION = None


def get_or_create_metrics():
    """
    Get or create Prometheus metrics.
    This function ensures metrics are only created once across all modules.
    """
    global REQUEST_COUNT, REQUEST_DURATION, _metrics_initialized
    
    with _metrics_lock:
        if not _metrics_initialized:
            try:
                # Try to create metrics
                REQUEST_COUNT = Counter(
                    'http_requests_total', 
                    'Total HTTP requests', 
                    ['method', 'endpoint', 'status']
                )
                REQUEST_DURATION = Histogram(
                    'http_request_duration_seconds', 
                    'HTTP request duration', 
                    ['method', 'endpoint']
                )
                _metrics_initialized = True
            except ValueError as e:
                if "Duplicated timeseries" in str(e):
                    # Metrics already exist, get them from registry
                    for metric in REGISTRY.collect():
                        if metric.name == 'http_requests_total':
                            REQUEST_COUNT = metric
                        elif metric.name == 'http_request_duration_seconds':
                            REQUEST_DURATION = metric
                    _metrics_initialized = True
                else:
                    raise
    
    return REQUEST_COUNT, REQUEST_DURATION


def get_request_count():
    """Get the request count metric."""
    count, _ = get_or_create_metrics()
    return count


def get_request_duration():
    """Get the request duration metric."""
    _, duration = get_or_create_metrics()
    return duration
