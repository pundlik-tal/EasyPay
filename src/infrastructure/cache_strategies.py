"""
EasyPay Payment Gateway - Advanced Cache Strategies

This module provides advanced caching strategies and patterns for improved performance.
"""

import json
import hashlib
import time
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio

from src.infrastructure.cache import CacheManager, get_cache_client
from src.core.exceptions import CacheError


class CacheStrategy:
    """Base cache strategy class."""
    
    def __init__(self, cache_manager: CacheManager, ttl: int = 300):
        self.cache = cache_manager
        self.ttl = ttl
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        # Create hash for long keys
        key_string = ":".join(key_parts)
        if len(key_string) > 200:
            key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
            return f"{prefix}:{key_hash}"
        
        return key_string


class WriteThroughCache(CacheStrategy):
    """Write-through cache strategy."""
    
    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Get from cache or fetch and cache the result."""
        try:
            # Try cache first
            cached_value = await self.cache.get(key)
            if cached_value:
                return json.loads(cached_value)
            
            # Cache miss - fetch data
            result = await fetch_func(*args, **kwargs)
            
            # Cache the result
            await self.cache.set(key, json.dumps(result, default=str), self.ttl)
            
            return result
            
        except Exception as e:
            # Fallback to direct fetch
            return await fetch_func(*args, **kwargs)


class WriteBehindCache(CacheStrategy):
    """Write-behind cache strategy for high-write scenarios."""
    
    def __init__(self, cache_manager: CacheManager, ttl: int = 300, batch_size: int = 100):
        super().__init__(cache_manager, ttl)
        self.batch_size = batch_size
        self.write_queue = asyncio.Queue()
        self._write_task = None
    
    async def start_background_writer(self):
        """Start background task for batch writes."""
        if self._write_task is None:
            self._write_task = asyncio.create_task(self._batch_writer())
    
    async def stop_background_writer(self):
        """Stop background writer task."""
        if self._write_task:
            self._write_task.cancel()
            try:
                await self._write_task
            except asyncio.CancelledError:
                pass
            self._write_task = None
    
    async def _batch_writer(self):
        """Background task to batch write operations."""
        batch = []
        
        while True:
            try:
                # Collect batch
                while len(batch) < self.batch_size:
                    try:
                        item = await asyncio.wait_for(self.write_queue.get(), timeout=1.0)
                        batch.append(item)
                    except asyncio.TimeoutError:
                        break
                
                # Process batch
                if batch:
                    await self._process_batch(batch)
                    batch.clear()
                
            except asyncio.CancelledError:
                # Process remaining items
                if batch:
                    await self._process_batch(batch)
                break
            except Exception as e:
                # Log error and continue
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in batch writer: {e}")
    
    async def _process_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of write operations."""
        # This would be implemented based on specific requirements
        pass
    
    async def queue_write(self, key: str, value: Any):
        """Queue a write operation."""
        await self.write_queue.put({"key": key, "value": value, "timestamp": time.time()})


class CacheAside(CacheStrategy):
    """Cache-aside pattern implementation."""
    
    async def get_or_compute(
        self,
        key: str,
        compute_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Get from cache or compute and cache."""
        try:
            # Try cache first
            cached_value = await self.cache.get(key)
            if cached_value:
                return json.loads(cached_value)
            
            # Cache miss - compute value
            result = await compute_func(*args, **kwargs)
            
            # Cache the result
            await self.cache.set(key, json.dumps(result, default=str), self.ttl)
            
            return result
            
        except Exception as e:
            # Fallback to direct computation
            return await compute_func(*args, **kwargs)


class MultiLevelCache:
    """Multi-level cache implementation (L1: Memory, L2: Redis)."""
    
    def __init__(self, redis_cache: CacheManager, memory_size: int = 1000):
        self.redis_cache = redis_cache
        self.memory_cache = {}  # Simple in-memory cache
        self.memory_size = memory_size
        self.access_times = {}  # Track access times for LRU
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from multi-level cache."""
        # L1: Memory cache
        if key in self.memory_cache:
            self.access_times[key] = time.time()
            return self.memory_cache[key]
        
        # L2: Redis cache
        try:
            redis_value = await self.redis_cache.get(key)
            if redis_value:
                # Promote to L1 cache
                await self._promote_to_l1(key, redis_value)
                return json.loads(redis_value)
        except Exception:
            pass
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set in multi-level cache."""
        # Set in both levels
        await self.redis_cache.set(key, json.dumps(value, default=str), ttl)
        await self._promote_to_l1(key, value)
    
    async def _promote_to_l1(self, key: str, value: Any):
        """Promote value to L1 cache."""
        # Implement LRU eviction if needed
        if len(self.memory_cache) >= self.memory_size:
            await self._evict_lru()
        
        self.memory_cache[key] = value
        self.access_times[key] = time.time()
    
    async def _evict_lru(self):
        """Evict least recently used item from L1 cache."""
        if not self.access_times:
            return
        
        # Find LRU item
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        
        # Remove from L1 cache
        del self.memory_cache[lru_key]
        del self.access_times[lru_key]


class CacheDecorator:
    """Decorator for caching function results."""
    
    def __init__(self, cache_strategy: CacheStrategy, key_prefix: str = ""):
        self.cache_strategy = cache_strategy
        self.key_prefix = key_prefix
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = self.cache_strategy.generate_key(
                f"{self.key_prefix}:{func.__name__}",
                *args,
                **kwargs
            )
            
            # Try cache first
            try:
                cached_result = await self.cache_strategy.cache.get(key)
                if cached_result:
                    return json.loads(cached_result)
            except Exception:
                pass
            
            # Cache miss - execute function
            result = await func(*args, **kwargs)
            
            # Cache the result
            try:
                await self.cache_strategy.cache.set(
                    key,
                    json.dumps(result, default=str),
                    self.cache_strategy.ttl
                )
            except Exception:
                pass
            
            return result
        
        return wrapper


class CacheMetrics:
    """Cache performance metrics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_requests = 0
    
    def record_hit(self):
        """Record a cache hit."""
        self.hits += 1
        self.total_requests += 1
    
    def record_miss(self):
        """Record a cache miss."""
        self.misses += 1
        self.total_requests += 1
    
    def record_error(self):
        """Record a cache error."""
        self.errors += 1
        self.total_requests += 1
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        if self.total_requests == 0:
            return 0.0
        return self.misses / self.total_requests
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_requests": self.total_requests,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate
        }


class CacheManager:
    """Enhanced cache manager with multiple strategies."""
    
    def __init__(self, redis_client=None):
        self.redis_cache = CacheManager(redis_client or get_cache_client())
        self.multi_level_cache = MultiLevelCache(self.redis_cache)
        self.metrics = CacheMetrics()
        
        # Initialize strategies
        self.write_through = WriteThroughCache(self.redis_cache)
        self.write_behind = WriteBehindCache(self.redis_cache)
        self.cache_aside = CacheAside(self.redis_cache)
    
    async def get(self, key: str, use_multi_level: bool = False) -> Optional[Any]:
        """Get value from cache."""
        try:
            if use_multi_level:
                result = await self.multi_level_cache.get(key)
            else:
                result = await self.redis_cache.get(key)
            
            if result:
                self.metrics.record_hit()
            else:
                self.metrics.record_miss()
            
            return result
            
        except Exception as e:
            self.metrics.record_error()
            raise CacheError(f"Cache get error: {str(e)}")
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        use_multi_level: bool = False
    ) -> bool:
        """Set value in cache."""
        try:
            if use_multi_level:
                await self.multi_level_cache.set(key, value, ttl)
            else:
                await self.redis_cache.set(key, value, ttl)
            
            return True
            
        except Exception as e:
            self.metrics.record_error()
            raise CacheError(f"Cache set error: {str(e)}")
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            # Delete from both levels
            redis_result = await self.redis_cache.delete(key)
            
            # Delete from L1 cache
            if key in self.multi_level_cache.memory_cache:
                del self.multi_level_cache.memory_cache[key]
                if key in self.multi_level_cache.access_times:
                    del self.multi_level_cache.access_times[key]
            
            return redis_result
            
        except Exception as e:
            self.metrics.record_error()
            raise CacheError(f"Cache delete error: {str(e)}")
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        try:
            keys = await self.redis_cache.redis.keys(pattern)
            if keys:
                return await self.redis_cache.redis.delete(*keys)
            return 0
            
        except Exception as e:
            self.metrics.record_error()
            raise CacheError(f"Cache pattern invalidation error: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        return self.metrics.get_stats()
    
    async def warm_cache(self, warm_data: Dict[str, Any], ttl: int = 300):
        """Warm cache with provided data."""
        for key, value in warm_data.items():
            try:
                await self.set(key, value, ttl)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to warm cache for key {key}: {e}")
    
    async def clear_all(self):
        """Clear all cache data."""
        try:
            await self.redis_cache.redis.flushdb()
            self.multi_level_cache.memory_cache.clear()
            self.multi_level_cache.access_times.clear()
        except Exception as e:
            raise CacheError(f"Cache clear error: {str(e)}")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_enhanced_cache_manager() -> CacheManager:
    """Get the global enhanced cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
    
    return _cache_manager


async def init_enhanced_cache() -> None:
    """Initialize enhanced cache system."""
    global _cache_manager
    
    _cache_manager = CacheManager()
    
    # Start background tasks
    await _cache_manager.write_behind.start_background_writer()
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Enhanced cache system initialized")


async def close_enhanced_cache() -> None:
    """Close enhanced cache system."""
    global _cache_manager
    
    if _cache_manager:
        await _cache_manager.write_behind.stop_background_writer()
        _cache_manager = None
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Enhanced cache system closed")
