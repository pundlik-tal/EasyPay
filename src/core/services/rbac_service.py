"""
EasyPay Payment Gateway - Role-Based Access Control Service
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import (
    ValidationError,
    DatabaseError,
    NotFoundError,
    AuthorizationError
)
from src.core.models.rbac import (
    Role, Permission, ResourceAccess, SecurityEvent,
    RoleStatus, ResourceType, ActionType
)
from src.core.models.auth import APIKey


class RBACService:
    """
    Role-Based Access Control service for managing roles, permissions,
    and resource access in the EasyPay system.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize RBAC service."""
        self.db = db
    
    # Role Management
    async def create_role(
        self,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        is_system_role: bool = False,
        priority: int = 0
    ) -> Role:
        """
        Create a new role.
        
        Args:
            name: Role name (unique identifier)
            display_name: Human-readable role name
            description: Role description
            permissions: List of permission names to assign
            is_system_role: Whether this is a system role
            priority: Role priority (higher = more important)
            
        Returns:
            Created Role object
            
        Raises:
            ValidationError: If role data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Validate role name
            if not name or len(name) < 3:
                raise ValidationError("Role name must be at least 3 characters long")
            
            # Check if role already exists
            existing_role = await self.get_role_by_name(name)
            if existing_role:
                raise ValidationError(f"Role '{name}' already exists")
            
            # Create role
            role = Role(
                name=name,
                display_name=display_name,
                description=description,
                is_system_role=is_system_role,
                priority=priority,
                status=RoleStatus.ACTIVE
            )
            
            self.db.add(role)
            await self.db.commit()
            await self.db.refresh(role)
            
            # Assign permissions if provided
            if permissions:
                await self.assign_permissions_to_role(role.id, permissions)
                await self.db.refresh(role)
            
            return role
            
        except ValidationError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to create role: {str(e)}")
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        try:
            result = await self.db.execute(
                select(Role).where(Role.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get role: {str(e)}")
    
    async def get_role_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        try:
            result = await self.db.execute(
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.id == role_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get role: {str(e)}")
    
    async def list_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        include_system: bool = False
    ) -> List[Role]:
        """List roles with pagination and filtering."""
        try:
            query = select(Role).options(selectinload(Role.permissions))
            
            if status:
                query = query.where(Role.status == status)
            
            if not include_system:
                query = query.where(Role.is_system_role == False)
            
            query = query.offset(skip).limit(limit).order_by(Role.priority.desc(), Role.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseError(f"Failed to list roles: {str(e)}")
    
    async def update_role(
        self,
        role_id: UUID,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None
    ) -> Role:
        """Update role."""
        try:
            role = await self.get_role_by_id(role_id)
            if not role:
                raise NotFoundError("Role not found")
            
            if role.is_system_role:
                raise ValidationError("Cannot modify system roles")
            
            update_data = {}
            if display_name is not None:
                update_data["display_name"] = display_name
            if description is not None:
                update_data["description"] = description
            if status is not None:
                update_data["status"] = status
            if priority is not None:
                update_data["priority"] = priority
            
            if update_data:
                update_data["updated_at"] = datetime.utcnow()
                await self.db.execute(
                    update(Role)
                    .where(Role.id == role_id)
                    .values(**update_data)
                )
                await self.db.commit()
                await self.db.refresh(role)
            
            return role
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to update role: {str(e)}")
    
    async def delete_role(self, role_id: UUID) -> bool:
        """Delete role (only non-system roles)."""
        try:
            role = await self.get_role_by_id(role_id)
            if not role:
                raise NotFoundError("Role not found")
            
            if role.is_system_role:
                raise ValidationError("Cannot delete system roles")
            
            # Check if role is assigned to any API keys
            api_keys_count = await self.db.execute(
                select(APIKey).where(APIKey.role_id == role_id)
            )
            if api_keys_count.scalar():
                raise ValidationError("Cannot delete role that is assigned to API keys")
            
            await self.db.execute(delete(Role).where(Role.id == role_id))
            await self.db.commit()
            
            return True
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to delete role: {str(e)}")
    
    # Permission Management
    async def create_permission(
        self,
        name: str,
        display_name: str,
        resource_type: str,
        action_type: str,
        description: Optional[str] = None,
        resource_pattern: Optional[str] = None,
        category: Optional[str] = None,
        is_system_permission: bool = False
    ) -> Permission:
        """Create a new permission."""
        try:
            # Validate permission data
            if not name or len(name) < 3:
                raise ValidationError("Permission name must be at least 3 characters long")
            
            # Check if permission already exists
            existing_permission = await self.get_permission_by_name(name)
            if existing_permission:
                raise ValidationError(f"Permission '{name}' already exists")
            
            # Create permission
            permission = Permission(
                name=name,
                display_name=display_name,
                resource_type=resource_type,
                action_type=action_type,
                description=description,
                resource_pattern=resource_pattern,
                category=category,
                is_system_permission=is_system_permission
            )
            
            self.db.add(permission)
            await self.db.commit()
            await self.db.refresh(permission)
            
            return permission
            
        except ValidationError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to create permission: {str(e)}")
    
    async def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name."""
        try:
            result = await self.db.execute(
                select(Permission).where(Permission.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get permission: {str(e)}")
    
    async def get_permission_by_id(self, permission_id: UUID) -> Optional[Permission]:
        """Get permission by ID."""
        try:
            result = await self.db.execute(
                select(Permission).where(Permission.id == permission_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get permission: {str(e)}")
    
    async def list_permissions(
        self,
        skip: int = 0,
        limit: int = 100,
        resource_type: Optional[str] = None,
        category: Optional[str] = None,
        include_system: bool = False
    ) -> List[Permission]:
        """List permissions with pagination and filtering."""
        try:
            query = select(Permission)
            
            if resource_type:
                query = query.where(Permission.resource_type == resource_type)
            
            if category:
                query = query.where(Permission.category == category)
            
            if not include_system:
                query = query.where(Permission.is_system_permission == False)
            
            query = query.offset(skip).limit(limit).order_by(Permission.category, Permission.name)
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseError(f"Failed to list permissions: {str(e)}")
    
    async def assign_permissions_to_role(
        self,
        role_id: UUID,
        permission_names: List[str]
    ) -> bool:
        """Assign permissions to a role."""
        try:
            role = await self.get_role_by_id(role_id)
            if not role:
                raise NotFoundError("Role not found")
            
            # Get permissions
            permissions = []
            for perm_name in permission_names:
                permission = await self.get_permission_by_name(perm_name)
                if not permission:
                    raise NotFoundError(f"Permission '{perm_name}' not found")
                permissions.append(permission)
            
            # Assign permissions
            role.permissions.extend(permissions)
            await self.db.commit()
            
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to assign permissions: {str(e)}")
    
    async def remove_permissions_from_role(
        self,
        role_id: UUID,
        permission_names: List[str]
    ) -> bool:
        """Remove permissions from a role."""
        try:
            role = await self.get_role_by_id(role_id)
            if not role:
                raise NotFoundError("Role not found")
            
            # Get permissions to remove
            permissions_to_remove = []
            for perm_name in permission_names:
                permission = await self.get_permission_by_name(perm_name)
                if permission and permission in role.permissions:
                    permissions_to_remove.append(permission)
            
            # Remove permissions
            for permission in permissions_to_remove:
                role.permissions.remove(permission)
            
            await self.db.commit()
            
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to remove permissions: {str(e)}")
    
    # Resource Access Management
    async def grant_resource_access(
        self,
        api_key_id: UUID,
        resource_type: str,
        resource_id: str,
        allowed_actions: List[str],
        denied_actions: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> ResourceAccess:
        """Grant access to a specific resource."""
        try:
            # Check if access already exists
            existing_access = await self.db.execute(
                select(ResourceAccess).where(
                    and_(
                        ResourceAccess.api_key_id == api_key_id,
                        ResourceAccess.resource_type == resource_type,
                        ResourceAccess.resource_id == resource_id
                    )
                )
            )
            existing_access = existing_access.scalar_one_or_none()
            
            if existing_access:
                # Update existing access
                await self.db.execute(
                    update(ResourceAccess)
                    .where(ResourceAccess.id == existing_access.id)
                    .values(
                        allowed_actions=allowed_actions,
                        denied_actions=denied_actions or [],
                        conditions=conditions,
                        expires_at=expires_at,
                        is_active=True,
                        updated_at=datetime.utcnow()
                    )
                )
                await self.db.commit()
                await self.db.refresh(existing_access)
                return existing_access
            else:
                # Create new access
                resource_access = ResourceAccess(
                    api_key_id=api_key_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    allowed_actions=allowed_actions,
                    denied_actions=denied_actions or [],
                    conditions=conditions,
                    expires_at=expires_at
                )
                
                self.db.add(resource_access)
                await self.db.commit()
                await self.db.refresh(resource_access)
                
                return resource_access
            
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to grant resource access: {str(e)}")
    
    async def revoke_resource_access(
        self,
        api_key_id: UUID,
        resource_type: str,
        resource_id: str
    ) -> bool:
        """Revoke access to a specific resource."""
        try:
            result = await self.db.execute(
                delete(ResourceAccess).where(
                    and_(
                        ResourceAccess.api_key_id == api_key_id,
                        ResourceAccess.resource_type == resource_type,
                        ResourceAccess.resource_id == resource_id
                    )
                )
            )
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to revoke resource access: {str(e)}")
    
    async def get_resource_access(
        self,
        api_key_id: UUID,
        resource_type: Optional[str] = None
    ) -> List[ResourceAccess]:
        """Get resource access for an API key."""
        try:
            query = select(ResourceAccess).where(ResourceAccess.api_key_id == api_key_id)
            
            if resource_type:
                query = query.where(ResourceAccess.resource_type == resource_type)
            
            query = query.where(ResourceAccess.is_active == True)
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseError(f"Failed to get resource access: {str(e)}")
    
    # Authorization Checks
    async def check_permission(
        self,
        api_key_id: UUID,
        resource_type: str,
        action: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        Check if an API key has permission to perform an action on a resource.
        
        Args:
            api_key_id: API key ID
            resource_type: Type of resource
            action: Action to perform
            resource_id: Specific resource ID (optional)
            
        Returns:
            True if permission is granted
        """
        try:
            # Get API key with role
            api_key_result = await self.db.execute(
                select(APIKey)
                .options(selectinload(APIKey.role).selectinload(Role.permissions))
                .where(APIKey.id == api_key_id)
            )
            api_key = api_key_result.scalar_one_or_none()
            
            if not api_key or not api_key.is_valid:
                return False
            
            # Check role-based permissions
            if api_key.role and api_key.role.is_active:
                role_permissions = api_key.role.get_permission_names()
                permission_name = f"{resource_type}:{action}"
                
                if permission_name in role_permissions:
                    # Check if there's a specific resource access that denies this
                    if resource_id:
                        resource_access = await self.db.execute(
                            select(ResourceAccess).where(
                                and_(
                                    ResourceAccess.api_key_id == api_key_id,
                                    ResourceAccess.resource_type == resource_type,
                                    ResourceAccess.resource_id == resource_id,
                                    ResourceAccess.is_active == True
                                )
                            )
                        )
                        resource_access = resource_access.scalar_one_or_none()
                        
                        if resource_access:
                            return resource_access.can_perform_action(action)
                    
                    return True
            
            # Check direct resource access
            if resource_id:
                resource_access = await self.db.execute(
                    select(ResourceAccess).where(
                        and_(
                            ResourceAccess.api_key_id == api_key_id,
                            ResourceAccess.resource_type == resource_type,
                            ResourceAccess.resource_id == resource_id,
                            ResourceAccess.is_active == True
                        )
                    )
                )
                resource_access = resource_access.scalar_one_or_none()
                
                if resource_access:
                    return resource_access.can_perform_action(action)
            
            # Check legacy permissions in API key
            legacy_permission = f"{resource_type}:{action}"
            if legacy_permission in api_key.permissions:
                return True
            
            return False
            
        except Exception as e:
            raise DatabaseError(f"Failed to check permission: {str(e)}")
    
    # Security Event Logging
    async def log_security_event(
        self,
        event_type: str,
        event_category: str,
        message: str,
        api_key_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        severity: str = "info",
        success: bool = True,
        failure_reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action_attempted: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> SecurityEvent:
        """Log a security event."""
        try:
            security_event = SecurityEvent(
                event_type=event_type,
                event_category=event_category,
                message=message,
                api_key_id=api_key_id,
                user_id=user_id,
                severity=severity,
                success=success,
                failure_reason=failure_reason,
                details=details,
                resource_type=resource_type,
                resource_id=resource_id,
                action_attempted=action_attempted,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id
            )
            
            self.db.add(security_event)
            await self.db.commit()
            await self.db.refresh(security_event)
            
            return security_event
            
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to log security event: {str(e)}")
    
    # System Initialization
    async def initialize_system_roles_and_permissions(self) -> Dict[str, Any]:
        """Initialize system roles and permissions."""
        try:
            initialized = {
                "roles_created": 0,
                "permissions_created": 0,
                "role_assignments": 0
            }
            
            # Create system permissions
            system_permissions = [
                # Payment permissions
                ("payment:create", "Create Payment", "payment", "create", "Create new payments"),
                ("payment:read", "Read Payment", "payment", "read", "View payment details"),
                ("payment:update", "Update Payment", "payment", "update", "Modify payment data"),
                ("payment:delete", "Delete Payment", "payment", "delete", "Delete payments"),
                ("payment:refund", "Refund Payment", "payment", "execute", "Process refunds"),
                ("payment:cancel", "Cancel Payment", "payment", "execute", "Cancel payments"),
                
                # Webhook permissions
                ("webhook:create", "Create Webhook", "webhook", "create", "Create webhook endpoints"),
                ("webhook:read", "Read Webhook", "webhook", "read", "View webhook details"),
                ("webhook:update", "Update Webhook", "webhook", "update", "Modify webhook settings"),
                ("webhook:delete", "Delete Webhook", "webhook", "delete", "Delete webhooks"),
                ("webhook:execute", "Execute Webhook", "webhook", "execute", "Trigger webhooks"),
                
                # API Key permissions
                ("api_key:create", "Create API Key", "api_key", "create", "Create new API keys"),
                ("api_key:read", "Read API Key", "api_key", "read", "View API key details"),
                ("api_key:update", "Update API Key", "api_key", "update", "Modify API key settings"),
                ("api_key:delete", "Delete API Key", "api_key", "delete", "Delete API keys"),
                
                # Admin permissions
                ("admin:read", "Admin Read", "system", "read", "Read admin data"),
                ("admin:write", "Admin Write", "system", "write", "Write admin data"),
                ("admin:manage", "Admin Manage", "system", "manage", "Full admin access"),
                
                # Audit permissions
                ("audit:read", "Read Audit Logs", "audit_log", "read", "View audit logs"),
                ("audit:manage", "Manage Audit Logs", "audit_log", "manage", "Manage audit logs"),
            ]
            
            for perm_data in system_permissions:
                existing = await self.get_permission_by_name(perm_data[0])
                if not existing:
                    await self.create_permission(
                        name=perm_data[0],
                        display_name=perm_data[1],
                        resource_type=perm_data[2],
                        action_type=perm_data[3],
                        description=perm_data[4],
                        is_system_permission=True,
                        category=perm_data[2]
                    )
                    initialized["permissions_created"] += 1
            
            # Create system roles
            system_roles = [
                ("admin", "Administrator", "Full system access", [
                    "payment:create", "payment:read", "payment:update", "payment:delete", "payment:refund", "payment:cancel",
                    "webhook:create", "webhook:read", "webhook:update", "webhook:delete", "webhook:execute",
                    "api_key:create", "api_key:read", "api_key:update", "api_key:delete",
                    "admin:read", "admin:write", "admin:manage",
                    "audit:read", "audit:manage"
                ], 100),
                ("payment_manager", "Payment Manager", "Manage payments and webhooks", [
                    "payment:create", "payment:read", "payment:update", "payment:refund", "payment:cancel",
                    "webhook:create", "webhook:read", "webhook:update", "webhook:delete", "webhook:execute"
                ], 80),
                ("payment_operator", "Payment Operator", "Process payments", [
                    "payment:create", "payment:read", "payment:refund", "payment:cancel"
                ], 60),
                ("payment_viewer", "Payment Viewer", "View payment data", [
                    "payment:read", "webhook:read"
                ], 40),
                ("api_developer", "API Developer", "Develop with API", [
                    "payment:create", "payment:read", "webhook:create", "webhook:read"
                ], 30),
            ]
            
            for role_data in system_roles:
                existing = await self.get_role_by_name(role_data[0])
                if not existing:
                    role = await self.create_role(
                        name=role_data[0],
                        display_name=role_data[1],
                        description=role_data[2],
                        permissions=role_data[3],
                        is_system_role=True,
                        priority=role_data[4]
                    )
                    initialized["roles_created"] += 1
                    initialized["role_assignments"] += len(role_data[3])
            
            return initialized
            
        except Exception as e:
            raise DatabaseError(f"Failed to initialize system roles and permissions: {str(e)}")
