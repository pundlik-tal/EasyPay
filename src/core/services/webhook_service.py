"""
EasyPay Payment Gateway - Webhook Service
"""
import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.webhook import Webhook, WebhookStatus, WebhookEventType
from src.core.repositories.webhook_repository import WebhookRepository
from src.core.services.request_signing_service import WebhookSigningService
from src.core.exceptions import (
    ValidationError,
    DatabaseError,
    WebhookNotFoundError,
    WebhookError
)
import logging

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Webhook service for managing webhook endpoints and delivery.
    
    This service handles webhook registration, delivery, retry logic,
    and signature verification for secure webhook communication.
    """
    
    def __init__(self, db: AsyncSession, webhook_secret: str):
        """
        Initialize webhook service.
        
        Args:
            db: Database session
            webhook_secret: Secret key for webhook signing
        """
        self.db = db
        self.webhook_repo = WebhookRepository(db)
        self.signing_service = WebhookSigningService(webhook_secret)
    
    async def register_webhook_endpoint(
        self,
        url: str,
        event_types: List[str],
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        is_test: bool = False,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Register a new webhook endpoint.
        
        Args:
            url: Webhook endpoint URL
            event_types: List of event types to subscribe to
            description: Webhook description
            metadata: Additional metadata
            is_test: Test mode flag
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary containing webhook registration details
            
        Raises:
            ValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                raise ValidationError("Webhook URL must start with http:// or https://")
            
            # Validate event types
            valid_events = [event.value for event in WebhookEventType]
            for event_type in event_types:
                if event_type not in valid_events:
                    raise ValidationError(f"Invalid event type: {event_type}")
            
            # Create webhook endpoint record
            webhook_data = {
                'url': url,
                'event_types': event_types,
                'description': description,
                'metadata': metadata or {},
                'is_test': is_test,
                'max_retries': max_retries,
                'status': 'active',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Store webhook endpoint (we'll create a separate table for this later)
            # For now, we'll use the existing webhook table with a special event_type
            webhook_data['event_type'] = 'webhook.endpoint.registered'
            webhook_data['event_id'] = f"endpoint_{uuid.uuid4().hex[:8]}"
            webhook_data['payload'] = webhook_data.copy()
            
            webhook = await self.webhook_repo.create(webhook_data)
            
            logger.info(f"Webhook endpoint registered: {url} for events: {event_types}")
            
            return {
                'id': str(webhook.id),
                'url': url,
                'event_types': event_types,
                'description': description,
                'metadata': metadata,
                'is_test': is_test,
                'max_retries': max_retries,
                'status': 'active',
                'created_at': webhook.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to register webhook endpoint: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Failed to register webhook endpoint: {str(e)}")
    
    async def create_webhook_event(
        self,
        event_type: str,
        event_id: str,
        payment_id: Optional[uuid.UUID] = None,
        data: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        is_test: bool = False
    ) -> Webhook:
        """
        Create a new webhook event for delivery.
        
        Args:
            event_type: Type of webhook event
            event_id: Unique event identifier
            payment_id: Related payment ID
            data: Event data payload
            url: Webhook endpoint URL (if not provided, will be determined by event type)
            headers: Additional headers for webhook delivery
            is_test: Test mode flag
            
        Returns:
            Created webhook instance
            
        Raises:
            ValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        try:
            # Validate event type
            valid_events = [event.value for event in WebhookEventType]
            if event_type not in valid_events:
                raise ValidationError(f"Invalid event type: {event_type}")
            
            # Prepare webhook data
            webhook_data = {
                'event_type': event_type,
                'event_id': event_id,
                'payment_id': payment_id,
                'url': url or self._get_default_webhook_url(event_type),
                'headers': headers or {},
                'payload': data or {},
                'status': WebhookStatus.PENDING.value,
                'retry_count': 0,
                'max_retries': 3,
                'is_test': is_test,
                'signature_verified': False,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Generate webhook signature
            payload_json = json.dumps(webhook_data['payload'], sort_keys=True)
            signature = self.signing_service.generate_webhook_signature(payload_json)
            webhook_data['headers']['X-Webhook-Signature'] = signature
            
            # Create webhook record
            webhook = await self.webhook_repo.create(webhook_data)
            
            logger.info(f"Webhook event created: {event_type} - {event_id}")
            
            return webhook
            
        except Exception as e:
            logger.error(f"Failed to create webhook event: {str(e)}")
            if isinstance(e, (ValidationError, DatabaseError)):
                raise
            raise DatabaseError(f"Failed to create webhook event: {str(e)}")
    
    async def deliver_webhook(self, webhook_id: uuid.UUID) -> Dict[str, Any]:
        """
        Deliver a webhook to its endpoint.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            Dictionary containing delivery result
            
        Raises:
            WebhookNotFoundError: If webhook not found
            WebhookError: If delivery fails
            DatabaseError: If database operation fails
        """
        try:
            # Get webhook
            webhook = await self.webhook_repo.get_by_id(webhook_id)
            if not webhook:
                raise WebhookNotFoundError(f"Webhook not found: {webhook_id}")
            
            # Check if webhook can be delivered
            if webhook.status not in [WebhookStatus.PENDING.value, WebhookStatus.RETRYING.value]:
                raise WebhookError(f"Webhook cannot be delivered in status: {webhook.status}")
            
            # Prepare delivery data
            payload_json = json.dumps(webhook.payload, sort_keys=True)
            headers = webhook.headers.copy()
            
            # Add standard webhook headers
            headers.update({
                'Content-Type': 'application/json',
                'User-Agent': 'EasyPay-Webhook/1.0',
                'X-Webhook-Event': webhook.event_type,
                'X-Webhook-Event-ID': webhook.event_id,
                'X-Webhook-Timestamp': str(int(datetime.utcnow().timestamp()))
            })
            
            # Deliver webhook (simulate HTTP request for now)
            delivery_result = await self._deliver_http_webhook(
                webhook.url,
                payload_json,
                headers
            )
            
            # Update webhook status based on delivery result
            if delivery_result['success']:
                await self.webhook_repo.mark_as_delivered(
                    webhook_id,
                    delivery_result['status_code'],
                    delivery_result['response_body'],
                    delivery_result['response_headers']
                )
                logger.info(f"Webhook delivered successfully: {webhook_id}")
            else:
                await self.webhook_repo.mark_as_failed(
                    webhook_id,
                    delivery_result.get('status_code'),
                    delivery_result.get('response_body')
                )
                logger.warning(f"Webhook delivery failed: {webhook_id}")
            
            return delivery_result
            
        except Exception as e:
            logger.error(f"Failed to deliver webhook {webhook_id}: {str(e)}")
            if isinstance(e, (WebhookNotFoundError, WebhookError)):
                raise
            raise WebhookError(f"Failed to deliver webhook: {str(e)}")
    
    async def retry_failed_webhooks(self) -> Dict[str, Any]:
        """
        Retry all failed webhooks that are ready for retry.
        
        Returns:
            Dictionary containing retry results
        """
        try:
            # Get webhooks ready for retry
            webhooks = await self.webhook_repo.get_webhooks_ready_for_retry()
            
            results = {
                'total_webhooks': len(webhooks),
                'successful_deliveries': 0,
                'failed_deliveries': 0,
                'errors': []
            }
            
            for webhook in webhooks:
                try:
                    delivery_result = await self.deliver_webhook(webhook.id)
                    if delivery_result['success']:
                        results['successful_deliveries'] += 1
                    else:
                        results['failed_deliveries'] += 1
                        
                        # Schedule next retry if possible
                        if webhook.can_retry:
                            retry_delay = self._calculate_retry_delay(webhook.retry_count)
                            await self.webhook_repo.schedule_retry(webhook.id, retry_delay)
                        else:
                            logger.warning(f"Webhook {webhook.id} exceeded max retries")
                            
                except Exception as e:
                    results['failed_deliveries'] += 1
                    results['errors'].append(f"Webhook {webhook.id}: {str(e)}")
                    logger.error(f"Failed to retry webhook {webhook.id}: {str(e)}")
            
            logger.info(f"Webhook retry completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to retry webhooks: {str(e)}")
            raise DatabaseError(f"Failed to retry webhooks: {str(e)}")
    
    async def verify_webhook_signature(
        self,
        payload: str,
        signature_header: str,
        max_age: int = 300
    ) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Webhook payload
            signature_header: Signature header value
            max_age: Maximum age of webhook in seconds
            
        Returns:
            True if signature is valid
            
        Raises:
            ValidationError: If signature verification fails
        """
        try:
            return self.signing_service.verify_webhook_signature(
                payload, signature_header, max_age
            )
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            raise ValidationError(f"Webhook signature verification failed: {str(e)}")
    
    async def get_webhook_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get webhook statistics.
        
        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Dictionary containing webhook statistics
        """
        try:
            return await self.webhook_repo.get_webhook_stats(start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to get webhook stats: {str(e)}")
            raise DatabaseError(f"Failed to get webhook stats: {str(e)}")
    
    async def list_webhooks(
        self,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        payment_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        List webhooks with filtering and pagination.
        
        Args:
            event_type: Filter by event type
            status: Filter by webhook status
            payment_id: Filter by payment ID
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number
            per_page: Items per page
            
        Returns:
            Dictionary containing webhooks list and pagination info
        """
        try:
            # Convert string enums to enum objects
            event_type_enum = None
            if event_type:
                try:
                    event_type_enum = WebhookEventType(event_type)
                except ValueError:
                    raise ValidationError(f"Invalid event type: {event_type}")
            
            status_enum = None
            if status:
                try:
                    status_enum = WebhookStatus(status)
                except ValueError:
                    raise ValidationError(f"Invalid status: {status}")
            
            return await self.webhook_repo.list_webhooks(
                event_type=event_type_enum,
                status=status_enum,
                payment_id=payment_id,
                start_date=start_date,
                end_date=end_date,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            logger.error(f"Failed to list webhooks: {str(e)}")
            if isinstance(e, ValidationError):
                raise
            raise DatabaseError(f"Failed to list webhooks: {str(e)}")
    
    def _get_default_webhook_url(self, event_type: str) -> str:
        """
        Get default webhook URL for event type.
        
        Args:
            event_type: Event type
            
        Returns:
            Default webhook URL
        """
        # This would typically be configured per customer/tenant
        # For now, return a placeholder URL
        return f"https://webhook.site/{event_type}"
    
    async def _deliver_http_webhook(
        self,
        url: str,
        payload: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Deliver webhook via HTTP request.
        
        Args:
            url: Webhook URL
            payload: Webhook payload
            headers: Request headers
            
        Returns:
            Dictionary containing delivery result
        """
        try:
            # For now, simulate webhook delivery
            # In production, this would use httpx or aiohttp
            import random
            
            # Simulate delivery success/failure
            success = random.random() > 0.1  # 90% success rate for testing
            
            if success:
                return {
                    'success': True,
                    'status_code': 200,
                    'response_body': '{"status": "success"}',
                    'response_headers': {'Content-Type': 'application/json'},
                    'delivery_time': datetime.utcnow().isoformat()
                }
            else:
                return {
                    'success': False,
                    'status_code': 500,
                    'response_body': '{"error": "Internal server error"}',
                    'response_headers': {'Content-Type': 'application/json'},
                    'delivery_time': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"HTTP webhook delivery failed: {str(e)}")
            return {
                'success': False,
                'status_code': None,
                'response_body': str(e),
                'response_headers': {},
                'delivery_time': datetime.utcnow().isoformat()
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
