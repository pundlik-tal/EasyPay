"""
EasyPay Payment Gateway - Payment Integration Tests
"""
import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

from src.core.services.payment_service import PaymentService
from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.api.v1.schemas.payment import (
    PaymentCreateRequest,
    PaymentUpdateRequest,
    PaymentRefundRequest,
    PaymentCancelRequest
)


class TestPaymentIntegration:
    """Integration tests for payment operations."""
    
    @pytest.fixture
    def payment_service(self, test_db_session):
        """Create payment service instance."""
        return PaymentService(test_db_session)
    
    @pytest.mark.asyncio
    async def test_complete_payment_lifecycle(self, payment_service):
        """Test complete payment lifecycle: create -> update -> refund -> cancel."""
        # Create payment
        create_request = PaymentCreateRequest(
            amount=Decimal("100.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_integration_test",
            customer_email="integration@example.com",
            customer_name="Integration Test Customer",
            card_token="tok_integration_test",
            description="Integration test payment",
            metadata={"test_type": "lifecycle", "step": "create"},
            is_test=True
        )
        
        payment = await payment_service.create_payment(create_request)
        assert payment.status == PaymentStatus.PENDING
        assert payment.amount == Decimal("100.00")
        assert payment.customer_id == "cust_integration_test"
        
        # Update payment
        update_request = PaymentUpdateRequest(
            description="Updated integration test payment",
            metadata={"test_type": "lifecycle", "step": "update", "updated_at": datetime.utcnow().isoformat()}
        )
        
        updated_payment = await payment_service.update_payment(payment.id, update_request)
        assert updated_payment.description == "Updated integration test payment"
        assert updated_payment.payment_metadata["step"] == "update"
        
        # Simulate payment completion (normally done by Authorize.net)
        updated_payment.status = PaymentStatus.COMPLETED
        await payment_service.session.commit()
        
        # Refund partial amount
        refund_request = PaymentRefundRequest(
            amount=Decimal("30.00"),
            reason="Partial refund for testing",
            metadata={"test_type": "lifecycle", "step": "refund"}
        )
        
        refunded_payment = await payment_service.refund_payment(payment.id, refund_request)
        assert refunded_payment.status == PaymentStatus.PARTIALLY_REFUNDED
        assert refunded_payment.refunded_amount == Decimal("30.00")
        assert refunded_payment.refund_count == 1
        
        # Refund remaining amount
        remaining_refund_request = PaymentRefundRequest(
            amount=Decimal("70.00"),
            reason="Complete refund for testing",
            metadata={"test_type": "lifecycle", "step": "complete_refund"}
        )
        
        fully_refunded_payment = await payment_service.refund_payment(payment.id, remaining_refund_request)
        assert fully_refunded_payment.status == PaymentStatus.REFUNDED
        assert fully_refunded_payment.refunded_amount == Decimal("100.00")
        assert fully_refunded_payment.refund_count == 2
    
    @pytest.mark.asyncio
    async def test_payment_search_and_filtering(self, payment_service):
        """Test payment search and filtering capabilities."""
        # Create multiple payments with different attributes
        payments_data = [
            {
                "amount": Decimal("50.00"),
                "customer_id": "cust_search_1",
                "customer_email": "search1@example.com",
                "status": PaymentStatus.COMPLETED,
                "description": "Search test payment 1"
            },
            {
                "amount": Decimal("75.00"),
                "customer_id": "cust_search_2",
                "customer_email": "search2@example.com",
                "status": PaymentStatus.PENDING,
                "description": "Search test payment 2"
            },
            {
                "amount": Decimal("25.00"),
                "customer_id": "cust_search_1",  # Same customer as first payment
                "customer_email": "search1@example.com",
                "status": PaymentStatus.COMPLETED,
                "description": "Search test payment 3"
            }
        ]
        
        created_payments = []
        for payment_data in payments_data:
            create_request = PaymentCreateRequest(
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD.value,
                customer_name="Search Test Customer",
                card_token="tok_search_test",
                metadata={"test_type": "search"},
                is_test=True,
                **payment_data
            )
            
            payment = await payment_service.create_payment(create_request)
            # Set the status manually since we're not processing through Authorize.net
            payment.status = payment_data["status"]
            await payment_service.session.commit()
            created_payments.append(payment)
        
        # Test filtering by customer_id
        customer_payments = await payment_service.list_payments(customer_id="cust_search_1")
        assert customer_payments["total"] == 2
        assert len(customer_payments["payments"]) == 2
        
        # Test filtering by status
        completed_payments = await payment_service.list_payments(status=PaymentStatus.COMPLETED)
        assert completed_payments["total"] == 2
        assert len(completed_payments["payments"]) == 2
        
        # Test filtering by both customer_id and status
        customer_completed_payments = await payment_service.list_payments(
            customer_id="cust_search_1",
            status=PaymentStatus.COMPLETED
        )
        assert customer_completed_payments["total"] == 2
        assert len(customer_completed_payments["payments"]) == 2
        
        # Test search functionality
        search_results = await payment_service.search_payments("search1@example.com")
        assert search_results["total"] >= 2  # Should find payments for this email
        
        # Test pagination
        paginated_results = await payment_service.list_payments(page=1, per_page=2)
        assert len(paginated_results["payments"]) <= 2
        assert paginated_results["page"] == 1
        assert paginated_results["per_page"] == 2
    
    @pytest.mark.asyncio
    async def test_payment_statistics(self, payment_service):
        """Test payment statistics functionality."""
        # Create payments with different amounts and statuses
        test_payments = [
            {"amount": Decimal("100.00"), "status": PaymentStatus.COMPLETED, "customer_id": "cust_stats_1"},
            {"amount": Decimal("200.00"), "status": PaymentStatus.COMPLETED, "customer_id": "cust_stats_1"},
            {"amount": Decimal("50.00"), "status": PaymentStatus.PENDING, "customer_id": "cust_stats_2"},
            {"amount": Decimal("75.00"), "status": PaymentStatus.COMPLETED, "customer_id": "cust_stats_2"},
            {"amount": Decimal("25.00"), "status": PaymentStatus.REFUNDED, "customer_id": "cust_stats_1"}
        ]
        
        for payment_data in test_payments:
            create_request = PaymentCreateRequest(
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD.value,
                customer_email="stats@example.com",
                customer_name="Stats Test Customer",
                card_token="tok_stats_test",
                description="Stats test payment",
                metadata={"test_type": "statistics"},
                is_test=True,
                **payment_data
            )
            
            payment = await payment_service.create_payment(create_request)
            payment.status = payment_data["status"]
            await payment_service.session.commit()
        
        # Test overall statistics
        stats = await payment_service.get_payment_stats()
        assert stats["total_count"] >= 5
        assert "total_amount" in stats
        assert "status_counts" in stats
        
        # Test customer-specific statistics
        customer_stats = await payment_service.get_payment_stats(customer_id="cust_stats_1")
        assert customer_stats["total_count"] >= 3  # 3 payments for cust_stats_1
        
        # Test date range statistics
        start_date = datetime.utcnow() - timedelta(days=1)
        end_date = datetime.utcnow() + timedelta(days=1)
        
        date_range_stats = await payment_service.get_payment_stats(
            start_date=start_date,
            end_date=end_date
        )
        assert date_range_stats["total_count"] >= 5
    
    @pytest.mark.asyncio
    async def test_payment_error_scenarios(self, payment_service):
        """Test various error scenarios in payment operations."""
        # Test creating payment with invalid data
        with pytest.raises(ValidationError):
            invalid_request = PaymentCreateRequest(
                amount=Decimal("-10.00"),  # Negative amount
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD.value,
                customer_id="cust_error_test",
                customer_email="error@example.com",
                customer_name="Error Test Customer",
                card_token="tok_error_test",
                description="Error test payment",
                is_test=True
            )
            await payment_service.create_payment(invalid_request)
        
        # Create a valid payment first
        valid_request = PaymentCreateRequest(
            amount=Decimal("100.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_error_test",
            customer_email="error@example.com",
            customer_name="Error Test Customer",
            card_token="tok_error_test",
            description="Error test payment",
            is_test=True
        )
        
        payment = await payment_service.create_payment(valid_request)
        
        # Test updating with invalid data
        with pytest.raises(ValidationError):
            invalid_update = PaymentUpdateRequest(description=None, metadata=None)
            await payment_service.update_payment(payment.id, invalid_update)
        
        # Test refunding non-refundable payment (PENDING status)
        with pytest.raises(ValidationError):
            refund_request = PaymentRefundRequest(amount=Decimal("50.00"), reason="Test refund")
            await payment_service.refund_payment(payment.id, refund_request)
        
        # Test cancelling non-cancellable payment (after setting to COMPLETED)
        payment.status = PaymentStatus.COMPLETED
        await payment_service.session.commit()
        
        with pytest.raises(ValidationError):
            cancel_request = PaymentCancelRequest(reason="Test cancellation")
            await payment_service.cancel_payment(payment.id, cancel_request)
    
    @pytest.mark.asyncio
    async def test_payment_external_id_operations(self, payment_service):
        """Test operations using external payment IDs."""
        # Create payment
        create_request = PaymentCreateRequest(
            amount=Decimal("50.00"),
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD.value,
            customer_id="cust_external_test",
            customer_email="external@example.com",
            customer_name="External Test Customer",
            card_token="tok_external_test",
            description="External ID test payment",
            is_test=True
        )
        
        payment = await payment_service.create_payment(create_request)
        external_id = payment.external_id
        
        # Test getting payment by external ID
        retrieved_payment = await payment_service.get_payment_by_external_id(external_id)
        assert retrieved_payment.id == payment.id
        assert retrieved_payment.external_id == external_id
        
        # Test updating payment using external ID
        update_request = PaymentUpdateRequest(
            description="Updated via external ID",
            metadata={"updated_via": "external_id"}
        )
        
        # We need to get the UUID first since update_payment expects UUID
        payment_by_external_id = await payment_service.get_payment_by_external_id(external_id)
        updated_payment = await payment_service.update_payment(payment_by_external_id.id, update_request)
        assert updated_payment.description == "Updated via external ID"
    
    @pytest.mark.asyncio
    async def test_concurrent_payment_operations(self, payment_service):
        """Test concurrent payment operations."""
        import asyncio
        
        # Create multiple payments concurrently
        async def create_payment(customer_id: str, amount: Decimal):
            create_request = PaymentCreateRequest(
                amount=amount,
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD.value,
                customer_id=customer_id,
                customer_email=f"{customer_id}@example.com",
                customer_name="Concurrent Test Customer",
                card_token=f"tok_{customer_id}",
                description=f"Concurrent test payment for {customer_id}",
                is_test=True
            )
            return await payment_service.create_payment(create_request)
        
        # Create 5 payments concurrently
        tasks = [
            create_payment(f"cust_concurrent_{i}", Decimal(f"{10 + i * 10}.00"))
            for i in range(5)
        ]
        
        payments = await asyncio.gather(*tasks)
        
        # Verify all payments were created successfully
        assert len(payments) == 5
        for i, payment in enumerate(payments):
            assert payment.customer_id == f"cust_concurrent_{i}"
            assert payment.amount == Decimal(f"{10 + i * 10}.00")
            assert payment.status == PaymentStatus.PENDING
        
        # Test concurrent updates
        async def update_payment(payment_id: uuid.UUID, description: str):
            update_request = PaymentUpdateRequest(
                description=description,
                metadata={"concurrent_update": True}
            )
            return await payment_service.update_payment(payment_id, update_request)
        
        update_tasks = [
            update_payment(payment.id, f"Updated payment {i}")
            for i, payment in enumerate(payments)
        ]
        
        updated_payments = await asyncio.gather(*update_tasks)
        
        # Verify all payments were updated successfully
        assert len(updated_payments) == 5
        for i, payment in enumerate(updated_payments):
            assert payment.description == f"Updated payment {i}"
            assert payment.payment_metadata["concurrent_update"] is True
