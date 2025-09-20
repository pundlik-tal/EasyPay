"""
EasyPay Payment Gateway - Configuration Management
"""
import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "EasyPay Payment Gateway"
    VERSION: str = "0.1.0"
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://easypay:password@localhost:5432/easypay",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(default=10, env="REDIS_POOL_SIZE")
    
    # Authorize.net Configuration
    AUTHORIZE_NET_API_LOGIN_ID: str = Field(
        default="", 
        env="AUTHORIZE_NET_API_LOGIN_ID",
        description="Authorize.net API Login ID"
    )
    AUTHORIZE_NET_TRANSACTION_KEY: str = Field(
        default="", 
        env="AUTHORIZE_NET_TRANSACTION_KEY",
        description="Authorize.net Transaction Key"
    )
    AUTHORIZE_NET_SANDBOX: bool = Field(
        default=True, 
        env="AUTHORIZE_NET_SANDBOX",
        description="Use Authorize.net sandbox environment"
    )
    AUTHORIZE_NET_API_URL: str = Field(
        default="https://apitest.authorize.net/xml/v1/request.api",
        env="AUTHORIZE_NET_API_URL"
    )
    AUTHORIZE_NET_WEBHOOK_SECRET: str = Field(
        default="your-authorize-net-webhook-secret-here",
        env="AUTHORIZE_NET_WEBHOOK_SECRET",
        description="Secret key for Authorize.net webhook signature verification"
    )
    
    # Security
    ALLOWED_HOSTS: List[str] = Field(default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    
    # Payment Settings
    DEFAULT_CURRENCY: str = "USD"
    SUPPORTED_CURRENCIES: List[str] = ["USD", "EUR", "GBP", "CAD"]
    
    # Fraud Detection
    FRAUD_THRESHOLD: float = 0.8
    MAX_DAILY_TRANSACTIONS: int = 1000
    
    # Webhook Settings
    WEBHOOK_SECRET: str = Field(
        default="your-webhook-secret-here", 
        env="WEBHOOK_SECRET",
        description="Secret key for webhook signature verification"
    )
    WEBHOOK_MAX_RETRIES: int = Field(default=3, env="WEBHOOK_MAX_RETRIES")
    WEBHOOK_RETRY_INTERVAL: int = Field(default=60, env="WEBHOOK_RETRY_INTERVAL")
    WEBHOOK_TIMEOUT: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables
        
    def get_authorize_net_url(self) -> str:
        """Get the appropriate Authorize.net API URL based on environment."""
        if self.AUTHORIZE_NET_SANDBOX:
            return "https://apitest.authorize.net/xml/v1/request.api"
        return "https://api.authorize.net/xml/v1/request.api"


# Global settings instance
settings = Settings()
