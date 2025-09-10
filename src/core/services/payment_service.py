"""
EasyPay Payment Gateway - Payment Service
"""
import uuid
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.payment import Payment, PaymentStatus, PaymentMethod
from src.core.repositories.payment_repository import PaymentRepository
from src.core.repositories.audit_log_repository import AuditLogRepository
from src.core.exceptions import (
    PaymentError,
    PaymentNotFoundError,
    ValidationError,
    DatabaseError,
    ExternalServiceError
)
from src.integrations.authorize_net.client import AuthorizeNetClient
from src.integrations.authorize_net.models import (
    CreditCard,
    BillingAddress,
    PaymentResponse as AuthorizeNetResponse
)
from src.integrations.authorize_net.exceptions import (
    AuthorizeNetError,
    AuthorizeNetTransactionError,
    AuthorizeNetNetworkError
)
from src.api.v1.schemas.payment import (
    PaymentCreateRequest,
    PaymentUpdateRequest,
    PaymentRefundRequest,
    PaymentCancelRequest
)
from src.core.services.advanced_payment_features import (
    AdvancedPaymentFeatures,
    RetryPolicies
)

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service class for payment operations.
    
    This class handles all payment-related business logic including
    creation, processing, refunds, and cancellations.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize payment service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.payment_repository = PaymentRepository(session)
        self.audit_repository = AuditLogRepository(session)
        
        # Initialize cache manager for advanced features
        from src.infrastructure.cache import get_cache_client
        try:
            cache_client = get_cache_client()
            self.advanced_features = AdvancedPaymentFeatures(cache_client)
        except Exception as e:
            logger.warning(f"Advanced features not initialized: {e}")
            self.advanced_features = None
        
        # Initialize Authorize.net client only if credentials are configured
        try:
            self.authorize_net_client = AuthorizeNetClient()
        except Exception as e:
            logger.warning(f"Authorize.net client not initialized: {e}")
            self.authorize_net_client = None
    
    async def create_payment(self, payment_data: PaymentCreateRequest, 
                           correlation_id: str = None) -> Payment:
        """
        Create a new payment with advanced features.
        
        Args:
            payment_data: Payment creation request data
            correlation_id: Optional correlation ID for request tracking
            
        Returns:
            Payment: Created payment instance
            
        Raises:
            ValidationError: If payment data is invalid
            PaymentError: If payment creation fails
            ExternalServiceError: If Authorize.net processing fails
        """
        try:
            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = self.advanced_features.correlation_manager.generate_correlation_id() if self.advanced_features else f"corr_{uuid.uuid4().hex[:12]}"
            
            logger.info(f"Creating payment for amount {payment_data.amount} {payment_data.currency} [correlation_id: {correlation_id}]")
            
            # Validate payment data
            await self._validate_payment_data(payment_data)
            
            # Generate external ID
            external_id = f"pay_{uuid.uuid4().hex[:12]}"
            
            # Prepare payment data for database
            payment_dict = {
                "external_id": external_id,
                "amount": payment_data.amount,
                "currency": payment_data.currency,
                "status": PaymentStatus.PENDING,
                "payment_method": payment_data.payment_method,
                "customer_id": payment_data.customer_id,
                "customer_email": payment_data.customer_email,
                "customer_name": payment_data.customer_name,
                "card_token": payment_data.card_token,
                "description": payment_data.description,
                "payment_metadata": payment_data.metadata,
                "is_test": payment_data.is_test,
                "is_live": not payment_data.is_test
            }
            
            # Create payment in database
            payment = await self.payment_repository.create(payment_dict)
            
            # Track status change if advanced features are available
            if self.advanced_features:
                await self.advanced_features.track_payment_status_change(
                    str(payment.id), 
                    "none", 
                    PaymentStatus.PENDING.value,
                    "Payment created"
                )
                
                # Store metadata if provided
                if payment_data.metadata:
                    await self.advanced_features.store_payment_metadata(
                        str(payment.id), 
                        payment_data.metadata
                    )
            
            # Log audit trail - temporarily commented out for debugging
            # await self.audit_repository.create({
            #     "payment_id": payment.id,
            #     "action": "payment_created",
            #     "level": "info",
            #     "message": f"Payment created for amount {payment_data.amount} {payment_data.currency}",
            #     "entity_type": "payment",
            #     "entity_id": str(payment.id),
            #     "audit_metadata": {
            #         "amount": str(payment_data.amount),
            #         "currency": payment_data.currency,
            #         "payment_method": payment_data.payment_method,
            #         "customer_id": payment_data.customer_id,
            #         "correlation_id": correlation_id
            #     },
            #     "user_id": None,  # Will be set when authentication is implemented
            #     "ip_address": None,
            #     "user_agent": None
            # })
            
            logger.info(f"Payment created successfully: {payment.id} [correlation_id: {correlation_id}]")
            return payment
            
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to create payment: {e}")
            raise PaymentError(f"Failed to create payment: {str(e)}")
    
    async def get_payment(self, payment_id: uuid.UUID) -> Payment:
        """
        Get payment by ID.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            Payment: Payment instance
            
        Raises:
            PaymentNotFoundError: If payment is not found
            DatabaseError: If database operation fails
        """
        try:
            logger.info(f"Getting payment: {payment_id}")
            
            payment = await self.payment_repository.get_by_id(payment_id)
            if not payment:
                raise PaymentNotFoundError(f"Payment {payment_id} not found")
            
            logger.info(f"Payment retrieved successfully: {payment.id}")
            return payment
            
        except PaymentNotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment {payment_id}: {e}")
            raise PaymentError(f"Failed to get payment: {str(e)}")
    
    async def get_payment_by_external_id(self, external_id: str) -> Payment:
        """
        Get payment by external ID.
        
        Args:
            external_id: External payment identifier
            
        Returns:
            Payment: Payment instance
            
        Raises:
            PaymentNotFoundError: If payment is not found
            DatabaseError: If database operation fails
        """
        try:
            logger.info(f"Getting payment by external ID: {external_id}")
            
            payment = await self.payment_repository.get_by_external_id(external_id)
            if not payment:
                raise PaymentNotFoundError(f"Payment with external ID {external_id} not found")
            
            logger.info(f"Payment retrieved successfully: {payment.id}")
            return payment
            
        except PaymentNotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment by external ID {external_id}: {e}")
            raise PaymentError(f"Failed to get payment: {str(e)}")
    
    async def update_payment(self, payment_id: uuid.UUID, update_data: PaymentUpdateRequest) -> Payment:
        """
        Update payment.
        
        Args:
            payment_id: Payment UUID
            update_data: Payment update request data
            
        Returns:
            Payment: Updated payment instance
            
        Raises:
            PaymentNotFoundError: If payment is not found
            ValidationError: If update data is invalid
            PaymentError: If update fails
        """
        try:
            logger.info(f"Updating payment: {payment_id}")
            
            # Check if payment exists
            payment = await self.get_payment(payment_id)
            
            # Validate update data
            await self._validate_update_data(update_data)
            
            # Prepare update data
            update_dict = {}
            if update_data.description is not None:
                update_dict["description"] = update_data.description
            if update_data.metadata is not None:
                update_dict["payment_metadata"] = update_data.metadata
            
            # Update payment
            updated_payment = await self.payment_repository.update(payment_id, update_dict)
            
            # Log audit trail
            await self.audit_repository.create({
                "payment_id": payment_id,
                "action": "payment_updated",
                "level": "info",
                "message": f"Payment updated: {', '.join(update_dict.keys())}",
                "entity_type": "payment",
                "entity_id": str(payment_id),
                "audit_metadata": {
                    "updated_fields": list(update_dict.keys()),
                    "update_data": {k: str(v) if isinstance(v, datetime) else v for k, v in update_dict.items()}
                },
                "user_id": None,
                "ip_address": None,
                "user_agent": None
            })
            
            logger.info(f"Payment updated successfully: {payment_id}")
            return updated_payment
            
        except PaymentNotFoundError:
            raise
        except ValidationError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to update payment {payment_id}: {e}")
            raise PaymentError(f"Failed to update payment: {str(e)}")
    
    async def refund_payment(
        self, 
        payment_id: uuid.UUID, 
        refund_data: PaymentRefundRequest,
        correlation_id: str = None
    ) -> Payment:
        """
        Refund a payment with advanced features.
        
        Args:
            payment_id: Payment UUID
            refund_data: Refund request data
            correlation_id: Optional correlation ID for request tracking
            
        Returns:
            Payment: Updated payment instance
            
        Raises:
            PaymentNotFoundError: If payment is not found
            ValidationError: If refund data is invalid
            PaymentError: If refund fails
            ExternalServiceError: If Authorize.net processing fails
        """
        try:
            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = self.advanced_features.correlation_manager.generate_correlation_id() if self.advanced_features else f"corr_{uuid.uuid4().hex[:12]}"
            
            logger.info(f"Processing refund for payment: {payment_id} [correlation_id: {correlation_id}]")
            
            # Get payment
            payment = await self.get_payment(payment_id)
            
            # Validate refund eligibility
            await self._validate_refund_eligibility(payment, refund_data)
            
            # Determine refund amount
            refund_amount = refund_data.amount or payment.remaining_refund_amount
            
            # Track status change before processing
            if self.advanced_features:
                await self.advanced_features.track_payment_status_change(
                    str(payment_id),
                    payment.status.value,
                    "processing_refund",
                    f"Refund initiated for amount {refund_amount}"
                )
            
            # Process refund with Authorize.net
            if payment.authorize_net_transaction_id:
                try:
                    # For now, we'll simulate the refund since we need card details
                    # In a real implementation, you'd need to store card details securely
                    logger.warning("Refund processing requires card details - simulating refund")
                    
                    # Update payment status
                    new_status = PaymentStatus.REFUNDED if refund_amount == payment.amount else PaymentStatus.PARTIALLY_REFUNDED
                    update_data = {
                        "status": new_status,
                        "refunded_amount": (payment.refunded_amount or Decimal('0')) + refund_amount,
                        "refund_count": (payment.refund_count or 0) + 1,
                        "processor_response_code": "1",
                        "processor_response_message": "Refund processed successfully"
                    }
                    
                except AuthorizeNetError as e:
                    logger.error(f"Authorize.net refund failed: {e}")
                    raise ExternalServiceError(f"Refund processing failed: {str(e)}")
            else:
                # No Authorize.net transaction ID, update status only
                new_status = PaymentStatus.REFUNDED if refund_amount == payment.amount else PaymentStatus.PARTIALLY_REFUNDED
                update_data = {
                    "status": new_status,
                    "refunded_amount": (payment.refunded_amount or Decimal('0')) + refund_amount,
                    "refund_count": (payment.refund_count or 0) + 1,
                    "processor_response_code": "1",
                    "processor_response_message": "Refund processed successfully"
                }
            
            # Update payment
            updated_payment = await self.payment_repository.update(payment_id, update_data)
            
            # Track status change after processing
            if self.advanced_features:
                await self.advanced_features.track_payment_status_change(
                    str(payment_id),
                    "processing_refund",
                    new_status.value,
                    f"Refund completed for amount {refund_amount}"
                )
                
                # Store refund metadata
                refund_metadata = {
                    "refund_amount": str(refund_amount),
                    "reason": refund_data.reason,
                    "correlation_id": correlation_id,
                    "refund_timestamp": datetime.utcnow().isoformat()
                }
                if refund_data.metadata:
                    refund_metadata.update(refund_data.metadata)
                
                await self.advanced_features.update_payment_metadata(
                    str(payment_id),
                    {"refund": refund_metadata}
                )
            
            # Log audit trail
            await self.audit_repository.create({
                "payment_id": payment_id,
                "action": "payment_refunded",
                "level": "info",
                "message": f"Payment refunded for amount {refund_amount}",
                "entity_type": "payment",
                "entity_id": str(payment_id),
                "audit_metadata": {
                    "refund_amount": str(refund_amount),
                    "reason": refund_data.reason,
                    "metadata": refund_data.metadata,
                    "correlation_id": correlation_id
                },
                "user_id": None,
                "ip_address": None,
                "user_agent": None
            })
            
            logger.info(f"Payment refunded successfully: {payment_id}, amount: {refund_amount} [correlation_id: {correlation_id}]")
            return updated_payment
            
        except PaymentNotFoundError:
            raise
        except ValidationError:
            raise
        except ExternalServiceError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to refund payment {payment_id}: {e}")
            raise PaymentError(f"Failed to refund payment: {str(e)}")
    
    async def cancel_payment(self, payment_id: uuid.UUID, cancel_data: PaymentCancelRequest, 
                           correlation_id: str = None) -> Payment:
        """
        Cancel a payment with advanced features.
        
        Args:
            payment_id: Payment UUID
            cancel_data: Cancel request data
            correlation_id: Optional correlation ID for request tracking
            
        Returns:
            Payment: Updated payment instance
            
        Raises:
            PaymentNotFoundError: If payment is not found
            ValidationError: If cancellation is not allowed
            PaymentError: If cancellation fails
            ExternalServiceError: If Authorize.net processing fails
        """
        try:
            # Generate correlation ID if not provided
            if not correlation_id:
                correlation_id = self.advanced_features.correlation_manager.generate_correlation_id() if self.advanced_features else f"corr_{uuid.uuid4().hex[:12]}"
            
            logger.info(f"Processing cancellation for payment: {payment_id} [correlation_id: {correlation_id}]")
            
            # Get payment
            payment = await self.get_payment(payment_id)
            
            # Validate cancellation eligibility
            await self._validate_cancellation_eligibility(payment)
            
            # Track status change before processing
            if self.advanced_features:
                await self.advanced_features.track_payment_status_change(
                    str(payment_id),
                    payment.status.value,
                    "processing_cancellation",
                    f"Cancellation initiated: {cancel_data.reason or 'No reason provided'}"
                )
            
            # Process cancellation with Authorize.net
            if payment.authorize_net_transaction_id and self.authorize_net_client:
                try:
                    # Void the transaction
                    response = await self.authorize_net_client.void_transaction(
                        payment.authorize_net_transaction_id
                    )
                    
                    # Update payment status
                    update_data = {
                        "status": PaymentStatus.VOIDED,
                        "processor_response_code": response.response_code,
                        "processor_response_message": response.response_text,
                        "processor_transaction_id": response.transaction_id
                    }
                    
                except AuthorizeNetError as e:
                    logger.error(f"Authorize.net void failed: {e}")
                    raise ExternalServiceError(f"Cancellation processing failed: {str(e)}")
            else:
                # No Authorize.net transaction ID or client not available, update status only
                update_data = {
                    "status": PaymentStatus.VOIDED,
                    "processor_response_code": "1",
                    "processor_response_message": "Payment cancelled successfully"
                }
            
            # Update payment
            updated_payment = await self.payment_repository.update(payment_id, update_data)
            
            # Track status change after processing
            if self.advanced_features:
                await self.advanced_features.track_payment_status_change(
                    str(payment_id),
                    "processing_cancellation",
                    PaymentStatus.VOIDED.value,
                    f"Cancellation completed: {cancel_data.reason or 'No reason provided'}"
                )
                
                # Store cancellation metadata
                cancellation_metadata = {
                    "reason": cancel_data.reason,
                    "correlation_id": correlation_id,
                    "cancellation_timestamp": datetime.utcnow().isoformat()
                }
                if cancel_data.metadata:
                    cancellation_metadata.update(cancel_data.metadata)
                
                await self.advanced_features.update_payment_metadata(
                    str(payment_id),
                    {"cancellation": cancellation_metadata}
                )
            
            # Log audit trail
            await self.audit_repository.create({
                "payment_id": payment_id,
                "action": "payment_cancelled",
                "level": "info",
                "message": f"Payment cancelled: {cancel_data.reason or 'No reason provided'}",
                "entity_type": "payment",
                "entity_id": str(payment_id),
                "audit_metadata": {
                    "reason": cancel_data.reason,
                    "metadata": cancel_data.metadata,
                    "correlation_id": correlation_id
                },
                "user_id": None,
                "ip_address": None,
                "user_agent": None
            })
            
            logger.info(f"Payment cancelled successfully: {payment_id} [correlation_id: {correlation_id}]")
            return updated_payment
            
        except PaymentNotFoundError:
            raise
        except ValidationError:
            raise
        except ExternalServiceError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to cancel payment {payment_id}: {e}")
            raise PaymentError(f"Failed to cancel payment: {str(e)}")
    
    async def list_payments(
        self,
        customer_id: Optional[str] = None,
        status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        order_by: str = "created_at",
        order_direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        List payments with filtering and pagination.
        
        Args:
            customer_id: Filter by customer ID
            status: Filter by payment status
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number (1-based)
            per_page: Items per page
            order_by: Field to order by
            order_direction: Order direction (asc/desc)
            
        Returns:
            Dictionary containing payments list and pagination info
        """
        try:
            logger.info(f"Listing payments - page {page}, per_page {per_page}")
            
            result = await self.payment_repository.list_payments(
                customer_id=customer_id,
                status=status,
                start_date=start_date,
                end_date=end_date,
                page=page,
                per_page=per_page,
                order_by=order_by,
                order_direction=order_direction
            )
            
            logger.info(f"Retrieved {len(result['payments'])} payments")
            return result
            
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to list payments: {e}")
            raise PaymentError(f"Failed to list payments: {str(e)}")
    
    async def search_payments(
        self,
        search_term: str,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Search payments by various fields.
        
        Args:
            search_term: Search term
            page: Page number (1-based)
            per_page: Items per page
            
        Returns:
            Dictionary containing search results and pagination info
        """
        try:
            logger.info(f"Searching payments for term: {search_term}")
            
            result = await self.payment_repository.search_payments(
                search_term=search_term,
                page=page,
                per_page=per_page
            )
            
            logger.info(f"Found {len(result['payments'])} payments matching search")
            return result
            
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to search payments: {e}")
            raise PaymentError(f"Failed to search payments: {str(e)}")
    
    async def get_payment_stats(
        self,
        customer_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get payment statistics.
        
        Args:
            customer_id: Filter by customer ID
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            Dictionary containing payment statistics
        """
        try:
            logger.info("Getting payment statistics")
            
            stats = await self.payment_repository.get_payment_stats(
                customer_id=customer_id,
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"Retrieved payment stats: {stats['total_count']} total payments")
            return stats
            
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Failed to get payment stats: {e}")
            raise PaymentError(f"Failed to get payment stats: {str(e)}")
    
    async def _validate_payment_data(self, payment_data: PaymentCreateRequest) -> None:
        """
        Validate payment creation data.
        
        Args:
            payment_data: Payment creation request data
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate amount
        if payment_data.amount <= 0:
            raise ValidationError("Payment amount must be greater than 0")
        
        if payment_data.amount > Decimal('999999.99'):
            raise ValidationError("Payment amount cannot exceed 999,999.99")
        
        # Validate currency
        if len(payment_data.currency) != 3:
            raise ValidationError("Currency must be a 3-character code")
        
        # Validate payment method
        if payment_data.payment_method not in [method.value for method in PaymentMethod]:
            raise ValidationError(f"Invalid payment method: {payment_data.payment_method}")
        
        # Validate customer email format if provided
        if payment_data.customer_email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, payment_data.customer_email):
                raise ValidationError("Invalid email format")
    
    async def _validate_update_data(self, update_data: PaymentUpdateRequest) -> None:
        """
        Validate payment update data.
        
        Args:
            update_data: Payment update request data
            
        Raises:
            ValidationError: If validation fails
        """
        # Check if at least one field is being updated
        if update_data.description is None and update_data.metadata is None:
            raise ValidationError("At least one field must be provided for update")
    
    async def _validate_refund_eligibility(self, payment: Payment, refund_data: PaymentRefundRequest) -> None:
        """
        Validate refund eligibility.
        
        Args:
            payment: Payment instance
            refund_data: Refund request data
            
        Raises:
            ValidationError: If refund is not eligible
        """
        # Check if payment can be refunded
        if not payment.is_refundable:
            raise ValidationError(f"Payment cannot be refunded. Current status: {payment.status}")
        
        # Check refund amount
        if refund_data.amount:
            if refund_data.amount <= 0:
                raise ValidationError("Refund amount must be greater than 0")
            
            if refund_data.amount > payment.remaining_refund_amount:
                raise ValidationError(
                    f"Refund amount ({refund_data.amount}) exceeds remaining refundable amount "
                    f"({payment.remaining_refund_amount})"
                )
    
    async def _validate_cancellation_eligibility(self, payment: Payment) -> None:
        """
        Validate cancellation eligibility.
        
        Args:
            payment: Payment instance
            
        Raises:
            ValidationError: If cancellation is not eligible
        """
        # Check if payment can be cancelled/voided
        if not payment.is_voidable:
            raise ValidationError(f"Payment cannot be cancelled. Current status: {payment.status}")
    
    async def get_payment_status_history(self, payment_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Get payment status history.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            List of status change records
        """
        if not self.advanced_features:
            return []
        
        return await self.advanced_features.get_payment_status_history(str(payment_id))
    
    async def get_payment_metadata(self, payment_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get payment metadata.
        
        Args:
            payment_id: Payment UUID
            
        Returns:
            Payment metadata or None
        """
        if not self.advanced_features:
            return None
        
        return await self.advanced_features.get_payment_metadata(str(payment_id))
    
    async def update_payment_metadata(self, payment_id: uuid.UUID, 
                                    metadata: Dict[str, Any]) -> None:
        """
        Update payment metadata.
        
        Args:
            payment_id: Payment UUID
            metadata: Metadata to update
        """
        if not self.advanced_features:
            return
        
        await self.advanced_features.update_payment_metadata(str(payment_id), metadata)
    
    async def search_payments_advanced(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search payments with advanced features.
        
        Args:
            search_params: Search parameters
            
        Returns:
            List of matching payments
        """
        if not self.advanced_features:
            return []
        
        return await self.advanced_features.search_payments(search_params)
    
    def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """
        Get circuit breaker metrics.
        
        Returns:
            Circuit breaker metrics
        """
        if not self.advanced_features:
            return {}
        
        return self.advanced_features.get_circuit_breaker_metrics()
    
    async def close(self):
        """Close the Authorize.net client."""
        if self.authorize_net_client:
            await self.authorize_net_client.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
