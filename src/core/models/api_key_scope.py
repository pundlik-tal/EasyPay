"""
EasyPay Payment Gateway - API Key Scope Model
"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, Boolean, Index, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.db_components.base import Base


class ScopeType(str, Enum):
    """Scope type enumeration."""
    ENVIRONMENT = "environment"
    DOMAIN = "domain"
    IP_RANGE = "ip_range"
    TIME_WINDOW = "time_window"
    RESOURCE_LIMIT = "resource_limit"
    FEATURE_FLAG = "feature_flag"


class APIKeyScope(Base):
    """
    API Key Scope model for environment-based access control.
    
    This model represents scoping rules for API keys,
    allowing fine-grained control over where and how API keys can be used.
    """
    __tablename__ = "api_key_scopes"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Scope details
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    scope_type = Column(String(50), nullable=False)
    scope_value = Column(String(500), nullable=False)  # The actual scope value
    scope_config = Column(JSON, nullable=True)  # Additional configuration
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="scopes")

    # Indexes for performance
    __table_args__ = (
        Index('idx_api_key_scopes_api_key', 'api_key_id'),
        Index('idx_api_key_scopes_type', 'scope_type'),
        Index('idx_api_key_scopes_active', 'is_active'),
        Index('idx_api_key_scopes_created', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<APIKeyScope(id={self.id}, type={self.scope_type}, value={self.scope_value})>"
