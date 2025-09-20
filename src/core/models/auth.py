"""
EasyPay Payment Gateway - Authentication Models
"""
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, Integer,
    Index, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.db_components.base import Base


class APIKeyStatus(str, Enum):
    """API Key status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class TokenType(str, Enum):
    """Token type enumeration."""
    ACCESS = "access"
    REFRESH = "refresh"


class Permission(str, Enum):
    """Permission enumeration."""
    PAYMENTS_READ = "payments:read"
    PAYMENTS_WRITE = "payments:write"
    PAYMENTS_DELETE = "payments:delete"
    WEBHOOKS_READ = "webhooks:read"
    WEBHOOKS_WRITE = "webhooks:write"
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"


class APIKey(Base):
    """
    API Key model for authentication.
    
    This model represents an API key in the EasyPay system,
    including permissions, usage tracking, and security features.
    """
    __tablename__ = "api_keys"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # API Key details
    key_id = Column(String(50), unique=True, nullable=False, index=True)
    key_secret_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status and permissions
    status = Column(String(50), nullable=False, default=APIKeyStatus.ACTIVE)
    permissions = Column(JSON, nullable=False, default=list)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    rate_limit_per_minute = Column(Integer, nullable=False, default=100)
    rate_limit_per_hour = Column(Integer, nullable=False, default=1000)
    rate_limit_per_day = Column(Integer, nullable=False, default=10000)
    
    # Security features
    ip_whitelist = Column(JSON, nullable=True)  # List of allowed IP addresses
    ip_blacklist = Column(JSON, nullable=True)  # List of blocked IP addresses
    user_agent_patterns = Column(JSON, nullable=True)  # Allowed user agent patterns
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # RBAC integration
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    # Temporarily comment out role relationship to isolate the issue
    # role = relationship("src.core.models.rbac.Role", back_populates="api_keys")
    
    # Relationships - temporarily disabled to fix database initialization
    # tokens = relationship("AuthToken", back_populates="api_key")
    # audit_logs = relationship("AuditLog", back_populates="api_key")
    # resource_access = relationship("ResourceAccess", back_populates="api_key")
    # security_events = relationship("SecurityEvent", back_populates="api_key")
    scopes = relationship("APIKeyScope", back_populates="api_key")

    # Indexes for performance
    __table_args__ = (
        Index('idx_api_keys_key_id', 'key_id'),
        Index('idx_api_keys_status', 'status'),
        Index('idx_api_keys_role_id', 'role_id'),
        Index('idx_api_keys_created_at', 'created_at'),
        Index('idx_api_keys_expires_at', 'expires_at'),
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, key_id={self.key_id}, name={self.name}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if API key is active."""
        return self.status == APIKeyStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def has_permission(self, permission: Permission) -> bool:
        """Check if API key has specific permission."""
        return permission.value in self.permissions

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if API key has any of the specified permissions."""
        return any(self.has_permission(perm) for perm in permissions)


class AuthToken(Base):
    """
    Authentication token model for JWT tokens.
    
    This model represents JWT tokens in the EasyPay system,
    including access and refresh tokens with expiration tracking.
    """
    __tablename__ = "auth_tokens"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Token details
    token_id = Column(String(50), unique=True, nullable=False, index=True)
    token_type = Column(String(50), nullable=False)
    jti = Column(String(255), unique=True, nullable=False, index=True)  # JWT ID
    
    # Relationships - temporarily disabled
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    # api_key = relationship("APIKey", back_populates="tokens")
    
    # Token payload (for validation)
    subject = Column(String(255), nullable=False)  # Usually the API key ID
    audience = Column(String(255), nullable=True)
    issuer = Column(String(255), nullable=False, default="easypay")
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    
    # Status
    is_revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for performance
    __table_args__ = (
        Index('idx_auth_tokens_token_id', 'token_id'),
        Index('idx_auth_tokens_jti', 'jti'),
        Index('idx_auth_tokens_api_key_id', 'api_key_id'),
        Index('idx_auth_tokens_expires_at', 'expires_at'),
        Index('idx_auth_tokens_subject', 'subject'),
    )

    def __repr__(self) -> str:
        return f"<AuthToken(id={self.id}, token_id={self.token_id}, type={self.token_type}, expires_at={self.expires_at})>"

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired

    @property
    def time_until_expiry(self) -> timedelta:
        """Get time until token expires."""
        if self.expires_at:
            return self.expires_at - datetime.utcnow()
        return timedelta(0)


class User(Base):
    """
    User model for future user management.
    
    This model represents a user in the EasyPay system,
    for future implementation of user-based authentication.
    """
    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User details
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile information
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    
    # Security
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    roles = relationship("src.core.models.rbac.Role", secondary="user_roles", back_populates="users")
    security_events = relationship("src.core.models.rbac.SecurityEvent", back_populates="user")

    # Indexes for performance
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
        Index('idx_users_is_active', 'is_active'),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
