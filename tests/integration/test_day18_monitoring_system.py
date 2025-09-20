#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Day 18 Monitoring System Test Script

This script tests all the monitoring and logging functionality implemented in Day 18.
"""

import asyncio
import json
import time
import requests
import sys
from typing import Dict, Any, List
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3000"
KIBANA_URL = "http://localhost:5601"

class MonitoringSystemTester:
    """Test suite for the monitoring system."""
    
    def __init__(self):
        self.results = []
        self.start_time = time.time()
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
    
    def test_health_endpoints(self) -> bool:
        """Test all health check endpoints."""
        print("\n🔍 Testing Health Check Endpoints...")
        
        endpoints = [
            "/health/",
            "/health/ready",
            "/health/live",
            "/health/detailed",
            "/health/metrics",
            "/health/startup",
            "/health/dependencies",
            "/health/performance"
        ]
        
        all_passed = True
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.log_test_result(
                        f"Health endpoint {endpoint}",
                        True,
                        f"Status: {data.get('status', 'unknown')}"
                    )
                else:
                    self.log_test_result(
                        f"Health endpoint {endpoint}",
                        False,
                        f"HTTP {response.status_code}"
                    )
                    all_passed = False
            except Exception as e:
                self.log_test_result(
                    f"Health endpoint {endpoint}",
                    False,
                    str(e)
                )
                all_passed = False
        
        return all_passed
    
    def test_prometheus_metrics(self) -> bool:
        """Test Prometheus metrics collection."""
        print("\n📊 Testing Prometheus Metrics...")
        
        try:
            # Test Prometheus is running
            response = requests.get(f"{PROMETHEUS_URL}/api/v1/status/config", timeout=10)
            if response.status_code == 200:
                self.log_test_result("Prometheus running", True)
            else:
                self.log_test_result("Prometheus running", False, f"HTTP {response.status_code}")
                return False
            
            # Test metrics endpoint
            response = requests.get(f"{BASE_URL}/metrics", timeout=10)
            if response.status_code == 200:
                metrics_data = response.text
                if "easypay_" in metrics_data:
                    self.log_test_result("Metrics endpoint", True, "EasyPay metrics found")
                else:
                    self.log_test_result("Metrics endpoint", False, "No EasyPay metrics found")
                    return False
            else:
                self.log_test_result("Metrics endpoint", False, f"HTTP {response.status_code}")
                return False
            
            # Test specific metrics
            metrics_to_check = [
                "easypay_http_requests_total",
                "easypay_payments_total",
                "easypay_webhooks_total",
                "easypay_auth_attempts_total",
                "easypay_system_cpu_usage_percent",
                "easypay_system_memory_usage_bytes"
            ]
            
            for metric in metrics_to_check:
                response = requests.get(
                    f"{PROMETHEUS_URL}/api/v1/query",
                    params={"query": metric},
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        self.log_test_result(f"Metric {metric}", True)
                    else:
                        self.log_test_result(f"Metric {metric}", False, "Query failed")
                        return False
                else:
                    self.log_test_result(f"Metric {metric}", False, f"HTTP {response.status_code}")
                    return False
            
            return True
            
        except Exception as e:
            self.log_test_result("Prometheus metrics", False, str(e))
            return False
    
    def test_grafana_dashboards(self) -> bool:
        """Test Grafana dashboards."""
        print("\n📈 Testing Grafana Dashboards...")
        
        try:
            # Test Grafana is running
            response = requests.get(f"{GRAFANA_URL}/api/health", timeout=10)
            if response.status_code == 200:
                self.log_test_result("Grafana running", True)
            else:
                self.log_test_result("Grafana running", False, f"HTTP {response.status_code}")
                return False
            
            # Test dashboard API
            response = requests.get(f"{GRAFANA_URL}/api/search", timeout=10)
            if response.status_code == 200:
                self.log_test_result("Grafana API", True)
            else:
                self.log_test_result("Grafana API", False, f"HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            self.log_test_result("Grafana dashboards", False, str(e))
            return False
    
    def test_log_aggregation(self) -> bool:
        """Test log aggregation (ELK stack)."""
        print("\n📝 Testing Log Aggregation...")
        
        try:
            # Test Elasticsearch
            response = requests.get(f"http://localhost:9200/_cluster/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ["green", "yellow"]:
                    self.log_test_result("Elasticsearch running", True, f"Status: {data.get('status')}")
                else:
                    self.log_test_result("Elasticsearch running", False, f"Status: {data.get('status')}")
                    return False
            else:
                self.log_test_result("Elasticsearch running", False, f"HTTP {response.status_code}")
                return False
            
            # Test Kibana
            response = requests.get(f"{KIBANA_URL}/api/status", timeout=10)
            if response.status_code == 200:
                self.log_test_result("Kibana running", True)
            else:
                self.log_test_result("Kibana running", False, f"HTTP {response.status_code}")
                return False
            
            # Test Logstash
            response = requests.get("http://localhost:9600/_node/stats", timeout=10)
            if response.status_code == 200:
                self.log_test_result("Logstash running", True)
            else:
                self.log_test_result("Logstash running", False, f"HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            self.log_test_result("Log aggregation", False, str(e))
            return False
    
    def test_alerting_rules(self) -> bool:
        """Test Prometheus alerting rules."""
        print("\n🚨 Testing Alerting Rules...")
        
        try:
            # Test alerting rules endpoint
            response = requests.get(f"{PROMETHEUS_URL}/api/v1/rules", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    rules = data.get("data", {}).get("groups", [])
                    if rules:
                        self.log_test_result("Alerting rules loaded", True, f"{len(rules)} rule groups")
                    else:
                        self.log_test_result("Alerting rules loaded", False, "No rules found")
                        return False
                else:
                    self.log_test_result("Alerting rules loaded", False, "API error")
                    return False
            else:
                self.log_test_result("Alerting rules loaded", False, f"HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            self.log_test_result("Alerting rules", False, str(e))
            return False
    
    def test_metrics_middleware(self) -> bool:
        """Test metrics middleware by making requests."""
        print("\n🔄 Testing Metrics Middleware...")
        
        try:
            # Make several requests to generate metrics
            endpoints_to_test = [
                "/health/",
                "/health/ready",
                "/health/live",
                "/api/v1/version"
            ]
            
            for endpoint in endpoints_to_test:
                try:
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                    if response.status_code in [200, 503]:  # 503 is expected for readiness if deps are down
                        self.log_test_result(f"Request to {endpoint}", True, f"Status: {response.status_code}")
                    else:
                        self.log_test_result(f"Request to {endpoint}", False, f"HTTP {response.status_code}")
                except Exception as e:
                    self.log_test_result(f"Request to {endpoint}", False, str(e))
            
            # Wait a moment for metrics to be collected
            time.sleep(2)
            
            # Check if metrics were recorded
            response = requests.get(f"{BASE_URL}/health/metrics", timeout=10)
            if response.status_code == 200:
                metrics = response.json()
                if metrics.get("metrics", {}).get("request_count", 0) > 0:
                    self.log_test_result("Metrics middleware", True, "Request metrics recorded")
                else:
                    self.log_test_result("Metrics middleware", False, "No request metrics found")
                    return False
            else:
                self.log_test_result("Metrics middleware", False, f"HTTP {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            self.log_test_result("Metrics middleware", False, str(e))
            return False
    
    def test_structured_logging(self) -> bool:
        """Test structured logging."""
        print("\n📋 Testing Structured Logging...")
        
        try:
            # Test if log files are being created
            import os
            log_file = "logs/easypay.log"
            if os.path.exists(log_file):
                self.log_test_result("Log file creation", True, f"Log file exists: {log_file}")
                
                # Check if log file has content
                with open(log_file, 'r') as f:
                    content = f.read()
                    if content.strip():
                        self.log_test_result("Log file content", True, "Log file has content")
                    else:
                        self.log_test_result("Log file content", False, "Log file is empty")
                        return False
            else:
                self.log_test_result("Log file creation", False, "Log file not found")
                return False
            
            return True
            
        except Exception as e:
            self.log_test_result("Structured logging", False, str(e))
            return False
    
    def test_system_metrics(self) -> bool:
        """Test system metrics collection."""
        print("\n💻 Testing System Metrics...")
        
        try:
            response = requests.get(f"{BASE_URL}/health/metrics", timeout=10)
            if response.status_code == 200:
                metrics = response.json()
                system_metrics = metrics.get("metrics", {})
                
                # Check for system metrics
                system_metrics_to_check = [
                    "system_cpu_usage",
                    "system_memory_usage",
                    "application_uptime"
                ]
                
                all_found = True
                for metric in system_metrics_to_check:
                    if metric in system_metrics:
                        self.log_test_result(f"System metric {metric}", True, f"Value: {system_metrics[metric]}")
                    else:
                        self.log_test_result(f"System metric {metric}", False, "Metric not found")
                        all_found = False
                
                return all_found
            else:
                self.log_test_result("System metrics", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("System metrics", False, str(e))
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all monitoring system tests."""
        print("🚀 Starting Day 18 Monitoring System Tests...")
        print("=" * 60)
        
        test_methods = [
            ("Health Endpoints", self.test_health_endpoints),
            ("Prometheus Metrics", self.test_prometheus_metrics),
            ("Grafana Dashboards", self.test_grafana_dashboards),
            ("Log Aggregation", self.test_log_aggregation),
            ("Alerting Rules", self.test_alerting_rules),
            ("Metrics Middleware", self.test_metrics_middleware),
            ("Structured Logging", self.test_structured_logging),
            ("System Metrics", self.test_system_metrics)
        ]
        
        passed_tests = 0
        total_tests = len(test_methods)
        
        for test_name, test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                self.log_test_result(test_name, False, f"Test failed with exception: {str(e)}")
        
        # Calculate results
        end_time = time.time()
        duration = end_time - self.start_time
        
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests) * 100,
            "duration_seconds": round(duration, 2),
            "timestamp": datetime.utcnow().isoformat(),
            "results": self.results
        }
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! Day 18 Monitoring System is working correctly.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} tests failed. Please check the results above.")
        
        return summary


def main():
    """Main test runner."""
    tester = MonitoringSystemTester()
    
    try:
        summary = tester.run_all_tests()
        
        # Save results to file
        with open("day18_monitoring_test_results.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: day18_monitoring_test_results.json")
        
        # Exit with appropriate code
        if summary["success_rate"] == 100:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
