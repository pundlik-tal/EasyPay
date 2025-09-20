"""
EasyPay Payment Gateway - Enhanced Performance Monitoring

This module provides comprehensive performance monitoring with real-time metrics,
alerting, and performance analysis capabilities.
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque

from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client.core import CollectorRegistry

from src.infrastructure.monitoring import (
    REQUEST_COUNT, REQUEST_DURATION, PAYMENT_COUNT, PAYMENT_PROCESSING_TIME,
    DATABASE_CONNECTIONS, CACHE_HITS, CACHE_MISSES, ERROR_COUNT
)


class PerformanceLevel(Enum):
    """Performance level indicators."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    unit: str = "seconds"


@dataclass
class PerformanceAlert:
    """Performance alert definition."""
    id: str
    metric_name: str
    level: PerformanceLevel
    message: str
    timestamp: datetime
    value: float
    threshold: float


class PerformanceAnalyzer:
    """Analyzes performance metrics and trends."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics_history = defaultdict(lambda: deque(maxlen=window_size))
        self.logger = logging.getLogger(__name__)
        
        # Performance thresholds
        self.thresholds = {
            "response_time": PerformanceThreshold("response_time", 0.5, 1.0),
            "throughput": PerformanceThreshold("throughput", 100, 50),
            "error_rate": PerformanceThreshold("error_rate", 0.01, 0.05),
            "cpu_usage": PerformanceThreshold("cpu_usage", 70.0, 85.0, "percent"),
            "memory_usage": PerformanceThreshold("memory_usage", 80.0, 90.0, "percent"),
            "database_query_time": PerformanceThreshold("database_query_time", 0.1, 0.5),
            "cache_hit_rate": PerformanceThreshold("cache_hit_rate", 0.8, 0.6)
        }
    
    def record_metric(self, metric_name: str, value: float, timestamp: datetime = None):
        """Record a metric value."""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        self.metrics_history[metric_name].append({
            "value": value,
            "timestamp": timestamp
        })
    
    def get_metric_trend(self, metric_name: str, window_minutes: int = 5) -> Dict[str, Any]:
        """Get metric trend over specified window."""
        
        if metric_name not in self.metrics_history:
            return {"trend": "no_data", "change": 0.0}
        
        history = self.metrics_history[metric_name]
        if len(history) < 2:
            return {"trend": "insufficient_data", "change": 0.0}
        
        # Get recent data points
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_data = [m for m in history if m["timestamp"] >= cutoff_time]
        
        if len(recent_data) < 2:
            return {"trend": "insufficient_data", "change": 0.0}
        
        # Calculate trend
        first_value = recent_data[0]["value"]
        last_value = recent_data[-1]["value"]
        change = last_value - first_value
        change_percent = (change / first_value) * 100 if first_value != 0 else 0
        
        # Determine trend direction
        if abs(change_percent) < 5:
            trend = "stable"
        elif change_percent > 5:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        return {
            "trend": trend,
            "change": change,
            "change_percent": change_percent,
            "first_value": first_value,
            "last_value": last_value,
            "data_points": len(recent_data)
        }
    
    def analyze_performance_level(self, metric_name: str) -> PerformanceLevel:
        """Analyze current performance level for a metric."""
        
        if metric_name not in self.metrics_history:
            return PerformanceLevel.CRITICAL
        
        history = self.metrics_history[metric_name]
        if not history:
            return PerformanceLevel.CRITICAL
        
        # Get current value
        current_value = history[-1]["value"]
        
        # Get threshold
        threshold = self.thresholds.get(metric_name)
        if not threshold:
            return PerformanceLevel.GOOD
        
        # Determine performance level
        if current_value <= threshold.warning_threshold:
            return PerformanceLevel.EXCELLENT
        elif current_value <= threshold.critical_threshold:
            return PerformanceLevel.GOOD
        elif current_value <= threshold.critical_threshold * 1.5:
            return PerformanceLevel.FAIR
        elif current_value <= threshold.critical_threshold * 2:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        
        summary = {
            "overall_level": PerformanceLevel.GOOD,
            "metrics": {},
            "alerts": [],
            "recommendations": []
        }
        
        critical_count = 0
        poor_count = 0
        
        for metric_name in self.metrics_history.keys():
            level = self.analyze_performance_level(metric_name)
            trend = self.get_metric_trend(metric_name)
            
            summary["metrics"][metric_name] = {
                "level": level.value,
                "trend": trend["trend"],
                "change_percent": trend["change_percent"]
            }
            
            if level == PerformanceLevel.CRITICAL:
                critical_count += 1
            elif level == PerformanceLevel.POOR:
                poor_count += 1
        
        # Determine overall level
        if critical_count > 0:
            summary["overall_level"] = PerformanceLevel.CRITICAL
        elif poor_count > 2:
            summary["overall_level"] = PerformanceLevel.POOR
        elif poor_count > 0:
            summary["overall_level"] = PerformanceLevel.FAIR
        
        # Generate recommendations
        summary["recommendations"] = self._generate_recommendations(summary["metrics"])
        
        return summary
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations."""
        
        recommendations = []
        
        for metric_name, data in metrics.items():
            level = data["level"]
            trend = data["trend"]
            
            if level == "critical":
                if metric_name == "response_time":
                    recommendations.append("Response time is critical - consider scaling or optimization")
                elif metric_name == "cpu_usage":
                    recommendations.append("CPU usage is critical - consider adding more resources")
                elif metric_name == "memory_usage":
                    recommendations.append("Memory usage is critical - consider memory optimization")
                elif metric_name == "error_rate":
                    recommendations.append("Error rate is critical - investigate and fix issues")
            
            elif level == "poor" and trend == "increasing":
                if metric_name == "response_time":
                    recommendations.append("Response time is degrading - monitor closely")
                elif metric_name == "cache_hit_rate":
                    recommendations.append("Cache hit rate is low - review caching strategy")
        
        return recommendations


class PerformanceAlertManager:
    """Manages performance alerts and notifications."""
    
    def __init__(self):
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.alert_handlers: List[Callable] = []
        self.logger = logging.getLogger(__name__)
    
    def add_alert_handler(self, handler: Callable):
        """Add alert handler function."""
        self.alert_handlers.append(handler)
    
    def check_alerts(self, analyzer: PerformanceAnalyzer) -> List[PerformanceAlert]:
        """Check for performance alerts."""
        
        new_alerts = []
        
        for metric_name in analyzer.metrics_history.keys():
            level = analyzer.analyze_performance_level(metric_name)
            
            if level in [PerformanceLevel.CRITICAL, PerformanceLevel.POOR]:
                alert_id = f"{metric_name}_{level.value}"
                
                # Check if alert already exists
                if alert_id not in self.active_alerts:
                    # Create new alert
                    history = analyzer.metrics_history[metric_name]
                    current_value = history[-1]["value"] if history else 0
                    
                    threshold = analyzer.thresholds.get(metric_name)
                    threshold_value = threshold.critical_threshold if threshold else 0
                    
                    alert = PerformanceAlert(
                        id=alert_id,
                        metric_name=metric_name,
                        level=level,
                        message=f"{metric_name} is {level.value}",
                        timestamp=datetime.now(),
                        value=current_value,
                        threshold=threshold_value
                    )
                    
                    self.active_alerts[alert_id] = alert
                    new_alerts.append(alert)
                    
                    # Send alert
                    await self._send_alert(alert)
        
        return new_alerts
    
    async def _send_alert(self, alert: PerformanceAlert):
        """Send alert to all handlers."""
        
        self.logger.warning(f"Performance alert: {alert.message}")
        
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler error: {e}")
    
    def clear_alert(self, alert_id: str):
        """Clear an active alert."""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())


class RealTimePerformanceMonitor:
    """Real-time performance monitoring system."""
    
    def __init__(self, update_interval: int = 10):
        self.update_interval = update_interval
        self.analyzer = PerformanceAnalyzer()
        self.alert_manager = PerformanceAlertManager()
        self.is_running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(__name__)
        
        # Custom metrics
        self.custom_metrics = {}
        self._setup_custom_metrics()
    
    def _setup_custom_metrics(self):
        """Setup custom Prometheus metrics."""
        
        # Performance metrics
        self.custom_metrics.update({
            "performance_level": Gauge(
                'easypay_performance_level',
                'Current performance level',
                ['metric_name']
            ),
            "performance_trend": Gauge(
                'easypay_performance_trend',
                'Performance trend',
                ['metric_name', 'trend']
            ),
            "active_alerts": Gauge(
                'easypay_active_alerts',
                'Number of active performance alerts',
                ['level']
            ),
            "system_load": Gauge(
                'easypay_system_load',
                'System load average',
                ['period']
            ),
            "disk_io": Counter(
                'easypay_disk_io_total',
                'Disk I/O operations',
                ['operation', 'device']
            ),
            "network_io": Counter(
                'easypay_network_io_total',
                'Network I/O operations',
                ['operation', 'interface']
            )
        })
    
    async def start_monitoring(self):
        """Start real-time monitoring."""
        
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
        self.logger.info("Real-time performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop real-time monitoring."""
        
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Real-time performance monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        
        while self.is_running:
            try:
                await self._collect_metrics()
                await self._update_prometheus_metrics()
                await self._check_alerts()
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _collect_metrics(self):
        """Collect system and application metrics."""
        
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        
        # Record metrics
        self.analyzer.record_metric("cpu_usage", cpu_percent)
        self.analyzer.record_metric("memory_usage", memory.percent)
        self.analyzer.record_metric("disk_usage", disk_usage.percent)
        
        # Load average
        load_avg = psutil.getloadavg()
        self.analyzer.record_metric("load_1min", load_avg[0])
        self.analyzer.record_metric("load_5min", load_avg[1])
        self.analyzer.record_metric("load_15min", load_avg[2])
        
        # Network I/O
        net_io = psutil.net_io_counters()
        self.analyzer.record_metric("network_bytes_sent", net_io.bytes_sent)
        self.analyzer.record_metric("network_bytes_recv", net_io.bytes_recv)
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        if disk_io:
            self.analyzer.record_metric("disk_read_bytes", disk_io.read_bytes)
            self.analyzer.record_metric("disk_write_bytes", disk_io.write_bytes)
    
    async def _update_prometheus_metrics(self):
        """Update Prometheus metrics."""
        
        # Update performance levels
        for metric_name in self.analyzer.metrics_history.keys():
            level = self.analyzer.analyze_performance_level(metric_name)
            trend = self.analyzer.get_metric_trend(metric_name)
            
            self.custom_metrics["performance_level"].labels(
                metric_name=metric_name
            ).set(level.value)
            
            self.custom_metrics["performance_trend"].labels(
                metric_name=metric_name,
                trend=trend["trend"]
            ).set(trend["change_percent"])
        
        # Update active alerts
        alerts = self.alert_manager.get_active_alerts()
        alert_counts = defaultdict(int)
        for alert in alerts:
            alert_counts[alert.level.value] += 1
        
        for level, count in alert_counts.items():
            self.custom_metrics["active_alerts"].labels(level=level).set(count)
        
        # Update system load
        load_avg = psutil.getloadavg()
        self.custom_metrics["system_load"].labels(period="1min").set(load_avg[0])
        self.custom_metrics["system_load"].labels(period="5min").set(load_avg[1])
        self.custom_metrics["system_load"].labels(period="15min").set(load_avg[2])
    
    async def _check_alerts(self):
        """Check for performance alerts."""
        await self.alert_manager.check_alerts(self.analyzer)
    
    def get_performance_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard."""
        
        summary = self.analyzer.get_performance_summary()
        alerts = self.alert_manager.get_active_alerts()
        
        return {
            "summary": summary,
            "alerts": [asdict(alert) for alert in alerts],
            "timestamp": datetime.now().isoformat(),
            "monitoring_status": "active" if self.is_running else "inactive"
        }
    
    def add_custom_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """Add custom metric."""
        
        self.analyzer.record_metric(name, value)
        
        if labels:
            # Update Prometheus metric if it exists
            if name in self.custom_metrics:
                metric = self.custom_metrics[name]
                if hasattr(metric, 'labels'):
                    metric.labels(**labels).set(value)


# Global performance monitor instance
_performance_monitor: Optional[RealTimePerformanceMonitor] = None


def get_performance_monitor() -> RealTimePerformanceMonitor:
    """Get the global performance monitor."""
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = RealTimePerformanceMonitor()
    
    return _performance_monitor


async def init_performance_monitoring() -> RealTimePerformanceMonitor:
    """Initialize performance monitoring system."""
    global _performance_monitor
    
    _performance_monitor = RealTimePerformanceMonitor()
    
    # Add alert handlers
    async def log_alert(alert: PerformanceAlert):
        logging.getLogger(__name__).warning(f"Performance alert: {alert.message}")
    
    _performance_monitor.alert_manager.add_alert_handler(log_alert)
    
    # Start monitoring
    await _performance_monitor.start_monitoring()
    
    logging.getLogger(__name__).info("Performance monitoring system initialized")
    
    return _performance_monitor


async def close_performance_monitoring():
    """Close performance monitoring system."""
    global _performance_monitor
    
    if _performance_monitor:
        await _performance_monitor.stop_monitoring()
        _performance_monitor = None
        
        logging.getLogger(__name__).info("Performance monitoring system closed")
