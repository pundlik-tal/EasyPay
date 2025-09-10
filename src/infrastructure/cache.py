"""
EasyPay Payment Gateway - Cache Infrastructure
"""
import os
from typing import Optional, Any

import redis.asyncio as redis
from redis.asyncio import Redis

from src.core.exceptions import CacheError

# Cache configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "10"))

# Global Redis client
_redis_client: Optional[Redis] = None


async def init_cache() -> None:
    """
    Initialize Redis cache connection.
    
    Raises:
        CacheError: If cache initialization fails
    """
    global _redis_client
    
    try:
        _redis_client = redis.from_url(
            REDIS_URL,
            max_connections=REDIS_POOL_SIZE,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={}
        )
        
        # Test connection
        await _redis_client.ping()
        
        # Log successful initialization
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Cache initialized successfully")
        
    except Exception as e:
        raise CacheError(f"Failed to initialize cache: {str(e)}")


def get_cache_client() -> Redis:
    """
    Get Redis cache client.
    
    Returns:
        Redis: Redis client instance
        
    Raises:
        CacheError: If cache client is not initialized
    """
    if _redis_client is None:
        raise CacheError("Cache client not initialized")
    
    return _redis_client


async def close_cache() -> None:
    """
    Close cache connections.
    
    Raises:
        CacheError: If cache closure fails
    """
    global _redis_client
    
    try:
        if _redis_client:
            await _redis_client.close()
            _redis_client = None
        
        # Log successful closure
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Cache connections closed successfully")
        
    except Exception as e:
        raise CacheError(f"Failed to close cache connections: {str(e)}")


class CacheManager:
    """Cache manager for common operations."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
            
        Raises:
            CacheError: If cache operation fails
        """
        try:
            value = await self.redis.get(key)
            return value.decode('utf-8') if value else None
        except Exception as e:
            raise CacheError(f"Failed to get cache key {key}: {str(e)}")
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds
            
        Returns:
            True if successful
            
        Raises:
            CacheError: If cache operation fails
        """
        try:
            if expire:
                await self.redis.setex(key, expire, value)
            else:
                await self.redis.set(key, value)
            return True
        except Exception as e:
            raise CacheError(f"Failed to set cache key {key}: {str(e)}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
            
        Raises:
            CacheError: If cache operation fails
        """
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            raise CacheError(f"Failed to delete cache key {key}: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
            
        Raises:
            CacheError: If cache operation fails
        """
        try:
            result = await self.redis.exists(key)
            return result > 0
        except Exception as e:
            raise CacheError(f"Failed to check cache key {key}: {str(e)}")
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment
            
        Raises:
            CacheError: If cache operation fails
        """
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            raise CacheError(f"Failed to increment cache key {key}: {str(e)}")
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to decrement by
            
        Returns:
            New value after decrement
            
        Raises:
            CacheError: If cache operation fails
        """
        try:
            return await self.redis.decrby(key, amount)
        except Exception as e:
            raise CacheError(f"Failed to decrement cache key {key}: {str(e)}")
