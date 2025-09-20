"""
EasyPay Payment Gateway - Webhook API Schemas
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, validator, ConfigDict


class WebhookCreateRequest(BaseModel):
    """Request schema for creating a webhook endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com/webhooks/payments",
                "event_types": ["payment.authorized", "payment.captured"],
                "description": "Payment webhook endpoint",
                "metadata": {"environment": "production"}
            }
        }
    )
    
    url: str = Field(..., description="Webhook endpoint URL")
    event_types: List[str] = Field(..., description="List of event types to subscribe to")
    description: Optional[str] = Field(None, description="Webhook description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_test: bool = Field(default=False, description="Test mode flag")

    @validator('url')
    def validate_url(cls, v):
        """Validate webhook URL."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @validator('event_types')
    def validate_event_types(cls, v):
        """Validate event types."""
        valid_events = [
            "payment.authorized",
            "payment.captured", 
            "payment.settled",
            "payment.refunded",
            "payment.voided",
            "payment.failed",
            "payment.declined",
            "fraud.detected",
            "chargeback.created",
            "dispute.created"
        ]
        for event_type in v:
            if event_type not in valid_events:
                raise ValueError(f'Invalid event type: {event_type}')
        return v


class WebhookEventRequest(BaseModel):
    """Request schema for webhook event data."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "payment.authorized",
                "event_id": "evt_123456789",
                "payment_id": "550e8400-e29b-41d4-a716-446655440000",
                "data": {
                    "id": "pay_123456789",
                    "amount": "10.00",
                    "status": "authorized"
                },
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
    )
    
    event_type: str = Field(..., description="Event type")
    event_id: str = Field(..., description="Unique event identifier")
    payment_id: Optional[uuid.UUID] = Field(None, description="Related payment ID")
    data: Dict[str, Any] = Field(..., description="Event data")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Event creation time")
    signature: Optional[str] = Field(None, description="Webhook signature for verification")


class WebhookResponse(BaseModel):
    """Response schema for webhook data."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "event_type": "payment.authorized",
                "event_id": "evt_123456789",
                "status": "delivered",
                "payment_id": "550e8400-e29b-41d4-a716-446655440000",
                "url": "https://example.com/webhooks/payments",
                "retry_count": 0,
                "max_retries": 3,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "delivered_at": "2024-01-01T00:00:00Z",
                "is_test": False,
                "signature_verified": True
            }
        }
    )
    
    id: uuid.UUID
    event_type: str
    event_id: str
    status: str
    payment_id: Optional[uuid.UUID] = None
    url: str
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    is_test: bool
    signature_verified: bool

    @property
    def can_retry(self) -> bool:
        """Check if webhook can be retried."""
        return (
            self.status in ["failed", "retrying"] and
            self.retry_count < self.max_retries
        )

    @property
    def is_expired(self) -> bool:
        """Check if webhook has expired."""
        return (
            self.status == "failed" and
            self.retry_count >= self.max_retries
        )


class WebhookListResponse(BaseModel):
    """Response schema for webhook list."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "webhooks": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "event_type": "payment.authorized",
                        "event_id": "evt_123456789",
                        "status": "delivered",
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
    
    webhooks: List[WebhookResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class WebhookSearchRequest(BaseModel):
    """Request schema for searching webhooks."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "payment.authorized",
                "status": "delivered",
                "payment_id": "550e8400-e29b-41d4-a716-446655440000",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
                "page": 1,
                "per_page": 20
            }
        }
    )
    
    event_type: Optional[str] = Field(None, description="Filter by event type")
    status: Optional[str] = Field(None, description="Filter by webhook status")
    payment_id: Optional[uuid.UUID] = Field(None, description="Filter by payment ID")
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


class WebhookRetryRequest(BaseModel):
    """Request schema for retrying webhook delivery."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "retry_delay_minutes": 5,
                "max_retries": 3
            }
        }
    )
    
    retry_delay_minutes: int = Field(default=5, ge=1, le=60, description="Delay before retry in minutes")
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum number of retries")

