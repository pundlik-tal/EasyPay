"""
EasyPay Payment Gateway - API Key Scoping Service
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, delete, and_, Column, String, DateTime, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    ValidationError,
    DatabaseError,
    NotFoundError,
    AuthorizationError
)
from src.core.models.auth import APIKey
from src.core.models.rbac import SecurityEvent
from src.infrastructure.db_components.base import Base


class Environment(str, Enum):
    """Environment enumeration."""
    SANDBOX = "sandbox"
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"


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


class ScopingService:
    """
    API Key Scoping service for managing environment-based access control.
    
    This service handles scoping rules for API keys, including environment
    restrictions, domain whitelisting, IP filtering, and time-based access.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize scoping service."""
        self.db = db
    
    async def create_scope(
        self,
        api_key_id: UUID,
        scope_type: str,
        scope_value: str,
        scope_config: Optional[Dict[str, Any]] = None
    ) -> APIKeyScope:
        """
        Create a new scope for an API key.
        
        Args:
            api_key_id: API key ID
            scope_type: Type of scope (environment, domain, etc.)
            scope_value: Scope value
            scope_config: Additional scope configuration
            
        Returns:
            Created APIKeyScope object
            
        Raises:
            ValidationError: If scope data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Validate scope type
            if scope_type not in [scope.value for scope in ScopeType]:
                raise ValidationError(f"Invalid scope type: {scope_type}")
            
            # Validate scope value based on type
            await self._validate_scope_value(scope_type, scope_value)
            
            # Create scope
            scope = APIKeyScope(
                api_key_id=api_key_id,
                scope_type=scope_type,
                scope_value=scope_value,
                scope_config=scope_config
            )
            
            self.db.add(scope)
            await self.db.commit()
            await self.db.refresh(scope)
            
            return scope
            
        except ValidationError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to create scope: {str(e)}")
    
    async def _validate_scope_value(self, scope_type: str, scope_value: str) -> None:
        """Validate scope value based on scope type."""
        if scope_type == ScopeType.ENVIRONMENT:
            if scope_value not in [env.value for env in Environment]:
                raise ValidationError(f"Invalid environment: {scope_value}")
        
        elif scope_type == ScopeType.DOMAIN:
            # Basic domain validation
            if not scope_value or len(scope_value) < 3:
                raise ValidationError("Domain must be at least 3 characters long")
        
        elif scope_type == ScopeType.IP_RANGE:
            # Basic IP range validation (can be enhanced)
            if not scope_value or "/" not in scope_value:
                raise ValidationError("IP range must be in CIDR format (e.g., 192.168.1.0/24)")
        
        elif scope_type == ScopeType.TIME_WINDOW:
            # Time window validation (e.g., "09:00-17:00", "mon-fri")
            if not scope_value:
                raise ValidationError("Time window cannot be empty")
        
        elif scope_type == ScopeType.RESOURCE_LIMIT:
            # Resource limit validation (e.g., "1000", "1000/hour")
            if not scope_value.isdigit() and "/" not in scope_value:
                raise ValidationError("Resource limit must be a number or number/period")
    
    async def get_scopes_for_api_key(
        self,
        api_key_id: UUID,
        scope_type: Optional[str] = None
    ) -> List[APIKeyScope]:
        """Get scopes for an API key."""
        try:
            query = select(APIKeyScope).where(
                and_(
                    APIKeyScope.api_key_id == api_key_id,
                    APIKeyScope.is_active == True
                )
            )
            
            if scope_type:
                query = query.where(APIKeyScope.scope_type == scope_type)
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseError(f"Failed to get scopes: {str(e)}")
    
    async def update_scope(
        self,
        scope_id: UUID,
        scope_value: Optional[str] = None,
        scope_config: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> APIKeyScope:
        """Update a scope."""
        try:
            scope = await self.db.execute(
                select(APIKeyScope).where(APIKeyScope.id == scope_id)
            )
            scope = scope.scalar_one_or_none()
            
            if not scope:
                raise NotFoundError("Scope not found")
            
            update_data = {}
            if scope_value is not None:
                await self._validate_scope_value(scope.scope_type, scope_value)
                update_data["scope_value"] = scope_value
            if scope_config is not None:
                update_data["scope_config"] = scope_config
            if is_active is not None:
                update_data["is_active"] = is_active
            
            if update_data:
                update_data["updated_at"] = datetime.utcnow()
                await self.db.execute(
                    update(APIKeyScope)
                    .where(APIKeyScope.id == scope_id)
                    .values(**update_data)
                )
                await self.db.commit()
                await self.db.refresh(scope)
            
            return scope
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to update scope: {str(e)}")
    
    async def delete_scope(self, scope_id: UUID) -> bool:
        """Delete a scope."""
        try:
            result = await self.db.execute(
                delete(APIKeyScope).where(APIKeyScope.id == scope_id)
            )
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to delete scope: {str(e)}")
    
    # Scope Validation Methods
    async def validate_environment_access(
        self,
        api_key_id: UUID,
        requested_environment: str
    ) -> bool:
        """Validate if API key can access the requested environment."""
        try:
            # Get environment scopes for the API key
            scopes = await self.get_scopes_for_api_key(
                api_key_id, 
                ScopeType.ENVIRONMENT
            )
            
            if not scopes:
                # No environment restrictions
                return True
            
            # Check if requested environment is allowed
            allowed_environments = [scope.scope_value for scope in scopes]
            return requested_environment in allowed_environments
            
        except Exception as e:
            raise DatabaseError(f"Failed to validate environment access: {str(e)}")
    
    async def validate_domain_access(
        self,
        api_key_id: UUID,
        requested_domain: str
    ) -> bool:
        """Validate if API key can access the requested domain."""
        try:
            # Get domain scopes for the API key
            scopes = await self.get_scopes_for_api_key(
                api_key_id, 
                ScopeType.DOMAIN
            )
            
            if not scopes:
                # No domain restrictions
                return True
            
            # Check if requested domain is allowed
            for scope in scopes:
                if self._domain_matches(scope.scope_value, requested_domain):
                    return True
            
            return False
            
        except Exception as e:
            raise DatabaseError(f"Failed to validate domain access: {str(e)}")
    
    def _domain_matches(self, scope_domain: str, requested_domain: str) -> bool:
        """Check if requested domain matches scope domain."""
        # Simple domain matching (can be enhanced with wildcards)
        if scope_domain.startswith("*."):
            # Wildcard subdomain
            base_domain = scope_domain[2:]
            return requested_domain.endswith(base_domain)
        else:
            # Exact match
            return scope_domain == requested_domain
    
    async def validate_ip_access(
        self,
        api_key_id: UUID,
        client_ip: str
    ) -> bool:
        """Validate if API key can access from the client IP."""
        try:
            # Get IP range scopes for the API key
            scopes = await self.get_scopes_for_api_key(
                api_key_id, 
                ScopeType.IP_RANGE
            )
            
            if not scopes:
                # No IP restrictions
                return True
            
            # Check if client IP is in allowed ranges
            for scope in scopes:
                if self._ip_in_range(client_ip, scope.scope_value):
                    return True
            
            return False
            
        except Exception as e:
            raise DatabaseError(f"Failed to validate IP access: {str(e)}")
    
    def _ip_in_range(self, ip: str, ip_range: str) -> bool:
        """Check if IP is in the specified range."""
        # Simplified IP range checking (can be enhanced with proper CIDR)
        try:
            if "/" in ip_range:
                # CIDR notation
                import ipaddress
                network = ipaddress.ip_network(ip_range, strict=False)
                return ipaddress.ip_address(ip) in network
            else:
                # Single IP
                return ip == ip_range
        except Exception:
            return False
    
    async def validate_time_access(
        self,
        api_key_id: UUID
    ) -> bool:
        """Validate if API key can access at the current time."""
        try:
            # Get time window scopes for the API key
            scopes = await self.get_scopes_for_api_key(
                api_key_id, 
                ScopeType.TIME_WINDOW
            )
            
            if not scopes:
                # No time restrictions
                return True
            
            # Check if current time is within allowed windows
            current_time = datetime.utcnow()
            for scope in scopes:
                if self._time_in_window(current_time, scope.scope_value):
                    return True
            
            return False
            
        except Exception as e:
            raise DatabaseError(f"Failed to validate time access: {str(e)}")
    
    def _time_in_window(self, current_time: datetime, time_window: str) -> bool:
        """Check if current time is within the specified window."""
        # Simplified time window checking
        try:
            if "-" in time_window:
                # Time range (e.g., "09:00-17:00")
                start_str, end_str = time_window.split("-")
                current_hour = current_time.hour
                start_hour = int(start_str.split(":")[0])
                end_hour = int(end_str.split(":")[0])
                
                return start_hour <= current_hour <= end_hour
            else:
                # Single time or other format
                return True
        except Exception:
            return False
    
    async def validate_resource_limit(
        self,
        api_key_id: UUID,
        resource_type: str,
        resource_count: int = 1
    ) -> bool:
        """Validate if API key is within resource limits."""
        try:
            # Get resource limit scopes for the API key
            scopes = await self.get_scopes_for_api_key(
                api_key_id, 
                ScopeType.RESOURCE_LIMIT
            )
            
            if not scopes:
                # No resource limits
                return True
            
            # Check resource limits (simplified implementation)
            for scope in scopes:
                if not self._within_resource_limit(
                    api_key_id, 
                    resource_type, 
                    scope.scope_value, 
                    resource_count
                ):
                    return False
            
            return True
            
        except Exception as e:
            raise DatabaseError(f"Failed to validate resource limit: {str(e)}")
    
    def _within_resource_limit(
        self,
        api_key_id: UUID,
        resource_type: str,
        limit_value: str,
        resource_count: int
    ) -> bool:
        """Check if resource usage is within limits."""
        # Simplified resource limit checking
        # In production, this would check actual usage from database/cache
        try:
            if "/" in limit_value:
                # Rate limit (e.g., "1000/hour")
                limit, period = limit_value.split("/")
                limit_num = int(limit)
                # For now, just return True (would check actual usage)
                return True
            else:
                # Absolute limit
                limit_num = int(limit_value)
                # For now, just return True (would check actual usage)
                return True
        except Exception:
            return False
    
    # Comprehensive Access Validation
    async def validate_api_key_access(
        self,
        api_key_id: UUID,
        environment: Optional[str] = None,
        domain: Optional[str] = None,
        client_ip: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_count: int = 1
    ) -> Dict[str, Any]:
        """
        Comprehensive API key access validation.
        
        Args:
            api_key_id: API key ID
            environment: Requested environment
            domain: Requested domain
            client_ip: Client IP address
            resource_type: Resource type for limits
            resource_count: Number of resources requested
            
        Returns:
            Dict containing validation results
        """
        try:
            validation_results = {
                "valid": True,
                "restrictions": [],
                "warnings": []
            }
            
            # Validate environment access
            if environment:
                env_valid = await self.validate_environment_access(api_key_id, environment)
                if not env_valid:
                    validation_results["valid"] = False
                    validation_results["restrictions"].append(f"Environment '{environment}' not allowed")
            
            # Validate domain access
            if domain:
                domain_valid = await self.validate_domain_access(api_key_id, domain)
                if not domain_valid:
                    validation_results["valid"] = False
                    validation_results["restrictions"].append(f"Domain '{domain}' not allowed")
            
            # Validate IP access
            if client_ip:
                ip_valid = await self.validate_ip_access(api_key_id, client_ip)
                if not ip_valid:
                    validation_results["valid"] = False
                    validation_results["restrictions"].append(f"IP '{client_ip}' not allowed")
            
            # Validate time access
            time_valid = await self.validate_time_access(api_key_id)
            if not time_valid:
                validation_results["valid"] = False
                validation_results["restrictions"].append("Access not allowed at current time")
            
            # Validate resource limits
            if resource_type:
                limit_valid = await self.validate_resource_limit(
                    api_key_id, 
                    resource_type, 
                    resource_count
                )
                if not limit_valid:
                    validation_results["valid"] = False
                    validation_results["restrictions"].append(f"Resource limit exceeded for '{resource_type}'")
            
            return validation_results
            
        except Exception as e:
            raise DatabaseError(f"Failed to validate API key access: {str(e)}")
    
    # Scope Management Utilities
    async def create_environment_scope(
        self,
        api_key_id: UUID,
        environment: str
    ) -> APIKeyScope:
        """Create an environment scope for an API key."""
        return await self.create_scope(
            api_key_id=api_key_id,
            scope_type=ScopeType.ENVIRONMENT,
            scope_value=environment
        )
    
    async def create_domain_scope(
        self,
        api_key_id: UUID,
        domain: str
    ) -> APIKeyScope:
        """Create a domain scope for an API key."""
        return await self.create_scope(
            api_key_id=api_key_id,
            scope_type=ScopeType.DOMAIN,
            scope_value=domain
        )
    
    async def create_ip_range_scope(
        self,
        api_key_id: UUID,
        ip_range: str
    ) -> APIKeyScope:
        """Create an IP range scope for an API key."""
        return await self.create_scope(
            api_key_id=api_key_id,
            scope_type=ScopeType.IP_RANGE,
            scope_value=ip_range
        )
    
    async def create_time_window_scope(
        self,
        api_key_id: UUID,
        time_window: str
    ) -> APIKeyScope:
        """Create a time window scope for an API key."""
        return await self.create_scope(
            api_key_id=api_key_id,
            scope_type=ScopeType.TIME_WINDOW,
            scope_value=time_window
        )
    
    async def create_resource_limit_scope(
        self,
        api_key_id: UUID,
        resource_limit: str
    ) -> APIKeyScope:
        """Create a resource limit scope for an API key."""
        return await self.create_scope(
            api_key_id=api_key_id,
            scope_type=ScopeType.RESOURCE_LIMIT,
            scope_value=resource_limit
        )
