"""
EasyPay Payment Gateway - Authentication Schemas
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class APIKeyCreateRequest(BaseModel):
    """Request schema for creating API keys."""
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Basic API Key",
                    "description": "A basic API key with standard permissions",
                    "value": {
                        "name": "Production API Key",
                        "description": "API key for production payment processing",
                        "permissions": ["payments:read", "payments:write"],
                        "rate_limit_per_minute": 100,
                        "rate_limit_per_hour": 1000,
                        "rate_limit_per_day": 10000
                    }
                },
                {
                    "summary": "Admin API Key",
                    "description": "An admin API key with full permissions",
                    "value": {
                        "name": "Admin API Key",
                        "description": "Full administrative access API key",
                        "permissions": [
                            "payments:read", "payments:write", "payments:delete",
                            "webhooks:read", "webhooks:write",
                            "admin:read", "admin:write"
                        ],
                        "expires_at": "2024-12-31T23:59:59Z",
                        "rate_limit_per_minute": 1000,
                        "rate_limit_per_hour": 10000,
                        "rate_limit_per_day": 100000,
                        "ip_whitelist": ["192.168.1.0/24", "10.0.0.0/8"]
                    }
                },
                {
                    "summary": "Read-Only API Key",
                    "description": "A read-only API key for monitoring",
                    "value": {
                        "name": "Monitoring API Key",
                        "description": "Read-only access for monitoring and reporting",
                        "permissions": ["payments:read", "webhooks:read"],
                        "rate_limit_per_minute": 50,
                        "rate_limit_per_hour": 500,
                        "rate_limit_per_day": 5000,
                        "expires_at": "2024-06-30T23:59:59Z"
                    }
                }
            ]
        }
    }
    
    name: str = Field(..., min_length=1, max_length=255, description="API key name")
    description: Optional[str] = Field(None, max_length=1000, description="API key description")
    permissions: List[str] = Field(default_factory=list, description="List of permissions")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    rate_limit_per_minute: int = Field(100, ge=1, le=10000, description="Rate limit per minute")
    rate_limit_per_hour: int = Field(1000, ge=1, le=100000, description="Rate limit per hour")
    rate_limit_per_day: int = Field(10000, ge=1, le=1000000, description="Rate limit per day")
    ip_whitelist: Optional[List[str]] = Field(None, description="Allowed IP addresses")
    ip_blacklist: Optional[List[str]] = Field(None, description="Blocked IP addresses")

    @validator('permissions')
    def validate_permissions(cls, v):
        """Validate permissions list."""
        valid_permissions = [
            "payments:read", "payments:write", "payments:delete",
            "webhooks:read", "webhooks:write",
            "admin:read", "admin:write"
        ]
        for permission in v:
            if permission not in valid_permissions:
                raise ValueError(f"Invalid permission: {permission}")
        return v

    @validator('expires_at')
    def validate_expires_at(cls, v):
        """Validate expiration date is in the future."""
        if v and v <= datetime.utcnow():
            raise ValueError("Expiration date must be in the future")
        return v


class APIKeyUpdateRequest(BaseModel):
    """Request schema for updating API keys."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="API key name")
    description: Optional[str] = Field(None, max_length=1000, description="API key description")
    permissions: Optional[List[str]] = Field(None, description="List of permissions")
    status: Optional[str] = Field(None, description="API key status")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000, description="Rate limit per minute")
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=100000, description="Rate limit per hour")
    rate_limit_per_day: Optional[int] = Field(None, ge=1, le=1000000, description="Rate limit per day")
    ip_whitelist: Optional[List[str]] = Field(None, description="Allowed IP addresses")
    ip_blacklist: Optional[List[str]] = Field(None, description="Blocked IP addresses")

    @validator('permissions')
    def validate_permissions(cls, v):
        """Validate permissions list."""
        if v is None:
            return v
        valid_permissions = [
            "payments:read", "payments:write", "payments:delete",
            "webhooks:read", "webhooks:write",
            "admin:read", "admin:write"
        ]
        for permission in v:
            if permission not in valid_permissions:
                raise ValueError(f"Invalid permission: {permission}")
        return v

    @validator('status')
    def validate_status(cls, v):
        """Validate status."""
        if v is None:
            return v
        valid_statuses = ["active", "inactive", "suspended", "expired"]
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}")
        return v

    @validator('expires_at')
    def validate_expires_at(cls, v):
        """Validate expiration date is in the future."""
        if v and v <= datetime.utcnow():
            raise ValueError("Expiration date must be in the future")
        return v


class APIKeyResponse(BaseModel):
    """Response schema for API key information."""
    id: UUID
    key_id: str
    name: str
    description: Optional[str]
    status: str
    permissions: List[str]
    usage_count: int
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    ip_whitelist: Optional[List[str]]
    ip_blacklist: Optional[List[str]]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Response schema for API key creation."""
    id: UUID
    key_id: str
    key_secret: str
    name: str
    description: Optional[str]
    permissions: List[str]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Response schema for API key list."""
    api_keys: List[APIKeyResponse]
    total: int
    page: int
    per_page: int


class TokenRequest(BaseModel):
    """Request schema for token generation."""
    api_key_id: str = Field(..., description="API key ID")
    api_key_secret: str = Field(..., description="API key secret")
    expires_in: Optional[int] = Field(3600, ge=300, le=86400, description="Token expiration in seconds")


class TokenResponse(BaseModel):
    """Response schema for token generation."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    expires_at: datetime


class TokenRefreshRequest(BaseModel):
    """Request schema for token refresh."""
    refresh_token: str = Field(..., description="Refresh token")


class TokenRefreshResponse(BaseModel):
    """Response schema for token refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    expires_at: datetime


class TokenValidationResponse(BaseModel):
    """Response schema for token validation."""
    valid: bool
    token_id: Optional[str]
    api_key_id: Optional[str]
    permissions: Optional[List[str]]
    expires_at: Optional[datetime]
    error: Optional[str]


class AuthErrorResponse(BaseModel):
    """Response schema for authentication errors."""
    error: str
    error_description: str
    error_code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PermissionCheckRequest(BaseModel):
    """Request schema for permission checking."""
    permission: str = Field(..., description="Permission to check")


class PermissionCheckResponse(BaseModel):
    """Response schema for permission checking."""
    has_permission: bool
    permission: str
    api_key_id: Optional[str]
