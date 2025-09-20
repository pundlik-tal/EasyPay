"""
EasyPay Payment Gateway - Webhook Model
"""
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, Integer,
    Index, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.database.base import Base


class WebhookStatus(str, Enum):
    """Webhook status enumeration."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


class WebhookEventType(str, Enum):
    """Webhook event type enumeration."""
    PAYMENT_AUTHORIZED = "payment.authorized"
    PAYMENT_CAPTURED = "payment.captured"
    PAYMENT_SETTLED = "payment.settled"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_VOIDED = "payment.voided"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_DECLINED = "payment.declined"
    FRAUD_DETECTED = "fraud.detected"
    CHARGEBACK_CREATED = "chargeback.created"
    DISPUTE_CREATED = "dispute.created"


class Webhook(Base):
    """
    Webhook model for storing webhook delivery information.
    
    This model tracks webhook events from Authorize.net and other sources,
    including delivery status, retry attempts, and event data.
    """
    __tablename__ = "webhooks"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Webhook details
    event_type = Column(String(100), nullable=False, index=True)
    event_id = Column(String(255), nullable=False, unique=True, index=True)
    status = Column(String(50), nullable=False, default=WebhookStatus.PENDING)
    
    # Payment relationship
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True, index=True)
    
    # Delivery information
    url = Column(Text, nullable=False)
    headers = Column(JSON, nullable=True)
    payload = Column(JSON, nullable=False)
    
    # Response information
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSON, nullable=True)
    
    # Retry information
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    next_retry_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # Flags
    is_test = Column(Boolean, nullable=False, default=False)
    signature_verified = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    payment = relationship("Payment", back_populates="webhooks")

    # Indexes for performance
    __table_args__ = (
        Index('idx_webhooks_event_type', 'event_type'),
        Index('idx_webhooks_status', 'status'),
        Index('idx_webhooks_payment_id', 'payment_id'),
        Index('idx_webhooks_created_at', 'created_at'),
        Index('idx_webhooks_next_retry_at', 'next_retry_at'),
    )

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, event_type={self.event_type}, status={self.status})>"

    @property
    def can_retry(self) -> bool:
        """Check if webhook can be retried."""
        return (
            self.status in [WebhookStatus.FAILED, WebhookStatus.RETRYING] and
            self.retry_count < self.max_retries
        )

    @property
    def is_expired(self) -> bool:
        """Check if webhook has expired."""
        return (
            self.status == WebhookStatus.FAILED and
            self.retry_count >= self.max_retries
        )

    def mark_as_delivered(self, response_status_code: int, response_body: str, response_headers: dict) -> None:
        """Mark webhook as successfully delivered."""
        self.status = WebhookStatus.DELIVERED
        self.response_status_code = response_status_code
        self.response_body = response_body
        self.response_headers = response_headers
        self.delivered_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_as_failed(self, response_status_code: Optional[int] = None, response_body: Optional[str] = None) -> None:
        """Mark webhook as failed."""
        self.status = WebhookStatus.FAILED
        self.response_status_code = response_status_code
        self.response_body = response_body
        self.failed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def schedule_retry(self, retry_delay_minutes: int = 5) -> None:
        """Schedule webhook for retry."""
        self.status = WebhookStatus.RETRYING
        self.retry_count += 1
        self.next_retry_at = datetime.utcnow() + timedelta(minutes=retry_delay_minutes)
        self.updated_at = datetime.utcnow()
