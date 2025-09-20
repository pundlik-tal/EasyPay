"""
EasyPay Payment Gateway - Role-Based Access Control Models
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, Integer,
    Index, ForeignKey, JSON, UniqueConstraint, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.db_components.base import Base


class RoleStatus(str, Enum):
    """Role status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class ResourceType(str, Enum):
    """Resource type enumeration."""
    PAYMENT = "payment"
    WEBHOOK = "webhook"
    API_KEY = "api_key"
    USER = "user"
    AUDIT_LOG = "audit_log"
    SYSTEM = "system"


class ActionType(str, Enum):
    """Action type enumeration."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"


# Association table for role-permission mapping
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True),
    Column('created_at', DateTime, nullable=False, default=datetime.utcnow)
)

# Association table for user-role mapping (for future user system)
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('created_at', DateTime, nullable=False, default=datetime.utcnow)
)


class Role(Base):
    """
    Role model for RBAC system.
    
    This model represents a role in the EasyPay system,
    which groups permissions together for easier management.
    """
    __tablename__ = "roles"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Role details
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status and metadata
    status = Column(String(50), nullable=False, default=RoleStatus.ACTIVE)
    is_system_role = Column(Boolean, nullable=False, default=False)  # System roles cannot be deleted
    priority = Column(Integer, nullable=False, default=0)  # Higher priority roles override lower ones
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    api_keys = relationship("APIKey", back_populates="role")
    users = relationship("User", secondary=user_roles, back_populates="roles")

    # Indexes for performance
    __table_args__ = (
        Index('idx_roles_name', 'name'),
        Index('idx_roles_status', 'status'),
        Index('idx_roles_priority', 'priority'),
        Index('idx_roles_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if role is active."""
        return self.status == RoleStatus.ACTIVE

    def has_permission(self, permission_name: str) -> bool:
        """Check if role has specific permission."""
        return any(perm.name == permission_name for perm in self.permissions)

    def get_permission_names(self) -> List[str]:
        """Get list of permission names for this role."""
        return [perm.name for perm in self.permissions]


class Permission(Base):
    """
    Permission model for RBAC system.
    
    This model represents a permission in the EasyPay system,
    which defines what actions can be performed on what resources.
    """
    __tablename__ = "permissions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Permission details
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Permission structure
    resource_type = Column(String(50), nullable=False)  # What resource this applies to
    action_type = Column(String(50), nullable=False)   # What action can be performed
    resource_pattern = Column(String(255), nullable=True)  # Pattern for resource matching (e.g., "payment:*", "webhook:123")
    
    # Metadata
    is_system_permission = Column(Boolean, nullable=False, default=False)
    category = Column(String(100), nullable=True)  # Group permissions by category
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    # Indexes for performance
    __table_args__ = (
        Index('idx_permissions_name', 'name'),
        Index('idx_permissions_resource_type', 'resource_type'),
        Index('idx_permissions_action_type', 'action_type'),
        Index('idx_permissions_category', 'category'),
        Index('idx_permissions_created_at', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name}, resource={self.resource_type}, action={self.action_type})>"

    def matches_resource(self, resource_id: str) -> bool:
        """
        Check if this permission matches a specific resource.
        
        Args:
            resource_id: Resource identifier to check
            
        Returns:
            True if permission matches the resource
        """
        if not self.resource_pattern:
            return True  # No pattern means it applies to all resources of this type
        
        # Simple pattern matching (can be enhanced with regex)
        if "*" in self.resource_pattern:
            pattern = self.resource_pattern.replace("*", "")
            return resource_id.startswith(pattern)
        
        return self.resource_pattern == resource_id

    @property
    def full_name(self) -> str:
        """Get full permission name in format 'resource:action'."""
        return f"{self.resource_type}:{self.action_type}"


class ResourceAccess(Base):
    """
    Resource access model for fine-grained access control.
    
    This model represents specific access permissions for individual resources,
    allowing for more granular control than role-based permissions alone.
    """
    __tablename__ = "resource_access"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Resource identification
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255), nullable=False)
    
    # Access control
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    
    # Permissions for this specific resource
    allowed_actions = Column(JSON, nullable=False, default=list)
    denied_actions = Column(JSON, nullable=False, default=list)
    
    # Access conditions
    conditions = Column(JSON, nullable=True)  # Additional conditions (IP, time, etc.)
    expires_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="resource_access")
    role = relationship("Role")

    # Indexes for performance
    __table_args__ = (
        Index('idx_resource_access_resource', 'resource_type', 'resource_id'),
        Index('idx_resource_access_api_key', 'api_key_id'),
        Index('idx_resource_access_role', 'role_id'),
        Index('idx_resource_access_active', 'is_active'),
        Index('idx_resource_access_expires', 'expires_at'),
        UniqueConstraint('resource_type', 'resource_id', 'api_key_id', name='unique_resource_api_key_access'),
    )

    def __repr__(self) -> str:
        return f"<ResourceAccess(id={self.id}, resource={self.resource_type}:{self.resource_id}, api_key={self.api_key_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if access has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if access is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def can_perform_action(self, action: str) -> bool:
        """
        Check if this access allows performing a specific action.
        
        Args:
            action: Action to check
            
        Returns:
            True if action is allowed
        """
        if not self.is_valid:
            return False
        
        # Check if action is explicitly denied
        if action in self.denied_actions:
            return False
        
        # Check if action is explicitly allowed
        if action in self.allowed_actions:
            return True
        
        # If no explicit permissions, deny by default
        return False


class SecurityEvent(Base):
    """
    Security event model for audit logging.
    
    This model represents security-related events in the EasyPay system,
    including authentication attempts, authorization failures, and security violations.
    """
    __tablename__ = "security_events"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False)  # auth, authorization, security, etc.
    severity = Column(String(20), nullable=False, default="info")  # info, warning, error, critical
    
    # Context
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(255), nullable=True)
    
    # Event data
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    
    # Resource context
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(255), nullable=True)
    action_attempted = Column(String(50), nullable=True)
    
    # Result
    success = Column(Boolean, nullable=False, default=True)
    failure_reason = Column(String(255), nullable=True)
    
    # Timestamps
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    api_key = relationship("APIKey", back_populates="security_events")
    user = relationship("User", back_populates="security_events")

    # Indexes for performance
    __table_args__ = (
        Index('idx_security_events_type', 'event_type'),
        Index('idx_security_events_category', 'event_category'),
        Index('idx_security_events_severity', 'severity'),
        Index('idx_security_events_api_key', 'api_key_id'),
        Index('idx_security_events_user', 'user_id'),
        Index('idx_security_events_ip', 'ip_address'),
        Index('idx_security_events_resource', 'resource_type', 'resource_id'),
        Index('idx_security_events_success', 'success'),
        Index('idx_security_events_occurred', 'occurred_at'),
    )

    def __repr__(self) -> str:
        return f"<SecurityEvent(id={self.id}, type={self.event_type}, severity={self.severity}, success={self.success})>"

    @property
    def is_critical(self) -> bool:
        """Check if event is critical."""
        return self.severity == "critical"

    @property
    def is_failure(self) -> bool:
        """Check if event represents a failure."""
        return not self.success
