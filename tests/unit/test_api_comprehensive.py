"""
Comprehensive tests for API components to achieve 80%+ coverage.
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# API imports
from src.api.v1.schemas.payment import (
    PaymentCreateRequest, PaymentUpdateRequest, PaymentRefundRequest,
    PaymentCancelRequest, PaymentResponse, PaymentListResponse,
    PaymentStatusResponse, PaymentMethodResponse
)
from src.api.v1.schemas.auth import (
    APIKeyCreateRequest, APIKeyUpdateRequest, APIKeyResponse,
    APIKeyListResponse, AuthTokenRequest, AuthTokenResponse
)
from src.api.v1.schemas.webhook import (
    WebhookCreateRequest, WebhookUpdateRequest, WebhookResponse,
    WebhookListResponse, WebhookEventRequest, WebhookEventResponse
)
from src.api.v1.schemas.common import (
    ErrorResponse, SuccessResponse, PaginationRequest, PaginationResponse,
    SortRequest, FilterRequest, HealthCheckResponse
)
from src.api.v1.schemas.errors import (
    ValidationErrorResponse, BusinessErrorResponse, SystemErrorResponse
)
from src.api.v1.schemas.versioning import (
    VersionInfo, VersionResponse, CompatibilityInfo
)

# Core model imports
from src.core.models.payment import PaymentStatus, PaymentMethod
from src.core.models.auth import APIKeyStatus, TokenType
from src.core.models.webhook import WebhookStatus
from src.core.models.audit_log import AuditLogLevel


class TestPaymentSchemasComprehensive:
    """Comprehensive tests for payment-related schemas."""
    
    def test_payment_create_request_comprehensive(self):
        """Test PaymentCreateRequest with all fields."""
        request = PaymentCreateRequest(
            amount=Decimal("100.50"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            customer_name="Test Customer",
            card_token="tok_123456789",
            description="Test payment creation",
            metadata={"order_id": "order_123", "source": "web"},
            is_test=True,
            webhook_url="https://example.com/webhook",
            webhook_secret="webhook_secret_123"
        )
        
        assert request.amount == Decimal("100.50")
        assert request.currency == "USD"
        assert request.payment_method == PaymentMethod.CREDIT_CARD.value
        assert request.customer_id == "cust_123"
        assert request.customer_email == "test@example.com"
        assert request.customer_name == "Test Customer"
        assert request.card_token == "tok_123456789"
        assert request.description == "Test payment creation"
        assert request.metadata == {"order_id": "order_123", "source": "web"}
        assert request.is_test is True
        assert request.webhook_url == "https://example.com/webhook"
        assert request.webhook_secret == "webhook_secret_123"
    
    def test_payment_update_request_comprehensive(self):
        """Test PaymentUpdateRequest with all fields."""
        request = PaymentUpdateRequest(
            description="Updated payment description",
            metadata={"updated": True, "timestamp": datetime.utcnow().isoformat()},
            customer_email="updated@example.com",
            customer_name="Updated Customer Name"
        )
        
        assert request.description == "Updated payment description"
        assert request.metadata["updated"] is True
        assert request.customer_email == "updated@example.com"
        assert request.customer_name == "Updated Customer Name"
    
    def test_payment_refund_request_comprehensive(self):
        """Test PaymentRefundRequest with all fields."""
        request = PaymentRefundRequest(
            amount=Decimal("50.00"),
            reason="Customer request for refund",
            metadata={"refund_reason": "customer_request", "processed_by": "admin"},
            notify_customer=True,
            refund_method="original_payment_method"
        )
        
        assert request.amount == Decimal("50.00")
        assert request.reason == "Customer request for refund"
        assert request.metadata["refund_reason"] == "customer_request"
        assert request.notify_customer is True
        assert request.refund_method == "original_payment_method"
    
    def test_payment_cancel_request_comprehensive(self):
        """Test PaymentCancelRequest with all fields."""
        request = PaymentCancelRequest(
            reason="Customer cancelled the order",
            metadata={"cancellation_reason": "customer_cancelled", "processed_by": "system"},
            notify_customer=True,
            refund_amount=Decimal("100.00")
        )
        
        assert request.reason == "Customer cancelled the order"
        assert request.metadata["cancellation_reason"] == "customer_cancelled"
        assert request.notify_customer is True
        assert request.refund_amount == Decimal("100.00")
    
    def test_payment_response_comprehensive(self):
        """Test PaymentResponse with all fields."""
        response = PaymentResponse(
            id=str(uuid.uuid4()),
            external_id="pay_123456789",
            amount=Decimal("100.50"),
            currency="USD",
            status=PaymentStatus.CAPTURED.value,
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_123",
            customer_email="test@example.com",
            customer_name="Test Customer",
            description="Test payment response",
            metadata={"order_id": "order_123"},
            is_test=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            refunded_amount=Decimal("0.00"),
            refund_count=0,
            webhook_url="https://example.com/webhook",
            webhook_status=WebhookStatus.SENT.value
        )
        
        assert response.id is not None
        assert response.external_id == "pay_123456789"
        assert response.amount == Decimal("100.50")
        assert response.currency == "USD"
        assert response.status == PaymentStatus.CAPTURED.value
        assert response.payment_method == PaymentMethod.CREDIT_CARD.value
        assert response.customer_id == "cust_123"
        assert response.customer_email == "test@example.com"
        assert response.customer_name == "Test Customer"
        assert response.description == "Test payment response"
        assert response.metadata == {"order_id": "order_123"}
        assert response.is_test is True
        assert response.created_at is not None
        assert response.updated_at is not None
        assert response.refunded_amount == Decimal("0.00")
        assert response.refund_count == 0
        assert response.webhook_url == "https://example.com/webhook"
        assert response.webhook_status == WebhookStatus.SENT.value
    
    def test_payment_list_response_comprehensive(self):
        """Test PaymentListResponse with all fields."""
        payments = [
            PaymentResponse(
                id=str(uuid.uuid4()),
                external_id="pay_1",
                amount=Decimal("10.00"),
                currency="USD",
                status=PaymentStatus.PENDING.value,
                payment_method=PaymentMethod.CREDIT_CARD.value
            ),
            PaymentResponse(
                id=str(uuid.uuid4()),
                external_id="pay_2",
                amount=Decimal("20.00"),
                currency="USD",
                status=PaymentStatus.CAPTURED.value,
                payment_method=PaymentMethod.DEBIT_CARD.value
            )
        ]
        
        response = PaymentListResponse(
            payments=payments,
            total_count=2,
            page=1,
            page_size=10,
            total_pages=1,
            has_next=False,
            has_previous=False
        )
        
        assert len(response.payments) == 2
        assert response.total_count == 2
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 1
        assert response.has_next is False
        assert response.has_previous is False
    
    def test_payment_status_response_comprehensive(self):
        """Test PaymentStatusResponse with all fields."""
        response = PaymentStatusResponse(
            external_id="pay_123456789",
            status=PaymentStatus.CAPTURED.value,
            amount=Decimal("100.50"),
            currency="USD",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            refunded_amount=Decimal("25.00"),
            refund_count=1
        )
        
        assert response.external_id == "pay_123456789"
        assert response.status == PaymentStatus.CAPTURED.value
        assert response.amount == Decimal("100.50")
        assert response.currency == "USD"
        assert response.created_at is not None
        assert response.updated_at is not None
        assert response.refunded_amount == Decimal("25.00")
        assert response.refund_count == 1
    
    def test_payment_method_response_comprehensive(self):
        """Test PaymentMethodResponse with all fields."""
        response = PaymentMethodResponse(
            method=PaymentMethod.CREDIT_CARD.value,
            display_name="Credit Card",
            description="Pay with credit card",
            supported_currencies=["USD", "EUR", "GBP"],
            is_available=True,
            processing_fee_percent=Decimal("2.9"),
            processing_fee_fixed=Decimal("0.30")
        )
        
        assert response.method == PaymentMethod.CREDIT_CARD.value
        assert response.display_name == "Credit Card"
        assert response.description == "Pay with credit card"
        assert response.supported_currencies == ["USD", "EUR", "GBP"]
        assert response.is_available is True
        assert response.processing_fee_percent == Decimal("2.9")
        assert response.processing_fee_fixed == Decimal("0.30")


class TestAuthSchemasComprehensive:
    """Comprehensive tests for auth-related schemas."""
    
    def test_api_key_create_request_comprehensive(self):
        """Test APIKeyCreateRequest with all fields."""
        request = APIKeyCreateRequest(
            name="Test API Key",
            description="Test API key for comprehensive testing",
            permissions=["payments:read", "payments:write", "webhooks:read"],
            rate_limit_per_minute=100,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            ip_whitelist=["192.168.1.0/24", "10.0.0.0/8"],
            ip_blacklist=["192.168.1.100"],
            expires_at=datetime.utcnow() + timedelta(days=30),
            is_test=True
        )
        
        assert request.name == "Test API Key"
        assert request.description == "Test API key for comprehensive testing"
        assert request.permissions == ["payments:read", "payments:write", "webhooks:read"]
        assert request.rate_limit_per_minute == 100
        assert request.rate_limit_per_hour == 1000
        assert request.rate_limit_per_day == 10000
        assert request.ip_whitelist == ["192.168.1.0/24", "10.0.0.0/8"]
        assert request.ip_blacklist == ["192.168.1.100"]
        assert request.expires_at is not None
        assert request.is_test is True
    
    def test_api_key_update_request_comprehensive(self):
        """Test APIKeyUpdateRequest with all fields."""
        request = APIKeyUpdateRequest(
            name="Updated API Key",
            description="Updated description",
            permissions=["payments:read"],
            rate_limit_per_minute=50,
            rate_limit_per_hour=500,
            rate_limit_per_day=5000,
            ip_whitelist=["192.168.1.0/24"],
            ip_blacklist=[],
            status=APIKeyStatus.INACTIVE.value
        )
        
        assert request.name == "Updated API Key"
        assert request.description == "Updated description"
        assert request.permissions == ["payments:read"]
        assert request.rate_limit_per_minute == 50
        assert request.rate_limit_per_hour == 500
        assert request.rate_limit_per_day == 5000
        assert request.ip_whitelist == ["192.168.1.0/24"]
        assert request.ip_blacklist == []
        assert request.status == APIKeyStatus.INACTIVE.value
    
    def test_api_key_response_comprehensive(self):
        """Test APIKeyResponse with all fields."""
        response = APIKeyResponse(
            id=str(uuid.uuid4()),
            key_id="ak_123456789",
            name="Test API Key",
            description="Test API key response",
            permissions=["payments:read", "payments:write"],
            status=APIKeyStatus.ACTIVE.value,
            rate_limit_per_minute=100,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            ip_whitelist=["192.168.1.0/24"],
            ip_blacklist=["192.168.1.100"],
            usage_count=150,
            last_used_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_test=True
        )
        
        assert response.id is not None
        assert response.key_id == "ak_123456789"
        assert response.name == "Test API Key"
        assert response.description == "Test API key response"
        assert response.permissions == ["payments:read", "payments:write"]
        assert response.status == APIKeyStatus.ACTIVE.value
        assert response.rate_limit_per_minute == 100
        assert response.rate_limit_per_hour == 1000
        assert response.rate_limit_per_day == 10000
        assert response.ip_whitelist == ["192.168.1.0/24"]
        assert response.ip_blacklist == ["192.168.1.100"]
        assert response.usage_count == 150
        assert response.last_used_at is not None
        assert response.expires_at is not None
        assert response.created_at is not None
        assert response.updated_at is not None
        assert response.is_test is True
    
    def test_api_key_list_response_comprehensive(self):
        """Test APIKeyListResponse with all fields."""
        api_keys = [
            APIKeyResponse(
                id=str(uuid.uuid4()),
                key_id="ak_1",
                name="API Key 1",
                status=APIKeyStatus.ACTIVE.value
            ),
            APIKeyResponse(
                id=str(uuid.uuid4()),
                key_id="ak_2",
                name="API Key 2",
                status=APIKeyStatus.INACTIVE.value
            )
        ]
        
        response = APIKeyListResponse(
            api_keys=api_keys,
            total_count=2,
            page=1,
            page_size=10,
            total_pages=1,
            has_next=False,
            has_previous=False
        )
        
        assert len(response.api_keys) == 2
        assert response.total_count == 2
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 1
        assert response.has_next is False
        assert response.has_previous is False
    
    def test_auth_token_request_comprehensive(self):
        """Test AuthTokenRequest with all fields."""
        request = AuthTokenRequest(
            grant_type="client_credentials",
            client_id="client_123",
            client_secret="secret_123",
            scope=["payments:read", "payments:write"]
        )
        
        assert request.grant_type == "client_credentials"
        assert request.client_id == "client_123"
        assert request.client_secret == "secret_123"
        assert request.scope == ["payments:read", "payments:write"]
    
    def test_auth_token_response_comprehensive(self):
        """Test AuthTokenResponse with all fields."""
        response = AuthTokenResponse(
            access_token="access_token_123",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="refresh_token_123",
            scope=["payments:read", "payments:write"]
        )
        
        assert response.access_token == "access_token_123"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
        assert response.refresh_token == "refresh_token_123"
        assert response.scope == ["payments:read", "payments:write"]


class TestWebhookSchemasComprehensive:
    """Comprehensive tests for webhook-related schemas."""
    
    def test_webhook_create_request_comprehensive(self):
        """Test WebhookCreateRequest with all fields."""
        request = WebhookCreateRequest(
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            is_active=True,
            secret="webhook_secret_123",
            metadata={"source": "test", "environment": "development"},
            max_retries=3,
            timeout_seconds=30,
            retry_delay_seconds=60
        )
        
        assert request.webhook_url == "https://example.com/webhook"
        assert request.event_type == "payment.created"
        assert request.is_active is True
        assert request.secret == "webhook_secret_123"
        assert request.metadata == {"source": "test", "environment": "development"}
        assert request.max_retries == 3
        assert request.timeout_seconds == 30
        assert request.retry_delay_seconds == 60
    
    def test_webhook_update_request_comprehensive(self):
        """Test WebhookUpdateRequest with all fields."""
        request = WebhookUpdateRequest(
            webhook_url="https://updated.example.com/webhook",
            is_active=False,
            secret="updated_webhook_secret_123",
            metadata={"updated": True},
            max_retries=5,
            timeout_seconds=45,
            retry_delay_seconds=120
        )
        
        assert request.webhook_url == "https://updated.example.com/webhook"
        assert request.is_active is False
        assert request.secret == "updated_webhook_secret_123"
        assert request.metadata["updated"] is True
        assert request.max_retries == 5
        assert request.timeout_seconds == 45
        assert request.retry_delay_seconds == 120
    
    def test_webhook_response_comprehensive(self):
        """Test WebhookResponse with all fields."""
        response = WebhookResponse(
            id=str(uuid.uuid4()),
            webhook_url="https://example.com/webhook",
            event_type="payment.created",
            is_active=True,
            secret="webhook_secret_123",
            metadata={"source": "test"},
            retry_count=0,
            max_retries=3,
            timeout_seconds=30,
            last_sent_at=datetime.utcnow(),
            next_retry_at=None,
            status=WebhookStatus.PENDING.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert response.id is not None
        assert response.webhook_url == "https://example.com/webhook"
        assert response.event_type == "payment.created"
        assert response.is_active is True
        assert response.secret == "webhook_secret_123"
        assert response.metadata == {"source": "test"}
        assert response.retry_count == 0
        assert response.max_retries == 3
        assert response.timeout_seconds == 30
        assert response.last_sent_at is not None
        assert response.next_retry_at is None
        assert response.status == WebhookStatus.PENDING.value
        assert response.created_at is not None
        assert response.updated_at is not None
    
    def test_webhook_list_response_comprehensive(self):
        """Test WebhookListResponse with all fields."""
        webhooks = [
            WebhookResponse(
                id=str(uuid.uuid4()),
                webhook_url="https://example1.com/webhook",
                event_type="payment.created",
                status=WebhookStatus.PENDING.value
            ),
            WebhookResponse(
                id=str(uuid.uuid4()),
                webhook_url="https://example2.com/webhook",
                event_type="payment.updated",
                status=WebhookStatus.SENT.value
            )
        ]
        
        response = WebhookListResponse(
            webhooks=webhooks,
            total_count=2,
            page=1,
            page_size=10,
            total_pages=1,
            has_next=False,
            has_previous=False
        )
        
        assert len(response.webhooks) == 2
        assert response.total_count == 2
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 1
        assert response.has_next is False
        assert response.has_previous is False
    
    def test_webhook_event_request_comprehensive(self):
        """Test WebhookEventRequest with all fields."""
        request = WebhookEventRequest(
            event_type="payment.created",
            event_data={"payment_id": "pay_123", "amount": "100.00"},
            webhook_id=str(uuid.uuid4()),
            retry_count=0
        )
        
        assert request.event_type == "payment.created"
        assert request.event_data == {"payment_id": "pay_123", "amount": "100.00"}
        assert request.webhook_id is not None
        assert request.retry_count == 0
    
    def test_webhook_event_response_comprehensive(self):
        """Test WebhookEventResponse with all fields."""
        response = WebhookEventResponse(
            event_id=str(uuid.uuid4()),
            webhook_id=str(uuid.uuid4()),
            status=WebhookStatus.SENT.value,
            response_code=200,
            response_body="OK",
            sent_at=datetime.utcnow(),
            retry_count=0
        )
        
        assert response.event_id is not None
        assert response.webhook_id is not None
        assert response.status == WebhookStatus.SENT.value
        assert response.response_code == 200
        assert response.response_body == "OK"
        assert response.sent_at is not None
        assert response.retry_count == 0


class TestCommonSchemasComprehensive:
    """Comprehensive tests for common schemas."""
    
    def test_error_response_comprehensive(self):
        """Test ErrorResponse with all fields."""
        response = ErrorResponse(
            error_type="validation_error",
            error_code="invalid_amount",
            message="Amount must be greater than 0",
            param="amount",
            request_id="req_123456789",
            timestamp=datetime.utcnow(),
            details={"min_amount": "0.01", "provided_amount": "0.00"}
        )
        
        assert response.error_type == "validation_error"
        assert response.error_code == "invalid_amount"
        assert response.message == "Amount must be greater than 0"
        assert response.param == "amount"
        assert response.request_id == "req_123456789"
        assert response.timestamp is not None
        assert response.details == {"min_amount": "0.01", "provided_amount": "0.00"}
    
    def test_success_response_comprehensive(self):
        """Test SuccessResponse with all fields."""
        response = SuccessResponse(
            data={"id": "pay_123456789", "status": "completed"},
            request_id="req_123456789",
            timestamp=datetime.utcnow(),
            message="Operation completed successfully"
        )
        
        assert response.data == {"id": "pay_123456789", "status": "completed"}
        assert response.request_id == "req_123456789"
        assert response.timestamp is not None
        assert response.message == "Operation completed successfully"
    
    def test_pagination_request_comprehensive(self):
        """Test PaginationRequest with all fields."""
        request = PaginationRequest(
            page=2,
            page_size=20,
            sort_by="created_at",
            sort_order="desc"
        )
        
        assert request.page == 2
        assert request.page_size == 20
        assert request.sort_by == "created_at"
        assert request.sort_order == "desc"
    
    def test_pagination_response_comprehensive(self):
        """Test PaginationResponse with all fields."""
        response = PaginationResponse(
            total_count=100,
            page=2,
            page_size=20,
            total_pages=5,
            has_next=True,
            has_previous=True
        )
        
        assert response.total_count == 100
        assert response.page == 2
        assert response.page_size == 20
        assert response.total_pages == 5
        assert response.has_next is True
        assert response.has_previous is True
    
    def test_sort_request_comprehensive(self):
        """Test SortRequest with all fields."""
        request = SortRequest(
            field="created_at",
            order="desc"
        )
        
        assert request.field == "created_at"
        assert request.order == "desc"
    
    def test_filter_request_comprehensive(self):
        """Test FilterRequest with all fields."""
        request = FilterRequest(
            field="status",
            operator="eq",
            value="completed",
            logical_operator="and"
        )
        
        assert request.field == "status"
        assert request.operator == "eq"
        assert request.value == "completed"
        assert request.logical_operator == "and"
    
    def test_health_check_response_comprehensive(self):
        """Test HealthCheckResponse with all fields."""
        response = HealthCheckResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            uptime_seconds=3600,
            services={
                "database": "healthy",
                "cache": "healthy",
                "external_api": "degraded"
            }
        )
        
        assert response.status == "healthy"
        assert response.timestamp is not None
        assert response.version == "1.0.0"
        assert response.uptime_seconds == 3600
        assert response.services["database"] == "healthy"
        assert response.services["cache"] == "healthy"
        assert response.services["external_api"] == "degraded"


class TestErrorSchemasComprehensive:
    """Comprehensive tests for error schemas."""
    
    def test_validation_error_response_comprehensive(self):
        """Test ValidationErrorResponse with all fields."""
        response = ValidationErrorResponse(
            error_type="validation_error",
            error_code="invalid_input",
            message="Validation failed",
            request_id="req_123456789",
            timestamp=datetime.utcnow(),
            validation_errors=[
                {"field": "amount", "message": "Amount must be greater than 0"},
                {"field": "currency", "message": "Currency is required"}
            ]
        )
        
        assert response.error_type == "validation_error"
        assert response.error_code == "invalid_input"
        assert response.message == "Validation failed"
        assert response.request_id == "req_123456789"
        assert response.timestamp is not None
        assert len(response.validation_errors) == 2
        assert response.validation_errors[0]["field"] == "amount"
        assert response.validation_errors[1]["field"] == "currency"
    
    def test_business_error_response_comprehensive(self):
        """Test BusinessErrorResponse with all fields."""
        response = BusinessErrorResponse(
            error_type="business_error",
            error_code="insufficient_funds",
            message="Insufficient funds for payment",
            request_id="req_123456789",
            timestamp=datetime.utcnow(),
            business_context={"account_balance": "50.00", "payment_amount": "100.00"}
        )
        
        assert response.error_type == "business_error"
        assert response.error_code == "insufficient_funds"
        assert response.message == "Insufficient funds for payment"
        assert response.request_id == "req_123456789"
        assert response.timestamp is not None
        assert response.business_context["account_balance"] == "50.00"
        assert response.business_context["payment_amount"] == "100.00"
    
    def test_system_error_response_comprehensive(self):
        """Test SystemErrorResponse with all fields."""
        response = SystemErrorResponse(
            error_type="system_error",
            error_code="internal_server_error",
            message="Internal server error occurred",
            request_id="req_123456789",
            timestamp=datetime.utcnow(),
            system_context={"component": "payment_service", "error_id": "err_123"}
        )
        
        assert response.error_type == "system_error"
        assert response.error_code == "internal_server_error"
        assert response.message == "Internal server error occurred"
        assert response.request_id == "req_123456789"
        assert response.timestamp is not None
        assert response.system_context["component"] == "payment_service"
        assert response.system_context["error_id"] == "err_123"


class TestVersioningSchemasComprehensive:
    """Comprehensive tests for versioning schemas."""
    
    def test_version_info_comprehensive(self):
        """Test VersionInfo with all fields."""
        version_info = VersionInfo(
            version="1.2.3",
            major=1,
            minor=2,
            patch=3,
            prerelease="beta.1",
            build="20240101"
        )
        
        assert version_info.version == "1.2.3"
        assert version_info.major == 1
        assert version_info.minor == 2
        assert version_info.patch == 3
        assert version_info.prerelease == "beta.1"
        assert version_info.build == "20240101"
    
    def test_version_response_comprehensive(self):
        """Test VersionResponse with all fields."""
        response = VersionResponse(
            current_version=VersionInfo(version="1.2.3", major=1, minor=2, patch=3),
            supported_versions=["1.0.0", "1.1.0", "1.2.0", "1.2.3"],
            deprecated_versions=["0.9.0", "0.9.1"],
            sunset_date=datetime.utcnow() + timedelta(days=90)
        )
        
        assert response.current_version.version == "1.2.3"
        assert len(response.supported_versions) == 4
        assert len(response.deprecated_versions) == 2
        assert response.sunset_date is not None
    
    def test_compatibility_info_comprehensive(self):
        """Test CompatibilityInfo with all fields."""
        compatibility_info = CompatibilityInfo(
            client_version="1.1.0",
            server_version="1.2.3",
            is_compatible=True,
            compatibility_level="minor",
            warnings=["Feature X is deprecated"],
            breaking_changes=[]
        )
        
        assert compatibility_info.client_version == "1.1.0"
        assert compatibility_info.server_version == "1.2.3"
        assert compatibility_info.is_compatible is True
        assert compatibility_info.compatibility_level == "minor"
        assert len(compatibility_info.warnings) == 1
        assert len(compatibility_info.breaking_changes) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
