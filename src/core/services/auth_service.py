"""
EasyPay Payment Gateway - Authentication Service
"""
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import (
    AuthenticationError,
    ValidationError,
    DatabaseError,
    NotFoundError
)
from src.core.models.auth import APIKey, AuthToken, APIKeyStatus, TokenType, Permission
from src.api.v1.schemas.auth import (
    APIKeyCreateRequest,
    APIKeyUpdateRequest,
    TokenRequest,
    TokenRefreshRequest
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key-change-in-production"  # Should be from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30


class AuthService:
    """
    Authentication service for managing API keys and JWT tokens.
    
    This service handles the creation, validation, and management of
    API keys and JWT tokens for the EasyPay system.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize authentication service."""
        self.db = db
    
    async def create_api_key(self, request: APIKeyCreateRequest) -> Dict[str, Any]:
        """
        Create a new API key.
        
        Args:
            request: API key creation request
            
        Returns:
            Dict containing API key details including the secret
            
        Raises:
            ValidationError: If request data is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Generate unique key ID and secret
            key_id = f"ak_{secrets.token_urlsafe(16)}"
            key_secret = secrets.token_urlsafe(32)
            
            # Hash the secret
            key_secret_hash = pwd_context.hash(key_secret)
            
            # Create API key record
            api_key = APIKey(
                key_id=key_id,
                key_secret_hash=key_secret_hash,
                name=request.name,
                description=request.description,
                permissions=request.permissions,
                expires_at=request.expires_at,
                rate_limit_per_minute=request.rate_limit_per_minute,
                rate_limit_per_hour=request.rate_limit_per_hour,
                rate_limit_per_day=request.rate_limit_per_day,
                ip_whitelist=request.ip_whitelist,
                ip_blacklist=request.ip_blacklist,
                status=APIKeyStatus.ACTIVE
            )
            
            self.db.add(api_key)
            await self.db.commit()
            await self.db.refresh(api_key)
            
            return {
                "id": api_key.id,
                "key_id": api_key.key_id,
                "key_secret": key_secret,  # Only returned once
                "name": api_key.name,
                "description": api_key.description,
                "permissions": api_key.permissions,
                "expires_at": api_key.expires_at,
                "created_at": api_key.created_at
            }
            
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to create API key: {str(e)}")
    
    async def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """
        Get API key by key ID.
        
        Args:
            key_id: API key ID
            
        Returns:
            APIKey object or None if not found
        """
        try:
            result = await self.db.execute(
                select(APIKey).where(APIKey.key_id == key_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get API key: {str(e)}")
    
    async def get_api_key_by_id(self, api_key_id: UUID) -> Optional[APIKey]:
        """
        Get API key by UUID.
        
        Args:
            api_key_id: API key UUID
            
        Returns:
            APIKey object or None if not found
        """
        try:
            result = await self.db.execute(
                select(APIKey).where(APIKey.id == api_key_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            raise DatabaseError(f"Failed to get API key: {str(e)}")
    
    async def list_api_keys(
        self, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[APIKey]:
        """
        List API keys with pagination and filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status
            
        Returns:
            List of APIKey objects
        """
        try:
            query = select(APIKey)
            
            if status:
                query = query.where(APIKey.status == status)
            
            query = query.offset(skip).limit(limit).order_by(APIKey.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            raise DatabaseError(f"Failed to list API keys: {str(e)}")
    
    async def update_api_key(
        self, 
        api_key_id: UUID, 
        request: APIKeyUpdateRequest
    ) -> APIKey:
        """
        Update an API key.
        
        Args:
            api_key_id: API key UUID
            request: Update request
            
        Returns:
            Updated APIKey object
            
        Raises:
            NotFoundError: If API key not found
            DatabaseError: If database operation fails
        """
        try:
            # Get existing API key
            api_key = await self.get_api_key_by_id(api_key_id)
            if not api_key:
                raise NotFoundError("API key not found")
            
            # Update fields
            update_data = request.dict(exclude_unset=True)
            if update_data:
                await self.db.execute(
                    update(APIKey)
                    .where(APIKey.id == api_key_id)
                    .values(**update_data, updated_at=datetime.utcnow())
                )
                await self.db.commit()
                
                # Refresh the object
                await self.db.refresh(api_key)
            
            return api_key
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to update API key: {str(e)}")
    
    async def delete_api_key(self, api_key_id: UUID) -> bool:
        """
        Delete an API key.
        
        Args:
            api_key_id: API key UUID
            
        Returns:
            True if deleted successfully
            
        Raises:
            NotFoundError: If API key not found
            DatabaseError: If database operation fails
        """
        try:
            # Check if API key exists
            api_key = await self.get_api_key_by_id(api_key_id)
            if not api_key:
                raise NotFoundError("API key not found")
            
            # Delete the API key
            await self.db.execute(
                delete(APIKey).where(APIKey.id == api_key_id)
            )
            await self.db.commit()
            
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to delete API key: {str(e)}")
    
    async def validate_api_key(self, key_id: str, key_secret: str) -> Optional[APIKey]:
        """
        Validate API key credentials.
        
        Args:
            key_id: API key ID
            key_secret: API key secret
            
        Returns:
            APIKey object if valid, None otherwise
        """
        try:
            api_key = await self.get_api_key(key_id)
            if not api_key:
                return None
            
            # Check if API key is valid
            if not api_key.is_valid:
                return None
            
            # Verify secret
            if not pwd_context.verify(key_secret, api_key.key_secret_hash):
                return None
            
            # Update usage tracking
            await self.db.execute(
                update(APIKey)
                .where(APIKey.id == api_key.id)
                .values(
                    last_used_at=datetime.utcnow(),
                    usage_count=APIKey.usage_count + 1
                )
            )
            await self.db.commit()
            
            return api_key
            
        except Exception as e:
            raise DatabaseError(f"Failed to validate API key: {str(e)}")
    
    async def generate_tokens(self, request: TokenRequest) -> Dict[str, Any]:
        """
        Generate JWT tokens for API key.
        
        Args:
            request: Token generation request
            
        Returns:
            Dict containing access and refresh tokens
            
        Raises:
            AuthenticationError: If API key validation fails
            DatabaseError: If database operation fails
        """
        try:
            # Validate API key
            api_key = await self.validate_api_key(request.api_key_id, request.api_key_secret)
            if not api_key:
                raise AuthenticationError("Invalid API key credentials")
            
            # Generate token IDs
            access_token_id = f"at_{secrets.token_urlsafe(16)}"
            refresh_token_id = f"rt_{secrets.token_urlsafe(16)}"
            
            # Calculate expiration times
            expires_in = request.expires_in or ACCESS_TOKEN_EXPIRE_MINUTES * 60
            access_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            refresh_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            
            # Create JWT payload
            access_payload = {
                "sub": str(api_key.id),
                "key_id": api_key.key_id,
                "permissions": api_key.permissions,
                "type": TokenType.ACCESS.value,
                "jti": access_token_id,
                "iat": datetime.utcnow().timestamp(),
                "exp": access_expires_at.timestamp()
            }
            
            refresh_payload = {
                "sub": str(api_key.id),
                "key_id": api_key.key_id,
                "type": TokenType.REFRESH.value,
                "jti": refresh_token_id,
                "iat": datetime.utcnow().timestamp(),
                "exp": refresh_expires_at.timestamp()
            }
            
            # Generate tokens
            access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
            refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
            
            # Store tokens in database
            access_token_record = AuthToken(
                token_id=access_token_id,
                token_type=TokenType.ACCESS.value,
                jti=access_token_id,
                api_key_id=api_key.id,
                subject=str(api_key.id),
                expires_at=access_expires_at
            )
            
            refresh_token_record = AuthToken(
                token_id=refresh_token_id,
                token_type=TokenType.REFRESH.value,
                jti=refresh_token_id,
                api_key_id=api_key.id,
                subject=str(api_key.id),
                expires_at=refresh_expires_at
            )
            
            self.db.add(access_token_record)
            self.db.add(refresh_token_record)
            await self.db.commit()
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": expires_in,
                "expires_at": access_expires_at
            }
            
        except AuthenticationError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to generate tokens: {str(e)}")
    
    async def refresh_token(self, request: TokenRefreshRequest) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            request: Token refresh request
            
        Returns:
            Dict containing new access and refresh tokens
            
        Raises:
            AuthenticationError: If refresh token is invalid
            DatabaseError: If database operation fails
        """
        try:
            # Decode and validate refresh token
            try:
                payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            except JWTError:
                raise AuthenticationError("Invalid refresh token")
            
            # Check if token exists in database
            token_record = await self.db.execute(
                select(AuthToken).where(
                    AuthToken.jti == payload["jti"],
                    AuthToken.token_type == TokenType.REFRESH.value,
                    AuthToken.is_revoked == False
                )
            )
            token_record = token_record.scalar_one_or_none()
            
            if not token_record or token_record.is_expired:
                raise AuthenticationError("Invalid or expired refresh token")
            
            # Get API key
            api_key = await self.get_api_key_by_id(UUID(payload["sub"]))
            if not api_key or not api_key.is_valid:
                raise AuthenticationError("API key is invalid")
            
            # Revoke old tokens
            await self.db.execute(
                update(AuthToken)
                .where(AuthToken.api_key_id == api_key.id)
                .values(
                    is_revoked=True,
                    revoked_at=datetime.utcnow(),
                    revoked_reason="refreshed"
                )
            )
            
            # Generate new tokens
            token_request = TokenRequest(
                api_key_id=api_key.key_id,
                api_key_secret="",  # Not needed for refresh
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            
            # We need to get the secret for validation, but this is a design issue
            # For now, we'll skip the secret validation in refresh
            return await self._generate_tokens_for_api_key(api_key, token_request.expires_in)
            
        except AuthenticationError:
            raise
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to refresh token: {str(e)}")
    
    async def _generate_tokens_for_api_key(self, api_key: APIKey, expires_in: int) -> Dict[str, Any]:
        """Generate tokens for an existing API key (internal method)."""
        # Generate token IDs
        access_token_id = f"at_{secrets.token_urlsafe(16)}"
        refresh_token_id = f"rt_{secrets.token_urlsafe(16)}"
        
        # Calculate expiration times
        access_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        refresh_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Create JWT payload
        access_payload = {
            "sub": str(api_key.id),
            "key_id": api_key.key_id,
            "permissions": api_key.permissions,
            "type": TokenType.ACCESS.value,
            "jti": access_token_id,
            "iat": datetime.utcnow().timestamp(),
            "exp": access_expires_at.timestamp()
        }
        
        refresh_payload = {
            "sub": str(api_key.id),
            "key_id": api_key.key_id,
            "type": TokenType.REFRESH.value,
            "jti": refresh_token_id,
            "iat": datetime.utcnow().timestamp(),
            "exp": refresh_expires_at.timestamp()
        }
        
        # Generate tokens
        access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # Store tokens in database
        access_token_record = AuthToken(
            token_id=access_token_id,
            token_type=TokenType.ACCESS.value,
            jti=access_token_id,
            api_key_id=api_key.id,
            subject=str(api_key.id),
            expires_at=access_expires_at
        )
        
        refresh_token_record = AuthToken(
            token_id=refresh_token_id,
            token_type=TokenType.REFRESH.value,
            jti=refresh_token_id,
            api_key_id=api_key.id,
            subject=str(api_key.id),
            expires_at=refresh_expires_at
        )
        
        self.db.add(access_token_record)
        self.db.add(refresh_token_record)
        await self.db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "expires_at": access_expires_at
        }
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Dict containing validation result and token info
        """
        try:
            # Decode token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if token exists in database
            token_record = await self.db.execute(
                select(AuthToken).where(
                    AuthToken.jti == payload["jti"],
                    AuthToken.token_type == TokenType.ACCESS.value,
                    AuthToken.is_revoked == False
                )
            )
            token_record = token_record.scalar_one_or_none()
            
            if not token_record or token_record.is_expired:
                return {
                    "valid": False,
                    "error": "Invalid or expired token"
                }
            
            # Update usage tracking
            await self.db.execute(
                update(AuthToken)
                .where(AuthToken.id == token_record.id)
                .values(
                    last_used_at=datetime.utcnow(),
                    usage_count=AuthToken.usage_count + 1
                )
            )
            await self.db.commit()
            
            return {
                "valid": True,
                "token_id": token_record.token_id,
                "api_key_id": payload["key_id"],
                "permissions": payload.get("permissions", []),
                "expires_at": token_record.expires_at
            }
            
        except JWTError:
            return {
                "valid": False,
                "error": "Invalid token format"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Token validation error: {str(e)}"
            }
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a JWT token.
        
        Args:
            token: JWT token to revoke
            
        Returns:
            True if token was revoked successfully
        """
        try:
            # Decode token to get JTI
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Revoke token in database
            await self.db.execute(
                update(AuthToken)
                .where(AuthToken.jti == payload["jti"])
                .values(
                    is_revoked=True,
                    revoked_at=datetime.utcnow(),
                    revoked_reason="manual_revocation"
                )
            )
            await self.db.commit()
            
            return True
            
        except JWTError:
            return False
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to revoke token: {str(e)}")
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired tokens from database.
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            # Delete expired tokens
            result = await self.db.execute(
                delete(AuthToken).where(
                    AuthToken.expires_at < datetime.utcnow()
                )
            )
            await self.db.commit()
            
            return result.rowcount
            
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to cleanup expired tokens: {str(e)}")
