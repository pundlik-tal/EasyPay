"""
EasyPay Payment Gateway - Dead Letter Queue Service

This module provides dead letter queue functionality for handling failed requests
and messages that cannot be processed immediately.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from src.core.exceptions import EasyPayException

logger = logging.getLogger(__name__)


class MessageStatus(str, Enum):
    """Message status in dead letter queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class DeadLetterMessage:
    """Dead letter queue message."""
    id: str
    original_data: Dict[str, Any]
    error_info: Dict[str, Any]
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 5
    status: MessageStatus = MessageStatus.PENDING
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.next_retry_at is None:
            self.next_retry_at = self.created_at + timedelta(minutes=5)


class DeadLetterQueueService:
    """Service for managing dead letter queue operations."""
    
    def __init__(self, max_queue_size: int = 1000, retry_delay_minutes: int = 5):
        self.max_queue_size = max_queue_size
        self.retry_delay_minutes = retry_delay_minutes
        self.messages: Dict[str, DeadLetterMessage] = {}
        self.processing_workers: List[asyncio.Task] = []
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            "total_messages": 0,
            "processed_messages": 0,
            "failed_messages": 0,
            "expired_messages": 0,
            "current_queue_size": 0
        }
    
    async def add_message(
        self,
        original_data: Dict[str, Any],
        error_info: Dict[str, Any],
        max_retries: int = 5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a message to the dead letter queue."""
        message_id = str(uuid.uuid4())
        
        # Check queue size limit
        if len(self.messages) >= self.max_queue_size:
            await self._cleanup_expired_messages()
            
            if len(self.messages) >= self.max_queue_size:
                # Remove oldest message
                oldest_id = min(self.messages.keys(), key=lambda k: self.messages[k].created_at)
                del self.messages[oldest_id]
                self.stats["expired_messages"] += 1
        
        message = DeadLetterMessage(
            id=message_id,
            original_data=original_data,
            error_info=error_info,
            created_at=datetime.utcnow(),
            max_retries=max_retries,
            metadata=metadata or {}
        )
        
        self.messages[message_id] = message
        self.stats["total_messages"] += 1
        self.stats["current_queue_size"] = len(self.messages)
        
        self.logger.info(f"Added message {message_id} to dead letter queue")
        return message_id
    
    async def get_message(self, message_id: str) -> Optional[DeadLetterMessage]:
        """Get a specific message by ID."""
        return self.messages.get(message_id)
    
    async def get_pending_messages(self, limit: int = 100) -> List[DeadLetterMessage]:
        """Get pending messages ready for retry."""
        current_time = datetime.utcnow()
        pending_messages = []
        
        for message in self.messages.values():
            if (message.status == MessageStatus.PENDING and
                message.next_retry_at <= current_time and
                message.retry_count < message.max_retries):
                pending_messages.append(message)
        
        # Sort by retry time and limit results
        pending_messages.sort(key=lambda m: m.next_retry_at)
        return pending_messages[:limit]
    
    async def retry_message(
        self,
        message_id: str,
        retry_handler: Callable[[Dict[str, Any]], Any]
    ) -> bool:
        """Retry processing a specific message."""
        message = self.messages.get(message_id)
        if not message:
            return False
        
        if message.status != MessageStatus.PENDING:
            return False
        
        message.status = MessageStatus.PROCESSING
        message.retry_count += 1
        
        try:
            self.logger.info(f"Retrying message {message_id} (attempt {message.retry_count})")
            
            # Call the retry handler
            result = await retry_handler(message.original_data)
            
            # Mark as completed
            message.status = MessageStatus.COMPLETED
            self.stats["processed_messages"] += 1
            
            # Remove from queue after successful processing
            del self.messages[message_id]
            self.stats["current_queue_size"] = len(self.messages)
            
            self.logger.info(f"Successfully processed message {message_id}")
            return True
            
        except Exception as e:
            # Handle retry failure
            message.status = MessageStatus.FAILED
            message.last_error = str(e)
            
            if message.retry_count >= message.max_retries:
                # Max retries exceeded, mark as failed permanently
                self.stats["failed_messages"] += 1
                self.logger.error(f"Message {message_id} failed after {message.max_retries} retries")
            else:
                # Schedule next retry
                message.status = MessageStatus.PENDING
                delay_minutes = self.retry_delay_minutes * (2 ** message.retry_count)  # Exponential backoff
                message.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
                self.logger.warning(f"Message {message_id} retry failed, next retry in {delay_minutes} minutes")
            
            return False
    
    async def delete_message(self, message_id: str) -> bool:
        """Delete a message from the queue."""
        if message_id in self.messages:
            del self.messages[message_id]
            self.stats["current_queue_size"] = len(self.messages)
            self.logger.info(f"Deleted message {message_id} from dead letter queue")
            return True
        return False
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get queue statistics."""
        status_counts = {}
        for message in self.messages.values():
            status_counts[message.status.value] = status_counts.get(message.status.value, 0) + 1
        
        return {
            **self.stats,
            "status_breakdown": status_counts,
            "oldest_message_age": self._get_oldest_message_age(),
            "average_retry_count": self._get_average_retry_count()
        }
    
    def _get_oldest_message_age(self) -> Optional[int]:
        """Get age of oldest message in minutes."""
        if not self.messages:
            return None
        
        oldest_message = min(self.messages.values(), key=lambda m: m.created_at)
        age = datetime.utcnow() - oldest_message.created_at
        return int(age.total_seconds() / 60)
    
    def _get_average_retry_count(self) -> float:
        """Get average retry count for all messages."""
        if not self.messages:
            return 0.0
        
        total_retries = sum(message.retry_count for message in self.messages.values())
        return total_retries / len(self.messages)
    
    async def _cleanup_expired_messages(self):
        """Clean up expired messages."""
        current_time = datetime.utcnow()
        expired_threshold = current_time - timedelta(hours=24)  # Messages older than 24 hours
        
        expired_messages = [
            message_id for message_id, message in self.messages.items()
            if message.created_at < expired_threshold
        ]
        
        for message_id in expired_messages:
            del self.messages[message_id]
            self.stats["expired_messages"] += 1
        
        if expired_messages:
            self.stats["current_queue_size"] = len(self.messages)
            self.logger.info(f"Cleaned up {len(expired_messages)} expired messages")
    
    async def start_processing_workers(self, num_workers: int = 3):
        """Start background workers to process dead letter queue."""
        if self.is_running:
            return
        
        self.is_running = True
        self.logger.info(f"Starting {num_workers} dead letter queue workers")
        
        for i in range(num_workers):
            worker = asyncio.create_task(self._processing_worker(f"worker-{i}"))
            self.processing_workers.append(worker)
    
    async def stop_processing_workers(self):
        """Stop background workers."""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Stopping dead letter queue workers")
        
        # Cancel all workers
        for worker in self.processing_workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.processing_workers, return_exceptions=True)
        self.processing_workers.clear()
    
    async def _processing_worker(self, worker_name: str):
        """Background worker for processing dead letter queue messages."""
        self.logger.info(f"Dead letter queue worker {worker_name} started")
        
        while self.is_running:
            try:
                # Get pending messages
                pending_messages = await self.get_pending_messages(limit=10)
                
                if not pending_messages:
                    # No messages to process, wait a bit
                    await asyncio.sleep(30)
                    continue
                
                # Process messages
                for message in pending_messages:
                    if not self.is_running:
                        break
                    
                    try:
                        # Here you would implement the actual retry logic
                        # For now, we'll just simulate processing
                        await self._simulate_message_processing(message)
                        
                    except Exception as e:
                        self.logger.error(f"Worker {worker_name} failed to process message {message.id}: {e}")
                
                # Small delay between processing cycles
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(10)
        
        self.logger.info(f"Dead letter queue worker {worker_name} stopped")
    
    async def _simulate_message_processing(self, message: DeadLetterMessage):
        """Simulate message processing (replace with actual retry logic)."""
        # This is a placeholder - in real implementation, you would:
        # 1. Extract the original request/operation from message.original_data
        # 2. Retry the original operation
        # 3. Handle success/failure appropriately
        
        self.logger.info(f"Simulating processing of message {message.id}")
        
        # Simulate processing delay
        await asyncio.sleep(1)
        
        # For demo purposes, we'll mark it as completed
        message.status = MessageStatus.COMPLETED
        del self.messages[message.id]
        self.stats["processed_messages"] += 1
        self.stats["current_queue_size"] = len(self.messages)


class DeadLetterQueueAPI:
    """API endpoints for dead letter queue management."""
    
    def __init__(self, dlq_service: DeadLetterQueueService):
        self.dlq_service = dlq_service
        self.logger = logging.getLogger(__name__)
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get dead letter queue status."""
        return await self.dlq_service.get_queue_statistics()
    
    async def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message."""
        message = await self.dlq_service.get_message(message_id)
        if message:
            return asdict(message)
        return None
    
    async def retry_message(self, message_id: str) -> Dict[str, Any]:
        """Retry a specific message."""
        success = await self.dlq_service.retry_message(
            message_id,
            self._default_retry_handler
        )
        
        return {
            "message_id": message_id,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def delete_message(self, message_id: str) -> Dict[str, Any]:
        """Delete a message from the queue."""
        success = await self.dlq_service.delete_message(message_id)
        
        return {
            "message_id": message_id,
            "deleted": success,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def cleanup_expired(self) -> Dict[str, Any]:
        """Clean up expired messages."""
        initial_count = len(self.dlq_service.messages)
        await self.dlq_service._cleanup_expired_messages()
        final_count = len(self.dlq_service.messages)
        
        return {
            "messages_removed": initial_count - final_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _default_retry_handler(self, original_data: Dict[str, Any]) -> Any:
        """Default retry handler (placeholder)."""
        # This would contain the actual retry logic
        # For now, we'll just log the attempt
        self.logger.info(f"Retrying operation with data: {original_data}")
        return {"status": "retried"}


# Global dead letter queue service instance
dead_letter_queue_service = DeadLetterQueueService()
