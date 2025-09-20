"""
EasyPay Payment Gateway - Comprehensive Audit Logging Service
"""
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import DatabaseError
from src.core.models.rbac import SecurityEvent
from src.core.models.audit_log import AuditLog


class AuditLoggingService:
    """
    Comprehensive audit logging service for security events and system activities.
    
    This service provides detailed logging of all security-related events,
    user actions, and system activities for compliance and monitoring.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize audit logging service."""
        self.db = db
    
    async def log_security_event(
        self,
        event_type: str,
        event_category: str,
        message: str,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        severity: str = "info",
        success: bool = True,
        failure_reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action_attempted: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> SecurityEvent:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            event_category: Category of event (auth, authorization, security, etc.)
            message: Event message
            api_key_id: Associated API key ID
            user_id: Associated user ID
            severity: Event severity (info, warning, error, critical)
            success: Whether the event represents success or failure
            failure_reason: Reason for failure (if applicable)
            details: Additional event details
            resource_type: Type of resource involved
            resource_id: ID of resource involved
            action_attempted: Action that was attempted
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request ID for correlation
            session_id: Session ID for correlation
            
        Returns:
            Created SecurityEvent object
        """
        try:
            security_event = SecurityEvent(
                event_type=event_type,
                event_category=event_category,
                message=message,
                api_key_id=api_key_id,
                user_id=user_id,
                severity=severity,
                success=success,
                failure_reason=failure_reason,
                details=details,
                resource_type=resource_type,
                resource_id=resource_id,
                action_attempted=action_attempted,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                session_id=session_id
            )
            
            self.db.add(security_event)
            await self.db.commit()
            await self.db.refresh(security_event)
            
            return security_event
            
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to log security event: {str(e)}")
    
    async def log_authentication_event(
        self,
        event_type: str,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log an authentication event."""
        message = f"Authentication {'success' if success else 'failure'}: {event_type}"
        
        return await self.log_security_event(
            event_type=event_type,
            event_category="authentication",
            message=message,
            api_key_id=api_key_id,
            user_id=user_id,
            severity="warning" if not success else "info",
            success=success,
            failure_reason=failure_reason,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
    
    async def log_authorization_event(
        self,
        event_type: str,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action_attempted: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log an authorization event."""
        message = f"Authorization {'success' if success else 'failure'}: {event_type}"
        
        return await self.log_security_event(
            event_type=event_type,
            event_category="authorization",
            message=message,
            api_key_id=api_key_id,
            user_id=user_id,
            severity="error" if not success else "info",
            success=success,
            failure_reason=failure_reason,
            resource_type=resource_type,
            resource_id=resource_id,
            action_attempted=action_attempted,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            details=details
        )
    
    async def log_api_access_event(
        self,
        endpoint: str,
        method: str,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        success: bool = True,
        status_code: Optional[int] = None,
        response_time: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log an API access event."""
        message = f"API access: {method} {endpoint}"
        
        event_details = details or {}
        if status_code:
            event_details["status_code"] = status_code
        if response_time:
            event_details["response_time_ms"] = response_time
        
        return await self.log_security_event(
            event_type="api_access",
            event_category="access",
            message=message,
            api_key_id=api_key_id,
            user_id=user_id,
            severity="info",
            success=success,
            details=event_details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
    
    async def log_data_access_event(
        self,
        resource_type: str,
        resource_id: str,
        action: str,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log a data access event."""
        message = f"Data access: {action} {resource_type}:{resource_id}"
        
        return await self.log_security_event(
            event_type="data_access",
            event_category="data",
            message=message,
            api_key_id=api_key_id,
            user_id=user_id,
            severity="info",
            success=success,
            failure_reason=failure_reason,
            resource_type=resource_type,
            resource_id=resource_id,
            action_attempted=action,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            details=details
        )
    
    async def log_configuration_change_event(
        self,
        config_type: str,
        config_key: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log a configuration change event."""
        message = f"Configuration change: {config_type}.{config_key}"
        
        event_details = details or {}
        event_details.update({
            "config_type": config_type,
            "config_key": config_key,
            "old_value": old_value,
            "new_value": new_value
        })
        
        return await self.log_security_event(
            event_type="config_change",
            event_category="configuration",
            message=message,
            api_key_id=api_key_id,
            user_id=user_id,
            severity="warning",
            success=True,
            details=event_details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
    
    async def log_security_violation_event(
        self,
        violation_type: str,
        message: str,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log a security violation event."""
        return await self.log_security_event(
            event_type=f"security_violation_{violation_type}",
            event_category="security",
            message=message,
            api_key_id=api_key_id,
            user_id=user_id,
            severity="critical",
            success=False,
            failure_reason=violation_type,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
    
    # Event Query Methods
    async def get_security_events(
        self,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None,
        event_category: Optional[str] = None,
        severity: Optional[str] = None,
        success: Optional[bool] = None,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[SecurityEvent]:
        """Get security events with filtering."""
        try:
            query = select(SecurityEvent)
            
            # Apply filters
            if event_type:
                query = query.where(SecurityEvent.event_type == event_type)
            
            if event_category:
                query = query.where(SecurityEvent.event_category == event_category)
            
            if severity:
                query = query.where(SecurityEvent.severity == severity)
            
            if success is not None:
                query = query.where(SecurityEvent.success == success)
            
            if api_key_id:
                query = query.where(SecurityEvent.api_key_id == api_key_id)
            
            if user_id:
                query = query.where(SecurityEvent.user_id == user_id)
            
            if resource_type:
                query = query.where(SecurityEvent.resource_type == resource_type)
            
            if resource_id:
                query = query.where(SecurityEvent.resource_id == resource_id)
            
            if start_date:
                query = query.where(SecurityEvent.occurred_at >= start_date)
            
            if end_date:
                query = query.where(SecurityEvent.occurred_at <= end_date)
            
            # Order by occurred_at descending
            query = query.order_by(desc(SecurityEvent.occurred_at))
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            raise DatabaseError(f"Failed to get security events: {str(e)}")
    
    async def get_failed_authentication_attempts(
        self,
        ip_address: Optional[str] = None,
        api_key_id: Optional[UUID] = None,
        hours: int = 24
    ) -> List[SecurityEvent]:
        """Get failed authentication attempts."""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = select(SecurityEvent).where(
                and_(
                    SecurityEvent.event_category == "authentication",
                    SecurityEvent.success == False,
                    SecurityEvent.occurred_at >= start_time
                )
            )
            
            if ip_address:
                query = query.where(SecurityEvent.ip_address == ip_address)
            
            if api_key_id:
                query = query.where(SecurityEvent.api_key_id == api_key_id)
            
            query = query.order_by(desc(SecurityEvent.occurred_at))
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            raise DatabaseError(f"Failed to get failed authentication attempts: {str(e)}")
    
    async def get_security_violations(
        self,
        hours: int = 24,
        severity: Optional[str] = None
    ) -> List[SecurityEvent]:
        """Get security violations."""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = select(SecurityEvent).where(
                and_(
                    SecurityEvent.event_category == "security",
                    SecurityEvent.severity.in_(["error", "critical"]),
                    SecurityEvent.occurred_at >= start_time
                )
            )
            
            if severity:
                query = query.where(SecurityEvent.severity == severity)
            
            query = query.order_by(desc(SecurityEvent.occurred_at))
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            raise DatabaseError(f"Failed to get security violations: {str(e)}")
    
    async def get_api_key_activity(
        self,
        api_key_id: UUID,
        hours: int = 24
    ) -> List[SecurityEvent]:
        """Get activity for a specific API key."""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = select(SecurityEvent).where(
                and_(
                    SecurityEvent.api_key_id == api_key_id,
                    SecurityEvent.occurred_at >= start_time
                )
            )
            
            query = query.order_by(desc(SecurityEvent.occurred_at))
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            raise DatabaseError(f"Failed to get API key activity: {str(e)}")
    
    # Statistics and Analytics
    async def get_security_event_stats(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get security event statistics."""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Total events
            total_query = select(SecurityEvent).where(
                SecurityEvent.occurred_at >= start_time
            )
            total_result = await self.db.execute(total_query)
            total_events = len(total_result.scalars().all())
            
            # Failed events
            failed_query = select(SecurityEvent).where(
                and_(
                    SecurityEvent.success == False,
                    SecurityEvent.occurred_at >= start_time
                )
            )
            failed_result = await self.db.execute(failed_query)
            failed_events = len(failed_result.scalars().all())
            
            # Critical events
            critical_query = select(SecurityEvent).where(
                and_(
                    SecurityEvent.severity == "critical",
                    SecurityEvent.occurred_at >= start_time
                )
            )
            critical_result = await self.db.execute(critical_query)
            critical_events = len(critical_result.scalars().all())
            
            # Authentication failures
            auth_failures_query = select(SecurityEvent).where(
                and_(
                    SecurityEvent.event_category == "authentication",
                    SecurityEvent.success == False,
                    SecurityEvent.occurred_at >= start_time
                )
            )
            auth_failures_result = await self.db.execute(auth_failures_query)
            auth_failures = len(auth_failures_result.scalars().all())
            
            return {
                "total_events": total_events,
                "failed_events": failed_events,
                "critical_events": critical_events,
                "authentication_failures": auth_failures,
                "success_rate": ((total_events - failed_events) / total_events * 100) if total_events > 0 else 0,
                "time_period_hours": hours
            }
            
        except Exception as e:
            raise DatabaseError(f"Failed to get security event stats: {str(e)}")
    
    async def cleanup_old_events(self, days: int = 90) -> int:
        """Clean up old security events."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.db.execute(
                select(SecurityEvent).where(
                    SecurityEvent.occurred_at < cutoff_date
                )
            )
            old_events = result.scalars().all()
            
            # Delete old events
            for event in old_events:
                await self.db.delete(event)
            
            await self.db.commit()
            
            return len(old_events)
            
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to cleanup old events: {str(e)}")


class AuditLogger:
    """
    Convenience class for logging audit events.
    
    This class provides easy-to-use methods for logging common audit events.
    """
    
    def __init__(self, audit_service: AuditLoggingService):
        """Initialize audit logger."""
        self.audit_service = audit_service
    
    async def log_login_success(
        self,
        api_key_id: UUID,
        ip_address: str,
        user_agent: str,
        request_id: str
    ):
        """Log successful login."""
        await self.audit_service.log_authentication_event(
            event_type="login_success",
            api_key_id=api_key_id,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
    
    async def log_login_failure(
        self,
        api_key_id: Optional[UUID],
        failure_reason: str,
        ip_address: str,
        user_agent: str,
        request_id: str
    ):
        """Log failed login."""
        await self.audit_service.log_authentication_event(
            event_type="login_failure",
            api_key_id=api_key_id,
            success=False,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
    
    async def log_permission_denied(
        self,
        api_key_id: UUID,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str,
        user_agent: str,
        request_id: str
    ):
        """Log permission denied."""
        await self.audit_service.log_authorization_event(
            event_type="permission_denied",
            api_key_id=api_key_id,
            success=False,
            failure_reason="Insufficient permissions",
            resource_type=resource_type,
            resource_id=resource_id,
            action_attempted=action,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
    
    async def log_api_request(
        self,
        endpoint: str,
        method: str,
        api_key_id: UUID,
        status_code: int,
        response_time: float,
        ip_address: str,
        user_agent: str,
        request_id: str
    ):
        """Log API request."""
        await self.audit_service.log_api_access_event(
            endpoint=endpoint,
            method=method,
            api_key_id=api_key_id,
            success=status_code < 400,
            status_code=status_code,
            response_time=response_time,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
    
    async def log_data_access(
        self,
        resource_type: str,
        resource_id: str,
        action: str,
        api_key_id: UUID,
        ip_address: str,
        user_agent: str,
        request_id: str
    ):
        """Log data access."""
        await self.audit_service.log_data_access_event(
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            api_key_id=api_key_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
