"""
EasyPay Payment Gateway - Payment Endpoints
"""
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.core.exceptions import (
    PaymentError,
    PaymentNotFoundError,
    ValidationError,
    DatabaseError,
    ExternalServiceError
)
from src.core.services.payment_service import PaymentService
from src.api.v1.schemas.payment import (
    PaymentCreateRequest,
    PaymentUpdateRequest,
    PaymentRefundRequest,
    PaymentCancelRequest,
    PaymentResponse,
    PaymentListResponse,
    PaymentSearchRequest
)

router = APIRouter()


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
) -> PaymentResponse:
    """
    Create a new payment with advanced features.
    
    Args:
        payment_data: Payment creation request data
        db: Database session dependency
        x_correlation_id: Optional correlation ID for request tracking
        
    Returns:
        PaymentResponse: Created payment information
        
    Raises:
        ValidationError: If payment data is invalid
        PaymentError: If payment creation fails
        ExternalServiceError: If Authorize.net processing fails
    """
    async with PaymentService(db) as payment_service:
        try:
            payment = await payment_service.create_payment(payment_data, x_correlation_id)
            return PaymentResponse.model_validate(payment)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        except ExternalServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e)
            )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> PaymentResponse:
    """
    Get payment by ID.
    
    Args:
        payment_id: Payment ID (UUID or external ID)
        db: Database session dependency
        
    Returns:
        PaymentResponse: Payment information
        
    Raises:
        PaymentNotFoundError: If payment is not found
        ValidationError: If payment ID is invalid
    """
    async with PaymentService(db) as payment_service:
        try:
            # Try to parse as UUID first
            try:
                payment_uuid = uuid.UUID(payment_id)
                payment = await payment_service.get_payment(payment_uuid)
            except ValueError:
                # If not a valid UUID, treat as external ID
                payment = await payment_service.get_payment_by_external_id(payment_id)
            
            return PaymentResponse.model_validate(payment)
        except PaymentNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.get("/", response_model=PaymentListResponse)
async def list_payments(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by payment status"),
    db: AsyncSession = Depends(get_db_session)
) -> PaymentListResponse:
    """
    List payments with optional filtering and pagination.
    
    Args:
        page: Page number (1-based)
        per_page: Items per page (1-100)
        customer_id: Filter by customer ID
        status: Filter by payment status
        db: Database session dependency
        
    Returns:
        PaymentListResponse: List of payments with pagination info
    """
    async with PaymentService(db) as payment_service:
        try:
            # Convert status string to enum if provided
            status_enum = None
            if status:
                from src.core.models.payment import PaymentStatus
                try:
                    status_enum = PaymentStatus(status)
                except ValueError:
                    raise ValidationError(f"Invalid status: {status}")
            
            result = await payment_service.list_payments(
                customer_id=customer_id,
                status=status_enum,
                page=page,
                per_page=per_page
            )
            
            # Convert to response format
            payments = [PaymentResponse.model_validate(p) for p in result["payments"]]
            
            return PaymentListResponse(
                payments=payments,
                total=result["total"],
                page=page,
                per_page=per_page,
                total_pages=(result["total"] + per_page - 1) // per_page
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: str,
    update_data: PaymentUpdateRequest,
    db: AsyncSession = Depends(get_db_session)
) -> PaymentResponse:
    """
    Update a payment.
    
    Args:
        payment_id: Payment ID to update (UUID or external ID)
        update_data: Update request data
        db: Database session dependency
        
    Returns:
        PaymentResponse: Updated payment information
        
    Raises:
        PaymentNotFoundError: If payment is not found
        ValidationError: If update data is invalid
    """
    async with PaymentService(db) as payment_service:
        try:
            # Try to parse as UUID first
            try:
                payment_uuid = uuid.UUID(payment_id)
            except ValueError:
                # If not a valid UUID, get payment by external ID first
                payment = await payment_service.get_payment_by_external_id(payment_id)
                payment_uuid = payment.id
            
            payment = await payment_service.update_payment(payment_uuid, update_data)
            return PaymentResponse.model_validate(payment)
        except PaymentNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
    payment_id: str,
    refund_data: PaymentRefundRequest,
    db: AsyncSession = Depends(get_db_session),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
) -> PaymentResponse:
    """
    Refund a payment.
    
    Args:
        payment_id: Payment ID to refund (UUID or external ID)
        refund_data: Refund request data
        db: Database session dependency
        
    Returns:
        PaymentResponse: Updated payment information
        
    Raises:
        PaymentNotFoundError: If payment is not found
        ValidationError: If refund data is invalid or payment cannot be refunded
        ExternalServiceError: If Authorize.net processing fails
    """
    async with PaymentService(db) as payment_service:
        try:
            # Try to parse as UUID first
            try:
                payment_uuid = uuid.UUID(payment_id)
            except ValueError:
                # If not a valid UUID, get payment by external ID first
                payment = await payment_service.get_payment_by_external_id(payment_id)
                payment_uuid = payment.id
            
            payment = await payment_service.refund_payment(payment_uuid, refund_data, x_correlation_id)
            return PaymentResponse.model_validate(payment)
        except PaymentNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except ExternalServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
async def cancel_payment(
    payment_id: str,
    cancel_data: PaymentCancelRequest,
    db: AsyncSession = Depends(get_db_session),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
) -> PaymentResponse:
    """
    Cancel a payment.
    
    Args:
        payment_id: Payment ID to cancel (UUID or external ID)
        cancel_data: Cancel request data
        db: Database session dependency
        
    Returns:
        PaymentResponse: Updated payment information
        
    Raises:
        PaymentNotFoundError: If payment is not found
        ValidationError: If payment cannot be cancelled
        ExternalServiceError: If Authorize.net processing fails
    """
    async with PaymentService(db) as payment_service:
        try:
            # Try to parse as UUID first
            try:
                payment_uuid = uuid.UUID(payment_id)
            except ValueError:
                # If not a valid UUID, get payment by external ID first
                payment = await payment_service.get_payment_by_external_id(payment_id)
                payment_uuid = payment.id
            
            payment = await payment_service.cancel_payment(payment_uuid, cancel_data, x_correlation_id)
            return PaymentResponse.model_validate(payment)
        except PaymentNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except ExternalServiceError as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.post("/search", response_model=PaymentListResponse)
async def search_payments(
    search_request: PaymentSearchRequest,
    db: AsyncSession = Depends(get_db_session)
) -> PaymentListResponse:
    """
    Search payments with advanced filtering.
    
    Args:
        search_request: Search request data
        db: Database session dependency
        
    Returns:
        PaymentListResponse: Search results with pagination info
    """
    async with PaymentService(db) as payment_service:
        try:
            # Convert status string to enum if provided
            status_enum = None
            if search_request.status:
                from src.core.models.payment import PaymentStatus
                try:
                    status_enum = PaymentStatus(search_request.status)
                except ValueError:
                    raise ValidationError(f"Invalid status: {search_request.status}")
            
            result = await payment_service.list_payments(
                customer_id=search_request.customer_id,
                status=status_enum,
                start_date=search_request.start_date,
                end_date=search_request.end_date,
                page=search_request.page,
                per_page=search_request.per_page
            )
            
            # Convert to response format
            payments = [PaymentResponse.model_validate(p) for p in result["payments"]]
            
            return PaymentListResponse(
                payments=payments,
                total=result["total"],
                page=search_request.page,
                per_page=search_request.per_page,
                total_pages=(result["total"] + search_request.per_page - 1) // search_request.per_page
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.get("/{payment_id}/status-history")
async def get_payment_status_history(
    payment_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> List[dict]:
    """
    Get payment status history.
    
    Args:
        payment_id: Payment ID (UUID or external ID)
        db: Database session dependency
        
    Returns:
        List of status change records
        
    Raises:
        PaymentNotFoundError: If payment is not found
    """
    async with PaymentService(db) as payment_service:
        try:
            # Try to parse as UUID first
            try:
                payment_uuid = uuid.UUID(payment_id)
            except ValueError:
                # If not a valid UUID, get payment by external ID first
                payment = await payment_service.get_payment_by_external_id(payment_id)
                payment_uuid = payment.id
            
            return await payment_service.get_payment_status_history(payment_uuid)
        except PaymentNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.get("/{payment_id}/metadata")
async def get_payment_metadata(
    payment_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get payment metadata.
    
    Args:
        payment_id: Payment ID (UUID or external ID)
        db: Database session dependency
        
    Returns:
        Payment metadata
        
    Raises:
        PaymentNotFoundError: If payment is not found
    """
    async with PaymentService(db) as payment_service:
        try:
            # Try to parse as UUID first
            try:
                payment_uuid = uuid.UUID(payment_id)
            except ValueError:
                # If not a valid UUID, get payment by external ID first
                payment = await payment_service.get_payment_by_external_id(payment_id)
                payment_uuid = payment.id
            
            metadata = await payment_service.get_payment_metadata(payment_uuid)
            return metadata or {}
        except PaymentNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.put("/{payment_id}/metadata")
async def update_payment_metadata(
    payment_id: str,
    metadata: dict,
    db: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Update payment metadata.
    
    Args:
        payment_id: Payment ID (UUID or external ID)
        metadata: Metadata to update
        db: Database session dependency
        
    Returns:
        Success message
        
    Raises:
        PaymentNotFoundError: If payment is not found
    """
    async with PaymentService(db) as payment_service:
        try:
            # Try to parse as UUID first
            try:
                payment_uuid = uuid.UUID(payment_id)
            except ValueError:
                # If not a valid UUID, get payment by external ID first
                payment = await payment_service.get_payment_by_external_id(payment_id)
                payment_uuid = payment.id
            
            await payment_service.update_payment_metadata(payment_uuid, metadata)
            return {"message": "Metadata updated successfully"}
        except PaymentNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )


@router.get("/metrics/circuit-breakers")
async def get_circuit_breaker_metrics(
    db: AsyncSession = Depends(get_db_session)
) -> dict:
    """
    Get circuit breaker metrics.
    
    Args:
        db: Database session dependency
        
    Returns:
        Circuit breaker metrics
    """
    async with PaymentService(db) as payment_service:
        try:
            return payment_service.get_circuit_breaker_metrics()
        except PaymentError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )