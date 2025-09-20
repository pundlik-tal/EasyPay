"""
EasyPay Payment Gateway - Cached Payment Repository

This module provides a cached version of the payment repository that integrates
with Redis for improved performance and reduced database load.
"""

import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repositories.payment_repository import PaymentRepository
from src.core.models.payment import Payment, PaymentStatus
from src.core.exceptions import PaymentNotFoundError, DatabaseError, CacheError
from src.infrastructure.cache import get_cache_client, CacheManager


class CachedPaymentRepository(PaymentRepository):
    """
    Cached payment repository with Redis integration.
    
    Provides the same interface as PaymentRepository but with Redis caching
    for improved performance and reduced database load.
    """
    
    def __init__(self, session: AsyncSession, cache_manager: Optional[CacheManager] = None):
        super().__init__(session)
        self.cache_manager = cache_manager or CacheManager(get_cache_client())
        
        # Cache configuration
        self.cache_ttl = 300  # 5 minutes default TTL
        self.payment_cache_prefix = "payment:"
        self.payment_list_cache_prefix = "payment_list:"
        self.payment_stats_cache_prefix = "payment_stats:"
        self.payment_search_cache_prefix = "payment_search:"
    
    def _get_payment_cache_key(self, payment_id: uuid.UUID) -> str:
        """Get cache key for a payment."""
        return f"{self.payment_cache_prefix}{str(payment_id)}"
    
    def _get_external_id_cache_key(self, external_id: str) -> str:
        """Get cache key for external ID lookup."""
        return f"{self.payment_cache_prefix}external:{external_id}"
    
    def _get_authorize_net_cache_key(self, authorize_net_id: str) -> str:
        """Get cache key for Authorize.net ID lookup."""
        return f"{self.payment_cache_prefix}authnet:{authorize_net_id}"
    
    def _get_list_cache_key(
        self,
        customer_id: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> str:
        """Get cache key for payment list query."""
        key_parts = [
            self.payment_list_cache_prefix,
            f"customer:{customer_id or 'all'}",
            f"status:{status.value if status else 'all'}",
            f"start:{start_date.isoformat() if start_date else 'none'}",
            f"end:{end_date.isoformat() if end_date else 'none'}",
            f"page:{page}",
            f"per_page:{per_page}",
            f"order:{order_by}:{order_direction}"
        ]
        return ":".join(key_parts)
    
    def _get_search_cache_key(
        self,
        search_term: str,
        page: int = 1,
        per_page: int = 20
    ) -> str:
        """Get cache key for payment search query."""
        return f"{self.payment_search_cache_prefix}{search_term}:page:{page}:per_page:{per_page}"
    
    def _get_stats_cache_key(
        self,
        customer_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """Get cache key for payment statistics."""
        key_parts = [
            self.payment_stats_cache_prefix,
            f"customer:{customer_id or 'all'}",
            f"start:{start_date.isoformat() if start_date else 'none'}",
            f"end:{end_date.isoformat() if end_date else 'none'}"
        ]
        return ":".join(key_parts)
    
    def _serialize_payment(self, payment: Payment) -> Dict[str, Any]:
        """Serialize payment for caching."""
        return {
            'id': str(payment.id),
            'external_id': payment.external_id,
            'authorize_net_transaction_id': payment.authorize_net_transaction_id,
            'amount': str(payment.amount),
            'currency': payment.currency,
            'status': payment.status,
            'payment_method': payment.payment_method,
            'customer_id': payment.customer_id,
            'customer_email': payment.customer_email,
            'customer_name': payment.customer_name,
            'card_token': payment.card_token,
            'card_last_four': payment.card_last_four,
            'card_brand': payment.card_brand,
            'card_exp_month': payment.card_exp_month,
            'card_exp_year': payment.card_exp_year,
            'description': payment.description,
            'payment_metadata': payment.payment_metadata,
            'processor_response_code': payment.processor_response_code,
            'processor_response_message': payment.processor_response_message,
            'processor_transaction_id': payment.processor_transaction_id,
            'refunded_amount': str(payment.refunded_amount) if payment.refunded_amount else None,
            'refund_count': payment.refund_count,
            'created_at': payment.created_at.isoformat(),
            'updated_at': payment.updated_at.isoformat(),
            'processed_at': payment.processed_at.isoformat() if payment.processed_at else None,
            'settled_at': payment.settled_at.isoformat() if payment.settled_at else None,
            'is_test': payment.is_test,
            'is_live': payment.is_live
        }
    
    def _deserialize_payment(self, data: Dict[str, Any]) -> Payment:
        """Deserialize payment from cache."""
        # Convert string amounts back to Decimal
        if data.get('amount'):
            data['amount'] = Decimal(data['amount'])
        if data.get('refunded_amount'):
            data['refunded_amount'] = Decimal(data['refunded_amount'])
        
        # Convert datetime strings back to datetime objects
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('processed_at'):
            data['processed_at'] = datetime.fromisoformat(data['processed_at'])
        if data.get('settled_at'):
            data['settled_at'] = datetime.fromisoformat(data['settled_at'])
        
        # Convert UUID string back to UUID
        if data.get('id'):
            data['id'] = uuid.UUID(data['id'])
        
        return Payment(**data)
    
    async def create(self, payment_data: Dict[str, Any]) -> Payment:
        """
        Create a new payment record with cache invalidation.
        
        Args:
            payment_data: Dictionary containing payment data
            
        Returns:
            Payment: Created payment instance
        """
        try:
            # Create payment in database
            payment = await super().create(payment_data)
            
            # Cache the new payment
            cache_key = self._get_payment_cache_key(payment.id)
            await self.cache_manager.set(
                cache_key,
                json.dumps(self._serialize_payment(payment)),
                expire=self.cache_ttl
            )
            
            # Cache external ID lookup
            external_id_key = self._get_external_id_cache_key(payment.external_id)
            await self.cache_manager.set(
                external_id_key,
                str(payment.id),
                expire=self.cache_ttl
            )
            
            # Cache Authorize.net ID lookup if present
            if payment.authorize_net_transaction_id:
                authnet_key = self._get_authorize_net_cache_key(payment.authorize_net_transaction_id)
                await self.cache_manager.set(
                    authnet_key,
                    str(payment.id),
                    expire=self.cache_ttl
                )
            
            # Invalidate list and stats caches
            await self._invalidate_list_caches()
            await self._invalidate_stats_caches()
            
            return payment
            
        except Exception as e:
            raise DatabaseError(f"Failed to create cached payment: {str(e)}")
    
    async def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        """
        Get payment by ID with cache lookup.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            Payment or None if not found
        """
        try:
            # Try cache first
            cache_key = self._get_payment_cache_key(payment_id)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                try:
                    payment_data = json.loads(cached_data)
                    return self._deserialize_payment(payment_data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to deserialize cached payment: {e}")
                    # Fall through to database lookup
            
            # Cache miss - get from database
            payment = await super().get_by_id(payment_id)
            
            if payment:
                # Cache the result
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(self._serialize_payment(payment)),
                    expire=self.cache_ttl
                )
            
            return payment
            
        except CacheError as e:
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().get_by_id(payment_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached payment by ID: {str(e)}")
    
    async def get_by_external_id(self, external_id: str) -> Optional[Payment]:
        """
        Get payment by external ID with cache lookup.
        
        Args:
            external_id: External payment identifier
            
        Returns:
            Payment or None if not found
        """
        try:
            # Try cache first
            external_id_key = self._get_external_id_cache_key(external_id)
            cached_id = await self.cache_manager.get(external_id_key)
            
            if cached_id:
                try:
                    payment_id = uuid.UUID(cached_id)
                    return await self.get_by_id(payment_id)
                except ValueError:
                    # Invalid UUID in cache
                    pass
            
            # Cache miss - get from database
            payment = await super().get_by_external_id(external_id)
            
            if payment:
                # Cache the external ID lookup
                await self.cache_manager.set(
                    external_id_key,
                    str(payment.id),
                    expire=self.cache_ttl
                )
                
                # Cache the payment itself
                cache_key = self._get_payment_cache_key(payment.id)
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(self._serialize_payment(payment)),
                    expire=self.cache_ttl
                )
            
            return payment
            
        except CacheError as e:
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().get_by_external_id(external_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached payment by external ID: {str(e)}")
    
    async def get_by_authorize_net_id(self, authorize_net_id: str) -> Optional[Payment]:
        """
        Get payment by Authorize.net transaction ID with cache lookup.
        
        Args:
            authorize_net_id: Authorize.net transaction identifier
            
        Returns:
            Payment or None if not found
        """
        try:
            # Try cache first
            authnet_key = self._get_authorize_net_cache_key(authorize_net_id)
            cached_id = await self.cache_manager.get(authnet_key)
            
            if cached_id:
                try:
                    payment_id = uuid.UUID(cached_id)
                    return await self.get_by_id(payment_id)
                except ValueError:
                    # Invalid UUID in cache
                    pass
            
            # Cache miss - get from database
            payment = await super().get_by_authorize_net_id(authorize_net_id)
            
            if payment:
                # Cache the Authorize.net ID lookup
                await self.cache_manager.set(
                    authnet_key,
                    str(payment.id),
                    expire=self.cache_ttl
                )
                
                # Cache the payment itself
                cache_key = self._get_payment_cache_key(payment.id)
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(self._serialize_payment(payment)),
                    expire=self.cache_ttl
                )
            
            return payment
            
        except CacheError as e:
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().get_by_authorize_net_id(authorize_net_id)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached payment by Authorize.net ID: {str(e)}")
    
    async def update(self, payment_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[Payment]:
        """
        Update payment record with cache invalidation.
        
        Args:
            payment_id: Payment UUID
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated Payment or None if not found
        """
        try:
            # Update in database
            payment = await super().update(payment_id, update_data)
            
            if payment:
                # Update cache
                cache_key = self._get_payment_cache_key(payment.id)
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(self._serialize_payment(payment)),
                    expire=self.cache_ttl
                )
                
                # Invalidate list and stats caches
                await self._invalidate_list_caches()
                await self._invalidate_stats_caches()
            
            return payment
            
        except Exception as e:
            raise DatabaseError(f"Failed to update cached payment: {str(e)}")
    
    async def delete(self, payment_id: uuid.UUID) -> bool:
        """
        Delete payment record with cache invalidation.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            # Get payment before deletion for cache cleanup
            payment = await self.get_by_id(payment_id)
            
            # Delete from database
            result = await super().delete(payment_id)
            
            if result and payment:
                # Remove from cache
                cache_key = self._get_payment_cache_key(payment_id)
                await self.cache_manager.delete(cache_key)
                
                # Remove external ID lookup
                external_id_key = self._get_external_id_cache_key(payment.external_id)
                await self.cache_manager.delete(external_id_key)
                
                # Remove Authorize.net ID lookup if present
                if payment.authorize_net_transaction_id:
                    authnet_key = self._get_authorize_net_cache_key(payment.authorize_net_transaction_id)
                    await self.cache_manager.delete(authnet_key)
                
                # Invalidate list and stats caches
                await self._invalidate_list_caches()
                await self._invalidate_stats_caches()
            
            return result
            
        except Exception as e:
            raise DatabaseError(f"Failed to delete cached payment: {str(e)}")
    
    async def list_payments(
        self,
        customer_id: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        List payments with caching.
        
        Args:
            customer_id: Filter by customer ID
            status: Filter by payment status
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number (1-based)
            per_page: Items per page
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            Dictionary containing payments list and pagination info
        """
        try:
            # Try cache first
            cache_key = self._get_list_cache_key(
                customer_id, status, start_date, end_date,
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
            result = await super().list_payments(
                customer_id, status, start_date, end_date,
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
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().list_payments(
                customer_id, status, start_date, end_date,
                page, per_page, order_by, order_direction
            )
        except Exception as e:
            raise DatabaseError(f"Failed to list cached payments: {str(e)}")
    
    async def search_payments(
        self,
        search_term: str,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search payments with caching.
        
        Args:
            search_term: Search term
            page: Page number (1-based)
            per_page: Items per page
            
        Returns:
            Dictionary containing search results and pagination info
        """
        try:
            # Try cache first
            cache_key = self._get_search_cache_key(search_term, page, per_page)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    # Invalid cache data, fall through to database
                    pass
            
            # Cache miss - get from database
            result = await super().search_payments(search_term, page, per_page)
            
            # Cache the result
            await self.cache_manager.set(
                cache_key,
                json.dumps(result, default=str),
                expire=self.cache_ttl
            )
            
            return result
            
        except CacheError as e:
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().search_payments(search_term, page, per_page)
        except Exception as e:
            raise DatabaseError(f"Failed to search cached payments: {str(e)}")
    
    async def get_payment_stats(
        self,
        customer_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get payment statistics with caching.
        
        Args:
            customer_id: Filter by customer ID
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Dictionary containing payment statistics
        """
        try:
            # Try cache first
            cache_key = self._get_stats_cache_key(customer_id, start_date, end_date)
            cached_data = await self.cache_manager.get(cache_key)
            
            if cached_data:
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    # Invalid cache data, fall through to database
                    pass
            
            # Cache miss - get from database
            result = await super().get_payment_stats(customer_id, start_date, end_date)
            
            # Cache the result
            await self.cache_manager.set(
                cache_key,
                json.dumps(result, default=str),
                expire=self.cache_ttl
            )
            
            return result
            
        except CacheError as e:
            logger.warning(f"Cache error, falling back to database: {e}")
            return await super().get_payment_stats(customer_id, start_date, end_date)
        except Exception as e:
            raise DatabaseError(f"Failed to get cached payment stats: {str(e)}")
    
    async def _invalidate_list_caches(self):
        """Invalidate all list-related caches."""
        try:
            # Get all list cache keys
            keys = await self.cache_manager.redis.keys(f"{self.payment_list_cache_prefix}*")
            if keys:
                await self.cache_manager.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Failed to invalidate list caches: {e}")
    
    async def _invalidate_stats_caches(self):
        """Invalidate all stats-related caches."""
        try:
            # Get all stats cache keys
            keys = await self.cache_manager.redis.keys(f"{self.payment_stats_cache_prefix}*")
            if keys:
                await self.cache_manager.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Failed to invalidate stats caches: {e}")
    
    async def invalidate_payment_cache(self, payment_id: uuid.UUID):
        """
        Invalidate cache for a specific payment.
        
        Args:
            payment_id: Payment UUID to invalidate
        """
        try:
            cache_key = self._get_payment_cache_key(payment_id)
            await self.cache_manager.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate payment cache: {e}")
    
    async def warm_cache(self, payment_ids: List[uuid.UUID]):
        """
        Warm the cache with specific payments.
        
        Args:
            payment_ids: List of payment UUIDs to cache
        """
        try:
            for payment_id in payment_ids:
                payment = await super().get_by_id(payment_id)
                if payment:
                    cache_key = self._get_payment_cache_key(payment_id)
                    await self.cache_manager.set(
                        cache_key,
                        json.dumps(self._serialize_payment(payment)),
                        expire=self.cache_ttl
                    )
        except Exception as e:
            logger.warning(f"Failed to warm cache: {e}")


# Import logger
import logging
logger = logging.getLogger(__name__)
