"""
EasyPay Payment Gateway - Webhook Retry Service
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.webhook_service import WebhookService
from src.core.models.webhook import WebhookStatus
from src.core.exceptions import DatabaseError
from src.infrastructure.logging import get_logger
from src.infrastructure.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class WebhookRetryService:
    """
    Background service for retrying failed webhook deliveries.
    
    This service runs in the background to automatically retry
    failed webhook deliveries with exponential backoff.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize webhook retry service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.webhook_service = WebhookService(db, settings.webhook_secret)
        self.running = False
        self.retry_interval = 60  # seconds
        self.max_concurrent_retries = 10
    
    async def start(self) -> None:
        """
        Start the webhook retry service.
        """
        if self.running:
            logger.warning("Webhook retry service is already running")
            return
        
        self.running = True
        logger.info("Starting webhook retry service")
        
        try:
            while self.running:
                await self._process_retries()
                await asyncio.sleep(self.retry_interval)
        except Exception as e:
            logger.error(f"Webhook retry service error: {str(e)}")
        finally:
            self.running = False
            logger.info("Webhook retry service stopped")
    
    async def stop(self) -> None:
        """
        Stop the webhook retry service.
        """
        logger.info("Stopping webhook retry service")
        self.running = False
    
    async def _process_retries(self) -> None:
        """
        Process webhook retries.
        """
        try:
            # Get webhooks ready for retry
            webhook_repo = self.webhook_service.webhook_repo
            webhooks = await webhook_repo.get_webhooks_ready_for_retry()
            
            if not webhooks:
                logger.debug("No webhooks ready for retry")
                return
            
            logger.info(f"Processing {len(webhooks)} webhooks for retry")
            
            # Process webhooks in batches
            batch_size = min(len(webhooks), self.max_concurrent_retries)
            batches = [webhooks[i:i + batch_size] for i in range(0, len(webhooks), batch_size)]
            
            for batch in batches:
                await self._process_batch(batch)
                
        except Exception as e:
            logger.error(f"Failed to process webhook retries: {str(e)}")
    
    async def _process_batch(self, webhooks: List[Any]) -> None:
        """
        Process a batch of webhooks for retry.
        
        Args:
            webhooks: List of webhooks to process
        """
        try:
            # Create tasks for concurrent processing
            tasks = []
            for webhook in webhooks:
                task = asyncio.create_task(self._retry_webhook(webhook))
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log results
            successful = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
            failed = len(results) - successful
            
            logger.info(f"Batch processed: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"Failed to process webhook batch: {str(e)}")
    
    async def _retry_webhook(self, webhook: Any) -> Dict[str, Any]:
        """
        Retry a single webhook.
        
        Args:
            webhook: Webhook to retry
            
        Returns:
            Dictionary containing retry result
        """
        try:
            logger.info(f"Retrying webhook: {webhook.id}")
            
            # Attempt delivery
            delivery_result = await self.webhook_service.deliver_webhook(webhook.id)
            
            if delivery_result['success']:
                logger.info(f"Webhook retry successful: {webhook.id}")
                return {
                    'webhook_id': str(webhook.id),
                    'success': True,
                    'retry_count': webhook.retry_count + 1,
                    'delivery_result': delivery_result
                }
            else:
                logger.warning(f"Webhook retry failed: {webhook.id}")
                
                # Schedule next retry if possible
                if webhook.can_retry:
                    retry_delay = self._calculate_retry_delay(webhook.retry_count)
                    await self.webhook_service.webhook_repo.schedule_retry(
                        webhook.id, retry_delay
                    )
                    logger.info(f"Webhook scheduled for next retry: {webhook.id}")
                else:
                    logger.warning(f"Webhook exceeded max retries: {webhook.id}")
                
                return {
                    'webhook_id': str(webhook.id),
                    'success': False,
                    'retry_count': webhook.retry_count + 1,
                    'delivery_result': delivery_result,
                    'scheduled_next_retry': webhook.can_retry
                }
                
        except Exception as e:
            logger.error(f"Failed to retry webhook {webhook.id}: {str(e)}")
            return {
                'webhook_id': str(webhook.id),
                'success': False,
                'error': str(e)
            }
    
    def _calculate_retry_delay(self, retry_count: int) -> int:
        """
        Calculate retry delay using exponential backoff.
        
        Args:
            retry_count: Current retry count
            
        Returns:
            Retry delay in minutes
        """
        # Exponential backoff: 5, 10, 20, 40 minutes
        base_delay = 5
        max_delay = 60
        delay = min(base_delay * (2 ** retry_count), max_delay)
        return delay
    
    async def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get retry service statistics.
        
        Returns:
            Dictionary containing retry statistics
        """
        try:
            webhook_repo = self.webhook_service.webhook_repo
            
            # Get webhook statistics
            stats = await webhook_repo.get_webhook_stats()
            
            # Get failed webhooks count
            failed_webhooks = await webhook_repo.get_failed_webhooks()
            
            # Get webhooks ready for retry
            ready_for_retry = await webhook_repo.get_webhooks_ready_for_retry()
            
            return {
                'service_status': 'running' if self.running else 'stopped',
                'retry_interval_seconds': self.retry_interval,
                'max_concurrent_retries': self.max_concurrent_retries,
                'webhook_stats': stats,
                'failed_webhooks_count': len(failed_webhooks),
                'ready_for_retry_count': len(ready_for_retry),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get retry stats: {str(e)}")
            raise DatabaseError(f"Failed to get retry stats: {str(e)}")
    
    async def force_retry_all_failed(self) -> Dict[str, Any]:
        """
        Force retry all failed webhooks immediately.
        
        Returns:
            Dictionary containing retry results
        """
        try:
            logger.info("Force retrying all failed webhooks")
            
            # Get all failed webhooks
            webhook_repo = self.webhook_service.webhook_repo
            failed_webhooks = await webhook_repo.get_failed_webhooks()
            
            if not failed_webhooks:
                return {
                    'message': 'No failed webhooks to retry',
                    'total_webhooks': 0,
                    'successful_retries': 0,
                    'failed_retries': 0
                }
            
            logger.info(f"Force retrying {len(failed_webhooks)} failed webhooks")
            
            # Process all failed webhooks
            results = await self._process_batch(failed_webhooks)
            
            successful = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
            failed = len(results) - successful
            
            return {
                'message': 'Force retry completed',
                'total_webhooks': len(failed_webhooks),
                'successful_retries': successful,
                'failed_retries': failed,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to force retry webhooks: {str(e)}")
            raise DatabaseError(f"Failed to force retry webhooks: {str(e)}")
    
    async def cleanup_expired_webhooks(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up expired webhooks older than specified days.
        
        Args:
            days_old: Number of days old for cleanup
            
        Returns:
            Dictionary containing cleanup results
        """
        try:
            logger.info(f"Cleaning up webhooks older than {days_old} days")
            
            webhook_repo = self.webhook_service.webhook_repo
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Get expired webhooks
            expired_webhooks = await webhook_repo.list_webhooks(
                status=WebhookStatus.EXPIRED.value,
                end_date=cutoff_date,
                per_page=1000  # Get all expired webhooks
            )
            
            expired_count = len(expired_webhooks['webhooks'])
            
            if expired_count == 0:
                return {
                    'message': 'No expired webhooks to clean up',
                    'cleaned_count': 0
                }
            
            # Delete expired webhooks
            deleted_count = 0
            for webhook in expired_webhooks['webhooks']:
                try:
                    await webhook_repo.delete(webhook.id)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete webhook {webhook.id}: {str(e)}")
            
            logger.info(f"Cleaned up {deleted_count} expired webhooks")
            
            return {
                'message': 'Webhook cleanup completed',
                'expired_count': expired_count,
                'cleaned_count': deleted_count,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired webhooks: {str(e)}")
            raise DatabaseError(f"Failed to cleanup expired webhooks: {str(e)}")
