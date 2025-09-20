"""
EasyPay Payment Gateway - API Versioning Schemas
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    V2 = "v2"  # Future version


class VersionInfo(BaseModel):
    """API version information."""
    version: str = Field(..., description="API version")
    status: str = Field(..., description="Version status (stable, deprecated, beta)")
    release_date: datetime = Field(..., description="Version release date")
    deprecation_date: Optional[datetime] = Field(None, description="Deprecation date")
    sunset_date: Optional[datetime] = Field(None, description="Sunset date")
    changelog_url: Optional[str] = Field(None, description="Changelog URL")
    migration_guide_url: Optional[str] = Field(None, description="Migration guide URL")


class VersionResponse(BaseModel):
    """Response schema for API version information."""
    model_config = {
        "json_schema_extra": {
            "example": {
                "current_version": "v1",
                "supported_versions": [
                    {
                        "version": "v1",
                        "status": "stable",
                        "release_date": "2024-01-01T00:00:00Z",
                        "deprecation_date": None,
                        "sunset_date": None,
                        "changelog_url": "https://docs.easypay.com/changelog/v1",
                        "migration_guide_url": None
                    }
                ],
                "deprecated_versions": [],
                "beta_versions": []
            }
        }
    }
    
    current_version: str = Field(..., description="Current API version")
    supported_versions: List[VersionInfo] = Field(..., description="List of supported versions")
    deprecated_versions: List[VersionInfo] = Field(default_factory=list, description="List of deprecated versions")
    beta_versions: List[VersionInfo] = Field(default_factory=list, description="List of beta versions")


class VersionHeader(BaseModel):
    """API version header information."""
    version: str = Field(..., description="Requested API version")
    client_name: Optional[str] = Field(None, description="Client application name")
    client_version: Optional[str] = Field(None, description="Client application version")


# API Version Configuration
API_VERSIONS = {
    "v1": {
        "status": "stable",
        "release_date": "2024-01-01T00:00:00Z",
        "deprecation_date": None,
        "sunset_date": None,
        "changelog_url": "https://docs.easypay.com/changelog/v1",
        "migration_guide_url": None,
        "features": [
            "Payment processing",
            "Authentication with API keys",
            "JWT token support",
            "Webhook handling",
            "Rate limiting",
            "Health checks"
        ],
        "endpoints": {
            "payments": [
                "POST /api/v1/payments",
                "GET /api/v1/payments/{id}",
                "GET /api/v1/payments",
                "PUT /api/v1/payments/{id}",
                "POST /api/v1/payments/{id}/refund",
                "POST /api/v1/payments/{id}/cancel",
                "POST /api/v1/payments/search"
            ],
            "authentication": [
                "POST /api/v1/auth/api-keys",
                "GET /api/v1/auth/api-keys",
                "GET /api/v1/auth/api-keys/{id}",
                "PUT /api/v1/auth/api-keys/{id}",
                "DELETE /api/v1/auth/api-keys/{id}",
                "POST /api/v1/auth/tokens",
                "POST /api/v1/auth/tokens/refresh",
                "POST /api/v1/auth/tokens/validate",
                "POST /api/v1/auth/tokens/revoke"
            ],
            "health": [
                "GET /health",
                "GET /health/ready",
                "GET /health/live",
                "GET /health/detailed"
            ]
        }
    }
}

# Version-specific configurations
VERSION_CONFIGS = {
    "v1": {
        "default_page_size": 20,
        "max_page_size": 100,
        "max_request_size": "10MB",
        "rate_limits": {
            "default_per_minute": 100,
            "default_per_hour": 1000,
            "default_per_day": 10000
        },
        "supported_currencies": ["USD", "EUR", "GBP", "CAD", "AUD"],
        "supported_payment_methods": ["credit_card", "debit_card"],
        "webhook_retry_attempts": 3,
        "webhook_timeout": 30
    }
}
