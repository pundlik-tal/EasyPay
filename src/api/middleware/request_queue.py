"""
EasyPay Payment Gateway - Request Queue Middleware

This module provides request queuing middleware for handling high-load scenarios
with rate limiting, priority queuing, and circuit breaker patterns.
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.infrastructure.cache_strategies import get_enhanced_cache_manager
from src.infrastructure.monitoring import REQUEST_COUNT, REQUEST_DURATION


class RequestPriority(Enum):
    """Request priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class QueueStatus(Enum):
    """Queue status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class QueuedRequest:
    """Request queued for processing."""
    id: str
    request: Request
    priority: RequestPriority
    queued_at: datetime
    timeout: int = 30  # seconds
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class QueueMetrics:
    """Queue performance metrics."""
    total_requests: int = 0
    queued_requests: int = 0
    processed_requests: int = 0
    rejected_requests: int = 0
    timeout_requests: int = 0
    average_wait_time: float = 0.0
    average_processing_time: float = 0.0
    queue_size: int = 0
    last_reset: datetime = None
    
    def __post_init__(self):
        if self.last_reset is None:
            self.last_reset = datetime.now()


class RateLimiter:
    """Rate limiter with sliding window algorithm."""
    
    def __init__(self, requests_per_minute: int = 100, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.windows = defaultdict(lambda: deque())
        self.logger = logging.getLogger(__name__)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client."""
        
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Clean old entries
        self._clean_old_entries(client_id, minute_ago, hour_ago)
        
        # Check minute limit
        minute_requests = len([t for t in self.windows[client_id] if t > minute_ago])
        if minute_requests >= self.requests_per_minute:
            return False
        
        # Check hour limit
        hour_requests = len([t for t in self.windows[client_id] if t > hour_ago])
        if hour_requests >= self.requests_per_hour:
            return False
        
        # Add current request
        self.windows[client_id].append(now)
        
        return True
    
    def _clean_old_entries(self, client_id: str, minute_ago: float, hour_ago: float):
        """Clean old entries from sliding window."""
        
        window = self.windows[client_id]
        while window and window[0] <= hour_ago:
            window.popleft()


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
        self.logger = logging.getLogger(__name__)
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation."""
        
        self.failure_count = 0
        
        if self.state == "half-open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "closed"
                self.logger.info("Circuit breaker closed")
    
    def _on_failure(self):
        """Handle failed operation."""
        
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.logger.warning("Circuit breaker opened")
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time
        }


class RequestQueue:
    """Priority-based request queue."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queues = {
            RequestPriority.CRITICAL: asyncio.Queue(),
            RequestPriority.HIGH: asyncio.Queue(),
            RequestPriority.NORMAL: asyncio.Queue(),
            RequestPriority.LOW: asyncio.Queue()
        }
        self.metrics = QueueMetrics()
        self.logger = logging.getLogger(__name__)
    
    async def enqueue(self, request: QueuedRequest) -> bool:
        """Add request to appropriate priority queue."""
        
        if self.metrics.queue_size >= self.max_size:
            self.metrics.rejected_requests += 1
            return False
        
        queue = self.queues[request.priority]
        await queue.put(request)
        
        self.metrics.queued_requests += 1
        self.metrics.queue_size += 1
        
        return True
    
    async def dequeue(self) -> Optional[QueuedRequest]:
        """Get next request from highest priority queue."""
        
        # Check queues in priority order
        for priority in [RequestPriority.CRITICAL, RequestPriority.HIGH, RequestPriority.NORMAL, RequestPriority.LOW]:
            queue = self.queues[priority]
            if not queue.empty():
                try:
                    request = queue.get_nowait()
                    self.metrics.queue_size -= 1
                    return request
                except asyncio.QueueEmpty:
                    continue
        
        return None
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        
        stats = {}
        for priority, queue in self.queues.items():
            stats[priority.name] = queue.qsize()
        
        stats["total_size"] = self.metrics.queue_size
        return stats


class RequestQueueMiddleware(BaseHTTPMiddleware):
    """Middleware for request queuing and load management."""
    
    def __init__(
        self,
        app: ASGIApp,
        max_queue_size: int = 1000,
        max_workers: int = 10,
        request_timeout: int = 30,
        rate_limit_per_minute: int = 100,
        rate_limit_per_hour: int = 1000,
        circuit_breaker_threshold: int = 5
    ):
        super().__init__(app)
        
        self.max_queue_size = max_queue_size
        self.max_workers = max_workers
        self.request_timeout = request_timeout
        self.circuit_breaker_threshold = circuit_breaker_threshold
        
        # Initialize components
        self.queue = RequestQueue(max_queue_size)
        self.rate_limiter = RateLimiter(rate_limit_per_minute, rate_limit_per_hour)
        self.circuit_breaker = CircuitBreaker(circuit_breaker_threshold)
        self.cache_manager = get_enhanced_cache_manager()
        
        # Worker management
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        
        # Metrics
        self.metrics = QueueMetrics()
        self.logger = logging.getLogger(__name__)
        
        # Endpoints that should bypass queuing
        self.bypass_endpoints = {
            "/health",
            "/health/ready",
            "/health/live",
            "/metrics"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through queue system."""
        
        start_time = time.time()
        
        # Check if endpoint should bypass queuing
        if request.url.path in self.bypass_endpoints:
            return await call_next(request)
        
        # Check circuit breaker
        if self.circuit_breaker.state == "open":
            return JSONResponse(
                status_code=503,
                content={"error": "Service temporarily unavailable", "code": "circuit_open"}
            )
        
        # Check rate limiting
        client_id = self._get_client_id(request)
        if not self.rate_limiter.is_allowed(client_id):
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "code": "rate_limit"}
            )
        
        # Determine request priority
        priority = self._determine_priority(request)
        
        # Check if we should queue the request
        if self._should_queue_request(request, priority):
            return await self._handle_queued_request(request, priority, call_next)
        else:
            # Process request directly
            return await self._process_request_directly(request, call_next, start_time)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        
        # Try to get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Try to get API key for authenticated requests
        api_key = request.headers.get("x-api-key")
        if api_key:
            return f"api_key:{api_key}"
        
        return f"ip:{client_ip}"
    
    def _determine_priority(self, request: Request) -> RequestPriority:
        """Determine request priority based on endpoint and headers."""
        
        path = request.url.path
        
        # Critical endpoints
        if path.startswith("/api/v1/payments") and request.method == "POST":
            return RequestPriority.CRITICAL
        
        # High priority endpoints
        if path.startswith("/api/v1/payments") and request.method == "GET":
            return RequestPriority.HIGH
        
        # Normal priority for other API endpoints
        if path.startswith("/api/v1/"):
            return RequestPriority.NORMAL
        
        # Low priority for everything else
        return RequestPriority.LOW
    
    def _should_queue_request(self, request: Request, priority: RequestPriority) -> bool:
        """Determine if request should be queued."""
        
        # Always queue low priority requests
        if priority == RequestPriority.LOW:
            return True
        
        # Queue if system is under load
        if self.metrics.queue_size > self.max_queue_size * 0.7:
            return True
        
        # Don't queue critical requests unless system is overloaded
        if priority == RequestPriority.CRITICAL and self.metrics.queue_size < self.max_queue_size * 0.9:
            return False
        
        return False
    
    async def _handle_queued_request(
        self,
        request: Request,
        priority: RequestPriority,
        call_next: Callable
    ) -> Response:
        """Handle request through queue system."""
        
        # Create queued request
        queued_request = QueuedRequest(
            id=str(uuid.uuid4()),
            request=request,
            priority=priority,
            queued_at=datetime.now(),
            timeout=self.request_timeout
        )
        
        # Try to enqueue
        if not await self.queue.enqueue(queued_request):
            return JSONResponse(
                status_code=503,
                content={"error": "Service overloaded", "code": "queue_full"}
            )
        
        # Wait for processing
        try:
            result = await asyncio.wait_for(
                self._wait_for_processing(queued_request, call_next),
                timeout=self.request_timeout
            )
            return result
            
        except asyncio.TimeoutError:
            self.metrics.timeout_requests += 1
            return JSONResponse(
                status_code=504,
                content={"error": "Request timeout", "code": "timeout"}
            )
    
    async def _wait_for_processing(
        self,
        queued_request: QueuedRequest,
        call_next: Callable
    ) -> Response:
        """Wait for request to be processed."""
        
        # This is a simplified implementation
        # In practice, you'd implement a proper worker system
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Process the request
        return await call_next(queued_request.request)
    
    async def _process_request_directly(
        self,
        request: Request,
        call_next: Callable,
        start_time: float
    ) -> Response:
        """Process request directly without queuing."""
        
        try:
            response = await call_next(request)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics.processed_requests += 1
            self.metrics.total_requests += 1
            
            # Update Prometheus metrics
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(processing_time)
            
            return response
            
        except Exception as e:
            # Update circuit breaker
            self.circuit_breaker._on_failure()
            
            self.logger.error(f"Request processing error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "code": "processing_error"}
            )
    
    async def start_workers(self):
        """Start worker tasks for processing queued requests."""
        
        if self.is_running:
            return
        
        self.is_running = True
        self.logger.info(f"Starting {self.max_workers} request queue workers")
        
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
    
    async def stop_workers(self):
        """Stop worker tasks."""
        
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Stopping request queue workers")
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
    
    async def _worker(self, worker_name: str):
        """Worker coroutine for processing queued requests."""
        
        self.logger.info(f"Request queue worker {worker_name} started")
        
        while self.is_running:
            try:
                # Get next request from queue
                queued_request = await self.queue.dequeue()
                if queued_request is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process request
                await self._process_queued_request(queued_request, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)
        
        self.logger.info(f"Request queue worker {worker_name} stopped")
    
    async def _process_queued_request(self, queued_request: QueuedRequest, worker_name: str):
        """Process a queued request."""
        
        start_time = time.time()
        
        try:
            # This would be implemented to actually process the request
            # For now, we'll just log it
            self.logger.info(f"Worker {worker_name} processing request {queued_request.id}")
            
            # Update metrics
            wait_time = time.time() - queued_request.queued_at.timestamp()
            self.metrics.average_wait_time = (
                (self.metrics.average_wait_time * self.metrics.processed_requests + wait_time) /
                (self.metrics.processed_requests + 1)
            )
            
            self.metrics.processed_requests += 1
            
        except Exception as e:
            self.logger.error(f"Failed to process queued request {queued_request.id}: {e}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and metrics."""
        
        queue_stats = self.queue.get_queue_stats()
        circuit_breaker_state = self.circuit_breaker.get_state()
        
        # Determine overall status
        if self.metrics.queue_size == 0:
            status = QueueStatus.HEALTHY
        elif self.metrics.queue_size < self.max_queue_size * 0.7:
            status = QueueStatus.DEGRADED
        elif self.metrics.queue_size < self.max_queue_size:
            status = QueueStatus.OVERLOADED
        else:
            status = QueueStatus.CIRCUIT_OPEN
        
        return {
            "status": status.value,
            "queue_stats": queue_stats,
            "metrics": asdict(self.metrics),
            "circuit_breaker": circuit_breaker_state,
            "is_running": self.is_running,
            "active_workers": len(self.workers)
        }


def create_request_queue_middleware(
    app: ASGIApp,
    max_queue_size: int = 1000,
    max_workers: int = 10,
    **kwargs
) -> RequestQueueMiddleware:
    """Factory function to create request queue middleware."""
    
    middleware = RequestQueueMiddleware(
        app,
        max_queue_size=max_queue_size,
        max_workers=max_workers,
        **kwargs
    )
    
    return middleware
