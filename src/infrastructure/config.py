"""
EasyPay Payment Gateway - Configuration Management
"""
import os
import secrets
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = Field(default="EasyPay Payment Gateway", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_environment: str = Field(default="development", env="APP_ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # API
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")
    
    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_hex(32), env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    
    # Database
    database_url: str = Field(default="postgresql://easypay:password@localhost:5432/easypay", env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_timeout: int = Field(default=30, env="DATABASE_TIMEOUT")
    
    # Redis Cache
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_timeout: int = Field(default=5, env="REDIS_TIMEOUT")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    
    # Authorize.Net
    authorize_net_api_login_id: str = Field(default="", env="AUTHORIZE_NET_API_LOGIN_ID")
    authorize_net_transaction_key: str = Field(default="", env="AUTHORIZE_NET_TRANSACTION_KEY")
    authorize_net_environment: str = Field(default="sandbox", env="AUTHORIZE_NET_ENVIRONMENT")
    authorize_net_timeout: int = Field(default=30, env="AUTHORIZE_NET_TIMEOUT")
    
    # Webhooks
    webhook_secret: str = Field(default_factory=lambda: secrets.token_hex(32), env="WEBHOOK_SECRET")
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    webhook_retry_attempts: int = Field(default=3, env="WEBHOOK_RETRY_ATTEMPTS")
    webhook_retry_delay: int = Field(default=60, env="WEBHOOK_RETRY_DELAY")  # seconds
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")  # seconds
    
    # Performance
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    max_request_size: int = Field(default=1048576, env="MAX_REQUEST_SIZE")  # 1MB
    worker_processes: int = Field(default=1, env="WORKER_PROCESSES")
    
    # Features
    feature_payment_validation: bool = Field(default=True, env="FEATURE_PAYMENT_VALIDATION")
    feature_fraud_detection: bool = Field(default=True, env="FEATURE_FRAUD_DETECTION")
    feature_audit_logging: bool = Field(default=True, env="FEATURE_AUDIT_LOGGING")
    feature_analytics: bool = Field(default=True, env="FEATURE_ANALYTICS")
    
    # External Services
    external_service_timeout: int = Field(default=30, env="EXTERNAL_SERVICE_TIMEOUT")
    external_service_retries: int = Field(default=3, env="EXTERNAL_SERVICE_RETRIES")
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator('cors_methods', mode='before')
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(',')]
        return v
    
    @field_validator('cors_headers', mode='before')
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(',')]
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {", ".join(valid_levels)}')
        return v.upper()
    
    @field_validator('log_format')
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ['json', 'text']
        if v.lower() not in valid_formats:
            raise ValueError(f'Log format must be one of: {", ".join(valid_formats)}')
        return v.lower()
    
    @field_validator('authorize_net_environment')
    @classmethod
    def validate_authorize_net_environment(cls, v):
        """Validate Authorize.Net environment."""
        valid_environments = ['sandbox', 'production']
        if v.lower() not in valid_environments:
            raise ValueError(f'Authorize.Net environment must be one of: {", ".join(valid_environments)}')
        return v.lower()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_environment.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.app_environment.lower() == "testing"
    
    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def authorize_net_base_url(self) -> str:
        """Get Authorize.Net base URL based on environment."""
        if self.authorize_net_environment == "production":
            return "https://api.authorize.net"
        else:
            return "https://apitest.authorize.net"
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get all feature flags."""
        return {
            "payment_validation": self.feature_payment_validation,
            "fraud_detection": self.feature_fraud_detection,
            "audit_logging": self.feature_audit_logging,
            "analytics": self.feature_analytics,
        }
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration."""
        return {
            "enabled": self.rate_limit_enabled,
            "requests": self.rate_limit_requests,
            "window": self.rate_limit_window,
        }
    
    def get_webhook_config(self) -> Dict[str, Any]:
        """Get webhook configuration."""
        return {
            "secret": self.webhook_secret,
            "timeout": self.webhook_timeout,
            "retry_attempts": self.webhook_retry_attempts,
            "retry_delay": self.webhook_retry_delay,
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration."""
        return {
            "url": self.redis_url,
            "password": self.redis_password,
            "db": self.redis_db,
            "timeout": self.redis_timeout,
            "ttl": self.cache_ttl,
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "url": self.database_url,
            "async_url": self.async_database_url,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow,
            "timeout": self.database_timeout,
        }
    
    def get_authorize_net_config(self) -> Dict[str, Any]:
        """Get Authorize.Net configuration."""
        return {
            "api_login_id": self.authorize_net_api_login_id,
            "transaction_key": self.authorize_net_transaction_key,
            "environment": self.authorize_net_environment,
            "base_url": self.authorize_net_base_url,
            "timeout": self.authorize_net_timeout,
        }
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra environment variables
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Global settings instance
settings = get_settings()
