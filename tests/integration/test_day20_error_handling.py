#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Day 20 Error Handling & Recovery Test Suite

This script tests all the error handling and recovery functionality implemented
for Day 20 of the MVP development plan.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, Any

import httpx
import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test data
TEST_PAYMENT_DATA = {
    "amount": 10.00,
    "currency": "USD",
    "payment_method": {
        "type": "credit_card",
        "card_number": "4111111111111111",
        "expiry_month": "12",
        "expiry_year": "2025",
        "cvv": "123"
    },
    "description": "Test payment for error handling"
}


class ErrorHandlingTestSuite:
    """Comprehensive test suite for error handling and recovery."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        self.start_time = datetime.utcnow()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def run_all_tests(self):
        """Run all error handling tests."""
        logger.info("Starting Day 20 Error Handling & Recovery Test Suite")
        logger.info("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Error Recovery Status", self.test_error_recovery_status),
            ("Dead Letter Queue Status", self.test_dead_letter_queue_status),
            ("Circuit Breaker Status", self.test_circuit_breaker_status),
            ("Graceful Shutdown Status", self.test_graceful_shutdown_status),
            ("Error Reporting Dashboard", self.test_error_reporting_dashboard),
            ("Error Recovery Mechanisms", self.test_error_recovery_mechanisms),
            ("Dead Letter Queue Operations", self.test_dead_letter_queue_operations),
            ("Circuit Breaker Operations", self.test_circuit_breaker_operations),
            ("Error Reporting Operations", self.test_error_reporting_operations),
            ("Graceful Shutdown Operations", self.test_graceful_shutdown_operations),
            ("Integration Tests", self.test_integration_scenarios)
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"Running: {test_name}")
                result = await test_func()
                self.test_results.append({
                    "test": test_name,
                    "status": "PASSED",
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                })
                logger.info(f"✅ {test_name}: PASSED")
            except Exception as e:
                logger.error(f"❌ {test_name}: FAILED - {e}")
                self.test_results.append({
                    "test": test_name,
                    "status": "FAILED",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        await self.print_test_summary()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test basic health check."""
        response = await self.client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        
        return {"status": "healthy", "response_time": response.elapsed.total_seconds()}
    
    async def test_error_recovery_status(self) -> Dict[str, Any]:
        """Test error recovery system status."""
        response = await self.client.get(f"{API_BASE}/error-management/recovery/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "error_statistics" in data
        assert "status" in data
        
        return data
    
    async def test_dead_letter_queue_status(self) -> Dict[str, Any]:
        """Test dead letter queue status."""
        response = await self.client.get(f"{API_BASE}/error-management/dead-letter-queue/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_messages" in data
        assert "current_queue_size" in data
        
        return data
    
    async def test_circuit_breaker_status(self) -> Dict[str, Any]:
        """Test circuit breaker status."""
        response = await self.client.get(f"{API_BASE}/error-management/circuit-breakers")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Check for expected circuit breakers
        circuit_breaker_names = [cb["name"] for cb in data]
        expected_breakers = ["authorize_net", "database", "cache", "webhook"]
        
        for expected in expected_breakers:
            assert expected in circuit_breaker_names, f"Missing circuit breaker: {expected}"
        
        return {"circuit_breakers": len(data), "names": circuit_breaker_names}
    
    async def test_graceful_shutdown_status(self) -> Dict[str, Any]:
        """Test graceful shutdown status."""
        response = await self.client.get(f"{API_BASE}/error-management/shutdown/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "is_shutting_down" in data
        assert "health_check_enabled" in data
        assert "active_connections" in data
        
        return data
    
    async def test_error_reporting_dashboard(self) -> Dict[str, Any]:
        """Test error reporting dashboard."""
        response = await self.client.get(f"{API_BASE}/error-management/errors/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        assert "metrics" in data
        assert "recent_errors" in data
        assert "recent_alerts" in data
        assert "trends" in data
        
        return data
    
    async def test_error_recovery_mechanisms(self) -> Dict[str, Any]:
        """Test error recovery mechanisms."""
        # Test error reporting
        error_report = {
            "error_type": "TestError",
            "error_message": "Test error for recovery mechanisms",
            "severity": "medium",
            "request_id": "test_req_123",
            "endpoint": "/test/endpoint",
            "method": "GET",
            "context": {"test": True}
        }
        
        response = await self.client.post(
            f"{API_BASE}/error-management/recovery/report-error",
            json=error_report
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "error_id" in data
        assert "status" in data
        
        return {"reported_error_id": data["error_id"]}
    
    async def test_dead_letter_queue_operations(self) -> Dict[str, Any]:
        """Test dead letter queue operations."""
        # Get messages
        response = await self.client.get(f"{API_BASE}/error-management/dead-letter-queue/messages")
        assert response.status_code == 200
        
        messages = response.json()
        assert isinstance(messages, list)
        
        # Test cleanup
        response = await self.client.post(f"{API_BASE}/error-management/dead-letter-queue/cleanup")
        assert response.status_code == 200
        
        cleanup_data = response.json()
        assert "messages_removed" in cleanup_data
        
        return {"messages_count": len(messages), "cleanup_result": cleanup_data}
    
    async def test_circuit_breaker_operations(self) -> Dict[str, Any]:
        """Test circuit breaker operations."""
        # Get healthy services
        response = await self.client.get(f"{API_BASE}/error-management/circuit-breakers/healthy")
        assert response.status_code == 200
        
        data = response.json()
        assert "healthy_services" in data
        assert "unhealthy_services" in data
        
        # Test reset circuit breaker (if any exist)
        if data["healthy_services"]:
            service_name = data["healthy_services"][0]
            response = await self.client.post(
                f"{API_BASE}/error-management/circuit-breakers/{service_name}/reset"
            )
            assert response.status_code == 200
            
            reset_data = response.json()
            assert "reset" in reset_data
        
        return data
    
    async def test_error_reporting_operations(self) -> Dict[str, Any]:
        """Test error reporting operations."""
        # Get error metrics
        response = await self.client.get(f"{API_BASE}/error-management/errors/metrics")
        assert response.status_code == 200
        
        metrics = response.json()
        assert "total_errors" in metrics
        assert "error_rate_per_minute" in metrics
        
        # Get error trends
        response = await self.client.get(f"{API_BASE}/error-management/errors/trends")
        assert response.status_code == 200
        
        trends = response.json()
        assert "time_range_hours" in trends
        assert "total_errors" in trends
        
        # Get alerts
        response = await self.client.get(f"{API_BASE}/error-management/alerts")
        assert response.status_code == 200
        
        alerts = response.json()
        assert isinstance(alerts, list)
        
        return {"metrics": metrics, "trends": trends, "alerts_count": len(alerts)}
    
    async def test_graceful_shutdown_operations(self) -> Dict[str, Any]:
        """Test graceful shutdown operations."""
        # Note: We won't actually initiate shutdown in tests to avoid breaking the system
        # Just test that the endpoint exists and returns proper response structure
        
        response = await self.client.get(f"{API_BASE}/error-management/shutdown/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "is_shutting_down" in data
        assert isinstance(data["is_shutting_down"], bool)
        
        return {"shutdown_status": data}
    
    async def test_integration_scenarios(self) -> Dict[str, Any]:
        """Test integration scenarios."""
        results = {}
        
        # Scenario 1: Report multiple errors and check metrics
        for i in range(5):
            error_report = {
                "error_type": f"IntegrationTestError_{i}",
                "error_message": f"Integration test error {i}",
                "severity": "medium",
                "request_id": f"integration_test_{i}",
                "context": {"test_scenario": "integration", "iteration": i}
            }
            
            response = await self.client.post(
                f"{API_BASE}/error-management/recovery/report-error",
                json=error_report
            )
            assert response.status_code == 200
        
        # Check that metrics reflect the reported errors
        response = await self.client.get(f"{API_BASE}/error-management/errors/metrics")
        assert response.status_code == 200
        
        metrics = response.json()
        assert metrics["total_errors"] >= 5  # At least our test errors
        
        results["error_reporting"] = "success"
        
        # Scenario 2: Check all systems are operational
        systems = [
            ("error_recovery", f"{API_BASE}/error-management/recovery/status"),
            ("dead_letter_queue", f"{API_BASE}/error-management/dead-letter-queue/status"),
            ("circuit_breakers", f"{API_BASE}/error-management/circuit-breakers"),
            ("error_reporting", f"{API_BASE}/error-management/errors/dashboard")
        ]
        
        for system_name, endpoint in systems:
            response = await self.client.get(endpoint)
            assert response.status_code == 200
            results[f"{system_name}_operational"] = True
        
        return results
    
    async def print_test_summary(self):
        """Print test summary."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        passed_tests = len([r for r in self.test_results if r["status"] == "PASSED"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAILED"])
        total_tests = len(self.test_results)
        
        logger.info("\n" + "=" * 60)
        logger.info("DAY 20 ERROR HANDLING & RECOVERY TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 60)
        
        if failed_tests > 0:
            logger.info("\nFAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAILED":
                    logger.info(f"❌ {result['test']}: {result['error']}")
        
        logger.info("\nPASSED TESTS:")
        for result in self.test_results:
            if result["status"] == "PASSED":
                logger.info(f"✅ {result['test']}")
        
        # Save detailed results
        results_file = f"day20_error_handling_test_results_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "test_suite": "Day 20 Error Handling & Recovery",
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "results": self.test_results
            }, f, indent=2)
        
        logger.info(f"\nDetailed results saved to: {results_file}")
        
        return passed_tests == total_tests


async def main():
    """Main test runner."""
    try:
        async with ErrorHandlingTestSuite() as test_suite:
            success = await test_suite.run_all_tests()
            
            if success:
                logger.info("\n🎉 ALL TESTS PASSED! Day 20 Error Handling & Recovery implementation is working correctly.")
                return 0
            else:
                logger.error("\n❌ SOME TESTS FAILED! Please review the error handling implementation.")
                return 1
                
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
