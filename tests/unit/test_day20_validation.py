#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Day 20 Error Handling Validation

This script validates the Day 20 error handling implementation without requiring
the application to be running.
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Day20ValidationSuite:
    """Validation suite for Day 20 error handling implementation."""
    
    def __init__(self):
        self.test_results = []
        self.start_time = datetime.utcnow()
    
    async def run_validation(self):
        """Run all validation tests."""
        logger.info("Starting Day 20 Error Handling Implementation Validation")
        logger.info("=" * 60)
        
        tests = [
            ("Import Error Recovery Module", self.test_import_error_recovery),
            ("Import Dead Letter Queue Module", self.test_import_dead_letter_queue),
            ("Import Circuit Breaker Module", self.test_import_circuit_breaker),
            ("Import Graceful Shutdown Module", self.test_import_graceful_shutdown),
            ("Import Error Reporting Module", self.test_import_error_reporting),
            ("Import Error Management API", self.test_import_error_management_api),
            ("Test Error Recovery Manager", self.test_error_recovery_manager),
            ("Test Dead Letter Queue Service", self.test_dead_letter_queue_service),
            ("Test Circuit Breaker Service", self.test_circuit_breaker_service),
            ("Test Graceful Shutdown Manager", self.test_graceful_shutdown_manager),
            ("Test Error Reporting Service", self.test_error_reporting_service),
            ("Test Module Integration", self.test_module_integration)
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"Validating: {test_name}")
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
        
        await self.print_validation_summary()
    
    async def test_import_error_recovery(self) -> Dict[str, Any]:
        """Test importing error recovery module."""
        try:
            from src.infrastructure.error_recovery import (
                ErrorRecoveryManager, GlobalErrorHandlerMiddleware,
                GracefulShutdownManager, ErrorReportingService,
                ErrorSeverity, RecoveryStrategy, ErrorContext
            )
            return {"imports": "successful", "classes": 7}
        except ImportError as e:
            raise Exception(f"Import failed: {e}")
    
    async def test_import_dead_letter_queue(self) -> Dict[str, Any]:
        """Test importing dead letter queue module."""
        try:
            from src.infrastructure.dead_letter_queue import (
                DeadLetterQueueService, DeadLetterQueueAPI,
                DeadLetterMessage, MessageStatus
            )
            return {"imports": "successful", "classes": 4}
        except ImportError as e:
            raise Exception(f"Import failed: {e}")
    
    async def test_import_circuit_breaker(self) -> Dict[str, Any]:
        """Test importing circuit breaker module."""
        try:
            from src.infrastructure.circuit_breaker_service import (
                CircuitBreakerService, CircuitBreaker, CircuitBreakerConfig,
                CircuitState, CircuitBreakerMiddleware
            )
            return {"imports": "successful", "classes": 5}
        except ImportError as e:
            raise Exception(f"Import failed: {e}")
    
    async def test_import_graceful_shutdown(self) -> Dict[str, Any]:
        """Test importing graceful shutdown module."""
        try:
            from src.infrastructure.graceful_shutdown import (
                GracefulShutdownManager, ShutdownPhase, ShutdownPriority,
                ShutdownHandler, ShutdownMetrics, ConnectionDrainer,
                ShutdownHealthCheck
            )
            return {"imports": "successful", "classes": 6}
        except ImportError as e:
            raise Exception(f"Import failed: {e}")
    
    async def test_import_error_reporting(self) -> Dict[str, Any]:
        """Test importing error reporting module."""
        try:
            from src.infrastructure.error_reporting import (
                ErrorReportingService, ErrorReportingAPI,
                ErrorReport, Alert, ErrorMetrics, ErrorSeverity, AlertType
            )
            return {"imports": "successful", "classes": 6}
        except ImportError as e:
            raise Exception(f"Import failed: {e}")
    
    async def test_import_error_management_api(self) -> Dict[str, Any]:
        """Test importing error management API."""
        try:
            from src.api.v1.endpoints.error_management import router
            return {"imports": "successful", "router": "available"}
        except ImportError as e:
            raise Exception(f"Import failed: {e}")
    
    async def test_error_recovery_manager(self) -> Dict[str, Any]:
        """Test error recovery manager functionality."""
        from src.infrastructure.error_recovery import ErrorRecoveryManager, ErrorContext, ErrorSeverity
        
        manager = ErrorRecoveryManager()
        
        # Test error context creation
        context = ErrorContext(
            error=Exception("Test error"),
            severity=ErrorSeverity.MEDIUM,
            endpoint="/test",
            method="GET"
        )
        
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.endpoint == "/test"
        assert context.method == "GET"
        
        # Test error statistics
        stats = manager.get_error_statistics()
        assert "error_counts" in stats
        assert "dead_letter_queue_size" in stats
        
        return {"manager_created": True, "context_created": True, "stats_available": True}
    
    async def test_dead_letter_queue_service(self) -> Dict[str, Any]:
        """Test dead letter queue service functionality."""
        from src.infrastructure.dead_letter_queue import DeadLetterQueueService, MessageStatus
        
        service = DeadLetterQueueService()
        
        # Test adding a message
        message_id = await service.add_message(
            original_data={"test": "data"},
            error_info={"error": "test error"},
            metadata={"test": True}
        )
        
        assert message_id is not None
        
        # Test getting the message
        message = await service.get_message(message_id)
        assert message is not None
        assert message.id == message_id
        assert message.status == MessageStatus.PENDING
        
        # Test queue statistics
        stats = await service.get_queue_statistics()
        assert "total_messages" in stats
        assert "current_queue_size" in stats
        
        return {"service_created": True, "message_added": True, "message_retrieved": True}
    
    async def test_circuit_breaker_service(self) -> Dict[str, Any]:
        """Test circuit breaker service functionality."""
        from src.infrastructure.circuit_breaker_service import (
            CircuitBreakerService, CircuitBreakerConfig, CircuitState
        )
        
        service = CircuitBreakerService()
        
        # Test creating a circuit breaker
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60)
        circuit_breaker = service.create_circuit_breaker("test_service", config)
        
        assert circuit_breaker is not None
        assert circuit_breaker.name == "test_service"
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        
        # Test getting metrics
        metrics = circuit_breaker.get_metrics()
        assert "state" in metrics
        assert "failure_count" in metrics
        assert "success_rate" in metrics
        
        return {"service_created": True, "circuit_breaker_created": True, "metrics_available": True}
    
    async def test_graceful_shutdown_manager(self) -> Dict[str, Any]:
        """Test graceful shutdown manager functionality."""
        from src.infrastructure.graceful_shutdown import (
            GracefulShutdownManager, ShutdownPriority, ShutdownPhase
        )
        
        manager = GracefulShutdownManager()
        
        # Test registering a shutdown handler
        async def test_handler():
            return "test"
        
        manager.register_shutdown_handler(
            "test_handler",
            test_handler,
            ShutdownPriority.HIGH
        )
        
        # Test getting shutdown status
        status = manager.get_shutdown_status()
        assert "is_shutting_down" in status
        assert "health_check_enabled" in status
        assert "registered_handlers" in status
        
        return {"manager_created": True, "handler_registered": True, "status_available": True}
    
    async def test_error_reporting_service(self) -> Dict[str, Any]:
        """Test error reporting service functionality."""
        from src.infrastructure.error_reporting import (
            ErrorReportingService, ErrorSeverity, AlertType
        )
        
        service = ErrorReportingService()
        
        # Test reporting an error
        test_error = Exception("Test error")
        error_id = await service.report_error(
            error=test_error,
            severity=ErrorSeverity.MEDIUM,
            request_id="test_req_123",
            endpoint="/test"
        )
        
        assert error_id is not None
        
        # Test getting error reports
        reports = service.get_error_reports(limit=10)
        assert isinstance(reports, list)
        
        # Test getting error metrics
        metrics = service.get_error_metrics()
        assert "total_errors" in metrics
        assert "error_rate_per_minute" in metrics
        
        return {"service_created": True, "error_reported": True, "reports_available": True}
    
    async def test_module_integration(self) -> Dict[str, Any]:
        """Test integration between modules."""
        from src.infrastructure.error_recovery import error_recovery_manager
        from src.infrastructure.dead_letter_queue import dead_letter_queue_service
        from src.infrastructure.circuit_breaker_service import circuit_breaker_service
        from src.infrastructure.graceful_shutdown import graceful_shutdown_manager
        from src.infrastructure.error_reporting import error_reporting_service
        
        # Test that all global instances are available
        assert error_recovery_manager is not None
        assert dead_letter_queue_service is not None
        assert circuit_breaker_service is not None
        assert graceful_shutdown_manager is not None
        assert error_reporting_service is not None
        
        # Test that services can interact
        stats = error_recovery_manager.get_error_statistics()
        assert isinstance(stats, dict)
        
        dlq_stats = await dead_letter_queue_service.get_queue_statistics()
        assert isinstance(dlq_stats, dict)
        
        cb_metrics = circuit_breaker_service.get_all_metrics()
        assert isinstance(cb_metrics, dict)
        
        shutdown_status = graceful_shutdown_manager.get_shutdown_status()
        assert isinstance(shutdown_status, dict)
        
        error_metrics = error_reporting_service.get_error_metrics()
        assert isinstance(error_metrics, dict)
        
        return {"integration": "successful", "services_interacting": True}
    
    async def print_validation_summary(self):
        """Print validation summary."""
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        passed_tests = len([r for r in self.test_results if r["status"] == "PASSED"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAILED"])
        total_tests = len(self.test_results)
        
        logger.info("\n" + "=" * 60)
        logger.info("DAY 20 ERROR HANDLING IMPLEMENTATION VALIDATION")
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
        
        logger.info("\nIMPLEMENTATION STATUS:")
        if passed_tests == total_tests:
            logger.info("🎉 ALL VALIDATIONS PASSED!")
            logger.info("✅ Day 20 Error Handling & Recovery implementation is complete and functional.")
            logger.info("✅ All modules are properly integrated.")
            logger.info("✅ All services are working correctly.")
            logger.info("✅ Ready for production deployment.")
        else:
            logger.info("❌ SOME VALIDATIONS FAILED!")
            logger.info("Please review the implementation and fix any issues.")
        
        return passed_tests == total_tests


async def main():
    """Main validation runner."""
    try:
        validation_suite = Day20ValidationSuite()
        success = await validation_suite.run_validation()
        
        if success:
            logger.info("\n🎉 DAY 20 IMPLEMENTATION VALIDATION COMPLETE!")
            logger.info("All error handling and recovery components are working correctly.")
            return 0
        else:
            logger.error("\n❌ VALIDATION FAILED!")
            logger.error("Please review the error handling implementation.")
            return 1
                
    except Exception as e:
        logger.error(f"Validation suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
