"""
EasyPay Payment Gateway - Payment Model
"""
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, Numeric, Text, Boolean, 
    Index, ForeignKey, JSON, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.database import Base


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    SETTLED = "settled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    VOIDED = "voided"
    FAILED = "failed"
    DECLINED = "declined"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"


class Payment(Base):
    """
    Payment model for storing payment transaction data.
    
    This model represents a payment transaction in the EasyPay system,
    including all necessary fields for processing, tracking, and auditing.
    """
    __tablename__ = "payments"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # External identifiers
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    authorize_net_transaction_id = Column(String(255), nullable=True, index=True)
    
    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(50), nullable=False, default=PaymentStatus.PENDING)
    payment_method = Column(String(50), nullable=False)
    
    # Customer information
    customer_id = Column(String(255), nullable=True, index=True)
    customer_email = Column(String(255), nullable=True)
    customer_name = Column(String(255), nullable=True)
    
    # Card information (tokenized)
    card_token = Column(String(255), nullable=True)
    card_last_four = Column(String(4), nullable=True)
    card_brand = Column(String(50), nullable=True)
    card_exp_month = Column(String(2), nullable=True)
    card_exp_year = Column(String(4), nullable=True)
    
    # Transaction details
    description = Column(Text, nullable=True)
    payment_metadata = Column(JSON, nullable=True)
    
    # Processing information
    processor_response_code = Column(String(50), nullable=True)
    processor_response_message = Column(Text, nullable=True)
    processor_transaction_id = Column(String(255), nullable=True)
    
    # Refund information
    refunded_amount = Column(Numeric(10, 2), nullable=True, default=0)
    refund_count = Column(Integer, nullable=True, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    settled_at = Column(DateTime, nullable=True)
    
    # Flags
    is_test = Column(Boolean, nullable=False, default=False)
    is_live = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    webhooks = relationship("Webhook", back_populates="payment")
    audit_logs = relationship("AuditLog", back_populates="payment")

    # Indexes for performance
    __table_args__ = (
        Index('idx_payments_customer_id', 'customer_id'),
        Index('idx_payments_status', 'status'),
        Index('idx_payments_created_at', 'created_at'),
        Index('idx_payments_external_id', 'external_id'),
        Index('idx_payments_authorize_net_id', 'authorize_net_transaction_id'),
    )

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, external_id={self.external_id}, amount={self.amount}, status={self.status})>"

    @property
    def is_refundable(self) -> bool:
        """Check if payment can be refunded."""
        return self.status in [PaymentStatus.CAPTURED, PaymentStatus.SETTLED]

    @property
    def is_voidable(self) -> bool:
        """Check if payment can be voided."""
        return self.status in [PaymentStatus.PENDING, PaymentStatus.AUTHORIZED]

    @property
    def remaining_refund_amount(self) -> Decimal:
        """Calculate remaining amount that can be refunded."""
        if self.refunded_amount is None:
            return self.amount
        return self.amount - self.refunded_amount
