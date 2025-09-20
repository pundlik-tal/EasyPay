"""
EasyPay Payment Gateway - Payment API Schemas
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, validator, ConfigDict


class PaymentCreateRequest(BaseModel):
    """Request schema for creating a new payment."""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Basic Credit Card Payment",
                    "description": "A simple credit card payment with customer information",
                    "value": {
                        "amount": "25.99",
                        "currency": "USD",
                        "payment_method": "credit_card",
                        "customer_id": "cust_123456789",
                        "customer_email": "john.doe@example.com",
                        "customer_name": "John Doe",
                        "card_token": "tok_visa_4242",
                        "description": "Premium subscription payment",
                        "metadata": {
                            "order_id": "order_2024_001",
                            "product": "premium_plan",
                            "subscription_id": "sub_123"
                        },
                        "is_test": True
                    }
                },
                {
                    "summary": "High-Value Payment",
                    "description": "A high-value payment with additional metadata",
                    "value": {
                        "amount": "999.99",
                        "currency": "USD",
                        "payment_method": "credit_card",
                        "customer_id": "cust_enterprise_001",
                        "customer_email": "enterprise@company.com",
                        "customer_name": "Enterprise Customer",
                        "card_token": "tok_amex_1234",
                        "description": "Enterprise license purchase",
                        "metadata": {
                            "order_id": "enterprise_2024_001",
                            "product": "enterprise_license",
                            "license_type": "annual",
                            "seats": 100,
                            "sales_rep": "rep_001"
                        },
                        "is_test": False
                    }
                },
                {
                    "summary": "Subscription Payment",
                    "description": "A recurring subscription payment",
                    "value": {
                        "amount": "9.99",
                        "currency": "USD",
                        "payment_method": "credit_card",
                        "customer_id": "cust_subscriber_001",
                        "customer_email": "subscriber@example.com",
                        "customer_name": "Jane Smith",
                        "card_token": "tok_mastercard_5555",
                        "description": "Monthly subscription renewal",
                        "metadata": {
                            "subscription_id": "sub_monthly_001",
                            "plan": "basic_monthly",
                            "billing_cycle": "monthly",
                            "renewal_date": "2024-02-01"
                        },
                        "is_test": True
                    }
                }
            ]
        }
    )
    
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="USD", max_length=3, description="Currency code")
    payment_method: str = Field(..., description="Payment method")
    customer_id: Optional[str] = Field(None, max_length=255, description="Customer identifier")
    customer_email: Optional[str] = Field(None, max_length=255, description="Customer email")
    customer_name: Optional[str] = Field(None, max_length=255, description="Customer name")
    card_token: Optional[str] = Field(None, max_length=255, description="Tokenized card data")
    description: Optional[str] = Field(None, description="Payment description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_test: bool = Field(default=False, description="Test mode flag")

    @validator('amount')
    def validate_amount(cls, v):
        """Validate payment amount."""
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v > Decimal('999999.99'):
            raise ValueError('Amount cannot exceed 999,999.99')
        return v

    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code."""
        if len(v) != 3:
            raise ValueError('Currency must be a 3-character code')
        return v.upper()


class PaymentUpdateRequest(BaseModel):
    """Request schema for updating a payment."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Updated payment description",
                "metadata": {"updated_field": "new_value"}
            }
        }
    )
    
    description: Optional[str] = Field(None, description="Payment description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PaymentRefundRequest(BaseModel):
    """Request schema for refunding a payment."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "5.00",
                "reason": "Customer requested refund",
                "metadata": {"refund_reason": "customer_request"}
            }
        }
    )
    
    amount: Optional[Decimal] = Field(None, gt=0, description="Refund amount (partial refund)")
    reason: Optional[str] = Field(None, max_length=500, description="Refund reason")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator('amount')
    def validate_amount(cls, v):
        """Validate refund amount."""
        if v is not None and v <= 0:
            raise ValueError('Refund amount must be greater than 0')
        return v


class PaymentCancelRequest(BaseModel):
    """Request schema for canceling a payment."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "Customer requested cancellation",
                "metadata": {"cancel_reason": "customer_request"}
            }
        }
    )
    
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PaymentResponse(BaseModel):
    """Response schema for payment data."""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Successful Payment",
                    "description": "A successfully processed payment",
                    "value": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "external_id": "pay_2024_001",
                        "amount": "25.99",
                        "currency": "USD",
                        "status": "captured",
                        "payment_method": "credit_card",
                        "customer_id": "cust_123456789",
                        "customer_email": "john.doe@example.com",
                        "customer_name": "John Doe",
                        "card_last_four": "4242",
                        "card_brand": "visa",
                        "description": "Premium subscription payment",
                        "metadata": {
                            "order_id": "order_2024_001",
                            "product": "premium_plan",
                            "subscription_id": "sub_123"
                        },
                        "processor_response_code": "1",
                        "processor_response_message": "This transaction has been approved",
                        "processor_transaction_id": "1234567890",
                        "refunded_amount": "0.00",
                        "refund_count": 0,
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:00:05Z",
                        "processed_at": "2024-01-01T12:00:05Z",
                        "settled_at": "2024-01-02T08:00:00Z",
                        "is_test": True
                    }
                },
                {
                    "summary": "Failed Payment",
                    "description": "A payment that failed processing",
                    "value": {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "external_id": "pay_2024_002",
                        "amount": "100.00",
                        "currency": "USD",
                        "status": "failed",
                        "payment_method": "credit_card",
                        "customer_id": "cust_123456790",
                        "customer_email": "jane.smith@example.com",
                        "customer_name": "Jane Smith",
                        "card_last_four": "5555",
                        "card_brand": "mastercard",
                        "description": "Product purchase",
                        "metadata": {
                            "order_id": "order_2024_002",
                            "product": "physical_good"
                        },
                        "processor_response_code": "05",
                        "processor_response_message": "Do not honor",
                        "processor_transaction_id": None,
                        "refunded_amount": None,
                        "refund_count": 0,
                        "created_at": "2024-01-01T12:05:00Z",
                        "updated_at": "2024-01-01T12:05:02Z",
                        "processed_at": "2024-01-01T12:05:02Z",
                        "settled_at": None,
                        "is_test": True
                    }
                },
                {
                    "summary": "Refunded Payment",
                    "description": "A payment that has been partially refunded",
                    "value": {
                        "id": "550e8400-e29b-41d4-a716-446655440002",
                        "external_id": "pay_2024_003",
                        "amount": "50.00",
                        "currency": "USD",
                        "status": "captured",
                        "payment_method": "credit_card",
                        "customer_id": "cust_123456791",
                        "customer_email": "customer@example.com",
                        "customer_name": "Customer Name",
                        "card_last_four": "1234",
                        "card_brand": "amex",
                        "description": "Service payment",
                        "metadata": {
                            "order_id": "order_2024_003",
                            "service": "consulting"
                        },
                        "processor_response_code": "1",
                        "processor_response_message": "This transaction has been approved",
                        "processor_transaction_id": "0987654321",
                        "refunded_amount": "25.00",
                        "refund_count": 1,
                        "created_at": "2024-01-01T12:10:00Z",
                        "updated_at": "2024-01-01T14:30:00Z",
                        "processed_at": "2024-01-01T12:10:05Z",
                        "settled_at": "2024-01-02T08:00:00Z",
                        "is_test": True
                    }
                }
            ]
        }
    )
    
    id: uuid.UUID
    external_id: str
    amount: Decimal
    currency: str
    status: str
    payment_method: str
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    customer_name: Optional[str] = None
    card_last_four: Optional[str] = None
    card_brand: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    processor_response_code: Optional[str] = None
    processor_response_message: Optional[str] = None
    processor_transaction_id: Optional[str] = None
    refunded_amount: Optional[Decimal] = None
    refund_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    is_test: bool

    @property
    def is_refundable(self) -> bool:
        """Check if payment can be refunded."""
        return self.status in ["captured", "settled"]

    @property
    def is_voidable(self) -> bool:
        """Check if payment can be voided."""
        return self.status in ["pending", "authorized"]

    @property
    def remaining_refund_amount(self) -> Decimal:
        """Calculate remaining amount that can be refunded."""
        if self.refunded_amount is None:
            return self.amount
        return self.amount - self.refunded_amount


class PaymentListResponse(BaseModel):
    """Response schema for payment list."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "payments": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "external_id": "pay_123456789",
                        "amount": "10.00",
                        "currency": "USD",
                        "status": "captured",
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "per_page": 20,
                "total_pages": 1
            }
        }
    )
    
    payments: List[PaymentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class PaymentSearchRequest(BaseModel):
    """Request schema for searching payments."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "cust_123456789",
                "status": "captured",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
                "page": 1,
                "per_page": 20
            }
        }
    )
    
    customer_id: Optional[str] = Field(None, description="Filter by customer ID")
    status: Optional[str] = Field(None, description="Filter by payment status")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range."""
        if v is not None and 'start_date' in values and values['start_date'] is not None:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v

