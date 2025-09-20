"""
EasyPay Payment Gateway - Common API Schemas
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    error: str = Field(default="validation_error", description="Error type")
    message: str = Field(..., description="Validation error message")
    field_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Field-specific errors")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class AuthenticationErrorResponse(BaseModel):
    """Authentication error response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    error: str = Field(default="authentication_error", description="Error type")
    message: str = Field(..., description="Authentication error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class AuthorizationErrorResponse(BaseModel):
    """Authorization error response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    error: str = Field(default="authorization_error", description="Error type")
    message: str = Field(..., description="Authorization error message")
    required_permission: Optional[str] = Field(None, description="Required permission")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class SuccessResponse(BaseModel):
    """Standard success response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    status: str = Field(default="success", description="Response status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class PaginationRequest(BaseModel):
    """Pagination request schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")


class PaginationResponse(BaseModel):
    """Pagination response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class SearchRequest(BaseModel):
    """Search request schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    query: Optional[str] = Field(None, description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    pagination: Optional[PaginationRequest] = Field(None, description="Pagination options")


class SearchResponse(BaseModel):
    """Search response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    results: List[Dict[str, Any]] = Field(..., description="Search results")
    pagination: PaginationResponse = Field(..., description="Pagination information")
    query: Optional[str] = Field(None, description="Original search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")


class AmountResponse(BaseModel):
    """Amount response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    value: Decimal = Field(..., description="Amount value")
    currency: str = Field(..., description="Currency code")
    formatted: Optional[str] = Field(None, description="Formatted amount string")


class MetadataResponse(BaseModel):
    """Metadata response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Creator ID")
    updated_by: Optional[str] = Field(None, description="Last updater ID")
    version: Optional[int] = Field(None, description="Version number")


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Health check timestamp")
    uptime: float = Field(..., description="Uptime in seconds")
    services: Dict[str, Dict[str, Any]] = Field(..., description="Service health statuses")


class ConfigurationResponse(BaseModel):
    """Configuration response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    environment: str = Field(..., description="Environment name")
    debug: bool = Field(..., description="Debug mode status")
    version: str = Field(..., description="Application version")
    features: Dict[str, bool] = Field(..., description="Feature flags")
    limits: Dict[str, Union[int, float]] = Field(..., description="System limits")


class BatchRequest(BaseModel):
    """Batch request schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    operations: List[Dict[str, Any]] = Field(..., min_items=1, max_items=100, description="Batch operations")
    options: Optional[Dict[str, Any]] = Field(None, description="Batch options")


class BatchResponse(BaseModel):
    """Batch response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    results: List[Dict[str, Any]] = Field(..., description="Batch operation results")
    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(..., description="Number of failed operations")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")


class RateLimitResponse(BaseModel):
    """Rate limit response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    limit: int = Field(..., description="Rate limit")
    remaining: int = Field(..., description="Remaining requests")
    reset_time: datetime = Field(..., description="Reset time")
    window: int = Field(..., description="Time window in seconds")


class AuditLogEntry(BaseModel):
    """Audit log entry schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource affected")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    user_id: Optional[str] = Field(None, description="User ID")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    timestamp: datetime = Field(..., description="Action timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
