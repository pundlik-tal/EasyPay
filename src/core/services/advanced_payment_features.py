"""
EasyPay Payment Gateway - Advanced Payment Features

This module implements advanced payment features including:
- Idempotency handling
- Retry logic with exponential backoff
- Circuit breaker pattern
- Request correlation IDs
- Payment status tracking
- Payment metadata support
- Payment search/filtering
- Payment history tracking
"""
import uuid
import time
import random
import hashlib
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass
from functools import wraps

from src.infrastructure.cache import CacheManager
from src.core.exceptions import PaymentError, ValidationError

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryPolicy(Enum):
    """Retry policy types."""
    FAST = "fast"
    STANDARD = "standard"
    SLOW = "slow"


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int
    base_delay: float
    max_delay: float
    backoff_multiplier: float
    jitter: bool = True
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            jitter = random.uniform(0, 0.1) * delay
            delay += jitter
        
        return delay


class RetryPolicies:
    """Predefined retry policies."""
    FAST = RetryConfig(
        max_retries=3,
        base_delay=0.1,
        max_delay=1.0,
        backoff_multiplier=2.0
    )
    
    STANDARD = RetryConfig(
        max_retries=5,
        base_delay=1.0,
        max_delay=30.0,
        backoff_multiplier=2.0
    )
    
    SLOW = RetryConfig(
        max_retries=10,
        base_delay=5.0,
        max_delay=300.0,
        backoff_multiplier=1.5
    )


class CircuitBreaker:
    """Circuit breaker implementation."""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_opens": 0
        }
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        self.metrics["total_calls"] += 1
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise PaymentError("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.metrics["successful_calls"] += 1
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.metrics["failed_calls"] += 1
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.metrics["circuit_opens"] += 1
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            **self.metrics,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_rate": (
                self.metrics["successful_calls"] / self.metrics["total_calls"]
                if self.metrics["total_calls"] > 0 else 0
            )
        }


class RetryManager:
    """Retry manager with exponential backoff."""
    
    def __init__(self, policy: RetryConfig = RetryPolicies.STANDARD):
        self.policy = policy
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Retry function with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.policy.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.policy.max_retries:
                    logger.error(f"Max retries ({self.policy.max_retries}) exceeded for {func.__name__}")
                    break
                
                # Calculate delay with jitter
                delay = self.policy.calculate_delay(attempt)
                logger.warning(f"Retry attempt {attempt + 1}/{self.policy.max_retries} for {func.__name__} in {delay:.2f}s")
                time.sleep(delay)
        
        raise last_exception


class IdempotencyManager:
    """Idempotency manager for payment operations."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.idempotency_ttl = 3600  # 1 hour
    
    def generate_idempotency_key(self, operation: str, **kwargs) -> str:
        """Generate idempotency key for operation."""
        # Create deterministic key from operation and parameters
        key_data = {
            "operation": operation,
            **kwargs
        }
        
        # Sort keys for consistent hashing
        sorted_data = sorted(key_data.items())
        key_string = "|".join(f"{k}:{v}" for k, v in sorted_data)
        
        # Generate hash
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        return f"idempotency:{operation}:{key_hash}"
    
    async def check_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        """Check if operation was already performed."""
        try:
            result = await self.cache.get(key)
            if result:
                # Parse JSON result
                import json
                return json.loads(result)
        except Exception as e:
            logger.warning(f"Failed to check idempotency key {key}: {e}")
        return None
    
    async def store_idempotency_result(self, key: str, result: Dict[str, Any]) -> None:
        """Store idempotency result."""
        try:
            import json
            await self.cache.set(key, json.dumps(result), self.idempotency_ttl)
        except Exception as e:
            logger.warning(f"Failed to store idempotency result for key {key}: {e}")


class CorrelationManager:
    """Request correlation ID manager."""
    
    @staticmethod
    def generate_correlation_id() -> str:
        """Generate correlation ID."""
        return f"corr_{uuid.uuid4().hex[:12]}"
    
    @staticmethod
    def extract_correlation_id(headers: Dict[str, str]) -> Optional[str]:
        """Extract correlation ID from headers."""
        return headers.get("X-Correlation-ID") or headers.get("X-Request-ID")


class PaymentStatusTracker:
    """Payment status tracking and history."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.status_history_ttl = 86400  # 24 hours
    
    async def track_status_change(self, payment_id: str, old_status: str, 
                                 new_status: str, reason: str = None) -> None:
        """Track payment status change."""
        try:
            status_change = {
                "payment_id": payment_id,
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store in cache
            key = f"status_history:{payment_id}"
            await self.cache.set(key, str(status_change), self.status_history_ttl)
            
            logger.info(f"Payment {payment_id} status changed from {old_status} to {new_status}")
            
        except Exception as e:
            logger.error(f"Failed to track status change for payment {payment_id}: {e}")
    
    async def get_status_history(self, payment_id: str) -> List[Dict[str, Any]]:
        """Get payment status history."""
        try:
            key = f"status_history:{payment_id}"
            history_data = await self.cache.get(key)
            if history_data:
                import json
                return json.loads(history_data)
        except Exception as e:
            logger.error(f"Failed to get status history for payment {payment_id}: {e}")
        return []


class PaymentMetadataManager:
    """Payment metadata management."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.metadata_ttl = 86400  # 24 hours
    
    async def store_metadata(self, payment_id: str, metadata: Dict[str, Any]) -> None:
        """Store payment metadata."""
        try:
            key = f"payment_metadata:{payment_id}"
            import json
            await self.cache.set(key, json.dumps(metadata), self.metadata_ttl)
        except Exception as e:
            logger.error(f"Failed to store metadata for payment {payment_id}: {e}")
    
    async def get_metadata(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment metadata."""
        try:
            key = f"payment_metadata:{payment_id}"
            metadata_data = await self.cache.get(key)
            if metadata_data:
                import json
                return json.loads(metadata_data)
        except Exception as e:
            logger.error(f"Failed to get metadata for payment {payment_id}: {e}")
        return None
    
    async def update_metadata(self, payment_id: str, updates: Dict[str, Any]) -> None:
        """Update payment metadata."""
        try:
            existing_metadata = await self.get_metadata(payment_id) or {}
            existing_metadata.update(updates)
            await self.store_metadata(payment_id, existing_metadata)
        except Exception as e:
            logger.error(f"Failed to update metadata for payment {payment_id}: {e}")


class PaymentSearchManager:
    """Payment search and filtering."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.search_cache_ttl = 300  # 5 minutes
    
    async def search_payments(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search payments with caching."""
        try:
            # Generate cache key from search parameters
            cache_key = self._generate_search_cache_key(search_params)
            
            # Check cache first
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                import json
                return json.loads(cached_result)
            
            # Perform search (this would be implemented by the repository)
            # For now, return empty list
            results = []
            
            # Cache results
            import json
            await self.cache.set(cache_key, json.dumps(results), self.search_cache_ttl)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search payments: {e}")
            return []
    
    def _generate_search_cache_key(self, search_params: Dict[str, Any]) -> str:
        """Generate cache key for search parameters."""
        # Sort parameters for consistent hashing
        sorted_params = sorted(search_params.items())
        key_string = "|".join(f"{k}:{v}" for k, v in sorted_params)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        return f"payment_search:{key_hash}"


class AdvancedPaymentFeatures:
    """Main class for advanced payment features."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.idempotency_manager = IdempotencyManager(cache_manager)
        self.correlation_manager = CorrelationManager()
        self.status_tracker = PaymentStatusTracker(cache_manager)
        self.metadata_manager = PaymentMetadataManager(cache_manager)
        self.search_manager = PaymentSearchManager(cache_manager)
        
        # Circuit breakers for different services
        self.authorize_net_circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=PaymentError
        )
        
        # Retry managers for different operations
        self.payment_retry = RetryManager(RetryPolicies.STANDARD)
        self.external_api_retry = RetryManager(RetryPolicies.FAST)
    
    def with_idempotency(self, operation: str):
        """Decorator for idempotent operations."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate idempotency key
                idempotency_key = self.idempotency_manager.generate_idempotency_key(
                    operation, **kwargs
                )
                
                # Check if operation was already performed
                existing_result = await self.idempotency_manager.check_idempotency(idempotency_key)
                if existing_result:
                    logger.info(f"Idempotent operation {operation} already performed")
                    return existing_result
                
                # Perform operation
                result = await func(*args, **kwargs)
                
                # Store result for idempotency
                await self.idempotency_manager.store_idempotency_result(
                    idempotency_key, result
                )
                
                return result
            return wrapper
        return decorator
    
    def with_retry(self, retry_manager: RetryManager = None):
        """Decorator for retry logic."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                retry_mgr = retry_manager or self.payment_retry
                return retry_mgr.retry_with_backoff(func, *args, **kwargs)
            return wrapper
        return decorator
    
    def with_circuit_breaker(self, circuit_breaker: CircuitBreaker = None):
        """Decorator for circuit breaker."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                circuit = circuit_breaker or self.authorize_net_circuit
                return circuit.call(func, *args, **kwargs)
            return wrapper
        return decorator
    
    async def track_payment_status_change(self, payment_id: str, old_status: str, 
                                        new_status: str, reason: str = None) -> None:
        """Track payment status change."""
        await self.status_tracker.track_status_change(payment_id, old_status, new_status, reason)
    
    async def get_payment_status_history(self, payment_id: str) -> List[Dict[str, Any]]:
        """Get payment status history."""
        return await self.status_tracker.get_status_history(payment_id)
    
    async def store_payment_metadata(self, payment_id: str, metadata: Dict[str, Any]) -> None:
        """Store payment metadata."""
        await self.metadata_manager.store_metadata(payment_id, metadata)
    
    async def get_payment_metadata(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment metadata."""
        return await self.metadata_manager.get_metadata(payment_id)
    
    async def update_payment_metadata(self, payment_id: str, updates: Dict[str, Any]) -> None:
        """Update payment metadata."""
        await self.metadata_manager.update_metadata(payment_id, updates)
    
    async def search_payments(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search payments."""
        return await self.search_manager.search_payments(search_params)
    
    def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "authorize_net": self.authorize_net_circuit.get_metrics()
        }
