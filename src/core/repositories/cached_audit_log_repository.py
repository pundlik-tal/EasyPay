"""
EasyPay Payment Gateway - Cached Audit Log Repository

This module provides a cached version of the audit log repository that integrates
with Redis for improved performance and reduced database load.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repositories.audit_log_repository import AuditLogRepository
from src.core.models.audit_log import AuditLog, AuditLogAction, AuditLogResource
from src.core.exceptions import AuditLogNotFoundError, DatabaseError, CacheError
from src.infrastructure.cache_strategies import get_enhanced_cache_manager, CacheStrategy


class CachedAuditLogRepository(AuditLogRepository):
    """
    Cached audit log repository with Redis integration.
    
    Provides the same interface as AuditLogRepository but with Redis caching
    for improved performance and reduced database load.
    """
    
    def __init__(self, session: AsyncSession, cache_manager=None):
        super().__init__(session)
        self.cache_manager = cache_manager or get_enhanced_cache_manager()
        self.cache_strategy = CacheStrategy(self.cache_manager, ttl=600)  # 10 minutes for audit logs
        
        # Cache configuration
        self.cache_ttl = 600  # 10 minutes default TTL for audit logs
        self.audit_log_cache_prefix = "audit_log:"
        self.audit_log_list_cache_prefix = "audit_log_list:"
        self.audit_log_stats_cache_prefix = "audit_log_stats:"
        self.audit_log_user_cache_prefix = "audit_log_user:"
    
    def _get_audit_log_cache_key(self, audit_log_id: uuid.UUID) -> str:
        """Get cache key for an audit log."""
        return f"{self.audit_log_cache_prefix}{str(audit_log_id)}"
    
    def _get_list_cache_key(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditLogAction] = None,
        resource: Optional[AuditLogResource] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> str:
        """Get cache key for audit log list query."""
        key_parts = [
            self.audit_log_list_cache_prefix,
            f"user:{user_id or 'all'}",
            f"action:{action.value if action else 'all'}",
            f"resource:{resource.value if resource else 'all'}",
            f"resource_id:{resource_id or 'all'}",
            f"start:{start_date.isoformat() if start_date else 'none'}",
            f"end:{end_date.isoformat() if end_date else 'none'}",
            f"page:{page}",
            f"per_page:{per_page}",
            f"order:{order_by}:{order_direction}"
        ]
        return ":".join(key_parts)
    
    def _get_stats_cache_key(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditLogAction] = None,
        resource: Optional[AuditLogResource] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Get cache key for audit log statistics."""
        key_parts = [
            self.audit_log_stats_cache_prefix,
            f"user:{user_id or 'all'}",
            f"action:{action.value if action else 'all'}",
            f"resource:{resource.value if resource else 'all'}",
            f"start:{start_date.isoformat() if start_date else 'none'}",
            f"end:{end_date.isoformat() if end_date else 'none'}"
        ]
        return ":".join(key_parts)
    
    def _get_user_activity_cache_key(self, user_id: str, days: int = 30) -> str:
        """Get cache key for user activity."""
        return f"{self.audit_log_user_cache_prefix}{user_id}:{days}d"
    
    def _serialize_audit_log(self, audit_log: AuditLog) -> Dict[str, Any]:
        """Serialize audit log for caching."""
        return {
            'id': str(audit_log.id),
            'user_id': audit_log.user_id,
            'action': audit_log.action,
            'resource': audit_log.resource,
            'resource_id': audit_log.resource_id,
            'old_values': audit_log.old_values,
            'new_values': audit_log.new_values,
            'ip_address': audit_log.ip_address,
            'user_agent': audit_log.user_agent,
            'created_at': audit_log.created_at.isoformat(),
            'is_test': audit_log.is_test,
            'is_live': audit_log.is_live
        }
    
    def _deserialize_audit_log(self, data: Dict[str, Any]) -> AuditLog:
        """Deserialize audit log from cache."""
        # Convert datetime strings back to datetime objects
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        # Convert UUID string back to UUID
        if data.get('id'):
            data['id'] = uuid.UUID(data['id'])
        
        return AuditLog(**data)
    
    async def create(self, audit_log_data: Dict[str, Any]) -> AuditLog:
        """
        Create a new audit log record with cache invalidation.
        
        Args:
            audit_log_data: Dictionary containing audit log data
            
        Returns:
            AuditLog: Created audit log instance
        """
        try:
            # Create audit log in database
            audit_log = await super().create(audit_log_data)
            
            # Cache the new audit log
            cache_key = self._get_audit_log_cache_key(audit_log.id)
            await self.cache_manager.set(
                cache_key,
                json.dumps(self._serialize_audit_log(audit_log)),
                expire=self.cache_ttl
            )
            
            # Invalidate list and stats caches
            await self._invalidate_list_caches()
            await self._invalidate_stats_caches()
            
            # Invalidate user activity cache if user_id is present
            if audit_log.user_id:
                await self._invalidate_user_activity_caches(audit_log.user_id)
            
            return audit_log
            
        except Exception as e:
            raise DatabaseError(f"Failed to create cached audit log: {str(e)}")
    
    async def get_by_id(self, audit_log_id: uuid.UUID) -> Optional[AuditLog]:
        """
        Get audit log by ID with cache lookup.
        
        Args:
            audit_log_id: Audit log UUID
            
        Returns:
            AuditLog or None if not found
        """
        try:
            # Try cache first
            cache_key = self._get_audit_log_cache_key(audit_log_id)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                try:
                    audit_log_data = json.loads(cached_data)
                    return self._deserialize_audit_log(audit_log_data)
                except (json.JSONDecodeError, ValueError) as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to deserialize cached audit log: {e}")
                    # Fall through to database lookup
            
            # Cache miss - get from database
            audit_log = await super().get_by_id(audit_log_id)
            
            if audit_log:
                # Cache the result
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(self._serialize_audit_log(audit_log)),
                    expire=self.cache_ttl
                )
            
            return audit_log
            
        except CacheError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().get_by_id(audit_log_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached audit log by ID: {str(e)}")
    
    async def list_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditLogAction] = None,
        resource: Optional[AuditLogResource] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        List audit logs with caching.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action
            resource: Filter by resource
            resource_id: Filter by resource ID
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number (1-based)
            per_page: Items per page
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            Dictionary containing audit logs list and pagination info
        """
        try:
            # Try cache first
            cache_key = self._get_list_cache_key(
                user_id, action, resource, resource_id, start_date, end_date,
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
            result = await super().list_audit_logs(
                user_id, action, resource, resource_id, start_date, end_date,
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
            return await super().list_audit_logs(
                user_id, action, resource, resource_id, start_date, end_date,
                page, per_page, order_by, order_direction
            )
        except Exception as e:
            raise DatabaseError(f"Failed to list cached audit logs: {str(e)}")
    
    async def get_audit_log_stats(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditLogAction] = None,
        resource: Optional[AuditLogResource] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics with caching.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action
            resource: Filter by resource
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Dictionary containing audit log statistics
        """
        try:
            # Try cache first
            cache_key = self._get_stats_cache_key(user_id, action, resource, start_date, end_date)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    # Invalid cache data, fall through to database
                    pass
            
            # Cache miss - get from database
            result = await super().get_audit_log_stats(user_id, action, resource, start_date, end_date)
            
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
            return await super().get_audit_log_stats(user_id, action, resource, start_date, end_date)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached audit log stats: {str(e)}")
    
    async def get_user_activity(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get user activity with caching.
        
        Args:
            user_id: User ID to get activity for
            days: Number of days to look back
            limit: Maximum number of logs to return
            
        Returns:
            List of audit logs for the user
        """
        try:
            # Use cache strategy for this query
            cache_key = f"{self._get_user_activity_cache_key(user_id, days)}:limit:{limit}"
            
            result = await self.cache_strategy.get_or_set(
                cache_key,
                super().get_user_activity,
                user_id,
                days,
                limit
            )
            
            return result
            
        except Exception as e:
            # Fallback to direct database query
            return await super().get_user_activity(user_id, days, limit)
    
    async def get_resource_history(
        self,
        resource: AuditLogResource,
        resource_id: str,
        limit: int = 50
    ) -> List[AuditLog]:
        """
        Get resource history with caching.
        
        Args:
            resource: Resource type
            resource_id: Resource ID
            limit: Maximum number of logs to return
            
        Returns:
            List of audit logs for the resource
        """
        try:
            # Use cache strategy for this query
            cache_key = f"audit_log_resource:{resource.value}:{resource_id}:limit:{limit}"
            
            result = await self.cache_strategy.get_or_set(
                cache_key,
                super().get_resource_history,
                resource,
                resource_id,
                limit
            )
            
            return result
            
        except Exception as e:
            # Fallback to direct database query
            return await super().get_resource_history(resource, resource_id, limit)
    
    async def _invalidate_list_caches(self):
        """Invalidate all list-related caches."""
        try:
            await self.cache_manager.invalidate_pattern(f"{self.audit_log_list_cache_prefix}*")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to invalidate list caches: {e}")
    
    async def _invalidate_stats_caches(self):
        """Invalidate all stats-related caches."""
        try:
            await self.cache_manager.invalidate_pattern(f"{self.audit_log_stats_cache_prefix}*")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to invalidate stats caches: {e}")
    
    async def _invalidate_user_activity_caches(self, user_id: str):
        """Invalidate user activity caches."""
        try:
            await self.cache_manager.invalidate_pattern(f"{self.audit_log_user_cache_prefix}{user_id}:*")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to invalidate user activity caches: {e}")
    
    async def invalidate_audit_log_cache(self, audit_log_id: uuid.UUID):
        """
        Invalidate cache for a specific audit log.
        
        Args:
            audit_log_id: Audit log UUID to invalidate
        """
        try:
            cache_key = self._get_audit_log_cache_key(audit_log_id)
            await self.cache_manager.delete(cache_key)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to invalidate audit log cache: {e}")
    
    async def warm_cache(self, audit_log_ids: List[uuid.UUID]):
        """
        Warm the cache with specific audit logs.
        
        Args:
            audit_log_ids: List of audit log UUIDs to cache
        """
        try:
            for audit_log_id in audit_log_ids:
                audit_log = await super().get_by_id(audit_log_id)
                if audit_log:
                    cache_key = self._get_audit_log_cache_key(audit_log_id)
                    await self.cache_manager.set(
                        cache_key,
                        json.dumps(self._serialize_audit_log(audit_log)),
                        expire=self.cache_ttl
                    )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to warm cache: {e}")
