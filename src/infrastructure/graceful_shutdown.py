"""
EasyPay Payment Gateway - Graceful Shutdown Service

This module provides comprehensive graceful shutdown functionality including:
- Signal handling for SIGTERM and SIGINT
- Resource cleanup management
- Connection draining
- Background task management
- Health check coordination
"""

import asyncio
import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Callable, Optional, Union
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ShutdownPhase(str, Enum):
    """Shutdown phases."""
    INITIATED = "initiated"
    DRAINING_CONNECTIONS = "draining_connections"
    STOPPING_SERVICES = "stopping_services"
    CLEANING_RESOURCES = "cleaning_resources"
    COMPLETED = "completed"


class ShutdownPriority(str, Enum):
    """Shutdown handler priorities."""
    CRITICAL = "critical"      # Must complete (database connections, etc.)
    HIGH = "high"              # Should complete (background tasks)
    MEDIUM = "medium"          # Nice to complete (cache cleanup)
    LOW = "low"                # Optional (metrics, logging)


@dataclass
class ShutdownHandler:
    """Shutdown handler definition."""
    name: str
    handler: Callable
    priority: ShutdownPriority
    timeout: int = 30  # seconds
    required: bool = True
    phase: ShutdownPhase = ShutdownPhase.STOPPING_SERVICES


@dataclass
class ShutdownMetrics:
    """Shutdown process metrics."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration: Optional[float] = None
    handlers_executed: int = 0
    handlers_failed: int = 0
    handlers_timeout: int = 0
    active_connections: int = 0
    background_tasks: int = 0


class GracefulShutdownManager:
    """Manages graceful shutdown of the application."""
    
    def __init__(self, shutdown_timeout: int = 60):
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_handlers: Dict[str, ShutdownHandler] = {}
        self.is_shutting_down = False
        self.current_phase = None
        self.metrics = ShutdownMetrics()
        self.logger = logging.getLogger(__name__)
        
        # Connection tracking
        self.active_connections: List[asyncio.Task] = []
        self.background_tasks: List[asyncio.Task] = []
        
        # Health check coordination
        self.health_check_enabled = True
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def register_shutdown_handler(
        self,
        name: str,
        handler: Callable,
        priority: ShutdownPriority = ShutdownPriority.MEDIUM,
        timeout: int = 30,
        required: bool = True,
        phase: ShutdownPhase = ShutdownPhase.STOPPING_SERVICES
    ):
        """Register a shutdown handler."""
        shutdown_handler = ShutdownHandler(
            name=name,
            handler=handler,
            priority=priority,
            timeout=timeout,
            required=required,
            phase=phase
        )
        
        self.shutdown_handlers[name] = shutdown_handler
        self.logger.info(f"Registered shutdown handler: {name} (priority: {priority.value})")
    
    def unregister_shutdown_handler(self, name: str) -> bool:
        """Unregister a shutdown handler."""
        if name in self.shutdown_handlers:
            del self.shutdown_handlers[name]
            self.logger.info(f"Unregistered shutdown handler: {name}")
            return True
        return False
    
    def track_connection(self, connection_task: asyncio.Task):
        """Track an active connection."""
        self.active_connections.append(connection_task)
        self.metrics.active_connections = len(self.active_connections)
    
    def untrack_connection(self, connection_task: asyncio.Task):
        """Untrack a connection."""
        if connection_task in self.active_connections:
            self.active_connections.remove(connection_task)
            self.metrics.active_connections = len(self.active_connections)
    
    def track_background_task(self, task: asyncio.Task):
        """Track a background task."""
        self.background_tasks.append(task)
        self.metrics.background_tasks = len(self.background_tasks)
    
    def untrack_background_task(self, task: asyncio.Task):
        """Untrack a background task."""
        if task in self.background_tasks:
            self.background_tasks.remove(task)
            self.metrics.background_tasks = len(self.background_tasks)
    
    async def shutdown(self):
        """Perform graceful shutdown."""
        if self.is_shutting_down:
            self.logger.warning("Shutdown already in progress")
            return
        
        self.is_shutting_down = True
        self.metrics.start_time = datetime.utcnow()
        
        self.logger.info("Starting graceful shutdown process...")
        
        try:
            # Phase 1: Disable health checks
            await self._disable_health_checks()
            
            # Phase 2: Drain connections
            await self._drain_connections()
            
            # Phase 3: Stop services
            await self._stop_services()
            
            # Phase 4: Cleanup resources
            await self._cleanup_resources()
            
            # Phase 5: Complete shutdown
            await self._complete_shutdown()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            await self._force_shutdown()
        
        finally:
            self.metrics.end_time = datetime.utcnow()
            if self.metrics.start_time:
                self.metrics.total_duration = (
                    self.metrics.end_time - self.metrics.start_time
                ).total_seconds()
            
            self.logger.info(f"Graceful shutdown completed in {self.metrics.total_duration:.2f}s")
    
    async def _disable_health_checks(self):
        """Disable health checks to prevent new connections."""
        self.current_phase = ShutdownPhase.INITIATED
        self.health_check_enabled = False
        self.logger.info("Health checks disabled")
    
    async def _drain_connections(self):
        """Drain existing connections."""
        self.current_phase = ShutdownPhase.DRAINING_CONNECTIONS
        self.logger.info(f"Draining {len(self.active_connections)} active connections...")
        
        # Wait for connections to complete or timeout
        if self.active_connections:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_connections, return_exceptions=True),
                    timeout=30
                )
            except asyncio.TimeoutError:
                self.logger.warning("Connection draining timeout, forcing closure")
                for connection in self.active_connections:
                    if not connection.done():
                        connection.cancel()
        
        self.logger.info("Connection draining completed")
    
    async def _stop_services(self):
        """Stop all registered services."""
        self.current_phase = ShutdownPhase.STOPPING_SERVICES
        self.logger.info("Stopping services...")
        
        # Group handlers by priority
        handlers_by_priority = {}
        for handler in self.shutdown_handlers.values():
            if handler.phase == ShutdownPhase.STOPPING_SERVICES:
                priority = handler.priority.value
                if priority not in handlers_by_priority:
                    handlers_by_priority[priority] = []
                handlers_by_priority[priority].append(handler)
        
        # Execute handlers in priority order
        priority_order = [ShutdownPriority.CRITICAL, ShutdownPriority.HIGH, 
                        ShutdownPriority.MEDIUM, ShutdownPriority.LOW]
        
        for priority in priority_order:
            handlers = handlers_by_priority.get(priority.value, [])
            if handlers:
                self.logger.info(f"Executing {priority.value} priority handlers...")
                await self._execute_handlers(handlers)
        
        self.logger.info("Services stopped")
    
    async def _cleanup_resources(self):
        """Cleanup resources."""
        self.current_phase = ShutdownPhase.CLEANING_RESOURCES
        self.logger.info("Cleaning up resources...")
        
        # Stop background tasks
        if self.background_tasks:
            self.logger.info(f"Stopping {len(self.background_tasks)} background tasks...")
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=10
                )
            except asyncio.TimeoutError:
                self.logger.warning("Background task cleanup timeout")
        
        # Execute cleanup handlers
        cleanup_handlers = [
            handler for handler in self.shutdown_handlers.values()
            if handler.phase == ShutdownPhase.CLEANING_RESOURCES
        ]
        
        if cleanup_handlers:
            await self._execute_handlers(cleanup_handlers)
        
        self.logger.info("Resource cleanup completed")
    
    async def _complete_shutdown(self):
        """Complete the shutdown process."""
        self.current_phase = ShutdownPhase.COMPLETED
        self.logger.info("Shutdown process completed")
    
    async def _execute_handlers(self, handlers: List[ShutdownHandler]):
        """Execute shutdown handlers."""
        for handler in handlers:
            try:
                self.logger.info(f"Executing shutdown handler: {handler.name}")
                
                # Execute handler with timeout
                if asyncio.iscoroutinefunction(handler.handler):
                    await asyncio.wait_for(handler.handler(), timeout=handler.timeout)
                else:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, handler.handler),
                        timeout=handler.timeout
                    )
                
                self.metrics.handlers_executed += 1
                self.logger.info(f"Shutdown handler {handler.name} completed successfully")
                
            except asyncio.TimeoutError:
                self.metrics.handlers_timeout += 1
                self.logger.error(f"Shutdown handler {handler.name} timed out after {handler.timeout}s")
                
                if handler.required:
                    self.logger.critical(f"Required shutdown handler {handler.name} failed")
                
            except Exception as e:
                self.metrics.handlers_failed += 1
                self.logger.error(f"Shutdown handler {handler.name} failed: {e}")
                
                if handler.required:
                    self.logger.critical(f"Required shutdown handler {handler.name} failed")
    
    async def _force_shutdown(self):
        """Force shutdown when graceful shutdown fails."""
        self.logger.critical("Forcing shutdown due to errors")
        
        # Cancel all remaining tasks
        all_tasks = self.active_connections + self.background_tasks
        for task in all_tasks:
            if not task.done():
                task.cancel()
        
        # Wait briefly for cancellation
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)
    
    def is_healthy(self) -> bool:
        """Check if the application is healthy (not shutting down)."""
        return not self.is_shutting_down and self.health_check_enabled
    
    def get_shutdown_status(self) -> Dict[str, Any]:
        """Get current shutdown status."""
        return {
            "is_shutting_down": self.is_shutting_down,
            "current_phase": self.current_phase.value if self.current_phase else None,
            "health_check_enabled": self.health_check_enabled,
            "active_connections": len(self.active_connections),
            "background_tasks": len(self.background_tasks),
            "registered_handlers": len(self.shutdown_handlers),
            "metrics": {
                "handlers_executed": self.metrics.handlers_executed,
                "handlers_failed": self.metrics.handlers_failed,
                "handlers_timeout": self.metrics.handlers_timeout,
                "total_duration": self.metrics.total_duration
            }
        }


class ConnectionDrainer:
    """Manages connection draining during shutdown."""
    
    def __init__(self, shutdown_manager: GracefulShutdownManager):
        self.shutdown_manager = shutdown_manager
        self.logger = logging.getLogger(__name__)
    
    async def drain_http_connections(self, app):
        """Drain HTTP connections."""
        self.logger.info("Draining HTTP connections...")
        
        # This would typically involve:
        # 1. Stop accepting new connections
        # 2. Wait for existing requests to complete
        # 3. Close remaining connections
        
        # For FastAPI, we can track request tasks
        # This is a simplified implementation
        await asyncio.sleep(1)  # Give time for requests to complete
        self.logger.info("HTTP connections drained")
    
    async def drain_database_connections(self, database_pool):
        """Drain database connections."""
        self.logger.info("Draining database connections...")
        
        if hasattr(database_pool, 'close'):
            await database_pool.close()
        
        self.logger.info("Database connections drained")
    
    async def drain_cache_connections(self, cache_client):
        """Drain cache connections."""
        self.logger.info("Draining cache connections...")
        
        if hasattr(cache_client, 'close'):
            await cache_client.close()
        
        self.logger.info("Cache connections drained")


class ShutdownHealthCheck:
    """Health check that respects shutdown state."""
    
    def __init__(self, shutdown_manager: GracefulShutdownManager):
        self.shutdown_manager = shutdown_manager
        self.logger = logging.getLogger(__name__)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check considering shutdown state."""
        if not self.shutdown_manager.is_healthy():
            return {
                "status": "shutting_down",
                "phase": self.shutdown_manager.current_phase.value if self.shutdown_manager.current_phase else None,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def readiness_check(self) -> Dict[str, Any]:
        """Perform readiness check."""
        if self.shutdown_manager.is_shutting_down:
            return {
                "ready": False,
                "reason": "shutting_down",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global shutdown manager instance
graceful_shutdown_manager = GracefulShutdownManager()


def get_shutdown_manager() -> GracefulShutdownManager:
    """Get the global shutdown manager."""
    return graceful_shutdown_manager


# Convenience functions for common shutdown handlers
async def shutdown_database():
    """Default database shutdown handler."""
    logger.info("Shutting down database connections...")
    # This would close database connections
    await asyncio.sleep(0.1)  # Simulate cleanup
    logger.info("Database connections closed")


async def shutdown_cache():
    """Default cache shutdown handler."""
    logger.info("Shutting down cache connections...")
    # This would close cache connections
    await asyncio.sleep(0.1)  # Simulate cleanup
    logger.info("Cache connections closed")


async def shutdown_background_tasks():
    """Default background task shutdown handler."""
    logger.info("Shutting down background tasks...")
    # This would stop background tasks
    await asyncio.sleep(0.1)  # Simulate cleanup
    logger.info("Background tasks stopped")


def setup_default_shutdown_handlers():
    """Setup default shutdown handlers."""
    graceful_shutdown_manager.register_shutdown_handler(
        "database",
        shutdown_database,
        ShutdownPriority.CRITICAL,
        timeout=30,
        required=True
    )
    
    graceful_shutdown_manager.register_shutdown_handler(
        "cache",
        shutdown_cache,
        ShutdownPriority.HIGH,
        timeout=15,
        required=True
    )
    
    graceful_shutdown_manager.register_shutdown_handler(
        "background_tasks",
        shutdown_background_tasks,
        ShutdownPriority.HIGH,
        timeout=10,
        required=True
    )


# Initialize default shutdown handlers
setup_default_shutdown_handlers()
