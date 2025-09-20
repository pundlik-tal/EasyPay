"""
EasyPay Payment Gateway - Cached Webhook Repository

This module provides a cached version of the webhook repository that integrates
with Redis for improved performance and reduced database load.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repositories.webhook_repository import WebhookRepository
from src.core.models.webhook import Webhook, WebhookStatus, WebhookEventType
from src.core.exceptions import WebhookNotFoundError, DatabaseError, CacheError
from src.infrastructure.cache_strategies import get_enhanced_cache_manager, CacheStrategy


class CachedWebhookRepository(WebhookRepository):
    """
    Cached webhook repository with Redis integration.
    
    Provides the same interface as WebhookRepository but with Redis caching
    for improved performance and reduced database load.
    """
    
    def __init__(self, session: AsyncSession, cache_manager=None):
        super().__init__(session)
        self.cache_manager = cache_manager or get_enhanced_cache_manager()
        self.cache_strategy = CacheStrategy(self.cache_manager, ttl=300)
        
        # Cache configuration
        self.cache_ttl = 300  # 5 minutes default TTL
        self.webhook_cache_prefix = "webhook:"
        self.webhook_list_cache_prefix = "webhook_list:"
        self.webhook_stats_cache_prefix = "webhook_stats:"
        self.webhook_retry_cache_prefix = "webhook_retry:"
    
    def _get_webhook_cache_key(self, webhook_id: uuid.UUID) -> str:
        """Get cache key for a webhook."""
        return f"{self.webhook_cache_prefix}{str(webhook_id)}"
    
    def _get_external_id_cache_key(self, external_id: str) -> str:
        """Get cache key for external ID lookup."""
        return f"{self.webhook_cache_prefix}external:{external_id}"
    
    def _get_list_cache_key(
        self,
        event_type: Optional[WebhookEventType] = None,
        status: Optional[WebhookStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> str:
        """Get cache key for webhook list query."""
        key_parts = [
            self.webhook_list_cache_prefix,
            f"event_type:{event_type.value if event_type else 'all'}",
            f"status:{status.value if status else 'all'}",
            f"start:{start_date.isoformat() if start_date else 'none'}",
            f"end:{end_date.isoformat() if end_date else 'none'}",
            f"page:{page}",
            f"per_page:{per_page}",
            f"order:{order_by}:{order_direction}"
        ]
        return ":".join(key_parts)
    
    def _get_stats_cache_key(
        self,
        event_type: Optional[WebhookEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Get cache key for webhook statistics."""
        key_parts = [
            self.webhook_stats_cache_prefix,
            f"event_type:{event_type.value if event_type else 'all'}",
            f"start:{start_date.isoformat() if start_date else 'none'}",
            f"end:{end_date.isoformat() if end_date else 'none'}"
        ]
        return ":".join(key_parts)
    
    def _serialize_webhook(self, webhook: Webhook) -> Dict[str, Any]:
        """Serialize webhook for caching."""
        return {
            'id': str(webhook.id),
            'external_id': webhook.external_id,
            'event_type': webhook.event_type,
            'status': webhook.status,
            'url': webhook.url,
            'headers': webhook.headers,
            'payload': webhook.payload,
            'response_status': webhook.response_status,
            'response_body': webhook.response_body,
            'retry_count': webhook.retry_count,
            'max_retries': webhook.max_retries,
            'next_retry_at': webhook.next_retry_at.isoformat() if webhook.next_retry_at else None,
            'created_at': webhook.created_at.isoformat(),
            'updated_at': webhook.updated_at.isoformat(),
            'delivered_at': webhook.delivered_at.isoformat() if webhook.delivered_at else None,
            'failed_at': webhook.failed_at.isoformat() if webhook.failed_at else None,
            'is_test': webhook.is_test,
            'is_live': webhook.is_live
        }
    
    def _deserialize_webhook(self, data: Dict[str, Any]) -> Webhook:
        """Deserialize webhook from cache."""
        # Convert datetime strings back to datetime objects
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('delivered_at'):
            data['delivered_at'] = datetime.fromisoformat(data['delivered_at'])
        if data.get('failed_at'):
            data['failed_at'] = datetime.fromisoformat(data['failed_at'])
        if data.get('next_retry_at'):
            data['next_retry_at'] = datetime.fromisoformat(data['next_retry_at'])
        
        # Convert UUID string back to UUID
        if data.get('id'):
            data['id'] = uuid.UUID(data['id'])
        
        return Webhook(**data)
    
    async def create(self, webhook_data: Dict[str, Any]) -> Webhook:
        """
        Create a new webhook record with cache invalidation.
        
        Args:
            webhook_data: Dictionary containing webhook data
            
        Returns:
            Webhook: Created webhook instance
        """
        try:
            # Create webhook in database
            webhook = await super().create(webhook_data)
            
            # Cache the new webhook
            cache_key = self._get_webhook_cache_key(webhook.id)
            await self.cache_manager.set(
                cache_key,
                json.dumps(self._serialize_webhook(webhook)),
                expire=self.cache_ttl
            )
            
            # Cache external ID lookup
            external_id_key = self._get_external_id_cache_key(webhook.external_id)
            await self.cache_manager.set(
                external_id_key,
                str(webhook.id),
                expire=self.cache_ttl
            )
            
            # Invalidate list and stats caches
            await self._invalidate_list_caches()
            await self._invalidate_stats_caches()
            
            return webhook
            
        except Exception as e:
            raise DatabaseError(f"Failed to create cached webhook: {str(e)}")
    
    async def get_by_id(self, webhook_id: uuid.UUID) -> Optional[Webhook]:
        """
        Get webhook by ID with cache lookup.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            Webhook or None if not found
        """
        try:
            # Try cache first
            cache_key = self._get_webhook_cache_key(webhook_id)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                try:
                    webhook_data = json.loads(cached_data)
                    return self._deserialize_webhook(webhook_data)
                except (json.JSONDecodeError, ValueError) as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to deserialize cached webhook: {e}")
                    # Fall through to database lookup
            
            # Cache miss - get from database
            webhook = await super().get_by_id(webhook_id)
            
            if webhook:
                # Cache the result
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(self._serialize_webhook(webhook)),
                    expire=self.cache_ttl
                )
            
            return webhook
            
        except CacheError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().get_by_id(webhook_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached webhook by ID: {str(e)}")
    
    async def get_by_external_id(self, external_id: str) -> Optional[Webhook]:
        """
        Get webhook by external ID with cache lookup.
        
        Args:
            external_id: External webhook identifier
            
        Returns:
            Webhook or None if not found
        """
        try:
            # Try cache first
            external_id_key = self._get_external_id_cache_key(external_id)
            cached_id = await self.cache_manager.get(external_id_key)
            
            if cached_id:
                try:
                    webhook_id = uuid.UUID(cached_id)
                    return await self.get_by_id(webhook_id)
                except ValueError:
                    # Invalid UUID in cache
                    pass
            
            # Cache miss - get from database
            webhook = await super().get_by_external_id(external_id)
            
            if webhook:
                # Cache the external ID lookup
                await self.cache_manager.set(
                    external_id_key,
                    str(webhook.id),
                    expire=self.cache_ttl
                )
                
                # Cache the webhook itself
                cache_key = self._get_webhook_cache_key(webhook.id)
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(self._serialize_webhook(webhook)),
                    expire=self.cache_ttl
                )
            
            return webhook
            
        except CacheError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().get_by_external_id(external_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached webhook by external ID: {str(e)}")
    
    async def update(self, webhook_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[Webhook]:
        """
        Update webhook record with cache invalidation.
        
        Args:
            webhook_id: Webhook UUID
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated Webhook or None if not found
        """
        try:
            # Update in database
            webhook = await super().update(webhook_id, update_data)
            
            if webhook:
                # Update cache
                cache_key = self._get_webhook_cache_key(webhook.id)
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(self._serialize_webhook(webhook)),
                    expire=self.cache_ttl
                )
                
                # Invalidate list and stats caches
                await self._invalidate_list_caches()
                await self._invalidate_stats_caches()
            
            return webhook
            
        except Exception as e:
            raise DatabaseError(f"Failed to update cached webhook: {str(e)}")
    
    async def list_webhooks(
        self,
        event_type: Optional[WebhookEventType] = None,
        status: Optional[WebhookStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        List webhooks with caching.
        
        Args:
            event_type: Filter by event type
            status: Filter by webhook status
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number (1-based)
            per_page: Items per page
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            Dictionary containing webhooks list and pagination info
        """
        try:
            # Try cache first
            cache_key = self._get_list_cache_key(
                event_type, status, start_date, end_date,
                page, per_page, order_by, order_direction
            )
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    # Invalid cache data, fall through to database
                    pass
            
            # Cache miss - get from database
            result = await super().list_webhooks(
                event_type, status, start_date, end_date,
                page, per_page, order_by, order_direction
            )
            
            # Cache the result
            await self.cache_manager.set(
                cache_key,
                json.dumps(result, default=str),
                expire=self.cache_ttl
            )
            
            return result
            
        except CacheError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().list_webhooks(
                event_type, status, start_date, end_date,
                page, per_page, order_by, order_direction
            )
        except Exception as e:
            raise DatabaseError(f"Failed to list cached webhooks: {str(e)}")
    
    async def get_webhook_stats(
        self,
        event_type: Optional[WebhookEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get webhook statistics with caching.
        
        Args:
            event_type: Filter by event type
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Dictionary containing webhook statistics
        """
        try:
            # Try cache first
            cache_key = self._get_stats_cache_key(event_type, start_date, end_date)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    # Invalid cache data, fall through to database
                    pass
            
            # Cache miss - get from database
            result = await super().get_webhook_stats(event_type, start_date, end_date)
            
            # Cache the result
            await self.cache_manager.set(
                cache_key,
                json.dumps(result, default=str),
                expire=self.cache_ttl
            )
            
            return result
            
        except CacheError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().get_webhook_stats(event_type, start_date, end_date)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached webhook stats: {str(e)}")
    
    async def get_pending_retries(self, limit: int = 100) -> List[Webhook]:
        """
        Get webhooks pending retry with caching.
        
        Args:
            limit: Maximum number of webhooks to return
            
        Returns:
            List of webhooks pending retry
        """
        try:
            # Use cache strategy for this query
            cache_key = f"{self.webhook_retry_cache_prefix}pending:{limit}"
            
            result = await self.cache_strategy.get_or_set(
                cache_key,
                super().get_pending_retries,
                limit
            )
            
            return result
            
        except Exception as e:
            # Fallback to direct database query
            return await super().get_pending_retries(limit)
    
    async def _invalidate_list_caches(self):
        """Invalidate all list-related caches."""
        try:
            await self.cache_manager.invalidate_pattern(f"{self.webhook_list_cache_prefix}*")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to invalidate list caches: {e}")
    
    async def _invalidate_stats_caches(self):
        """Invalidate all stats-related caches."""
        try:
            await self.cache_manager.invalidate_pattern(f"{self.webhook_stats_cache_prefix}*")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to invalidate stats caches: {e}")
    
    async def invalidate_webhook_cache(self, webhook_id: uuid.UUID):
        """
        Invalidate cache for a specific webhook.
        
        Args:
            webhook_id: Webhook UUID to invalidate
        """
        try:
            cache_key = self._get_webhook_cache_key(webhook_id)
            await self.cache_manager.delete(cache_key)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to invalidate webhook cache: {e}")
    
    async def warm_cache(self, webhook_ids: List[uuid.UUID]):
        """
        Warm the cache with specific webhooks.
        
        Args:
            webhook_ids: List of webhook UUIDs to cache
        """
        try:
            for webhook_id in webhook_ids:
                webhook = await super().get_by_id(webhook_id)
                if webhook:
                    cache_key = self._get_webhook_cache_key(webhook_id)
                    await self.cache_manager.set(
                        cache_key,
                        json.dumps(self._serialize_webhook(webhook)),
                        expire=self.cache_ttl
                    )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to warm cache: {e}")
