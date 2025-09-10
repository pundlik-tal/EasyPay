"""
EasyPay Payment Gateway - Audit Log Repository
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.models.audit_log import AuditLog, AuditLogLevel, AuditLogAction
from src.core.exceptions import DatabaseError


class AuditLogRepository:
    """
    Repository for audit log-related database operations.
    
    This class provides methods for CRUD operations on audit logs,
    including logging, querying, and reporting.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, audit_log_data: Dict[str, Any]) -> AuditLog:
        """
        Create a new audit log record.
        
        Args:
            audit_log_data: Dictionary containing audit log data
            
        Returns:
            AuditLog: Created audit log instance
            
        Raises:
            DatabaseError: If creation fails
        """
        try:
            audit_log = AuditLog(**audit_log_data)
            self.session.add(audit_log)
            await self.session.commit()
            await self.session.refresh(audit_log)
            return audit_log
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create audit log: {str(e)}")
    
    async def get_by_id(self, audit_log_id: uuid.UUID) -> Optional[AuditLog]:
        """
        Get audit log by ID.
        
        Args:
            audit_log_id: Audit log UUID
            
        Returns:
            AuditLog or None if not found
        """
        try:
            result = await self.session.execute(
                select(AuditLog)
                .options(selectinload(AuditLog.payment))
                .where(AuditLog.id == audit_log_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get audit log by ID: {str(e)}")
    
    async def list_audit_logs(
        self,
        action: Optional[AuditLogAction] = None,
        level: Optional[AuditLogLevel] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        payment_id: Optional[uuid.UUID] = None,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        List audit logs with filtering and pagination.
        
        Args:
            action: Filter by action
            level: Filter by log level
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            payment_id: Filter by payment ID
            user_id: Filter by user ID
            api_key_id: Filter by API key ID
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
            # Build query
            query = select(AuditLog)
            
            # Apply filters
            conditions = []
            if action:
                conditions.append(AuditLog.action == action.value)
            if level:
                conditions.append(AuditLog.level == level.value)
            if entity_type:
                conditions.append(AuditLog.entity_type == entity_type)
            if entity_id:
                conditions.append(AuditLog.entity_id == entity_id)
            if payment_id:
                conditions.append(AuditLog.payment_id == payment_id)
            if user_id:
                conditions.append(AuditLog.user_id == user_id)
            if api_key_id:
                conditions.append(AuditLog.api_key_id == api_key_id)
            if start_date:
                conditions.append(AuditLog.created_at >= start_date)
            if end_date:
                conditions.append(AuditLog.created_at <= end_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Apply ordering
            order_column = getattr(AuditLog, order_by, AuditLog.created_at)
            if order_direction.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
            
            # Get total count
            count_query = select(func.count(AuditLog.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)
            
            # Execute query
            result = await self.session.execute(query)
            audit_logs = result.scalars().all()
            
            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "audit_logs": list(audit_logs),
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        except Exception as e:
            raise DatabaseError(f"Failed to list audit logs: {str(e)}")
    
    async def get_audit_logs_by_payment(self, payment_id: uuid.UUID) -> List[AuditLog]:
        """
        Get all audit logs for a specific payment.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            List of audit logs for the payment
        """
        try:
            result = await self.session.execute(
                select(AuditLog)
                .where(AuditLog.payment_id == payment_id)
                .order_by(AuditLog.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get audit logs by payment: {str(e)}")
    
    async def get_audit_logs_by_user(self, user_id: str) -> List[AuditLog]:
        """
        Get all audit logs for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of audit logs for the user
        """
        try:
            result = await self.session.execute(
                select(AuditLog)
                .where(AuditLog.user_id == user_id)
                .order_by(AuditLog.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get audit logs by user: {str(e)}")
    
    async def get_audit_logs_by_api_key(self, api_key_id: str) -> List[AuditLog]:
        """
        Get all audit logs for a specific API key.
        
        Args:
            api_key_id: API key identifier
            
        Returns:
            List of audit logs for the API key
        """
        try:
            result = await self.session.execute(
                select(AuditLog)
                .where(AuditLog.api_key_id == api_key_id)
                .order_by(AuditLog.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get audit logs by API key: {str(e)}")
    
    async def get_audit_logs_by_action(self, action: AuditLogAction) -> List[AuditLog]:
        """
        Get all audit logs for a specific action.
        
        Args:
            action: Audit log action
            
        Returns:
            List of audit logs for the action
        """
        try:
            result = await self.session.execute(
                select(AuditLog)
                .where(AuditLog.action == action.value)
                .order_by(AuditLog.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get audit logs by action: {str(e)}")
    
    async def get_audit_logs_by_level(self, level: AuditLogLevel) -> List[AuditLog]:
        """
        Get all audit logs for a specific level.
        
        Args:
            level: Audit log level
            
        Returns:
            List of audit logs for the level
        """
        try:
            result = await self.session.execute(
                select(AuditLog)
                .where(AuditLog.level == level.value)
                .order_by(AuditLog.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            raise DatabaseError(f"Failed to get audit logs by level: {str(e)}")
    
    async def get_audit_log_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Dictionary containing audit log statistics
        """
        try:
            # Build base query
            base_query = select(AuditLog)
            conditions = []
            
            if start_date:
                conditions.append(AuditLog.created_at >= start_date)
            if end_date:
                conditions.append(AuditLog.created_at <= end_date)
            
            if conditions:
                base_query = base_query.where(and_(*conditions))
            
            # Get total count
            count_query = select(func.count(AuditLog.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            total_result = await self.session.execute(count_query)
            total_count = total_result.scalar()
            
            # Get level counts
            level_query = (
                select(AuditLog.level, func.count(AuditLog.id))
                .group_by(AuditLog.level)
            )
            if conditions:
                level_query = level_query.where(and_(*conditions))
            
            level_result = await self.session.execute(level_query)
            level_counts = dict(level_result.fetchall())
            
            # Get action counts
            action_query = (
                select(AuditLog.action, func.count(AuditLog.id))
                .group_by(AuditLog.action)
            )
            if conditions:
                action_query = action_query.where(and_(*conditions))
            
            action_result = await self.session.execute(action_query)
            action_counts = dict(action_result.fetchall())
            
            # Get entity type counts
            entity_type_query = (
                select(AuditLog.entity_type, func.count(AuditLog.id))
                .group_by(AuditLog.entity_type)
            )
            if conditions:
                entity_type_query = entity_type_query.where(and_(*conditions))
            
            entity_type_result = await self.session.execute(entity_type_query)
            entity_type_counts = dict(entity_type_result.fetchall())
            
            return {
                "total_count": total_count,
                "level_counts": level_counts,
                "action_counts": action_counts,
                "entity_type_counts": entity_type_counts
            }
        except Exception as e:
            raise DatabaseError(f"Failed to get audit log stats: {str(e)}")
    
    async def search_audit_logs(
        self,
        search_term: str,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search audit logs by message content.
        
        Args:
            search_term: Search term
            page: Page number (1-based)
            per_page: Items per page
            
        Returns:
            Dictionary containing search results and pagination info
        """
        try:
            # Build search conditions
            search_conditions = or_(
                AuditLog.message.ilike(f"%{search_term}%"),
                AuditLog.action.ilike(f"%{search_term}%"),
                AuditLog.entity_type.ilike(f"%{search_term}%"),
                AuditLog.entity_id.ilike(f"%{search_term}%"),
                AuditLog.user_id.ilike(f"%{search_term}%"),
                AuditLog.api_key_id.ilike(f"%{search_term}%")
            )
            
            # Get total count
            count_query = select(func.count(AuditLog.id)).where(search_conditions)
            total_result = await self.session.execute(count_query)
            total = total_result.scalar()
            
            # Get results
            query = (
                select(AuditLog)
                .where(search_conditions)
                .order_by(AuditLog.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            
            result = await self.session.execute(query)
            audit_logs = result.scalars().all()
            
            # Calculate pagination info
            total_pages = (total + per_page - 1) // per_page
            
            return {
                "audit_logs": list(audit_logs),
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "search_term": search_term
            }
        except Exception as e:
            raise DatabaseError(f"Failed to search audit logs: {str(e)}")
    
    async def log_payment_action(
        self,
        action: AuditLogAction,
        payment_id: uuid.UUID,
        message: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        level: AuditLogLevel = AuditLogLevel.INFO
    ) -> AuditLog:
        """
        Log a payment-related action.
        
        Args:
            action: Action being logged
            payment_id: Payment UUID
            message: Log message
            user_id: User identifier
            api_key_id: API key identifier
            metadata: Additional metadata
            old_values: Previous values
            new_values: New values
            level: Log level
            
        Returns:
            Created AuditLog instance
        """
        try:
            audit_log = AuditLog.create_payment_log(
                action=action,
                payment_id=payment_id,
                message=message,
                user_id=user_id,
                api_key_id=api_key_id,
                metadata=metadata,
                old_values=old_values,
                new_values=new_values,
                level=level
            )
            
            self.session.add(audit_log)
            await self.session.commit()
            await self.session.refresh(audit_log)
            return audit_log
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to log payment action: {str(e)}")
    
    async def log_security_action(
        self,
        action: AuditLogAction,
        message: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: AuditLogLevel = AuditLogLevel.WARNING
    ) -> AuditLog:
        """
        Log a security-related action.
        
        Args:
            action: Action being logged
            message: Log message
            user_id: User identifier
            api_key_id: API key identifier
            ip_address: IP address
            user_agent: User agent string
            metadata: Additional metadata
            level: Log level
            
        Returns:
            Created AuditLog instance
        """
        try:
            audit_log = AuditLog.create_security_log(
                action=action,
                message=message,
                user_id=user_id,
                api_key_id=api_key_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata,
                level=level
            )
            
            self.session.add(audit_log)
            await self.session.commit()
            await self.session.refresh(audit_log)
            return audit_log
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to log security action: {str(e)}")
    
    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        Clean up old audit logs.
        
        Args:
            days_to_keep: Number of days to keep logs
            
        Returns:
            Number of logs deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            result = await self.session.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff_date)
            )
            
            deleted_count = result.rowcount
            await self.session.commit()
            return deleted_count
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to cleanup old logs: {str(e)}")
