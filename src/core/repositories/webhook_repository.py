"""
EasyPay Payment Gateway - Webhook Repository
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.models.webhook import Webhook, WebhookStatus, WebhookEventType
from src.core.exceptions import WebhookNotFoundError, DatabaseError


class WebhookRepository:
    """
    Repository for webhook-related database operations.
    
    This class provides methods for CRUD operations on webhooks,
    including delivery management, retry logic, and event tracking.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, webhook_data: Dict[str, Any]) -> Webhook:
        """
        Create a new webhook record.
        
        Args:
            webhook_data: Dictionary containing webhook data
            
        Returns:
            Webhook: Created webhook instance
            
        Raises:
            DatabaseError: If creation fails
        """
        try:
            webhook = Webhook(**webhook_data)
            self.session.add(webhook)
            await self.session.commit()
            await self.session.refresh(webhook)
            return webhook
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create webhook: {str(e)}")
    
    async def get_by_id(self, webhook_id: uuid.UUID) -> Optional[Webhook]:
        """
        Get webhook by ID.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            Webhook or None if not found
        """
        try:
            result = await self.session.execute(
                select(Webhook)
                .options(selectinload(Webhook.payment))
                .where(Webhook.id == webhook_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get webhook by ID: {str(e)}")
    
    async def get_by_event_id(self, event_id: str) -> Optional[Webhook]:
        """
        Get webhook by event ID.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Webhook or None if not found
        """
        try:
            result = await self.session.execute(
                select(Webhook)
                .options(selectinload(Webhook.payment))
                .where(Webhook.event_id == event_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get webhook by event ID: {str(e)}")
    
    async def update(self, webhook_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[Webhook]:
        """
        Update webhook record.
        
        Args:
            webhook_id: Webhook UUID
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated Webhook or None if not found
            
        Raises:
            DatabaseError: If update fails
        """
        try:
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            # First, get the webhook to check if it exists
            webhook = await self.get_by_id(webhook_id)
            if not webhook:
                return None
            
            # Update the webhook object
            for key, value in update_data.items():
                setattr(webhook, key, value)
            
            await self.session.commit()
            await self.session.refresh(webhook)
            return webhook
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update webhook: {str(e)}")
    
    async def delete(self, webhook_id: uuid.UUID) -> bool:
        """
        Delete webhook record.
        
        Args:
            webhook_id: Webhook UUID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            result = await self.session.execute(
                delete(Webhook).where(Webhook.id == webhook_id)
            )
            
            if result.rowcount == 0:
                return False
                
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to delete webhook: {str(e)}")
    
    async def list_webhooks(
        self,
        event_type: Optional[WebhookEventType] = None,
        status: Optional[WebhookStatus] = None,
        payment_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        List webhooks with filtering and pagination.
        
        Args:
            event_type: Filter by event type
            status: Filter by webhook status
            payment_id: Filter by payment ID
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
            # Build query
            query = select(Webhook)
            
            # Apply filters
            conditions = []
            if event_type:
                conditions.append(Webhook.event_type == event_type)
            if status:
                conditions.append(Webhook.status == status)
            if payment_id:
                conditions.append(Webhook.payment_id == payment_id)
            if start_date:
                conditions.append(Webhook.created_at >= start_date)
            if end_date:
                conditions.append(Webhook.created_at <= end_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply ordering
            order_column = getattr(Webhook, order_by, Webhook.created_at)
            if order_direction.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
            
            # Get total count
            count_query = select(func.count(Webhook.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.session.execute(query)
            webhooks = result.scalars().all()
            
            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "webhooks": list(webhooks),
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        except Exception as e:
            raise DatabaseError(f"Failed to list webhooks: {str(e)}")
    
    async def get_failed_webhooks(self, max_retries: int = 3) -> List[Webhook]:
        """
        Get webhooks that have failed and can be retried.
        
        Args:
            max_retries: Maximum number of retries allowed
            
        Returns:
            List of failed webhooks that can be retried
        """
        try:
            result = await self.session.execute(
                select(Webhook)
                .where(
                    and_(
                        Webhook.status.in_([WebhookStatus.FAILED, WebhookStatus.RETRYING]),
                        Webhook.retry_count < max_retries
                    )
                )
                .order_by(Webhook.created_at.asc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get failed webhooks: {str(e)}")
    
    async def get_webhooks_ready_for_retry(self) -> List[Webhook]:
        """
        Get webhooks that are ready for retry (past their retry time).
        
        Returns:
            List of webhooks ready for retry
        """
        try:
            now = datetime.utcnow()
            result = await self.session.execute(
                select(Webhook)
                .where(
                    and_(
                        Webhook.status == WebhookStatus.RETRYING,
                        Webhook.next_retry_at <= now
                    )
                )
                .order_by(Webhook.next_retry_at.asc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get webhooks ready for retry: {str(e)}")
    
    async def get_webhooks_by_payment(self, payment_id: uuid.UUID) -> List[Webhook]:
        """
        Get all webhooks for a specific payment.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            List of webhooks for the payment
        """
        try:
            result = await self.session.execute(
                select(Webhook)
                .where(Webhook.payment_id == payment_id)
                .order_by(Webhook.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get webhooks by payment: {str(e)}")
    
    async def get_webhooks_by_event_type(self, event_type: WebhookEventType) -> List[Webhook]:
        """
        Get all webhooks for a specific event type.
        
        Args:
            event_type: Event type
            
        Returns:
            List of webhooks for the event type
        """
        try:
            result = await self.session.execute(
                select(Webhook)
                .where(Webhook.event_type == event_type)
                .order_by(Webhook.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get webhooks by event type: {str(e)}")
    
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
            # Build base query
            base_query = select(Webhook)
            conditions = []
            
            if start_date:
                conditions.append(Webhook.created_at >= start_date)
            if end_date:
                conditions.append(Webhook.created_at <= end_date)
            
            if conditions:
                base_query = base_query.where(and_(*conditions))
            
            # Get total count
            count_query = select(func.count(Webhook.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await self.session.execute(count_query)
            total_count = total_result.scalar()
            
            # Get status counts
            status_query = (
                select(Webhook.status, func.count(Webhook.id))
                .group_by(Webhook.status)
            )
            if conditions:
                status_query = status_query.where(and_(*conditions))
            
            status_result = await self.session.execute(status_query)
            status_counts = dict(status_result.fetchall())
            
            # Get event type counts
            event_type_query = (
                select(Webhook.event_type, func.count(Webhook.id))
                .group_by(Webhook.event_type)
            )
            if conditions:
                event_type_query = event_type_query.where(and_(*conditions))
            
            event_type_result = await self.session.execute(event_type_query)
            event_type_counts = dict(event_type_result.fetchall())
            
            return {
                "total_count": total_count,
                "status_counts": status_counts,
                "event_type_counts": event_type_counts
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get webhook stats: {str(e)}")
    
    async def mark_as_delivered(
        self,
        webhook_id: uuid.UUID,
        response_status_code: int,
        response_body: str,
        response_headers: Dict[str, Any]
    ) -> Optional[Webhook]:
        """
        Mark webhook as successfully delivered.
        
        Args:
            webhook_id: Webhook UUID
            response_status_code: HTTP response status code
            response_body: Response body
            response_headers: Response headers
            
        Returns:
            Updated Webhook or None if not found
        """
        try:
            update_data = {
                'status': WebhookStatus.DELIVERED,
                'response_status_code': response_status_code,
                'response_body': response_body,
                'response_headers': response_headers,
                'delivered_at': datetime.utcnow()
            }
            return await self.update(webhook_id, update_data)
        except Exception as e:
            raise DatabaseError(f"Failed to mark webhook as delivered: {str(e)}")
    
    async def mark_as_failed(
        self,
        webhook_id: uuid.UUID,
        response_status_code: Optional[int] = None,
        response_body: Optional[str] = None
    ) -> Optional[Webhook]:
        """
        Mark webhook as failed.
        
        Args:
            webhook_id: Webhook UUID
            response_status_code: HTTP response status code
            response_body: Response body
            
        Returns:
            Updated Webhook or None if not found
        """
        try:
            update_data = {
                'status': WebhookStatus.FAILED,
                'failed_at': datetime.utcnow()
            }
            
            if response_status_code is not None:
                update_data['response_status_code'] = response_status_code
            if response_body is not None:
                update_data['response_body'] = response_body
                
            return await self.update(webhook_id, update_data)
        except Exception as e:
            raise DatabaseError(f"Failed to mark webhook as failed: {str(e)}")
    
    async def schedule_retry(
        self,
        webhook_id: uuid.UUID,
        retry_delay_minutes: int = 5
    ) -> Optional[Webhook]:
        """
        Schedule webhook for retry.
        
        Args:
            webhook_id: Webhook UUID
            retry_delay_minutes: Delay before retry in minutes
            
        Returns:
            Updated Webhook or None if not found
        """
        try:
            webhook = await self.get_by_id(webhook_id)
            if not webhook:
                return None
            
            update_data = {
                'status': WebhookStatus.RETRYING,
                'retry_count': webhook.retry_count + 1,
                'next_retry_at': datetime.utcnow() + timedelta(minutes=retry_delay_minutes)
            }
            
            return await self.update(webhook_id, update_data)
        except Exception as e:
            raise DatabaseError(f"Failed to schedule webhook retry: {str(e)}")
