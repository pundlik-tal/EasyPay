"""
EasyPay Payment Gateway - Security Features Tests
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.rbac_service import RBACService
from src.core.services.scoping_service import ScopingService
from src.core.services.request_signing_service import RequestSigningService, WebhookSigningService
from src.core.services.audit_logging_service import AuditLoggingService
from src.core.models.rbac import Role, Permission, SecurityEvent
from src.core.models.auth import APIKey, APIKeyStatus


class TestRBACService:
    """Test RBAC service functionality."""
    
    @pytest.fixture
    async def rbac_service(self, db_session: AsyncSession):
        """Create RBAC service instance."""
        return RBACService(db_session)
    
    @pytest.mark.asyncio
    async def test_create_role(self, rbac_service: RBACService):
        """Test role creation."""
        role = await rbac_service.create_role(
            name="test_role",
            display_name="Test Role",
            description="A test role",
            permissions=["payment:read", "payment:write"]
        )
        
        assert role.name == "test_role"
        assert role.display_name == "Test Role"
        assert role.status == "active"
        assert len(role.permissions) == 2
    
    @pytest.mark.asyncio
    async def test_create_permission(self, rbac_service: RBACService):
        """Test permission creation."""
        permission = await rbac_service.create_permission(
            name="test_permission",
            display_name="Test Permission",
            resource_type="payment",
            action_type="read",
            description="A test permission"
        )
        
        assert permission.name == "test_permission"
        assert permission.resource_type == "payment"
        assert permission.action_type == "read"
    
    @pytest.mark.asyncio
    async def test_assign_permissions_to_role(self, rbac_service: RBACService):
        """Test assigning permissions to role."""
        # Create role and permission
        role = await rbac_service.create_role(
            name="test_role_2",
            display_name="Test Role 2"
        )
        
        permission = await rbac_service.create_permission(
            name="test_permission_2",
            display_name="Test Permission 2",
            resource_type="payment",
            action_type="write"
        )
        
        # Assign permission to role
        result = await rbac_service.assign_permissions_to_role(
            role.id, ["test_permission_2"]
        )
        
        assert result is True
        
        # Verify assignment
        updated_role = await rbac_service.get_role_by_id(role.id)
        assert len(updated_role.permissions) == 1
        assert updated_role.permissions[0].name == "test_permission_2"
    
    @pytest.mark.asyncio
    async def test_check_permission(self, rbac_service: RBACService):
        """Test permission checking."""
        # Create role with permission
        role = await rbac_service.create_role(
            name="test_role_3",
            display_name="Test Role 3",
            permissions=["payment:read"]
        )
        
        # Create API key with role
        api_key = APIKey(
            key_id="test_key",
            key_secret_hash="hashed_secret",
            name="Test Key",
            role_id=role.id,
            status=APIKeyStatus.ACTIVE
        )
        
        # Mock database session
        rbac_service.db.add(api_key)
        await rbac_service.db.commit()
        
        # Check permission
        has_permission = await rbac_service.check_permission(
            api_key_id=api_key.id,
            resource_type="payment",
            action="read"
        )
        
        assert has_permission is True
        
        # Check denied permission
        has_permission = await rbac_service.check_permission(
            api_key_id=api_key.id,
            resource_type="payment",
            action="delete"
        )
        
        assert has_permission is False
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, rbac_service: RBACService):
        """Test security event logging."""
        event = await rbac_service.log_security_event(
            event_type="test_event",
            event_category="test",
            message="Test security event",
            severity="info",
            success=True
        )
        
        assert event.event_type == "test_event"
        assert event.event_category == "test"
        assert event.severity == "info"
        assert event.success is True


class TestScopingService:
    """Test API key scoping service functionality."""
    
    @pytest.fixture
    async def scoping_service(self, db_session: AsyncSession):
        """Create scoping service instance."""
        return ScopingService(db_session)
    
    @pytest.mark.asyncio
    async def test_create_environment_scope(self, scoping_service: ScopingService):
        """Test creating environment scope."""
        api_key_id = uuid4()
        
        scope = await scoping_service.create_environment_scope(
            api_key_id=api_key_id,
            environment="sandbox"
        )
        
        assert scope.scope_type == "environment"
        assert scope.scope_value == "sandbox"
        assert scope.api_key_id == api_key_id
    
    @pytest.mark.asyncio
    async def test_create_domain_scope(self, scoping_service: ScopingService):
        """Test creating domain scope."""
        api_key_id = uuid4()
        
        scope = await scoping_service.create_domain_scope(
            api_key_id=api_key_id,
            domain="example.com"
        )
        
        assert scope.scope_type == "domain"
        assert scope.scope_value == "example.com"
        assert scope.api_key_id == api_key_id
    
    @pytest.mark.asyncio
    async def test_create_ip_range_scope(self, scoping_service: ScopingService):
        """Test creating IP range scope."""
        api_key_id = uuid4()
        
        scope = await scoping_service.create_ip_range_scope(
            api_key_id=api_key_id,
            ip_range="192.168.1.0/24"
        )
        
        assert scope.scope_type == "ip_range"
        assert scope.scope_value == "192.168.1.0/24"
        assert scope.api_key_id == api_key_id
    
    @pytest.mark.asyncio
    async def test_validate_environment_access(self, scoping_service: ScopingService):
        """Test environment access validation."""
        api_key_id = uuid4()
        
        # Create sandbox scope
        await scoping_service.create_environment_scope(
            api_key_id=api_key_id,
            environment="sandbox"
        )
        
        # Test allowed environment
        allowed = await scoping_service.validate_environment_access(
            api_key_id=api_key_id,
            requested_environment="sandbox"
        )
        assert allowed is True
        
        # Test denied environment
        denied = await scoping_service.validate_environment_access(
            api_key_id=api_key_id,
            requested_environment="production"
        )
        assert denied is False
    
    @pytest.mark.asyncio
    async def test_validate_domain_access(self, scoping_service: ScopingService):
        """Test domain access validation."""
        api_key_id = uuid4()
        
        # Create domain scope
        await scoping_service.create_domain_scope(
            api_key_id=api_key_id,
            domain="example.com"
        )
        
        # Test allowed domain
        allowed = await scoping_service.validate_domain_access(
            api_key_id=api_key_id,
            requested_domain="example.com"
        )
        assert allowed is True
        
        # Test denied domain
        denied = await scoping_service.validate_domain_access(
            api_key_id=api_key_id,
            requested_domain="malicious.com"
        )
        assert denied is False
    
    @pytest.mark.asyncio
    async def test_validate_ip_access(self, scoping_service: ScopingService):
        """Test IP access validation."""
        api_key_id = uuid4()
        
        # Create IP range scope
        await scoping_service.create_ip_range_scope(
            api_key_id=api_key_id,
            ip_range="192.168.1.0/24"
        )
        
        # Test allowed IP
        allowed = await scoping_service.validate_ip_access(
            api_key_id=api_key_id,
            client_ip="192.168.1.100"
        )
        assert allowed is True
        
        # Test denied IP
        denied = await scoping_service.validate_ip_access(
            api_key_id=api_key_id,
            client_ip="10.0.0.1"
        )
        assert denied is False


class TestRequestSigningService:
    """Test request signing service functionality."""
    
    @pytest.fixture
    def signing_service(self):
        """Create request signing service instance."""
        return RequestSigningService("test-secret-key")
    
    def test_generate_signature(self, signing_service: RequestSigningService):
        """Test signature generation."""
        method = "POST"
        url = "https://api.easypay.com/v1/payments"
        headers = {"Content-Type": "application/json"}
        body = '{"amount": 1000}'
        
        signature = signing_service.generate_signature(
            method=method,
            url=url,
            headers=headers,
            body=body
        )
        
        assert signature is not None
        assert len(signature) > 0
    
    def test_verify_signature(self, signing_service: RequestSigningService):
        """Test signature verification."""
        method = "POST"
        url = "https://api.easypay.com/v1/payments"
        headers = {"Content-Type": "application/json"}
        body = '{"amount": 1000}'
        timestamp = int(datetime.now().timestamp())
        
        # Generate signature
        signature = signing_service.generate_signature(
            method=method,
            url=url,
            headers=headers,
            body=body,
            timestamp=timestamp
        )
        
        # Verify signature
        is_valid = signing_service.verify_signature(
            method=method,
            url=url,
            headers=headers,
            body=body,
            signature=signature,
            timestamp=timestamp
        )
        
        assert is_valid is True
    
    def test_create_signed_request(self, signing_service: RequestSigningService):
        """Test creating signed request."""
        method = "POST"
        url = "https://api.easypay.com/v1/payments"
        headers = {"Content-Type": "application/json"}
        body = '{"amount": 1000}'
        
        signed_headers = signing_service.create_signed_request(
            method=method,
            url=url,
            headers=headers,
            body=body
        )
        
        assert "X-Timestamp" in signed_headers
        assert "X-Signature" in signed_headers
        assert "X-Signature-Method" in signed_headers
        assert "X-Signature-Version" in signed_headers
    
    def test_extract_signature_info(self, signing_service: RequestSigningService):
        """Test signature info extraction."""
        headers = {
            "X-Timestamp": "1234567890",
            "X-Signature": "test-signature",
            "X-Signature-Method": "HMAC-SHA256",
            "X-Signature-Version": "1.0"
        }
        
        sig_info = signing_service.extract_signature_info(headers)
        
        assert sig_info["timestamp"] == 1234567890
        assert sig_info["signature"] == "test-signature"
        assert sig_info["method"] == "HMAC-SHA256"
        assert sig_info["version"] == "1.0"


class TestWebhookSigningService:
    """Test webhook signing service functionality."""
    
    @pytest.fixture
    def webhook_service(self):
        """Create webhook signing service instance."""
        return WebhookSigningService("test-webhook-secret")
    
    def test_generate_webhook_signature(self, webhook_service: WebhookSigningService):
        """Test webhook signature generation."""
        payload = '{"event": "payment.completed", "data": {"id": "pay_123"}}'
        
        signature = webhook_service.generate_webhook_signature(payload)
        
        assert signature is not None
        assert "t=" in signature
        assert "v1=" in signature
    
    def test_verify_webhook_signature(self, webhook_service: WebhookSigningService):
        """Test webhook signature verification."""
        payload = '{"event": "payment.completed", "data": {"id": "pay_123"}}'
        
        # Generate signature
        signature = webhook_service.generate_webhook_signature(payload)
        
        # Verify signature
        is_valid = webhook_service.verify_webhook_signature(
            payload=payload,
            signature_header=signature
        )
        
        assert is_valid is True


class TestAuditLoggingService:
    """Test audit logging service functionality."""
    
    @pytest.fixture
    async def audit_service(self, db_session: AsyncSession):
        """Create audit logging service instance."""
        return AuditLoggingService(db_session)
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, audit_service: AuditLoggingService):
        """Test security event logging."""
        event = await audit_service.log_security_event(
            event_type="test_event",
            event_category="test",
            message="Test security event",
            severity="info",
            success=True
        )
        
        assert event.event_type == "test_event"
        assert event.event_category == "test"
        assert event.severity == "info"
        assert event.success is True
    
    @pytest.mark.asyncio
    async def test_log_authentication_event(self, audit_service: AuditLoggingService):
        """Test authentication event logging."""
        event = await audit_service.log_authentication_event(
            event_type="login_success",
            api_key_id=uuid4(),
            success=True,
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        assert event.event_type == "login_success"
        assert event.event_category == "authentication"
        assert event.success is True
        assert event.ip_address == "192.168.1.1"
    
    @pytest.mark.asyncio
    async def test_log_authorization_event(self, audit_service: AuditLoggingService):
        """Test authorization event logging."""
        event = await audit_service.log_authorization_event(
            event_type="permission_denied",
            api_key_id=uuid4(),
            success=False,
            failure_reason="Insufficient permissions",
            resource_type="payment",
            resource_id="pay_123",
            action_attempted="delete"
        )
        
        assert event.event_type == "permission_denied"
        assert event.event_category == "authorization"
        assert event.success is False
        assert event.resource_type == "payment"
        assert event.resource_id == "pay_123"
    
    @pytest.mark.asyncio
    async def test_log_api_access_event(self, audit_service: AuditLoggingService):
        """Test API access event logging."""
        event = await audit_service.log_api_access_event(
            endpoint="/api/v1/payments",
            method="POST",
            api_key_id=uuid4(),
            success=True,
            status_code=200,
            response_time=150.5,
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        assert event.event_type == "api_access"
        assert event.event_category == "access"
        assert event.success is True
        assert event.details["status_code"] == 200
        assert event.details["response_time_ms"] == 150.5
    
    @pytest.mark.asyncio
    async def test_get_security_events(self, audit_service: AuditLoggingService):
        """Test getting security events."""
        # Create test events
        await audit_service.log_security_event(
            event_type="test_event_1",
            event_category="test",
            message="Test event 1",
            severity="info"
        )
        
        await audit_service.log_security_event(
            event_type="test_event_2",
            event_category="test",
            message="Test event 2",
            severity="warning"
        )
        
        # Get events
        events = await audit_service.get_security_events(
            event_category="test",
            limit=10
        )
        
        assert len(events) >= 2
        
        # Filter by severity
        warning_events = await audit_service.get_security_events(
            event_category="test",
            severity="warning"
        )
        
        assert len(warning_events) >= 1
        assert all(event.severity == "warning" for event in warning_events)
    
    @pytest.mark.asyncio
    async def test_get_security_event_stats(self, audit_service: AuditLoggingService):
        """Test getting security event statistics."""
        # Create test events
        await audit_service.log_security_event(
            event_type="success_event",
            event_category="test",
            message="Success event",
            severity="info",
            success=True
        )
        
        await audit_service.log_security_event(
            event_type="failure_event",
            event_category="test",
            message="Failure event",
            severity="error",
            success=False
        )
        
        await audit_service.log_security_event(
            event_type="critical_event",
            event_category="test",
            message="Critical event",
            severity="critical",
            success=False
        )
        
        # Get stats
        stats = await audit_service.get_security_event_stats(hours=24)
        
        assert stats["total_events"] >= 3
        assert stats["failed_events"] >= 2
        assert stats["critical_events"] >= 1
        assert stats["success_rate"] >= 0


class TestSecurityIntegration:
    """Test integration of all security features."""
    
    @pytest.mark.asyncio
    async def test_complete_security_flow(self, db_session: AsyncSession):
        """Test complete security flow integration."""
        # Initialize services
        rbac_service = RBACService(db_session)
        scoping_service = ScopingService(db_session)
        audit_service = AuditLoggingService(db_session)
        signing_service = RequestSigningService("test-secret")
        
        # Create role and permission
        role = await rbac_service.create_role(
            name="payment_manager",
            display_name="Payment Manager",
            permissions=["payment:read", "payment:write"]
        )
        
        # Create API key with role
        api_key = APIKey(
            key_id="test_key",
            key_secret_hash="hashed_secret",
            name="Test Key",
            role_id=role.id,
            status=APIKeyStatus.ACTIVE
        )
        
        db_session.add(api_key)
        await db_session.commit()
        
        # Create scopes
        await scoping_service.create_environment_scope(
            api_key_id=api_key.id,
            environment="sandbox"
        )
        
        await scoping_service.create_domain_scope(
            api_key_id=api_key.id,
            domain="example.com"
        )
        
        # Test permission check
        has_permission = await rbac_service.check_permission(
            api_key_id=api_key.id,
            resource_type="payment",
            action="read"
        )
        assert has_permission is True
        
        # Test scoping validation
        validation_result = await scoping_service.validate_api_key_access(
            api_key_id=api_key.id,
            environment="sandbox",
            domain="example.com",
            client_ip="192.168.1.1"
        )
        assert validation_result["valid"] is True
        
        # Test request signing
        method = "POST"
        url = "https://api.easypay.com/v1/payments"
        headers = {"Content-Type": "application/json"}
        body = '{"amount": 1000}'
        
        signature = signing_service.generate_signature(
            method=method,
            url=url,
            headers=headers,
            body=body
        )
        
        is_valid = signing_service.verify_signature(
            method=method,
            url=url,
            headers=headers,
            body=body,
            signature=signature,
            timestamp=int(datetime.now().timestamp())
        )
        assert is_valid is True
        
        # Test audit logging
        event = await audit_service.log_security_event(
            event_type="integration_test",
            event_category="test",
            message="Complete security flow test",
            api_key_id=api_key.id,
            severity="info",
            success=True
        )
        
        assert event.event_type == "integration_test"
        assert event.api_key_id == api_key.id
        assert event.success is True


@pytest.mark.asyncio
async def test_security_performance():
    """Test security features performance."""
    signing_service = RequestSigningService("test-secret")
    
    # Test signature generation performance
    start_time = datetime.now()
    
    for _ in range(100):
        signature = signing_service.generate_signature(
            method="POST",
            url="https://api.easypay.com/v1/payments",
            headers={"Content-Type": "application/json"},
            body='{"amount": 1000}'
        )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Should complete 100 signatures in less than 1 second
    assert duration < 1.0
    
    # Test signature verification performance
    start_time = datetime.now()
    
    for _ in range(100):
        is_valid = signing_service.verify_signature(
            method="POST",
            url="https://api.easypay.com/v1/payments",
            headers={"Content-Type": "application/json"},
            body='{"amount": 1000}',
            signature=signature,
            timestamp=int(datetime.now().timestamp())
        )
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Should complete 100 verifications in less than 1 second
    assert duration < 1.0
