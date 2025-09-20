"""
EasyPay Payment Gateway - API Endpoints Integration Tests
"""
import pytest
import uuid
from decimal import Decimal
from httpx import AsyncClient

from src.core.models.payment import PaymentStatus, PaymentMethod


class TestPaymentEndpoints:
    """Integration tests for payment API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_payment_endpoint(self, test_client: AsyncClient):
        """Test POST /payments endpoint."""
        payment_data = {
            "amount": "25.50",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_api_test",
            "customer_email": "api@example.com",
            "customer_name": "API Test Customer",
            "card_token": "tok_api_test",
            "description": "API test payment",
            "metadata": {"test_type": "api_endpoint"},
            "is_test": True
        }
        
        response = await test_client.post("/api/v1/payments/", json=payment_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert "external_id" in data
        assert data["amount"] == "25.50"
        assert data["currency"] == "USD"
        assert data["status"] == PaymentStatus.PENDING.value
        assert data["customer_id"] == "cust_api_test"
        assert data["customer_email"] == "api@example.com"
        assert data["description"] == "API test payment"
        assert data["is_test"] is True
    
    @pytest.mark.asyncio
    async def test_create_payment_with_correlation_id(self, test_client: AsyncClient):
        """Test POST /payments endpoint with correlation ID."""
        payment_data = {
            "amount": "15.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_correlation_test",
            "customer_email": "correlation@example.com",
            "customer_name": "Correlation Test Customer",
            "card_token": "tok_correlation_test",
            "description": "Correlation test payment",
            "is_test": True
        }
        
        headers = {"X-Correlation-ID": "test-correlation-123"}
        response = await test_client.post("/api/v1/payments/", json=payment_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == "15.00"
    
    @pytest.mark.asyncio
    async def test_create_payment_validation_error(self, test_client: AsyncClient):
        """Test POST /payments endpoint with validation error."""
        invalid_payment_data = {
            "amount": "-10.00",  # Invalid negative amount
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_validation_test",
            "customer_email": "validation@example.com",
            "customer_name": "Validation Test Customer",
            "card_token": "tok_validation_test",
            "description": "Validation test payment",
            "is_test": True
        }
        
        response = await test_client.post("/api/v1/payments/", json=invalid_payment_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Payment amount must be greater than 0" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_get_payment_by_uuid(self, test_client: AsyncClient, sample_payment):
        """Test GET /payments/{id} endpoint with UUID."""
        response = await test_client.get(f"/api/v1/payments/{sample_payment.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(sample_payment.id)
        assert data["external_id"] == sample_payment.external_id
        assert data["amount"] == str(sample_payment.amount)
        assert data["currency"] == sample_payment.currency
        assert data["status"] == sample_payment.status.value
    
    @pytest.mark.asyncio
    async def test_get_payment_by_external_id(self, test_client: AsyncClient, sample_payment):
        """Test GET /payments/{id} endpoint with external ID."""
        response = await test_client.get(f"/api/v1/payments/{sample_payment.external_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(sample_payment.id)
        assert data["external_id"] == sample_payment.external_id
    
    @pytest.mark.asyncio
    async def test_get_payment_not_found(self, test_client: AsyncClient):
        """Test GET /payments/{id} endpoint with non-existent ID."""
        non_existent_id = str(uuid.uuid4())
        response = await test_client.get(f"/api/v1/payments/{non_existent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Payment {non_existent_id} not found" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_list_payments_endpoint(self, test_client: AsyncClient, sample_payment):
        """Test GET /payments endpoint."""
        response = await test_client.get("/api/v1/payments/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "payments" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        assert len(data["payments"]) >= 1
        assert data["total"] >= 1
    
    @pytest.mark.asyncio
    async def test_list_payments_with_filters(self, test_client: AsyncClient, sample_payment):
        """Test GET /payments endpoint with filters."""
        # Test filtering by customer_id
        response = await test_client.get(
            f"/api/v1/payments/?customer_id={sample_payment.customer_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["payments"]) >= 1
        for payment in data["payments"]:
            assert payment["customer_id"] == sample_payment.customer_id
        
        # Test filtering by status
        response = await test_client.get(
            f"/api/v1/payments/?status={sample_payment.status.value}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["payments"]) >= 1
        for payment in data["payments"]:
            assert payment["status"] == sample_payment.status.value
    
    @pytest.mark.asyncio
    async def test_list_payments_pagination(self, test_client: AsyncClient):
        """Test GET /payments endpoint pagination."""
        response = await test_client.get("/api/v1/payments/?page=1&per_page=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["per_page"] == 5
        assert len(data["payments"]) <= 5
    
    @pytest.mark.asyncio
    async def test_list_payments_invalid_status(self, test_client: AsyncClient):
        """Test GET /payments endpoint with invalid status."""
        response = await test_client.get("/api/v1/payments/?status=invalid_status")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid status" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_update_payment_endpoint(self, test_client: AsyncClient, sample_payment):
        """Test PUT /payments/{id} endpoint."""
        update_data = {
            "description": "Updated via API",
            "metadata": {"updated_via": "api", "timestamp": "2024-01-01T00:00:00Z"}
        }
        
        response = await test_client.put(
            f"/api/v1/payments/{sample_payment.id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(sample_payment.id)
        assert data["description"] == "Updated via API"
        assert data["metadata"]["updated_via"] == "api"
    
    @pytest.mark.asyncio
    async def test_update_payment_by_external_id(self, test_client: AsyncClient, sample_payment):
        """Test PUT /payments/{id} endpoint with external ID."""
        update_data = {
            "description": "Updated via external ID",
            "metadata": {"updated_via": "external_id"}
        }
        
        response = await test_client.put(
            f"/api/v1/payments/{sample_payment.external_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(sample_payment.id)
        assert data["description"] == "Updated via external ID"
    
    @pytest.mark.asyncio
    async def test_update_payment_validation_error(self, test_client: AsyncClient, sample_payment):
        """Test PUT /payments/{id} endpoint with validation error."""
        invalid_update_data = {
            "description": None,
            "metadata": None  # Both fields are None
        }
        
        response = await test_client.put(
            f"/api/v1/payments/{sample_payment.id}",
            json=invalid_update_data
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "At least one field must be provided for update" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_refund_payment_endpoint(self, test_client: AsyncClient, sample_payment):
        """Test POST /payments/{id}/refund endpoint."""
        # First, set the payment status to COMPLETED to make it refundable
        # This would normally be done by Authorize.net processing
        sample_payment.status = PaymentStatus.COMPLETED
        await sample_payment.awaitable_attrs.session.commit()
        
        refund_data = {
            "amount": "5.00",
            "reason": "API test refund",
            "metadata": {"refund_via": "api"}
        }
        
        response = await test_client.post(
            f"/api/v1/payments/{sample_payment.id}/refund",
            json=refund_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(sample_payment.id)
        assert data["status"] in [PaymentStatus.REFUNDED.value, PaymentStatus.PARTIALLY_REFUNDED.value]
        assert data["refunded_amount"] == "5.00"
        assert data["refund_count"] == 1
    
    @pytest.mark.asyncio
    async def test_refund_payment_with_correlation_id(self, test_client: AsyncClient, sample_payment):
        """Test POST /payments/{id}/refund endpoint with correlation ID."""
        # Set payment status to COMPLETED
        sample_payment.status = PaymentStatus.COMPLETED
        await sample_payment.awaitable_attrs.session.commit()
        
        refund_data = {
            "amount": "3.00",
            "reason": "Correlation test refund"
        }
        
        headers = {"X-Correlation-ID": "refund-correlation-456"}
        response = await test_client.post(
            f"/api/v1/payments/{sample_payment.id}/refund",
            json=refund_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["refunded_amount"] == "3.00"
    
    @pytest.mark.asyncio
    async def test_refund_payment_not_refundable(self, test_client: AsyncClient, sample_payment):
        """Test POST /payments/{id}/refund endpoint with non-refundable payment."""
        # Keep payment status as PENDING (not refundable)
        refund_data = {
            "amount": "5.00",
            "reason": "Test refund"
        }
        
        response = await test_client.post(
            f"/api/v1/payments/{sample_payment.id}/refund",
            json=refund_data
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Payment cannot be refunded" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_cancel_payment_endpoint(self, test_client: AsyncClient, sample_payment):
        """Test POST /payments/{id}/cancel endpoint."""
        # Keep payment status as PENDING (cancellable)
        cancel_data = {
            "reason": "API test cancellation",
            "metadata": {"cancelled_via": "api"}
        }
        
        response = await test_client.post(
            f"/api/v1/payments/{sample_payment.id}/cancel",
            json=cancel_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(sample_payment.id)
        assert data["status"] == PaymentStatus.VOIDED.value
    
    @pytest.mark.asyncio
    async def test_cancel_payment_not_cancellable(self, test_client: AsyncClient, sample_payment):
        """Test POST /payments/{id}/cancel endpoint with non-cancellable payment."""
        # Set payment status to COMPLETED (not cancellable)
        sample_payment.status = PaymentStatus.COMPLETED
        await sample_payment.awaitable_attrs.session.commit()
        
        cancel_data = {
            "reason": "Test cancellation"
        }
        
        response = await test_client.post(
            f"/api/v1/payments/{sample_payment.id}/cancel",
            json=cancel_data
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Payment cannot be cancelled" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_search_payments_endpoint(self, test_client: AsyncClient, sample_payment):
        """Test POST /payments/search endpoint."""
        search_data = {
            "customer_id": sample_payment.customer_id,
            "status": sample_payment.status.value,
            "page": 1,
            "per_page": 10
        }
        
        response = await test_client.post("/api/v1/payments/search", json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "payments" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data
        assert len(data["payments"]) >= 1
    
    @pytest.mark.asyncio
    async def test_search_payments_with_date_range(self, test_client: AsyncClient, sample_payment):
        """Test POST /payments/search endpoint with date range."""
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)
        
        search_data = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "page": 1,
            "per_page": 10
        }
        
        response = await test_client.post("/api/v1/payments/search", json=search_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "payments" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_get_payment_status_history_endpoint(self, test_client: AsyncClient, sample_payment):
        """Test GET /payments/{id}/status-history endpoint."""
        response = await test_client.get(f"/api/v1/payments/{sample_payment.id}/status-history")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a list (may be empty if no advanced features)
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_payment_metadata_endpoint(self, test_client: AsyncClient, sample_payment):
        """Test GET /payments/{id}/metadata endpoint."""
        response = await test_client.get(f"/api/v1/payments/{sample_payment.id}/metadata")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a dictionary (may be empty if no advanced features)
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_update_payment_metadata_endpoint(self, test_client: AsyncClient, sample_payment):
        """Test PUT /payments/{id}/metadata endpoint."""
        metadata = {
            "api_test": True,
            "updated_at": "2024-01-01T00:00:00Z",
            "source": "api_endpoint_test"
        }
        
        response = await test_client.put(
            f"/api/v1/payments/{sample_payment.id}/metadata",
            json=metadata
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert data["message"] == "Metadata updated successfully"
    
    @pytest.mark.asyncio
    async def test_get_circuit_breaker_metrics_endpoint(self, test_client: AsyncClient):
        """Test GET /payments/metrics/circuit-breakers endpoint."""
        response = await test_client.get("/api/v1/payments/metrics/circuit-breakers")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a dictionary (may be empty if no advanced features)
        assert isinstance(data, dict)


class TestPaymentEndpointsErrorHandling:
    """Test error handling in payment API endpoints."""
    
    @pytest.mark.asyncio
    async def test_invalid_json_request(self, test_client: AsyncClient):
        """Test endpoint with invalid JSON request."""
        response = await test_client.post(
            "/api/v1/payments/",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, test_client: AsyncClient):
        """Test endpoint with missing required fields."""
        incomplete_data = {
            "amount": "10.00",
            "currency": "USD"
            # Missing required fields
        }
        
        response = await test_client.post("/api/v1/payments/", json=incomplete_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_invalid_uuid_format(self, test_client: AsyncClient):
        """Test endpoint with invalid UUID format."""
        invalid_uuid = "not-a-uuid"
        response = await test_client.get(f"/api/v1/payments/{invalid_uuid}")
        
        # Should treat as external ID and return 404 if not found
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_large_request_body(self, test_client: AsyncClient):
        """Test endpoint with large request body."""
        large_metadata = {"data": "x" * 10000}  # Large metadata
        
        payment_data = {
            "amount": "10.00",
            "currency": "USD",
            "payment_method": PaymentMethod.CREDIT_CARD.value,
            "customer_id": "cust_large_test",
            "customer_email": "large@example.com",
            "customer_name": "Large Test Customer",
            "card_token": "tok_large_test",
            "description": "Large test payment",
            "metadata": large_metadata,
            "is_test": True
        }
        
        response = await test_client.post("/api/v1/payments/", json=payment_data)
        
        # Should handle large requests gracefully
        assert response.status_code in [201, 413, 422]  # Created, Payload Too Large, or validation error
