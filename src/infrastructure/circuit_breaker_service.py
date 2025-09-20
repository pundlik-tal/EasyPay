"""
EasyPay Payment Gateway - Circuit Breaker Service

This module provides comprehensive circuit breaker functionality for external services
and internal components to prevent cascading failures.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Type, Union, List
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager

from src.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service is back


class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3,
        timeout: float = 30.0,
        expected_exceptions: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.expected_exceptions = expected_exceptions


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    circuit_opens: int = 0
    circuit_closes: int = 0
    timeout_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None


class CircuitBreaker:
    """Enhanced circuit breaker implementation."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        self.metrics = CircuitBreakerMetrics()
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        self.metrics.total_calls += 1
        
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
            else:
                self.logger.warning(f"Circuit breaker {self.name} is OPEN - blocking request")
                raise ExternalServiceError(f"Service {self.name} is temporarily unavailable")
        
        # Execute the function with timeout
        try:
            result = await asyncio.wait_for(
                self._execute_function(func, *args, **kwargs),
                timeout=self.config.timeout
            )
            
            await self._on_success()
            return result
            
        except asyncio.TimeoutError:
            self.metrics.timeout_calls += 1
            await self._on_failure(ExternalServiceError(f"Service {self.name} timeout"))
            raise ExternalServiceError(f"Service {self.name} timeout")
            
        except Exception as e:
            if isinstance(e, self.config.expected_exceptions):
                await self._on_failure(e)
                raise e
            else:
                # Unexpected exception, don't count as failure
                self.logger.error(f"Unexpected exception in circuit breaker {self.name}: {e}")
                raise e
    
    async def _execute_function(self, func: Callable, *args, **kwargs) -> Any:
        """Execute the function."""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    async def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.success_count += 1
        self.last_success_time = datetime.utcnow()
        
        self.metrics.successful_calls += 1
        self.metrics.last_success_time = self.last_success_time
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.metrics.circuit_closes += 1
                self.logger.info(f"Circuit breaker {self.name} closed after {self.success_count} successful calls")
        
        elif self.state == CircuitState.CLOSED:
            # Reset success count in closed state
            self.success_count = 0
    
    async def _on_failure(self, error: Exception):
        """Handle failed call."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = datetime.utcnow()
        
        self.metrics.failed_calls += 1
        self.metrics.last_failure_time = self.last_failure_time
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.metrics.circuit_opens += 1
            self.logger.warning(f"Circuit breaker {self.name} opened after {self.failure_count} failures")
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        success_rate = (
            self.metrics.successful_calls / self.metrics.total_calls
            if self.metrics.total_calls > 0 else 0
        )
        
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "success_rate": success_rate,
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "successful_calls": self.metrics.successful_calls,
                "failed_calls": self.metrics.failed_calls,
                "timeout_calls": self.metrics.timeout_calls,
                "circuit_opens": self.metrics.circuit_opens,
                "circuit_closes": self.metrics.circuit_closes,
                "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                "last_success_time": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None
            }
        }
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.logger.info(f"Circuit breaker {self.name} manually reset")


class CircuitBreakerService:
    """Service for managing multiple circuit breakers."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = CircuitBreakerConfig()
        self.logger = logging.getLogger(__name__)
    
    def create_circuit_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Create a new circuit breaker."""
        if name in self.circuit_breakers:
            self.logger.warning(f"Circuit breaker {name} already exists")
            return self.circuit_breakers[name]
        
        circuit_config = config or self.default_config
        circuit_breaker = CircuitBreaker(name, circuit_config)
        self.circuit_breakers[name] = circuit_breaker
        
        self.logger.info(f"Created circuit breaker {name}")
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get an existing circuit breaker."""
        return self.circuit_breakers.get(name)
    
    def get_or_create_circuit_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        return self.get_circuit_breaker(name) or self.create_circuit_breaker(name, config)
    
    async def call_with_circuit_breaker(
        self,
        service_name: str,
        func: Callable,
        *args,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> Any:
        """Call function with circuit breaker protection."""
        circuit_breaker = self.get_or_create_circuit_breaker(service_name, config)
        return await circuit_breaker.call(func, *args, **kwargs)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {
            name: cb.get_metrics()
            for name, cb in self.circuit_breakers.items()
        }
    
    def get_healthy_services(self) -> List[str]:
        """Get list of healthy services (circuit closed)."""
        return [
            name for name, cb in self.circuit_breakers.items()
            if cb.get_state() == CircuitState.CLOSED
        ]
    
    def get_unhealthy_services(self) -> List[str]:
        """Get list of unhealthy services (circuit open)."""
        return [
            name for name, cb in self.circuit_breakers.items()
            if cb.get_state() == CircuitState.OPEN
        ]
    
    def reset_circuit_breaker(self, name: str) -> bool:
        """Reset a specific circuit breaker."""
        circuit_breaker = self.get_circuit_breaker(name)
        if circuit_breaker:
            circuit_breaker.reset()
            return True
        return False
    
    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers."""
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.reset()
        self.logger.info("Reset all circuit breakers")


class CircuitBreakerMiddleware:
    """Middleware for automatic circuit breaker integration."""
    
    def __init__(self, circuit_breaker_service: CircuitBreakerService):
        self.circuit_breaker_service = circuit_breaker_service
        self.logger = logging.getLogger(__name__)
    
    async def protect_service_call(
        self,
        service_name: str,
        func: Callable,
        *args,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> Any:
        """Protect a service call with circuit breaker."""
        try:
            return await self.circuit_breaker_service.call_with_circuit_breaker(
                service_name, func, *args, config=config, **kwargs
            )
        except ExternalServiceError as e:
            self.logger.error(f"Circuit breaker protection triggered for {service_name}: {e}")
            raise e


@asynccontextmanager
async def circuit_breaker_context(
    service_name: str,
    circuit_breaker_service: CircuitBreakerService,
    config: Optional[CircuitBreakerConfig] = None
):
    """Context manager for circuit breaker protection."""
    circuit_breaker = circuit_breaker_service.get_or_create_circuit_breaker(service_name, config)
    
    try:
        yield circuit_breaker
    except Exception as e:
        await circuit_breaker._on_failure(e)
        raise


# Decorator for automatic circuit breaker protection
def with_circuit_breaker(
    service_name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator to automatically protect functions with circuit breaker."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            circuit_breaker_service = get_circuit_breaker_service()
            return await circuit_breaker_service.call_with_circuit_breaker(
                service_name, func, *args, config=config, **kwargs
            )
        return wrapper
    return decorator


# Global circuit breaker service instance
circuit_breaker_service = CircuitBreakerService()


def get_circuit_breaker_service() -> CircuitBreakerService:
    """Get the global circuit breaker service."""
    return circuit_breaker_service


# Pre-configured circuit breakers for common services
def setup_default_circuit_breakers():
    """Setup default circuit breakers for common services."""
    # Authorize.net circuit breaker
    authorize_net_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=120,
        success_threshold=2,
        timeout=30.0
    )
    circuit_breaker_service.create_circuit_breaker("authorize_net", authorize_net_config)
    
    # Database circuit breaker
    database_config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,
        success_threshold=3,
        timeout=10.0
    )
    circuit_breaker_service.create_circuit_breaker("database", database_config)
    
    # Cache circuit breaker
    cache_config = CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=30,
        success_threshold=5,
        timeout=5.0
    )
    circuit_breaker_service.create_circuit_breaker("cache", cache_config)
    
    # External webhook circuit breaker
    webhook_config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=300,
        success_threshold=2,
        timeout=60.0
    )
    circuit_breaker_service.create_circuit_breaker("webhook", webhook_config)


# Initialize default circuit breakers
setup_default_circuit_breakers()
