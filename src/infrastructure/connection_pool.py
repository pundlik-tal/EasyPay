"""
EasyPay Payment Gateway - Enhanced Connection Pool Management

This module provides enhanced database connection pooling with monitoring,
optimization, and advanced pool management features.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for

from src.core.config import Settings
from src.core.exceptions import DatabaseError


class ConnectionPoolMonitor:
    """Monitor connection pool health and performance."""
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self.metrics = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_checked_out': 0,
            'connections_checked_in': 0,
            'pool_overflow': 0,
            'pool_timeout': 0,
            'last_reset': datetime.now()
        }
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners for pool monitoring."""
        
        @listens_for(Engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            self.metrics['connections_created'] += 1
        
        @listens_for(Engine, "close")
        def on_close(dbapi_connection, connection_record):
            self.metrics['connections_closed'] += 1
        
        @listens_for(Engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            self.metrics['connections_checked_out'] += 1
        
        @listens_for(Engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            self.metrics['connections_checked_in'] += 1
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status and metrics."""
        pool = self.engine.pool
        
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'invalid': pool.invalid(),
            'metrics': self.metrics.copy(),
            'pool_class': pool.__class__.__name__,
            'pool_timeout': getattr(pool, 'timeout', None),
            'pool_recycle': getattr(pool, 'recycle', None),
            'pool_pre_ping': getattr(pool, 'pre_ping', None)
        }
    
    def reset_metrics(self):
        """Reset connection metrics."""
        self.metrics = {
            'connections_created': 0,
            'connections_closed': 0,
            'connections_checked_out': 0,
            'connections_checked_in': 0,
            'pool_overflow': 0,
            'pool_timeout': 0,
            'last_reset': datetime.now()
        }


class ConnectionPoolManager:
    """Advanced connection pool manager with optimization."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engines: Dict[str, AsyncEngine] = {}
        self.monitors: Dict[str, ConnectionPoolMonitor] = {}
        self.logger = logging.getLogger(__name__)
        
        # Pool configuration
        self.pool_config = {
            'pool_size': settings.DATABASE_POOL_SIZE,
            'max_overflow': settings.DATABASE_MAX_OVERFLOW,
            'pool_timeout': 30,  # seconds
            'pool_recycle': 3600,  # 1 hour
            'pool_pre_ping': True,
            'pool_reset_on_return': 'commit'
        }
    
    async def create_engine(
        self,
        database_url: str,
        pool_name: str = "default",
        **kwargs
    ) -> AsyncEngine:
        """Create an optimized async engine with connection pooling."""
        
        # Merge pool configuration with kwargs
        engine_kwargs = {**self.pool_config, **kwargs}
        
        # Convert to async URL
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        try:
            # Create async engine
            engine = create_async_engine(
                async_url,
                poolclass=QueuePool,
                **engine_kwargs
            )
            
            # Store engine and create monitor
            self.engines[pool_name] = engine
            self.monitors[pool_name] = ConnectionPoolMonitor(engine)
            
            self.logger.info(f"Created connection pool '{pool_name}' with config: {engine_kwargs}")
            
            return engine
            
        except Exception as e:
            raise DatabaseError(f"Failed to create connection pool '{pool_name}': {str(e)}")
    
    async def create_read_replica_engine(
        self,
        read_urls: List[str],
        pool_name: str = "read_replica"
    ) -> AsyncEngine:
        """Create a read replica engine with load balancing."""
        
        # For simplicity, use the first read URL
        # In production, you'd implement proper load balancing
        if not read_urls:
            raise DatabaseError("No read replica URLs provided")
        
        return await self.create_engine(read_urls[0], pool_name)
    
    async def create_session_factory(
        self,
        pool_name: str = "default"
    ) -> sessionmaker:
        """Create a session factory for a specific pool."""
        
        if pool_name not in self.engines:
            raise DatabaseError(f"Pool '{pool_name}' not found")
        
        engine = self.engines[pool_name]
        
        return sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    @asynccontextmanager
    async def get_session(self, pool_name: str = "default"):
        """Get a database session with automatic cleanup."""
        
        if pool_name not in self.engines:
            raise DatabaseError(f"Pool '{pool_name}' not found")
        
        session_factory = await self.create_session_factory(pool_name)
        
        async with session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise DatabaseError(f"Database session error: {str(e)}")
            finally:
                await session.close()
    
    async def health_check(self, pool_name: str = "default") -> Dict[str, Any]:
        """Perform health check on a connection pool."""
        
        if pool_name not in self.engines:
            return {"status": "error", "message": f"Pool '{pool_name}' not found"}
        
        engine = self.engines[pool_name]
        monitor = self.monitors[pool_name]
        
        try:
            # Test connection
            async with engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            # Get pool status
            pool_status = monitor.get_pool_status()
            
            return {
                "status": "healthy",
                "pool_status": pool_status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def optimize_pool(self, pool_name: str = "default") -> Dict[str, Any]:
        """Optimize connection pool based on usage patterns."""
        
        if pool_name not in self.monitors:
            raise DatabaseError(f"Pool '{pool_name}' not found")
        
        monitor = self.monitors[pool_name]
        pool_status = monitor.get_pool_status()
        
        optimizations = []
        
        # Check for pool overflow
        if pool_status['overflow'] > 0:
            optimizations.append({
                'type': 'increase_pool_size',
                'current_size': pool_status['pool_size'],
                'suggested_size': pool_status['pool_size'] + pool_status['overflow'],
                'reason': 'Pool overflow detected'
            })
        
        # Check for high checkout ratio
        checkout_ratio = pool_status['checked_out'] / max(pool_status['pool_size'], 1)
        if checkout_ratio > 0.8:
            optimizations.append({
                'type': 'increase_pool_size',
                'current_size': pool_status['pool_size'],
                'suggested_size': int(pool_status['pool_size'] * 1.5),
                'reason': 'High checkout ratio detected'
            })
        
        # Check for connection timeouts
        if monitor.metrics['pool_timeout'] > 0:
            optimizations.append({
                'type': 'increase_timeout',
                'current_timeout': self.pool_config['pool_timeout'],
                'suggested_timeout': self.pool_config['pool_timeout'] * 2,
                'reason': 'Connection timeouts detected'
            })
        
        return {
            'pool_name': pool_name,
            'current_status': pool_status,
            'optimizations': optimizations,
            'timestamp': datetime.now().isoformat()
        }
    
    async def warm_up_pool(self, pool_name: str = "default", connections: int = None):
        """Warm up connection pool by creating initial connections."""
        
        if pool_name not in self.engines:
            raise DatabaseError(f"Pool '{pool_name}' not found")
        
        engine = self.engines[pool_name]
        pool_size = connections or self.pool_config['pool_size']
        
        self.logger.info(f"Warming up pool '{pool_name}' with {pool_size} connections")
        
        # Create connections to warm up the pool
        connections_created = []
        try:
            for i in range(min(pool_size, 10)):  # Limit to 10 for safety
                conn = await engine.connect()
                connections_created.append(conn)
            
            self.logger.info(f"Successfully warmed up {len(connections_created)} connections")
            
        finally:
            # Close all connections
            for conn in connections_created:
                await conn.close()
    
    async def close_pool(self, pool_name: str = "default"):
        """Close a connection pool."""
        
        if pool_name in self.engines:
            engine = self.engines[pool_name]
            await engine.dispose()
            del self.engines[pool_name]
            del self.monitors[pool_name]
            
            self.logger.info(f"Closed connection pool '{pool_name}'")
    
    async def close_all_pools(self):
        """Close all connection pools."""
        
        for pool_name in list(self.engines.keys()):
            await self.close_pool(pool_name)
        
        self.logger.info("Closed all connection pools")
    
    def get_all_pool_status(self) -> Dict[str, Any]:
        """Get status of all connection pools."""
        
        status = {}
        for pool_name, monitor in self.monitors.items():
            status[pool_name] = monitor.get_pool_status()
        
        return status


class ConnectionPoolOptimizer:
    """Automatically optimize connection pools based on usage patterns."""
    
    def __init__(self, pool_manager: ConnectionPoolManager):
        self.pool_manager = pool_manager
        self.logger = logging.getLogger(__name__)
        self.optimization_history = []
    
    async def run_optimization_cycle(self):
        """Run a complete optimization cycle for all pools."""
        
        self.logger.info("Starting connection pool optimization cycle")
        
        for pool_name in self.pool_manager.engines.keys():
            try:
                optimization_result = await self.pool_manager.optimize_pool(pool_name)
                self.optimization_history.append(optimization_result)
                
                # Log optimizations
                for opt in optimization_result['optimizations']:
                    self.logger.info(
                        f"Pool '{pool_name}' optimization: {opt['type']} - {opt['reason']}"
                    )
                
            except Exception as e:
                self.logger.error(f"Failed to optimize pool '{pool_name}': {e}")
    
    def get_optimization_history(self, pool_name: str = None) -> List[Dict[str, Any]]:
        """Get optimization history for a specific pool or all pools."""
        
        if pool_name:
            return [opt for opt in self.optimization_history if opt['pool_name'] == pool_name]
        
        return self.optimization_history


# Global connection pool manager
_pool_manager: Optional[ConnectionPoolManager] = None


def get_pool_manager() -> ConnectionPoolManager:
    """Get the global connection pool manager."""
    global _pool_manager
    
    if _pool_manager is None:
        from src.core.config import Settings
        settings = Settings()
        _pool_manager = ConnectionPoolManager(settings)
    
    return _pool_manager


async def init_connection_pools(settings: Settings) -> ConnectionPoolManager:
    """Initialize connection pools."""
    global _pool_manager
    
    _pool_manager = ConnectionPoolManager(settings)
    
    # Create main database pool
    await _pool_manager.create_engine(
        settings.DATABASE_URL,
        "main"
    )
    
    # Warm up the pool
    await _pool_manager.warm_up_pool("main")
    
    logging.getLogger(__name__).info("Connection pools initialized")
    
    return _pool_manager


async def close_connection_pools():
    """Close all connection pools."""
    global _pool_manager
    
    if _pool_manager:
        await _pool_manager.close_all_pools()
        _pool_manager = None
        
        logging.getLogger(__name__).info("Connection pools closed")
