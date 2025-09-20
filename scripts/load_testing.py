#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Load Testing Script

This script provides comprehensive load testing for the payment gateway APIs.
It simulates high concurrent usage and measures performance under load.

Usage:
    python scripts/load_testing.py [--base-url URL] [--concurrent-users N] [--duration SECONDS] [--ramp-up SECONDS]
"""

import asyncio
import json
import sys
import os
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
import argparse
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics
import aiohttp
from concurrent.futures import ThreadPoolExecutor


@dataclass
class LoadTestResult:
    """Result of a single load test request."""
    timestamp: str
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class LoadTestSummary:
    """Summary of load test results."""
    test_duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    requests_per_second: float
    average_response_time: float
    min_response_time: float
    max_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    status_code_distribution: Dict[str, int]
    endpoint_performance: Dict[str, Dict[str, Any]]
    error_summary: Dict[str, int]


class LoadTester:
    """Comprehensive load testing system for payment gateway APIs."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[LoadTestResult] = []
        
        # Test scenarios
        self.scenarios = [
            {
                "name": "Health Check",
                "endpoint": "/health",
                "method": "GET",
                "weight": 20
            },
            {
                "name": "Payment List",
                "endpoint": "/api/v1/payments/?page=1&per_page=10",
                "method": "GET",
                "weight": 30
            },
            {
                "name": "Create Payment",
                "endpoint": "/api/v1/payments/",
                "method": "POST",
                "weight": 40
            },
            {
                "name": "Subscription List",
                "endpoint": "/api/v1/subscriptions/?page=1&per_page=5",
                "method": "GET",
                "weight": 10
            }
        ]
        
        # Test data generators
        self.test_customers = [
            {"id": f"load_test_{i}", "email": f"loadtest{i}@example.com", "name": f"Load Test User {i}"}
            for i in range(100)
        ]
        
        self.test_cards = [
            "tok_visa_4242",
            "tok_mastercard_5555", 
            "tok_amex_3782",
            "tok_discover_6011"
        ]
    
    def generate_payment_data(self, user_id: str) -> Dict[str, Any]:
        """Generate test payment data."""
        customer = random.choice(self.test_customers)
        amount = round(random.uniform(1.00, 100.00), 2)
        
        return {
            "amount": str(amount),
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": customer["id"],
            "customer_email": customer["email"],
            "customer_name": customer["name"],
            "card_token": random.choice(self.test_cards),
            "description": f"Load test payment - {user_id}",
            "metadata": {
                "load_test": True,
                "user_id": user_id,
                "test_run": datetime.now().isoformat(),
                "amount_category": "low" if amount < 25 else "medium" if amount < 75 else "high"
            },
            "is_test": True
        }
    
    async def make_request(self, scenario: Dict[str, Any], user_id: str) -> LoadTestResult:
        """Make a single request for load testing."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if scenario["method"] == "GET":
                    response = await client.get(f"{self.base_url}{scenario['endpoint']}")
                elif scenario["method"] == "POST":
                    if scenario["name"] == "Create Payment":
                        data = self.generate_payment_data(user_id)
                    else:
                        data = {}
                    
                    response = await client.post(
                        f"{self.base_url}{scenario['endpoint']}",
                        json=data,
                        headers={"Content-Type": "application/json"}
                    )
                else:
                    response = await client.request(scenario["method"], f"{self.base_url}{scenario['endpoint']}")
                
                response_time = time.time() - start_time
                
                return LoadTestResult(
                    timestamp=datetime.now().isoformat(),
                    endpoint=scenario["endpoint"],
                    method=scenario["method"],
                    status_code=response.status_code,
                    response_time=response_time,
                    success=200 <= response.status_code < 400,
                    user_id=user_id
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            return LoadTestResult(
                timestamp=datetime.now().isoformat(),
                endpoint=scenario["endpoint"],
                method=scenario["method"],
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=str(e),
                user_id=user_id
            )
    
    async def user_simulation(self, user_id: str, duration: float, requests_per_second: float):
        """Simulate a single user's behavior."""
        request_interval = 1.0 / requests_per_second
        start_time = time.time()
        
        while time.time() - start_time < duration:
            # Select scenario based on weights
            scenario = self.select_scenario()
            
            # Make request
            result = await self.make_request(scenario, user_id)
            self.results.append(result)
            
            # Wait for next request
            await asyncio.sleep(request_interval)
    
    def select_scenario(self) -> Dict[str, Any]:
        """Select a test scenario based on weights."""
        total_weight = sum(scenario["weight"] for scenario in self.scenarios)
        random_weight = random.uniform(0, total_weight)
        
        current_weight = 0
        for scenario in self.scenarios:
            current_weight += scenario["weight"]
            if random_weight <= current_weight:
                return scenario
        
        return self.scenarios[0]  # Fallback
    
    async def run_load_test(self, concurrent_users: int, duration: float, ramp_up: float = 0):
        """Run the load test."""
        print(f"🚀 Starting Load Test")
        print(f"📡 Target: {self.base_url}")
        print(f"👥 Concurrent Users: {concurrent_users}")
        print(f"⏱️  Duration: {duration} seconds")
        print(f"📈 Ramp-up: {ramp_up} seconds")
        print("=" * 60)
        
        start_time = time.time()
        
        # Calculate requests per second per user
        requests_per_second = 1.0  # Start with 1 RPS per user
        
        # Create user tasks
        tasks = []
        for i in range(concurrent_users):
            user_id = f"user_{i:03d}"
            task = asyncio.create_task(
                self.user_simulation(user_id, duration, requests_per_second)
            )
            tasks.append(task)
            
            # Ramp-up delay
            if ramp_up > 0:
                await asyncio.sleep(ramp_up / concurrent_users)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        test_duration = time.time() - start_time
        
        print(f"\n✅ Load test completed in {test_duration:.2f} seconds")
        return test_duration
    
    def calculate_summary(self, test_duration: float) -> LoadTestSummary:
        """Calculate load test summary."""
        if not self.results:
            return LoadTestSummary(
                test_duration=test_duration,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0.0,
                requests_per_second=0.0,
                average_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                median_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                status_code_distribution={},
                endpoint_performance={},
                error_summary={}
            )
        
        total_requests = len(self.results)
        successful_requests = sum(1 for r in self.results if r.success)
        failed_requests = total_requests - successful_requests
        success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        
        # Response time statistics
        response_times = [r.response_time for r in self.results if r.response_time > 0]
        
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
        
        # Status code distribution
        status_code_distribution = defaultdict(int)
        for result in self.results:
            status_code_distribution[str(result.status_code)] += 1
        
        # Endpoint performance
        endpoint_performance = defaultdict(lambda: {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "success_rate": 0.0,
            "average_response_time": 0.0,
            "min_response_time": 0.0,
            "max_response_time": 0.0
        })
        
        for result in self.results:
            endpoint = result.endpoint
            perf = endpoint_performance[endpoint]
            perf["total_requests"] += 1
            if result.success:
                perf["successful_requests"] += 1
            else:
                perf["failed_requests"] += 1
            
            if result.response_time > 0:
                if perf["min_response_time"] == 0 or result.response_time < perf["min_response_time"]:
                    perf["min_response_time"] = result.response_time
                if result.response_time > perf["max_response_time"]:
                    perf["max_response_time"] = result.response_time
        
        # Calculate endpoint averages
        for endpoint, perf in endpoint_performance.items():
            if perf["total_requests"] > 0:
                perf["success_rate"] = (perf["successful_requests"] / perf["total_requests"]) * 100
                
                endpoint_times = [r.response_time for r in self.results 
                                if r.endpoint == endpoint and r.response_time > 0]
                if endpoint_times:
                    perf["average_response_time"] = statistics.mean(endpoint_times)
        
        # Error summary
        error_summary = defaultdict(int)
        for result in self.results:
            if result.error_message:
                error_summary[result.error_message] += 1
        
        return LoadTestSummary(
            test_duration=test_duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            requests_per_second=requests_per_second,
            average_response_time=average_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            status_code_distribution=dict(status_code_distribution),
            endpoint_performance=dict(endpoint_performance),
            error_summary=dict(error_summary)
        )
    
    def print_summary(self, summary: LoadTestSummary):
        """Print load test summary."""
        print(f"\n📊 Load Test Summary")
        print("=" * 60)
        print(f"Test Duration: {summary.test_duration:.2f} seconds")
        print(f"Total Requests: {summary.total_requests}")
        print(f"Successful Requests: {summary.successful_requests}")
        print(f"Failed Requests: {summary.failed_requests}")
        print(f"Success Rate: {summary.success_rate:.2f}%")
        print(f"Requests per Second: {summary.requests_per_second:.2f}")
        print(f"Average Response Time: {summary.average_response_time:.3f}s")
        print(f"Min Response Time: {summary.min_response_time:.3f}s")
        print(f"Max Response Time: {summary.max_response_time:.3f}s")
        print(f"Median Response Time: {summary.median_response_time:.3f}s")
        print(f"95th Percentile: {summary.p95_response_time:.3f}s")
        print(f"99th Percentile: {summary.p99_response_time:.3f}s")
        
        if summary.status_code_distribution:
            print(f"\nStatus Code Distribution:")
            for code, count in sorted(summary.status_code_distribution.items()):
                percentage = (count / summary.total_requests) * 100
                print(f"  {code}: {count} ({percentage:.1f}%)")
        
        if summary.endpoint_performance:
            print(f"\nEndpoint Performance:")
            for endpoint, perf in summary.endpoint_performance.items():
                print(f"  {endpoint}:")
                print(f"    Requests: {perf['total_requests']}")
                print(f"    Success Rate: {perf['success_rate']:.1f}%")
                print(f"    Avg Response Time: {perf['average_response_time']:.3f}s")
                print(f"    Response Time Range: {perf['min_response_time']:.3f}s - {perf['max_response_time']:.3f}s")
        
        if summary.error_summary:
            print(f"\nError Summary:")
            for error, count in sorted(summary.error_summary.items()):
                percentage = (count / summary.total_requests) * 100
                print(f"  {error}: {count} ({percentage:.1f}%)")
    
    def export_results(self, summary: LoadTestSummary, filename: Optional[str] = None) -> str:
        """Export load test results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
        
        export_data = {
            "test_info": {
                "base_url": self.base_url,
                "test_timestamp": datetime.now().isoformat(),
                "summary": asdict(summary)
            },
            "detailed_results": [asdict(result) for result in self.results]
        }
        
        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return filename


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Payment Gateway Load Testing")
    parser.add_argument("--base-url", default="http://localhost:8000",
                       help="Base URL for the API (default: http://localhost:8000)")
    parser.add_argument("--concurrent-users", type=int, default=10,
                       help="Number of concurrent users (default: 10)")
    parser.add_argument("--duration", type=int, default=60,
                       help="Test duration in seconds (default: 60)")
    parser.add_argument("--ramp-up", type=int, default=10,
                       help="Ramp-up time in seconds (default: 10)")
    parser.add_argument("--export", action="store_true",
                       help="Export results to JSON file")
    
    args = parser.parse_args()
    
    print("🚀 EasyPay Payment Gateway - Load Testing")
    print("=" * 60)
    
    tester = LoadTester(args.base_url)
    
    try:
        test_duration = await tester.run_load_test(
            args.concurrent_users, 
            args.duration, 
            args.ramp_up
        )
        
        summary = tester.calculate_summary(test_duration)
        tester.print_summary(summary)
        
        if args.export:
            filename = tester.export_results(summary)
            print(f"\n📄 Results exported to: {filename}")
        
        # Performance assessment
        print(f"\n🎯 Performance Assessment:")
        if summary.success_rate >= 95:
            print("✅ Excellent success rate")
        elif summary.success_rate >= 90:
            print("⚠️  Good success rate")
        else:
            print("❌ Poor success rate - needs investigation")
        
        if summary.average_response_time <= 1.0:
            print("✅ Excellent response time")
        elif summary.average_response_time <= 2.0:
            print("⚠️  Good response time")
        else:
            print("❌ Poor response time - needs optimization")
        
        if summary.requests_per_second >= 100:
            print("✅ High throughput")
        elif summary.requests_per_second >= 50:
            print("⚠️  Moderate throughput")
        else:
            print("❌ Low throughput - needs scaling")
        
        return 0 if summary.success_rate >= 90 and summary.average_response_time <= 2.0 else 1
        
    except Exception as e:
        print(f"💥 Load test error: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Load test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
