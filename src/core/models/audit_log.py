"""
EasyPay Payment Gateway - Audit Log Model
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, Integer,
    Index, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.db_components.base import Base


class AuditLogLevel(str, Enum):
    """Audit log level enumeration."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogAction(str, Enum):
    """Audit log action enumeration."""
    PAYMENT_CREATED = "payment.created"
    PAYMENT_UPDATED = "payment.updated"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_VOIDED = "payment.voided"
    PAYMENT_CAPTURED = "payment.captured"
    WEBHOOK_RECEIVED = "webhook.received"
    WEBHOOK_DELIVERED = "webhook.delivered"
    WEBHOOK_FAILED = "webhook.failed"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    SYSTEM_ERROR = "system.error"
    SECURITY_VIOLATION = "security.violation"


class AuditLog(Base):
    """
    Audit log model for tracking all system events.
    
    This model provides comprehensive audit trail for all operations
    in the EasyPay system, including payments, webhooks, and security events.
    """
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    action = Column(String(100), nullable=False, index=True)
    level = Column(String(20), nullable=False, default=AuditLogLevel.INFO)
    message = Column(Text, nullable=False)
    
    # Entity information
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(String(255), nullable=True, index=True)
    
    # Payment relationship
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True, index=True)
    
    # User/API information
    user_id = Column(String(255), nullable=True, index=True)
    api_key_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    
    # Request information
    request_id = Column(String(255), nullable=True, index=True)
    correlation_id = Column(String(255), nullable=True, index=True)
    
    # Additional data
    audit_metadata = Column(JSON, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Flags
    is_test = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    payment = relationship("Payment", back_populates="audit_logs")

    # Indexes for performance
    __table_args__ = (
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_level', 'level'),
        Index('idx_audit_logs_entity_type', 'entity_type'),
        Index('idx_audit_logs_entity_id', 'entity_id'),
        Index('idx_audit_logs_payment_id', 'payment_id'),
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_request_id', 'request_id'),
        Index('idx_audit_logs_correlation_id', 'correlation_id'),
        Index('idx_audit_logs_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, level={self.level})>"

    @classmethod
    def create_payment_log(
        cls,
        action: AuditLogAction,
        payment_id: uuid.UUID,
        message: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        level: AuditLogLevel = AuditLogLevel.INFO
    ) -> "AuditLog":
        """Create an audit log entry for a payment-related action."""
        return cls(
            action=action.value,
            level=level.value,
            message=message,
            entity_type="payment",
            entity_id=str(payment_id),
            payment_id=payment_id,
            user_id=user_id,
            api_key_id=api_key_id,
            audit_metadata=metadata,
            old_values=old_values,
            new_values=new_values
        )

    @classmethod
    def create_webhook_log(
        cls,
        action: AuditLogAction,
        webhook_id: uuid.UUID,
        message: str,
        metadata: Optional[dict] = None,
        level: AuditLogLevel = AuditLogLevel.INFO
    ) -> "AuditLog":
        """Create an audit log entry for a webhook-related action."""
        return cls(
            action=action.value,
            level=level.value,
            message=message,
            entity_type="webhook",
            entity_id=str(webhook_id),
            audit_metadata=metadata
        )

    @classmethod
    def create_security_log(
        cls,
        action: AuditLogAction,
        message: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None,
        level: AuditLogLevel = AuditLogLevel.WARNING
    ) -> "AuditLog":
        """Create an audit log entry for a security-related action."""
        return cls(
            action=action.value,
            level=level.value,
            message=message,
            entity_type="security",
            user_id=user_id,
            api_key_id=api_key_id,
            ip_address=ip_address,
            user_agent=user_agent,
            audit_metadata=metadata
        )
