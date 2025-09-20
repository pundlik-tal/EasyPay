"""
EasyPay Payment Gateway - Webhook API Endpoints
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.schemas.webhook import (
    WebhookCreateRequest,
    WebhookEventRequest,
    WebhookResponse,
    WebhookListResponse,
    WebhookSearchRequest,
    WebhookRetryRequest
)
from src.api.v1.schemas.common import (
    ErrorResponse,
    ValidationErrorResponse,
    AuthenticationErrorResponse,
    AuthorizationErrorResponse
)
from src.api.v1.middleware.auth import require_webhooks_read, require_webhooks_write
from src.infrastructure.database import get_db_session
from src.core.services.webhook_service import WebhookService
from src.core.exceptions import (
    ValidationError,
    DatabaseError,
    WebhookNotFoundError,
    WebhookDeliveryError
)
from src.infrastructure.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Webhook endpoint registered successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid request data"},
        401: {"model": AuthenticationErrorResponse, "description": "Authentication required"},
        403: {"model": AuthorizationErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Register Webhook Endpoint",
    description="""
    Register a new webhook endpoint for receiving payment events.
    
    ### Webhook Features
    - **Event Subscription**: Subscribe to specific payment events
    - **Secure Delivery**: HMAC signature verification for security
    - **Retry Logic**: Automatic retry with exponential backoff
    - **Test Mode**: Support for test webhooks
    - **Metadata Support**: Custom metadata for webhook identification
    
    ### Supported Events
    - `payment.authorized`: Payment authorized but not captured
    - `payment.captured`: Payment captured successfully
    - `payment.settled`: Payment settled in merchant account
    - `payment.refunded`: Payment refunded
    - `payment.voided`: Payment voided/cancelled
    - `payment.failed`: Payment failed
    - `payment.declined`: Payment declined by processor
    - `fraud.detected`: Fraud detected
    - `chargeback.created`: Chargeback created
    - `dispute.created`: Dispute created
    
    ### Security
    - All webhooks include HMAC signature for verification
    - Signature header: `X-Webhook-Signature`
    - Verify signatures to ensure webhook authenticity
    - Use HTTPS endpoints for secure delivery
    
    ### Retry Policy
    - Default: 3 retry attempts
    - Exponential backoff: 5, 10, 20 minutes
    - Maximum retry delay: 60 minutes
    - Failed webhooks marked as expired after max retries
    """,
    tags=["webhooks"]
)
async def register_webhook_endpoint(
    request: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_webhooks_write)
) -> WebhookResponse:
    """
    Register a new webhook endpoint.
    
    Args:
        request: Webhook registration request
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        WebhookResponse: Registered webhook information
        
    Raises:
        ValidationError: If request data is invalid
        DatabaseError: If database operation fails
    """
    try:
        webhook_service = WebhookService(db, settings.webhook_secret)
        
        # Register webhook endpoint
        result = await webhook_service.register_webhook_endpoint(
            url=request.url,
            event_types=request.event_types,
            description=request.description,
            metadata=request.metadata,
            is_test=request.is_test
        )
        
        # Create a webhook record for the endpoint registration
        webhook = await webhook_service.create_webhook_event(
            event_type="webhook.endpoint.registered",
            event_id=f"endpoint_{result['id']}",
            data=result,
            url=request.url,
            is_test=request.is_test
        )
        
        return WebhookResponse(
            id=webhook.id,
            event_type=webhook.event_type,
            event_id=webhook.event_id,
            status=webhook.status,
            payment_id=webhook.payment_id,
            url=webhook.url,
            retry_count=webhook.retry_count,
            max_retries=webhook.max_retries,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at,
            delivered_at=webhook.delivered_at,
            failed_at=webhook.failed_at,
            next_retry_at=webhook.next_retry_at,
            is_test=webhook.is_test,
            signature_verified=webhook.signature_verified
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/webhooks",
    response_model=WebhookListResponse,
    responses={
        200: {"description": "Webhooks retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Authentication required"},
        403: {"model": AuthorizationErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="List Webhooks",
    description="""
    List webhooks with filtering and pagination.
    
    ### Filtering Options
    - **Event Type**: Filter by specific event types
    - **Status**: Filter by webhook status (pending, delivered, failed, retrying, expired)
    - **Payment ID**: Filter by related payment
    - **Date Range**: Filter by creation date range
    - **Test Mode**: Filter by test/production webhooks
    
    ### Pagination
    - Default: 20 items per page
    - Maximum: 100 items per page
    - Page numbers start from 1
    
    ### Sorting
    - Default: Created date (newest first)
    - Supports multiple sort fields
    """,
    tags=["webhooks"]
)
async def list_webhooks(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status: Optional[str] = Query(None, description="Filter by webhook status"),
    payment_id: Optional[uuid.UUID] = Query(None, description="Filter by payment ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_webhooks_read)
) -> WebhookListResponse:
    """
    List webhooks with filtering and pagination.
    
    Args:
        page: Page number
        per_page: Items per page
        event_type: Filter by event type
        status: Filter by webhook status
        payment_id: Filter by payment ID
        start_date: Filter by start date
        end_date: Filter by end date
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        WebhookListResponse: List of webhooks with pagination info
    """
    try:
        webhook_service = WebhookService(db, settings.webhook_secret)
        
        result = await webhook_service.list_webhooks(
            event_type=event_type,
            status=status,
            payment_id=payment_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page
        )
        
        # Convert webhooks to response format
        webhook_responses = []
        for webhook in result['webhooks']:
            webhook_responses.append(WebhookResponse(
                id=webhook.id,
                event_type=webhook.event_type,
                event_id=webhook.event_id,
                status=webhook.status,
                payment_id=webhook.payment_id,
                url=webhook.url,
                retry_count=webhook.retry_count,
                max_retries=webhook.max_retries,
                created_at=webhook.created_at,
                updated_at=webhook.updated_at,
                delivered_at=webhook.delivered_at,
                failed_at=webhook.failed_at,
                next_retry_at=webhook.next_retry_at,
                is_test=webhook.is_test,
                signature_verified=webhook.signature_verified
            ))
        
        return WebhookListResponse(
            webhooks=webhook_responses,
            total=result['total'],
            page=result['page'],
            per_page=result['per_page'],
            total_pages=result['total_pages']
        )
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    responses={
        200: {"description": "Webhook retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Webhook not found"},
        401: {"model": AuthenticationErrorResponse, "description": "Authentication required"},
        403: {"model": AuthorizationErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get Webhook",
    description="""
    Get webhook details by ID.
    
    ### Response Includes
    - **Webhook Details**: Event type, ID, status, URL
    - **Delivery Info**: Retry count, delivery timestamps
    - **Response Data**: HTTP response from webhook delivery
    - **Security Info**: Signature verification status
    """,
    tags=["webhooks"]
)
async def get_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_webhooks_read)
) -> WebhookResponse:
    """
    Get webhook by ID.
    
    Args:
        webhook_id: Webhook UUID
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        WebhookResponse: Webhook information
        
    Raises:
        NotFoundError: If webhook not found
        DatabaseError: If database operation fails
    """
    try:
        webhook_service = WebhookService(db, settings.webhook_secret)
        
        # Get webhook from repository
        webhook_repo = webhook_service.webhook_repo
        webhook = await webhook_repo.get_by_id(webhook_id)
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        return WebhookResponse(
            id=webhook.id,
            event_type=webhook.event_type,
            event_id=webhook.event_id,
            status=webhook.status,
            payment_id=webhook.payment_id,
            url=webhook.url,
            retry_count=webhook.retry_count,
            max_retries=webhook.max_retries,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at,
            delivered_at=webhook.delivered_at,
            failed_at=webhook.failed_at,
            next_retry_at=webhook.next_retry_at,
            is_test=webhook.is_test,
            signature_verified=webhook.signature_verified
        )
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/webhooks/{webhook_id}/retry",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Webhook retry initiated successfully"},
        404: {"model": ErrorResponse, "description": "Webhook not found"},
        400: {"model": ValidationErrorResponse, "description": "Webhook cannot be retried"},
        401: {"model": AuthenticationErrorResponse, "description": "Authentication required"},
        403: {"model": AuthorizationErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Retry Webhook",
    description="""
    Retry webhook delivery.
    
    ### Retry Conditions
    - Webhook must be in failed or retrying status
    - Retry count must be less than maximum retries
    - Webhook must not be expired
    
    ### Retry Behavior
    - Immediate retry attempt
    - Updates retry count and status
    - Schedules next retry if delivery fails
    - Returns delivery result
    """,
    tags=["webhooks"]
)
async def retry_webhook(
    webhook_id: uuid.UUID,
    request: WebhookRetryRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_webhooks_write)
) -> Dict[str, Any]:
    """
    Retry webhook delivery.
    
    Args:
        webhook_id: Webhook UUID
        request: Retry configuration
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        Dictionary containing retry result
        
    Raises:
        NotFoundError: If webhook not found
        ValidationError: If webhook cannot be retried
        DatabaseError: If database operation fails
    """
    try:
        webhook_service = WebhookService(db, settings.webhook_secret)
        
        # Get webhook
        webhook_repo = webhook_service.webhook_repo
        webhook = await webhook_repo.get_by_id(webhook_id)
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Check if webhook can be retried
        if not webhook.can_retry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook cannot be retried"
            )
        
        # Update max retries if provided
        if request.max_retries != webhook.max_retries:
            await webhook_repo.update(webhook_id, {'max_retries': request.max_retries})
        
        # Retry webhook delivery
        delivery_result = await webhook_service.deliver_webhook(webhook_id)
        
        return {
            'webhook_id': str(webhook_id),
            'retry_count': webhook.retry_count + 1,
            'delivery_result': delivery_result,
            'retry_delay_minutes': request.retry_delay_minutes,
            'max_retries': request.max_retries
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/webhooks/retry-failed",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Failed webhooks retry initiated successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Authentication required"},
        403: {"model": AuthorizationErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Retry All Failed Webhooks",
    description="""
    Retry all failed webhooks that are ready for retry.
    
    ### Retry Criteria
    - Webhooks in failed or retrying status
    - Retry count less than maximum retries
    - Past their scheduled retry time
    
    ### Retry Process
    - Processes webhooks in batches
    - Uses exponential backoff for retry delays
    - Updates webhook status based on delivery results
    - Returns summary of retry operations
    """,
    tags=["webhooks"]
)
async def retry_all_failed_webhooks(
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_webhooks_write)
) -> Dict[str, Any]:
    """
    Retry all failed webhooks that are ready for retry.
    
    Args:
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        Dictionary containing retry results
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        webhook_service = WebhookService(db, settings.webhook_secret)
        
        result = await webhook_service.retry_failed_webhooks()
        
        return {
            'message': 'Failed webhooks retry completed',
            'results': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/webhooks/stats",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Webhook statistics retrieved successfully"},
        401: {"model": AuthenticationErrorResponse, "description": "Authentication required"},
        403: {"model": AuthorizationErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get Webhook Statistics",
    description="""
    Get webhook delivery statistics.
    
    ### Statistics Include
    - **Total Count**: Total number of webhooks
    - **Status Breakdown**: Count by status (pending, delivered, failed, etc.)
    - **Event Type Breakdown**: Count by event type
    - **Date Range**: Optional filtering by date range
    
    ### Use Cases
    - Monitor webhook delivery success rates
    - Identify problematic event types
    - Track webhook volume over time
    - Generate delivery reports
    """,
    tags=["webhooks"]
)
async def get_webhook_stats(
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_webhooks_read)
) -> Dict[str, Any]:
    """
    Get webhook statistics.
    
    Args:
        start_date: Filter by start date
        end_date: Filter by end date
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        Dictionary containing webhook statistics
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        webhook_service = WebhookService(db, settings.webhook_secret)
        
        stats = await webhook_service.get_webhook_stats(start_date, end_date)
        
        return {
            'statistics': stats,
            'timestamp': datetime.utcnow().isoformat(),
            'date_range': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        }
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/webhooks/events",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Webhook event created successfully"},
        400: {"model": ValidationErrorResponse, "description": "Invalid event data"},
        401: {"model": AuthenticationErrorResponse, "description": "Authentication required"},
        403: {"model": AuthorizationErrorResponse, "description": "Insufficient permissions"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Create Webhook Event",
    description="""
    Create a new webhook event for delivery.
    
    ### Event Creation
    - **Event Type**: Specify the type of event
    - **Event ID**: Unique identifier for the event
    - **Payment ID**: Optional related payment
    - **Event Data**: Payload data for the webhook
    - **Custom URL**: Optional custom webhook URL
    
    ### Automatic Processing
    - Event is queued for immediate delivery
    - Signature is generated automatically
    - Retry logic is applied on delivery failure
    - Status is tracked throughout the process
    """,
    tags=["webhooks"]
)
async def create_webhook_event(
    request: WebhookEventRequest,
    db: AsyncSession = Depends(get_db_session),
    auth_context: dict = Depends(require_webhooks_write)
) -> Dict[str, Any]:
    """
    Create a new webhook event for delivery.
    
    Args:
        request: Webhook event request
        db: Database session dependency
        auth_context: Authentication context
        
    Returns:
        Dictionary containing created webhook information
        
    Raises:
        ValidationError: If request data is invalid
        DatabaseError: If database operation fails
    """
    try:
        webhook_service = WebhookService(db, settings.webhook_secret)
        
        # Create webhook event
        webhook = await webhook_service.create_webhook_event(
            event_type=request.event_type,
            event_id=request.event_id,
            payment_id=request.payment_id,
            data=request.data,
            is_test=False  # Production webhook
        )
        
        # Attempt immediate delivery
        delivery_result = await webhook_service.deliver_webhook(webhook.id)
        
        return {
            'webhook_id': str(webhook.id),
            'event_type': webhook.event_type,
            'event_id': webhook.event_id,
            'status': webhook.status,
            'delivery_result': delivery_result,
            'created_at': webhook.created_at.isoformat()
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
