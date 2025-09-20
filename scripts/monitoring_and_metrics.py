#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Monitoring and Metrics Script

This script provides comprehensive monitoring and metrics collection for the payment gateway APIs.
It tracks usage patterns, performance metrics, and provides real-time monitoring capabilities.

Usage:
    python scripts/monitoring_and_metrics.py [--base-url URL] [--duration SECONDS] [--interval SECONDS]
"""

import asyncio
import json
import sys
import os
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
import argparse
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: str
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a time period."""
    timestamp: str
    duration: int  # seconds
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    average_response_time: float
    min_response_time: float
    max_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    status_code_distribution: Dict[str, int]
    endpoint_distribution: Dict[str, int]
    error_distribution: Dict[str, int]


class PaymentGatewayMonitor:
    """Comprehensive payment gateway monitoring system."""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 interval: int = 10, max_history: int = 1000):
        self.base_url = base_url
        self.interval = interval
        self.max_history = max_history
        self.client = httpx.AsyncClient(timeout=30.0)
        self.metrics_history: deque = deque(maxlen=max_history)
        self.running = False
        
        # Test endpoints to monitor
        self.monitored_endpoints = [
            ("/health", "GET"),
            ("/health/ready", "GET"),
            ("/api/v1/payments/", "GET"),
            ("/api/v1/payments/", "POST"),
            ("/api/v1/subscriptions/", "GET"),
            ("/api/v1/webhooks/health", "GET")
        ]
        
        # Performance thresholds
        self.thresholds = {
            "response_time_warning": 1.0,  # seconds
            "response_time_critical": 3.0,  # seconds
            "success_rate_warning": 95.0,  # percentage
            "success_rate_critical": 90.0,  # percentage
        }
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def collect_metric(self, endpoint: str, method: str) -> MetricPoint:
        """Collect a single metric point."""
        try:
            start_time = time.time()
            
            if method == "GET":
                response = await self.client.get(f"{self.base_url}{endpoint}")
            elif method == "POST":
                # For POST requests, use a simple test payload
                test_data = {
                    "amount": "1.00",
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "customer_id": "monitor_test",
                    "customer_email": "monitor@example.com",
                    "is_test": True
                }
                response = await self.client.post(
                    f"{self.base_url}{endpoint}",
                    json=test_data,
                    headers={"Content-Type": "application/json"}
                )
            else:
                response = await self.client.request(method, f"{self.base_url}{endpoint}")
            
            response_time = time.time() - start_time
            
            return MetricPoint(
                timestamp=datetime.now().isoformat(),
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time=response_time,
                success=200 <= response.status_code < 400,
                error_message=None
            )
            
        except Exception as e:
            return MetricPoint(
                timestamp=datetime.now().isoformat(),
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time=0.0,
                success=False,
                error_message=str(e)
            )
    
    async def collect_metrics_cycle(self) -> List[MetricPoint]:
        """Collect metrics for all monitored endpoints."""
        metrics = []
        
        for endpoint, method in self.monitored_endpoints:
            metric = await self.collect_metric(endpoint, method)
            metrics.append(metric)
            self.metrics_history.append(metric)
        
        return metrics
    
    def aggregate_metrics(self, duration: int = 60) -> AggregatedMetrics:
        """Aggregate metrics for the specified duration."""
        cutoff_time = datetime.now() - timedelta(seconds=duration)
        
        # Filter metrics within the time window
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m.timestamp) >= cutoff_time
        ]
        
        if not recent_metrics:
            return AggregatedMetrics(
                timestamp=datetime.now().isoformat(),
                duration=duration,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0.0,
                average_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                median_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                status_code_distribution={},
                endpoint_distribution={},
                error_distribution={}
            )
        
        # Calculate basic metrics
        total_requests = len(recent_metrics)
        successful_requests = sum(1 for m in recent_metrics if m.success)
        failed_requests = total_requests - successful_requests
        success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
        
        # Calculate response time metrics
        response_times = [m.response_time for m in recent_metrics if m.response_time > 0]
        
        if response_times:
            average_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            median_response_time = statistics.median(response_times)
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
        else:
            average_response_time = 0.0
            min_response_time = 0.0
            max_response_time = 0.0
            median_response_time = 0.0
            p95_response_time = 0.0
            p99_response_time = 0.0
        
        # Calculate distributions
        status_code_distribution = defaultdict(int)
        endpoint_distribution = defaultdict(int)
        error_distribution = defaultdict(int)
        
        for metric in recent_metrics:
            status_code_distribution[str(metric.status_code)] += 1
            endpoint_distribution[metric.endpoint] += 1
            if metric.error_message:
                error_distribution[metric.error_message] += 1
        
        return AggregatedMetrics(
            timestamp=datetime.now().isoformat(),
            duration=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            average_response_time=average_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            status_code_distribution=dict(status_code_distribution),
            endpoint_distribution=dict(endpoint_distribution),
            error_distribution=dict(error_distribution)
        )
    
    def check_alerts(self, metrics: AggregatedMetrics) -> List[str]:
        """Check for alert conditions."""
        alerts = []
        
        # Response time alerts
        if metrics.average_response_time > self.thresholds["response_time_critical"]:
            alerts.append(f"🚨 CRITICAL: Average response time {metrics.average_response_time:.3f}s exceeds critical threshold")
        elif metrics.average_response_time > self.thresholds["response_time_warning"]:
            alerts.append(f"⚠️  WARNING: Average response time {metrics.average_response_time:.3f}s exceeds warning threshold")
        
        # Success rate alerts
        if metrics.success_rate < self.thresholds["success_rate_critical"]:
            alerts.append(f"🚨 CRITICAL: Success rate {metrics.success_rate:.1f}% below critical threshold")
        elif metrics.success_rate < self.thresholds["success_rate_warning"]:
            alerts.append(f"⚠️  WARNING: Success rate {metrics.success_rate:.1f}% below warning threshold")
        
        # High error rate alerts
        if metrics.failed_requests > 0:
            error_rate = (metrics.failed_requests / metrics.total_requests) * 100
            if error_rate > 10:  # More than 10% errors
                alerts.append(f"🚨 CRITICAL: High error rate {error_rate:.1f}%")
            elif error_rate > 5:  # More than 5% errors
                alerts.append(f"⚠️  WARNING: Elevated error rate {error_rate:.1f}%")
        
        return alerts
    
    def print_metrics_summary(self, metrics: AggregatedMetrics):
        """Print a formatted metrics summary."""
        print(f"\n📊 Metrics Summary ({metrics.duration}s window)")
        print("-" * 50)
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful: {metrics.successful_requests} ({metrics.success_rate:.1f}%)")
        print(f"Failed: {metrics.failed_requests}")
        print(f"Average Response Time: {metrics.average_response_time:.3f}s")
        print(f"Response Time Range: {metrics.min_response_time:.3f}s - {metrics.max_response_time:.3f}s")
        print(f"Median Response Time: {metrics.median_response_time:.3f}s")
        print(f"95th Percentile: {metrics.p95_response_time:.3f}s")
        print(f"99th Percentile: {metrics.p99_response_time:.3f}s")
        
        if metrics.status_code_distribution:
            print(f"\nStatus Code Distribution:")
            for code, count in sorted(metrics.status_code_distribution.items()):
                percentage = (count / metrics.total_requests) * 100
                print(f"  {code}: {count} ({percentage:.1f}%)")
        
        if metrics.endpoint_distribution:
            print(f"\nEndpoint Distribution:")
            for endpoint, count in sorted(metrics.endpoint_distribution.items()):
                percentage = (count / metrics.total_requests) * 100
                print(f"  {endpoint}: {count} ({percentage:.1f}%)")
        
        if metrics.error_distribution:
            print(f"\nError Distribution:")
            for error, count in sorted(metrics.error_distribution.items()):
                percentage = (count / metrics.total_requests) * 100
                print(f"  {error}: {count} ({percentage:.1f}%)")
    
    async def monitor_continuously(self, duration: int = 300):
        """Monitor continuously for the specified duration."""
        print(f"🔍 Starting continuous monitoring for {duration} seconds")
        print(f"📡 Monitoring {self.base_url}")
        print(f"⏱️  Collection interval: {self.interval} seconds")
        print(f"🚨 Alert thresholds:")
        print(f"   Response time warning: {self.thresholds['response_time_warning']}s")
        print(f"   Response time critical: {self.thresholds['response_time_critical']}s")
        print(f"   Success rate warning: {self.thresholds['success_rate_warning']}%")
        print(f"   Success rate critical: {self.thresholds['success_rate_critical']}%")
        print("=" * 60)
        
        self.running = True
        start_time = time.time()
        
        try:
            while self.running and (time.time() - start_time) < duration:
                cycle_start = time.time()
                
                # Collect metrics
                await self.collect_metrics_cycle()
                
                # Aggregate and display metrics
                metrics = self.aggregate_metrics(60)  # 60-second window
                self.print_metrics_summary(metrics)
                
                # Check for alerts
                alerts = self.check_alerts(metrics)
                if alerts:
                    print("\n🚨 ALERTS:")
                    for alert in alerts:
                        print(f"  {alert}")
                
                # Wait for next cycle
                cycle_time = time.time() - cycle_start
                sleep_time = max(0, self.interval - cycle_time)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
                print("=" * 60)
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        finally:
            self.running = False
    
    def stop_monitoring(self):
        """Stop the monitoring process."""
        self.running = False
    
    def export_metrics(self, filename: Optional[str] = None) -> str:
        """Export collected metrics to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"payment_gateway_metrics_{timestamp}.json"
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "collection_interval": self.interval,
            "total_metrics_collected": len(self.metrics_history),
            "thresholds": self.thresholds,
            "metrics": [asdict(m) for m in self.metrics_history],
            "aggregated_metrics": [
                asdict(self.aggregate_metrics(60)),
                asdict(self.aggregate_metrics(300)),
                asdict(self.aggregate_metrics(900))
            ]
        }
        
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return filename


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Payment Gateway Monitoring and Metrics")
    parser.add_argument("--base-url", default="http://localhost:8000",
                       help="Base URL for the API (default: http://localhost:8000)")
    parser.add_argument("--duration", type=int, default=300,
                       help="Monitoring duration in seconds (default: 300)")
    parser.add_argument("--interval", type=int, default=10,
                       help="Metrics collection interval in seconds (default: 10)")
    parser.add_argument("--export", action="store_true",
                       help="Export metrics to JSON file at the end")
    
    args = parser.parse_args()
    
    print("🔍 EasyPay Payment Gateway - Monitoring and Metrics")
    print("=" * 60)
    
    async with PaymentGatewayMonitor(args.base_url, args.interval) as monitor:
        # Set up signal handler for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\n📊 Received signal {signum}, stopping monitoring...")
            monitor.stop_monitoring()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            await monitor.monitor_continuously(args.duration)
        except Exception as e:
            print(f"💥 Monitoring error: {e}")
            return 1
        
        # Export metrics if requested
        if args.export:
            filename = monitor.export_metrics()
            print(f"\n📄 Metrics exported to: {filename}")
        
        # Final summary
        final_metrics = monitor.aggregate_metrics(args.duration)
        print(f"\n📊 Final Summary ({args.duration}s total)")
        print("-" * 40)
        print(f"Total Metrics Collected: {len(monitor.metrics_history)}")
        print(f"Average Response Time: {final_metrics.average_response_time:.3f}s")
        print(f"Success Rate: {final_metrics.success_rate:.1f}%")
        print(f"Total Requests: {final_metrics.total_requests}")
        
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
