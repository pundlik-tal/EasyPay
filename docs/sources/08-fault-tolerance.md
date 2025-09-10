# Fault Tolerance and Error Handling Guide

## Overview

Fault tolerance is critical for payment processing systems. This guide covers strategies for building resilient systems that can handle failures gracefully and maintain service availability.

## Table of Contents
1. [Fault Tolerance Principles](#fault-tolerance-principles)
2. [Error Handling Strategies](#error-handling-strategies)
3. [Retry Mechanisms](#retry-mechanisms)
4. [Circuit Breaker Pattern](#circuit-breaker-pattern)
5. [Fallback Strategies](#fallback-strategies)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Implementation Examples](#implementation-examples)

## Fault Tolerance Principles

### 1. Fail Fast
- Detect failures quickly
- Avoid cascading failures
- Provide immediate feedback
- Implement timeouts

### 2. Fail Safe
- Graceful degradation
- Preserve data integrity
- Maintain partial functionality
- Clear error messages

### 3. Fail Over
- Automatic failover to backup systems
- Load balancing across instances
- Database replication
- Service redundancy

### 4. Fail Back
- Automatic recovery when primary systems restore
- Health check monitoring
- Gradual traffic shifting
- Data synchronization

## Error Handling Strategies

### Error Classification

**Transient Errors** (Retryable):
- Network timeouts
- Temporary service unavailability
- Rate limiting
- Database connection issues

**Permanent Errors** (Non-retryable):
- Invalid credentials
- Malformed requests
- Authorization failures
- Business logic errors

**System Errors** (Critical):
- Database corruption
- Memory exhaustion
- Disk space issues
- Security breaches

### Error Response Format

```json
{
  "error": {
    "type": "payment_processing_error",
    "code": "AUTHORIZE_NET_UNAVAILABLE",
    "message": "Payment processor is temporarily unavailable",
    "details": {
      "retry_after": 30,
      "max_retries": 3,
      "original_error": "Connection timeout"
    },
    "request_id": "req_123456789",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### Error Handling Implementation

```python
import logging
from enum import Enum
from typing import Optional, Dict, Any

class ErrorType(Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    SYSTEM = "system"

class PaymentError(Exception):
    def __init__(self, message: str, error_type: ErrorType, 
                 retry_after: Optional[int] = None, 
                 max_retries: Optional[int] = None):
        self.message = message
        self.error_type = error_type
        self.retry_after = retry_after
        self.max_retries = max_retries
        super().__init__(message)

class ErrorHandler:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors based on type and context."""
        if isinstance(error, PaymentError):
            return self._handle_payment_error(error, context)
        else:
            return self._handle_generic_error(error, context)
    
    def _handle_payment_error(self, error: PaymentError, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment-specific errors."""
        self.logger.error(f"Payment error: {error.message}", extra=context)
        
        if error.error_type == ErrorType.TRANSIENT:
            return {
                "action": "retry",
                "retry_after": error.retry_after,
                "max_retries": error.max_retries
            }
        elif error.error_type == ErrorType.PERMANENT:
            return {
                "action": "fail",
                "reason": error.message
            }
        else:  # SYSTEM
            return {
                "action": "escalate",
                "reason": "System error requires immediate attention"
            }
    
    def _handle_generic_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic errors."""
        self.logger.error(f"Unexpected error: {str(error)}", extra=context)
        return {
            "action": "fail",
            "reason": "Internal server error"
        }
```

## Retry Mechanisms

### Exponential Backoff

```python
import time
import random
from typing import Callable, Any

class RetryManager:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Retry function with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    break
                
                # Calculate delay with jitter
                delay = self.base_delay * (2 ** attempt)
                jitter = random.uniform(0, 0.1) * delay
                total_delay = delay + jitter
                
                time.sleep(total_delay)
        
        raise last_exception
```

### Retry Policies

```python
from dataclasses import dataclass
from typing import List, Callable

@dataclass
class RetryPolicy:
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
    FAST = RetryPolicy(
        max_retries=3,
        base_delay=0.1,
        max_delay=1.0,
        backoff_multiplier=2.0
    )
    
    STANDARD = RetryPolicy(
        max_retries=5,
        base_delay=1.0,
        max_delay=30.0,
        backoff_multiplier=2.0
    )
    
    SLOW = RetryPolicy(
        max_retries=10,
        base_delay=5.0,
        max_delay=300.0,
        backoff_multiplier=1.5
    )
```

## Circuit Breaker Pattern

### Circuit Breaker Implementation

```python
import time
from enum import Enum
from typing import Callable, Any

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
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
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### Circuit Breaker with Monitoring

```python
import logging
from typing import Dict, Any

class MonitoredCircuitBreaker(CircuitBreaker):
    def __init__(self, name: str, logger: logging.Logger, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.logger = logger
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_opens": 0
        }
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with monitoring."""
        self.metrics["total_calls"] += 1
        
        try:
            result = super().call(func, *args, **kwargs)
            self.metrics["successful_calls"] += 1
            return result
        except Exception as e:
            self.metrics["failed_calls"] += 1
            self.logger.error(f"Circuit breaker {self.name} failed: {str(e)}")
            raise e
    
    def _on_failure(self):
        """Handle failed call with monitoring."""
        super()._on_failure()
        if self.state == CircuitState.OPEN:
            self.metrics["circuit_opens"] += 1
            self.logger.warning(f"Circuit breaker {self.name} opened")
    
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
```

## Fallback Strategies

### Graceful Degradation

```python
from typing import Optional, Dict, Any

class PaymentService:
    def __init__(self, primary_gateway, fallback_gateway):
        self.primary_gateway = primary_gateway
        self.fallback_gateway = fallback_gateway
        self.circuit_breaker = CircuitBreaker()
    
    def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment with fallback strategy."""
        try:
            # Try primary gateway
            return self.circuit_breaker.call(
                self.primary_gateway.process_payment,
                payment_data
            )
        except Exception as e:
            # Fallback to secondary gateway
            return self._fallback_payment(payment_data, str(e))
    
    def _fallback_payment(self, payment_data: Dict[str, Any], 
                         error: str) -> Dict[str, Any]:
        """Process payment using fallback gateway."""
        try:
            result = self.fallback_gateway.process_payment(payment_data)
            result["fallback_used"] = True
            result["fallback_reason"] = error
            return result
        except Exception as e:
            # Both gateways failed
            return {
                "success": False,
                "error": "All payment gateways unavailable",
                "details": {
                    "primary_error": error,
                    "fallback_error": str(e)
                }
            }
```

### Cached Responses

```python
import redis
import json
from typing import Optional, Dict, Any

class CachedPaymentService:
    def __init__(self, payment_service, redis_client, cache_ttl: int = 300):
        self.payment_service = payment_service
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
    
    def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment with caching."""
        # Check cache first
        cache_key = self._generate_cache_key(payment_data)
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            # Process payment
            result = self.payment_service.process_payment(payment_data)
            
            # Cache successful result
            if result.get("success"):
                self._set_cache(cache_key, result)
            
            return result
        except Exception as e:
            # Try to return cached result on failure
            if cached_result:
                cached_result["cached_fallback"] = True
                return cached_result
            
            raise e
    
    def _generate_cache_key(self, payment_data: Dict[str, Any]) -> str:
        """Generate cache key for payment data."""
        key_data = {
            "amount": payment_data["amount"],
            "currency": payment_data["currency"],
            "customer_id": payment_data.get("customer_id")
        }
        return f"payment:{hash(json.dumps(key_data, sort_keys=True))}"
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache."""
        try:
            cached_data = self.redis_client.get(key)
            return json.loads(cached_data) if cached_data else None
        except Exception:
            return None
    
    def _set_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Set data in cache."""
        try:
            self.redis_client.setex(
                key, 
                self.cache_ttl, 
                json.dumps(data)
            )
        except Exception:
            pass  # Cache failure shouldn't break payment processing
```

## Monitoring and Alerting

### Health Checks

```python
from typing import Dict, Any, List
import asyncio

class HealthChecker:
    def __init__(self, services: List[Any]):
        self.services = services
    
    async def check_health(self) -> Dict[str, Any]:
        """Check health of all services."""
        health_status = {
            "overall": "healthy",
            "services": {},
            "timestamp": time.time()
        }
        
        for service in self.services:
            service_name = service.__class__.__name__
            try:
                service_health = await self._check_service_health(service)
                health_status["services"][service_name] = service_health
                
                if service_health["status"] != "healthy":
                    health_status["overall"] = "unhealthy"
            except Exception as e:
                health_status["services"][service_name] = {
                    "status": "error",
                    "error": str(e)
                }
                health_status["overall"] = "unhealthy"
        
        return health_status
    
    async def _check_service_health(self, service: Any) -> Dict[str, Any]:
        """Check individual service health."""
        if hasattr(service, 'health_check'):
            return await service.health_check()
        else:
            return {"status": "unknown"}
```

### Alerting System

```python
import smtplib
from email.mime.text import MIMEText
from typing import Dict, Any, List

class AlertManager:
    def __init__(self, smtp_config: Dict[str, str], 
                 alert_recipients: List[str]):
        self.smtp_config = smtp_config
        self.alert_recipients = alert_recipients
    
    def send_alert(self, alert_type: str, message: str, 
                   severity: str = "warning") -> None:
        """Send alert notification."""
        subject = f"[{severity.upper()}] {alert_type}"
        
        email_body = f"""
        Alert Type: {alert_type}
        Severity: {severity}
        Message: {message}
        Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        try:
            self._send_email(subject, email_body)
        except Exception as e:
            print(f"Failed to send alert: {e}")
    
    def _send_email(self, subject: str, body: str) -> None:
        """Send email alert."""
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.smtp_config['from']
        msg['To'] = ', '.join(self.alert_recipients)
        
        with smtplib.SMTP(self.smtp_config['host'], 
                         self.smtp_config['port']) as server:
            server.starttls()
            server.login(self.smtp_config['user'], 
                        self.smtp_config['password'])
            server.send_message(msg)
```

## Implementation Examples

### Complete Fault-Tolerant Payment Service

```python
import asyncio
import logging
from typing import Dict, Any, Optional

class FaultTolerantPaymentService:
    def __init__(self, primary_gateway, fallback_gateway, 
                 redis_client, alert_manager):
        self.primary_gateway = primary_gateway
        self.fallback_gateway = fallback_gateway
        self.redis_client = redis_client
        self.alert_manager = alert_manager
        self.logger = logging.getLogger(__name__)
        
        # Circuit breakers for each gateway
        self.primary_circuit = MonitoredCircuitBreaker(
            "primary_gateway", self.logger
        )
        self.fallback_circuit = MonitoredCircuitBreaker(
            "fallback_gateway", self.logger
        )
    
    async def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment with full fault tolerance."""
        try:
            # Try primary gateway
            result = await self.primary_circuit.call(
                self.primary_gateway.process_payment,
                payment_data
            )
            
            # Log success
            self.logger.info("Payment processed successfully via primary gateway")
            return result
            
        except Exception as e:
            self.logger.warning(f"Primary gateway failed: {e}")
            
            try:
                # Try fallback gateway
                result = await self.fallback_circuit.call(
                    self.fallback_gateway.process_payment,
                    payment_data
                )
                
                # Send alert about fallback usage
                self.alert_manager.send_alert(
                    "FALLBACK_GATEWAY_USED",
                    f"Primary gateway failed, using fallback: {e}",
                    "warning"
                )
                
                result["fallback_used"] = True
                return result
                
            except Exception as fallback_error:
                self.logger.error(f"Both gateways failed: {fallback_error}")
                
                # Send critical alert
                self.alert_manager.send_alert(
                    "PAYMENT_SERVICE_DOWN",
                    f"All payment gateways unavailable: {fallback_error}",
                    "critical"
                )
                
                # Return cached result if available
                cached_result = await self._get_cached_result(payment_data)
                if cached_result:
                    cached_result["cached_fallback"] = True
                    return cached_result
                
                # Return error response
                return {
                    "success": False,
                    "error": "Payment service temporarily unavailable",
                    "retry_after": 300
                }
    
    async def _get_cached_result(self, payment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached payment result."""
        try:
            cache_key = f"payment:{hash(str(payment_data))}"
            cached_data = await self.redis_client.get(cache_key)
            return json.loads(cached_data) if cached_data else None
        except Exception:
            return None
```

## Best Practices

### 1. Error Classification
- Classify errors by type and severity
- Implement appropriate handling for each type
- Use structured error responses
- Log errors with context

### 2. Retry Strategies
- Use exponential backoff with jitter
- Set appropriate retry limits
- Implement circuit breakers
- Monitor retry success rates

### 3. Fallback Mechanisms
- Implement multiple fallback layers
- Use cached responses when possible
- Provide graceful degradation
- Maintain data consistency

### 4. Monitoring and Alerting
- Monitor all critical components
- Set up appropriate alert thresholds
- Implement health checks
- Track error rates and patterns

### 5. Testing
- Test failure scenarios
- Implement chaos engineering
- Monitor system behavior under load
- Regular disaster recovery drills

## Common Issues and Solutions

### Issue: Cascading Failures
- **Cause**: One service failure causes others to fail
- **Solution**: Implement circuit breakers and timeouts

### Issue: Slow Recovery
- **Cause**: Long retry delays or no automatic recovery
- **Solution**: Implement health checks and automatic failover

### Issue: Data Inconsistency
- **Cause**: Partial failures during transactions
- **Solution**: Use database transactions and idempotency

### Issue: Alert Fatigue
- **Cause**: Too many alerts for non-critical issues
- **Solution**: Implement alert filtering and severity levels

## Next Steps

1. Review [Performance Optimization Guide](09-performance-optimization.md)
2. Create [Integration Examples](10-integration-examples.md)
3. Implement [Security Best Practices](11-security-guide.md)
4. Set up [Monitoring and Observability](12-monitoring-guide.md)

## Resources

- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Retry Patterns](https://docs.microsoft.com/en-us/azure/architecture/patterns/retry)
- [Fault Tolerance](https://en.wikipedia.org/wiki/Fault_tolerance)
- [Chaos Engineering](https://principlesofchaos.org/)
