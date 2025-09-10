# Performance Optimization and Low Latency Guide

## Overview

This guide covers strategies for optimizing payment gateway performance and achieving low latency. Performance is critical for user experience and business success.

## Table of Contents
1. [Performance Metrics](#performance-metrics)
2. [Database Optimization](#database-optimization)
3. [Caching Strategies](#caching-strategies)
4. [API Optimization](#api-optimization)
5. [Network Optimization](#network-optimization)
6. [Code Optimization](#code-optimization)
7. [Monitoring and Profiling](#monitoring-and-profiling)

## Performance Metrics

### Key Performance Indicators (KPIs)

**Response Time Metrics**:
- **P50**: 50th percentile response time
- **P95**: 95th percentile response time
- **P99**: 99th percentile response time
- **Average**: Mean response time

**Throughput Metrics**:
- **Requests per second (RPS)**
- **Transactions per second (TPS)**
- **Concurrent users**
- **Peak load capacity**

**Resource Utilization**:
- **CPU usage**
- **Memory usage**
- **Disk I/O**
- **Network I/O**

### Target Performance Goals

```yaml
performance_targets:
  api_response_time:
    p50: "< 100ms"
    p95: "< 200ms"
    p99: "< 500ms"
  
  database_queries:
    simple_queries: "< 10ms"
    complex_queries: "< 50ms"
    batch_operations: "< 100ms"
  
  external_api_calls:
    authorize_net: "< 300ms"
    webhooks: "< 100ms"
    notifications: "< 50ms"
  
  throughput:
    peak_rps: "> 1000"
    sustained_rps: "> 500"
    concurrent_users: "> 10000"
```

## Database Optimization

### Indexing Strategy

```sql
-- Primary indexes for payments table
CREATE INDEX idx_payments_merchant_id ON payments(merchant_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at);
CREATE INDEX idx_payments_correlation_id ON payments(correlation_id);

-- Composite indexes for common queries
CREATE INDEX idx_payments_merchant_status ON payments(merchant_id, status);
CREATE INDEX idx_payments_created_status ON payments(created_at, status);
CREATE INDEX idx_payments_merchant_created ON payments(merchant_id, created_at);

-- Partial indexes for active records
CREATE INDEX idx_payments_active ON payments(merchant_id) 
WHERE status IN ('pending', 'processing', 'completed');

-- Covering indexes for read-heavy queries
CREATE INDEX idx_payments_list ON payments(merchant_id, created_at, status, amount) 
INCLUDE (id, payment_method, authorize_net_transaction_id);
```

### Query Optimization

```python
# Bad: N+1 query problem
def get_payments_with_customers(merchant_id: str):
    payments = Payment.objects.filter(merchant_id=merchant_id)
    for payment in payments:
        customer = Customer.objects.get(id=payment.customer_id)
        payment.customer = customer
    return payments

# Good: Single query with join
def get_payments_with_customers(merchant_id: str):
    return Payment.objects.select_related('customer').filter(
        merchant_id=merchant_id
    )

# Bad: Multiple database calls
def get_payment_stats(merchant_id: str):
    total_payments = Payment.objects.filter(merchant_id=merchant_id).count()
    successful_payments = Payment.objects.filter(
        merchant_id=merchant_id, status='completed'
    ).count()
    return {'total': total_payments, 'successful': successful_payments}

# Good: Single query with aggregation
def get_payment_stats(merchant_id: str):
    from django.db.models import Count, Case, When, IntegerField
    
    stats = Payment.objects.filter(merchant_id=merchant_id).aggregate(
        total=Count('id'),
        successful=Count(Case(
            When(status='completed', then=1),
            output_field=IntegerField()
        ))
    )
    return stats
```

### Connection Pooling

```python
import asyncpg
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# AsyncPG connection pool
async def create_connection_pool():
    return await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="easypay",
        password="password",
        database="easypay",
        min_size=10,
        max_size=100,
        command_timeout=60
    )

# SQLAlchemy connection pool
engine = create_engine(
    "postgresql://easypay:password@localhost/easypay",
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### Database Partitioning

```sql
-- Partition payments table by date
CREATE TABLE payments (
    id UUID PRIMARY KEY,
    merchant_id UUID NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE payments_2024_01 PARTITION OF payments
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE payments_2024_02 PARTITION OF payments
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Create index on partition key
CREATE INDEX idx_payments_created_at ON payments (created_at);
```

## Caching Strategies

### Redis Caching

```python
import redis
import json
import pickle
from typing import Any, Optional, Union

class CacheManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 300  # 5 minutes
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        try:
            ttl = ttl or self.default_ttl
            data = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, data)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def get_or_set(self, key: str, factory: callable, ttl: int = None) -> Any:
        """Get from cache or set using factory function."""
        value = await self.get(key)
        if value is None:
            value = await factory()
            await self.set(key, value, ttl)
        return value
```

### Application-Level Caching

```python
from functools import lru_cache, wraps
import asyncio
from typing import Any, Callable

# Synchronous caching
@lru_cache(maxsize=1000)
def get_merchant_config(merchant_id: str) -> dict:
    """Cache merchant configuration."""
    return database.get_merchant_config(merchant_id)

# Asynchronous caching
def async_cache(ttl: int = 300):
    """Decorator for async function caching."""
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    return result
            
            result = await func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        
        return wrapper
    return decorator

@async_cache(ttl=600)
async def get_payment_methods(customer_id: str) -> list:
    """Cache customer payment methods."""
    return await database.get_payment_methods(customer_id)
```

### Cache Invalidation

```python
class CacheInvalidator:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    async def invalidate_merchant_cache(self, merchant_id: str):
        """Invalidate all merchant-related cache."""
        pattern = f"merchant:{merchant_id}:*"
        keys = await self.cache.redis.keys(pattern)
        if keys:
            await self.cache.redis.delete(*keys)
    
    async def invalidate_payment_cache(self, payment_id: str):
        """Invalidate payment-related cache."""
        patterns = [
            f"payment:{payment_id}",
            f"payment:*:{payment_id}",
            f"customer:*:payments"
        ]
        
        for pattern in patterns:
            keys = await self.cache.redis.keys(pattern)
            if keys:
                await self.cache.redis.delete(*keys)
```

## API Optimization

### Request/Response Optimization

```python
from fastapi import FastAPI, Response
from fastapi.middleware.gzip import GZipMiddleware
import orjson

app = FastAPI()

# Enable gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Use orjson for faster JSON serialization
@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str, response: Response):
    payment = await get_payment_from_db(payment_id)
    
    # Set cache headers
    response.headers["Cache-Control"] = "public, max-age=300"
    response.headers["ETag"] = f'"{payment.updated_at.timestamp()}"'
    
    return payment

# Implement pagination
@app.get("/payments")
async def list_payments(
    merchant_id: str,
    page: int = 1,
    size: int = 20,
    response: Response
):
    offset = (page - 1) * size
    
    payments = await get_payments_paginated(merchant_id, offset, size)
    total = await get_payments_count(merchant_id)
    
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Size"] = str(size)
    
    return {
        "data": payments,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size
        }
    }
```

### Async Processing

```python
import asyncio
from asyncio import Queue
from typing import Dict, Any

class AsyncPaymentProcessor:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.queue = Queue()
        self.workers = []
    
    async def start(self):
        """Start worker processes."""
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
    
    async def _worker(self, name: str):
        """Worker process for handling payments."""
        while True:
            try:
                payment_data = await self.queue.get()
                await self._process_payment(payment_data)
                self.queue.task_done()
            except Exception as e:
                print(f"Worker {name} error: {e}")
    
    async def queue_payment(self, payment_data: Dict[str, Any]):
        """Queue payment for processing."""
        await self.queue.put(payment_data)
    
    async def _process_payment(self, payment_data: Dict[str, Any]):
        """Process individual payment."""
        # Payment processing logic
        pass

# Usage
processor = AsyncPaymentProcessor(max_workers=10)
await processor.start()

# Queue payments for processing
await processor.queue_payment(payment_data)
```

### Connection Pooling

```python
import aiohttp
import asyncio
from typing import Dict, Any

class HTTPClient:
    def __init__(self, max_connections: int = 100):
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=30,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(connector=self.connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request with connection pooling."""
        async with self.session.post(url, json=data) as response:
            return await response.json()

# Usage
async def process_payment_with_authorize_net(payment_data: Dict[str, Any]):
    async with HTTPClient() as client:
        response = await client.post(
            "https://apitest.authorize.net/xml/v1/request.api",
            payment_data
        )
        return response
```

## Network Optimization

### HTTP/2 and Keep-Alive

```python
import httpx

# HTTP/2 client with keep-alive
async def create_http_client():
    return httpx.AsyncClient(
        http2=True,
        limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30
        ),
        timeout=httpx.Timeout(30.0)
    )
```

### DNS Optimization

```python
import socket
import asyncio
from typing import List, Tuple

class DNSResolver:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300
    
    async def resolve_hostname(self, hostname: str) -> str:
        """Resolve hostname with caching."""
        if hostname in self.cache:
            ip, timestamp = self.cache[hostname]
            if time.time() - timestamp < self.cache_ttl:
                return ip
        
        # Resolve hostname
        loop = asyncio.get_event_loop()
        ip = await loop.run_in_executor(
            None, socket.gethostbyname, hostname
        )
        
        self.cache[hostname] = (ip, time.time())
        return ip
```

### CDN Configuration

```yaml
# CloudFlare configuration
cloudflare:
  cache_rules:
    - pattern: "*.css"
      ttl: "1y"
    - pattern: "*.js"
      ttl: "1y"
    - pattern: "*.png"
      ttl: "1y"
    - pattern: "/api/v1/payments/*"
      ttl: "5m"
  
  compression:
    enabled: true
    algorithms: ["gzip", "brotli"]
  
  minification:
    enabled: true
    html: true
    css: true
    js: true
```

## Code Optimization

### Algorithm Optimization

```python
# Bad: O(n²) complexity
def find_duplicate_payments(payments: List[Dict]) -> List[Dict]:
    duplicates = []
    for i, payment1 in enumerate(payments):
        for j, payment2 in enumerate(payments[i+1:], i+1):
            if (payment1['amount'] == payment2['amount'] and
                payment1['merchant_id'] == payment2['merchant_id']):
                duplicates.append(payment1)
    return duplicates

# Good: O(n) complexity with hash set
def find_duplicate_payments(payments: List[Dict]) -> List[Dict]:
    seen = set()
    duplicates = []
    
    for payment in payments:
        key = (payment['amount'], payment['merchant_id'])
        if key in seen:
            duplicates.append(payment)
        else:
            seen.add(key)
    
    return duplicates
```

### Memory Optimization

```python
# Bad: Loading all data into memory
def process_large_payment_batch(payment_ids: List[str]):
    payments = []
    for payment_id in payment_ids:
        payment = get_payment(payment_id)
        payments.append(payment)
    
    # Process all payments
    for payment in payments:
        process_payment(payment)

# Good: Streaming processing
def process_large_payment_batch(payment_ids: List[str]):
    for payment_id in payment_ids:
        payment = get_payment(payment_id)
        process_payment(payment)
        # Payment is garbage collected after processing
```

### Profiling and Optimization

```python
import cProfile
import pstats
from functools import wraps

def profile_function(func):
    """Decorator to profile function performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)  # Print top 10 functions
        
        return result
    return wrapper

# Usage
@profile_function
def process_payment_batch(payments: List[Dict]):
    # Payment processing logic
    pass
```

## Monitoring and Profiling

### Performance Monitoring

```python
import time
import logging
from functools import wraps
from typing import Callable, Any

class PerformanceMonitor:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.metrics = {}
    
    def monitor_function(self, func_name: str):
        """Decorator to monitor function performance."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    self._record_metric(func_name, duration, success=True)
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self._record_metric(func_name, duration, success=False)
                    raise e
            
            return wrapper
        return decorator
    
    def _record_metric(self, func_name: str, duration: float, success: bool):
        """Record performance metric."""
        if func_name not in self.metrics:
            self.metrics[func_name] = {
                'total_calls': 0,
                'total_duration': 0,
                'successful_calls': 0,
                'failed_calls': 0
            }
        
        self.metrics[func_name]['total_calls'] += 1
        self.metrics[func_name]['total_duration'] += duration
        
        if success:
            self.metrics[func_name]['successful_calls'] += 1
        else:
            self.metrics[func_name]['failed_calls'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.metrics
```

### APM Integration

```python
from elasticapm import Client
from elasticapm.contrib.fastapi import FastAPM

# Elastic APM configuration
apm_client = Client({
    'SERVICE_NAME': 'easypay-payment-service',
    'SECRET_TOKEN': 'your-secret-token',
    'SERVER_URL': 'https://your-apm-server.com',
    'ENVIRONMENT': 'production'
})

# FastAPI integration
app = FastAPI()
FastAPM(app, apm_client)

# Custom transaction tracking
@apm_client.capture_span('process_payment')
async def process_payment(payment_data: Dict[str, Any]):
    # Payment processing logic
    pass
```

### Load Testing

```python
import asyncio
import aiohttp
import time
from typing import List, Dict, Any

class LoadTester:
    def __init__(self, base_url: str, max_concurrent: int = 100):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.results = []
    
    async def run_load_test(self, requests: List[Dict[str, Any]], 
                           duration: int = 60):
        """Run load test for specified duration."""
        start_time = time.time()
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        tasks = []
        while time.time() - start_time < duration:
            for request in requests:
                task = asyncio.create_task(
                    self._make_request(semaphore, request)
                )
                tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._analyze_results()
    
    async def _make_request(self, semaphore: asyncio.Semaphore, 
                           request: Dict[str, Any]):
        """Make individual request."""
        async with semaphore:
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}{request['endpoint']}",
                        json=request['data']
                    ) as response:
                        duration = time.time() - start_time
                        self.results.append({
                            'status_code': response.status,
                            'duration': duration,
                            'success': response.status < 400
                        })
            except Exception as e:
                duration = time.time() - start_time
                self.results.append({
                    'status_code': 0,
                    'duration': duration,
                    'success': False,
                    'error': str(e)
                })
    
    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze load test results."""
        if not self.results:
            return {}
        
        durations = [r['duration'] for r in self.results]
        successful = [r for r in self.results if r['success']]
        
        return {
            'total_requests': len(self.results),
            'successful_requests': len(successful),
            'success_rate': len(successful) / len(self.results),
            'average_duration': sum(durations) / len(durations),
            'p95_duration': sorted(durations)[int(len(durations) * 0.95)],
            'p99_duration': sorted(durations)[int(len(durations) * 0.99)]
        }
```

## Best Practices

### 1. Database Optimization
- Use appropriate indexes
- Optimize queries
- Implement connection pooling
- Use database partitioning for large tables

### 2. Caching Strategy
- Cache frequently accessed data
- Use appropriate cache TTL
- Implement cache invalidation
- Monitor cache hit rates

### 3. API Design
- Use pagination for large datasets
- Implement compression
- Set appropriate cache headers
- Use async processing

### 4. Code Optimization
- Profile before optimizing
- Use efficient algorithms
- Minimize memory usage
- Implement proper error handling

### 5. Monitoring
- Track key performance metrics
- Set up alerting
- Regular performance testing
- Continuous optimization

## Common Performance Issues

### Issue: Slow Database Queries
- **Cause**: Missing indexes, inefficient queries
- **Solution**: Add indexes, optimize queries, use query analysis

### Issue: High Memory Usage
- **Cause**: Memory leaks, large data structures
- **Solution**: Profile memory usage, optimize data structures

### Issue: Slow API Responses
- **Cause**: Synchronous processing, external API calls
- **Solution**: Use async processing, implement caching

### Issue: High CPU Usage
- **Cause**: Inefficient algorithms, tight loops
- **Solution**: Optimize algorithms, use profiling tools

## Next Steps

1. Create [Integration Examples](10-integration-examples.md)
2. Implement [Security Best Practices](11-security-guide.md)
3. Set up [Monitoring and Observability](12-monitoring-guide.md)
4. Review [Deployment Guide](13-deployment-guide.md)

## Resources

- [FastAPI Performance](https://fastapi.tiangolo.com/benchmarks/)
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/performance-tips.html)
- [Redis Performance](https://redis.io/docs/manual/performance/)
- [Python Performance](https://docs.python.org/3/library/profile.html)
