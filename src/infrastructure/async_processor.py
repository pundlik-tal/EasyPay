"""
EasyPay Payment Gateway - Async Background Task Processor

This module provides async background task processing with queue management,
retry logic, and monitoring capabilities.
"""

import asyncio
import time
import uuid
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

from src.infrastructure.cache_strategies import get_enhanced_cache_manager
from src.core.exceptions import DatabaseError


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Background task definition."""
    id: str
    name: str
    func: str  # Function name to execute
    args: List[Any]
    kwargs: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    retry_delay: int = 60  # seconds
    timeout: int = 300  # seconds
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    result: Optional[Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class TaskQueue:
    """In-memory task queue with priority support."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.queues = {
            TaskPriority.CRITICAL: asyncio.Queue(),
            TaskPriority.HIGH: asyncio.Queue(),
            TaskPriority.NORMAL: asyncio.Queue(),
            TaskPriority.LOW: asyncio.Queue()
        }
        self.task_registry: Dict[str, Task] = {}
        self.logger = logging.getLogger(__name__)
    
    async def enqueue(self, task: Task) -> bool:
        """Add task to appropriate priority queue."""
        
        if len(self.task_registry) >= self.max_size:
            self.logger.warning(f"Task queue is full, rejecting task {task.id}")
            return False
        
        # Store task in registry
        self.task_registry[task.id] = task
        
        # Add to appropriate priority queue
        queue = self.queues[task.priority]
        await queue.put(task)
        
        self.logger.info(f"Enqueued task {task.id} with priority {task.priority.name}")
        return True
    
    async def dequeue(self) -> Optional[Task]:
        """Get next task from highest priority queue."""
        
        # Check queues in priority order
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]:
            queue = self.queues[priority]
            if not queue.empty():
                try:
                    task = queue.get_nowait()
                    return task
                except asyncio.QueueEmpty:
                    continue
        
        return None
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.task_registry.get(task_id)
    
    def update_task(self, task: Task):
        """Update task in registry."""
        self.task_registry[task.id] = task
    
    def remove_task(self, task_id: str):
        """Remove task from registry."""
        if task_id in self.task_registry:
            del self.task_registry[task_id]
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        stats = {}
        for priority, queue in self.queues.items():
            stats[priority.name] = queue.qsize()
        stats["total_tasks"] = len(self.task_registry)
        return stats


class TaskExecutor(ABC):
    """Abstract base class for task executors."""
    
    @abstractmethod
    async def execute(self, task: Task) -> Any:
        """Execute a task and return result."""
        pass


class FunctionTaskExecutor(TaskExecutor):
    """Task executor that executes functions by name."""
    
    def __init__(self, function_registry: Dict[str, Callable]):
        self.function_registry = function_registry
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, task: Task) -> Any:
        """Execute task function."""
        
        if task.func not in self.function_registry:
            raise ValueError(f"Function '{task.func}' not found in registry")
        
        func = self.function_registry[task.func]
        
        # Execute function
        if asyncio.iscoroutinefunction(func):
            return await func(*task.args, **task.kwargs)
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *task.args, **task.kwargs)


class AsyncTaskProcessor:
    """Main async task processor."""
    
    def __init__(
        self,
        executor: TaskExecutor,
        max_workers: int = 5,
        cache_manager=None
    ):
        self.executor = executor
        self.max_workers = max_workers
        self.cache_manager = cache_manager or get_enhanced_cache_manager()
        self.queue = TaskQueue()
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Metrics
        self.metrics = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
            "total_processing_time": 0.0
        }
    
    async def start(self):
        """Start the task processor."""
        
        if self.is_running:
            self.logger.warning("Task processor is already running")
            return
        
        self.is_running = True
        self.logger.info(f"Starting async task processor with {self.max_workers} workers")
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        
        self.logger.info("Async task processor started")
    
    async def stop(self):
        """Stop the task processor."""
        
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Stopping async task processor")
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        self.logger.info("Async task processor stopped")
    
    async def _worker(self, worker_name: str):
        """Worker coroutine that processes tasks."""
        
        self.logger.info(f"Worker {worker_name} started")
        
        while self.is_running:
            try:
                # Get next task
                task = await self.queue.dequeue()
                if task is None:
                    await asyncio.sleep(0.1)  # Short sleep if no tasks
                    continue
                
                # Process task
                await self._process_task(task, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)  # Sleep on error
        
        self.logger.info(f"Worker {worker_name} stopped")
    
    async def _process_task(self, task: Task, worker_name: str):
        """Process a single task."""
        
        start_time = time.time()
        
        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self.queue.update_task(task)
            
            self.logger.info(f"Worker {worker_name} processing task {task.id}")
            
            # Execute task with timeout
            result = await asyncio.wait_for(
                self.executor.execute(task),
                timeout=task.timeout
            )
            
            # Task completed successfully
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            self.queue.update_task(task)
            
            # Update metrics
            processing_time = time.time() - start_time
            self.metrics["tasks_processed"] += 1
            self.metrics["total_processing_time"] += processing_time
            
            self.logger.info(f"Task {task.id} completed in {processing_time:.3f}s")
            
        except asyncio.TimeoutError:
            await self._handle_task_failure(task, "Task timeout", worker_name)
            
        except Exception as e:
            await self._handle_task_failure(task, str(e), worker_name)
    
    async def _handle_task_failure(self, task: Task, error_message: str, worker_name: str):
        """Handle task failure with retry logic."""
        
        task.retry_count += 1
        task.error_message = error_message
        
        if task.retry_count <= task.max_retries:
            # Retry task
            task.status = TaskStatus.RETRYING
            self.queue.update_task(task)
            
            self.logger.warning(
                f"Task {task.id} failed (attempt {task.retry_count}/{task.max_retries}): {error_message}"
            )
            
            # Schedule retry
            await asyncio.sleep(task.retry_delay)
            await self.queue.enqueue(task)
            
            self.metrics["tasks_retried"] += 1
            
        else:
            # Task failed permanently
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            self.queue.update_task(task)
            
            self.logger.error(f"Task {task.id} failed permanently: {error_message}")
            self.metrics["tasks_failed"] += 1
    
    async def submit_task(
        self,
        name: str,
        func: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        retry_delay: int = 60,
        timeout: int = 300
    ) -> str:
        """Submit a new task for processing."""
        
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            name=name,
            func=func,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout
        )
        
        success = await self.queue.enqueue(task)
        if not success:
            raise RuntimeError("Failed to enqueue task - queue is full")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status and details."""
        
        task = self.queue.get_task(task_id)
        if task is None:
            return None
        
        return asdict(task)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get processor metrics."""
        
        queue_stats = self.queue.get_queue_stats()
        
        return {
            **self.metrics,
            "queue_stats": queue_stats,
            "is_running": self.is_running,
            "active_workers": len(self.workers),
            "average_processing_time": (
                self.metrics["total_processing_time"] / max(self.metrics["tasks_processed"], 1)
            )
        }


class BackgroundTaskManager:
    """Manager for background tasks with persistence."""
    
    def __init__(self, processor: AsyncTaskProcessor):
        self.processor = processor
        self.cache_manager = get_enhanced_cache_manager()
        self.logger = logging.getLogger(__name__)
        
        # Task function registry
        self.function_registry: Dict[str, Callable] = {}
    
    def register_function(self, name: str, func: Callable):
        """Register a function for background execution."""
        self.function_registry[name] = func
        self.logger.info(f"Registered function: {name}")
    
    async def start_background_task(
        self,
        name: str,
        func: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        delay: int = 0
    ) -> str:
        """Start a background task."""
        
        if delay > 0:
            # Schedule delayed task
            await asyncio.sleep(delay)
        
        return await self.processor.submit_task(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority
        )
    
    async def schedule_recurring_task(
        self,
        name: str,
        func: str,
        interval: int,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Schedule a recurring task."""
        
        # Create recurring task function
        async def recurring_wrapper():
            while True:
                try:
                    await self.start_background_task(
                        name=f"{name}_recurring",
                        func=func,
                        args=args,
                        kwargs=kwargs,
                        priority=priority
                    )
                except Exception as e:
                    self.logger.error(f"Recurring task {name} error: {e}")
                
                await asyncio.sleep(interval)
        
        # Start recurring task
        task_id = str(uuid.uuid4())
        asyncio.create_task(recurring_wrapper())
        
        self.logger.info(f"Scheduled recurring task {name} with interval {interval}s")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return self.processor.get_task_status(task_id)
    
    def get_processor_metrics(self) -> Dict[str, Any]:
        """Get processor metrics."""
        return self.processor.get_metrics()


# Global task processor instance
_task_processor: Optional[AsyncTaskProcessor] = None
_task_manager: Optional[BackgroundTaskManager] = None


def get_task_processor() -> AsyncTaskProcessor:
    """Get the global task processor."""
    global _task_processor
    
    if _task_processor is None:
        executor = FunctionTaskExecutor({})
        _task_processor = AsyncTaskProcessor(executor)
    
    return _task_processor


def get_task_manager() -> BackgroundTaskManager:
    """Get the global task manager."""
    global _task_manager
    
    if _task_manager is None:
        processor = get_task_processor()
        _task_manager = BackgroundTaskManager(processor)
    
    return _task_manager


async def init_async_processing() -> BackgroundTaskManager:
    """Initialize async processing system."""
    global _task_processor, _task_manager
    
    # Create processor with function registry
    executor = FunctionTaskExecutor({})
    _task_processor = AsyncTaskProcessor(executor)
    
    # Create task manager
    _task_manager = BackgroundTaskManager(_task_processor)
    
    # Start processor
    await _task_processor.start()
    
    logging.getLogger(__name__).info("Async processing system initialized")
    
    return _task_manager


async def close_async_processing():
    """Close async processing system."""
    global _task_processor
    
    if _task_processor:
        await _task_processor.stop()
        _task_processor = None
        
        logging.getLogger(__name__).info("Async processing system closed")
