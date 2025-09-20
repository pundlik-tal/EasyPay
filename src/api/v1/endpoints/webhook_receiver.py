"""
EasyPay Payment Gateway - Webhook Receiver Endpoints
"""
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.integrations.webhooks.webhook_handler import WebhookHandler
from src.infrastructure.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/webhooks/payment",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Payment webhook processed successfully"},
        400: {"model": Dict[str, Any], "description": "Invalid webhook data"},
        401: {"model": Dict[str, Any], "description": "Invalid webhook signature"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Receive Payment Webhook",
    description="""
    Receive and process payment-related webhooks from external services.
    
    ### Supported Events
    - `payment.authorized`: Payment authorized but not captured
    - `payment.captured`: Payment captured successfully
    - `payment.settled`: Payment settled in merchant account
    - `payment.refunded`: Payment refunded
    - `payment.voided`: Payment voided/cancelled
    - `payment.failed`: Payment failed
    - `payment.declined`: Payment declined by processor
    
    ### Security
    - All webhooks must include valid HMAC signature
    - Signature header: `X-Webhook-Signature`
    - Signature format: `t={timestamp},v1={signature}`
    - Timestamp validation prevents replay attacks
    
    ### Payload Format
    ```json
    {
        "event_type": "payment.authorized",
        "event_id": "evt_123456789",
        "payment_id": "pay_123456789",
        "data": {
            "id": "pay_123456789",
            "amount": "10.00",
            "currency": "USD",
            "status": "authorized"
        },
        "created_at": "2024-01-01T00:00:00Z"
    }
    ```
    """,
    tags=["webhook-receiver"]
)
async def receive_payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Receive and process payment webhook.
    
    Args:
        request: FastAPI request object
        db: Database session dependency
        
    Returns:
        Dictionary containing processing result
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        webhook_handler = WebhookHandler(db)
        result = await webhook_handler.process_webhook_request(request, "payment")
        
        logger.info(f"Payment webhook processed successfully: {result.get('webhook_id')}")
        
        return webhook_handler.generate_webhook_response(
            success=True,
            message="Payment webhook processed successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process payment webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment webhook processing failed: {str(e)}"
        )


@router.post(
    "/webhooks/fraud",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Fraud webhook processed successfully"},
        400: {"model": Dict[str, Any], "description": "Invalid webhook data"},
        401: {"model": Dict[str, Any], "description": "Invalid webhook signature"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Receive Fraud Webhook",
    description="""
    Receive and process fraud detection webhooks.
    
    ### Fraud Events
    - `fraud.detected`: Fraud detected in transaction
    - `fraud.review`: Transaction flagged for review
    - `fraud.approved`: Transaction approved after review
    - `fraud.declined`: Transaction declined due to fraud
    
    ### Payload Format
    ```json
    {
        "event_type": "fraud.detected",
        "event_id": "fraud_123456789",
        "data": {
            "transaction_id": "txn_123456789",
            "risk_score": 85,
            "fraud_reasons": ["velocity_check", "geolocation_mismatch"],
            "recommendation": "decline"
        },
        "created_at": "2024-01-01T00:00:00Z"
    }
    ```
    """,
    tags=["webhook-receiver"]
)
async def receive_fraud_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Receive and process fraud webhook.
    
    Args:
        request: FastAPI request object
        db: Database session dependency
        
    Returns:
        Dictionary containing processing result
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        webhook_handler = WebhookHandler(db)
        result = await webhook_handler.process_webhook_request(request, "fraud")
        
        logger.info(f"Fraud webhook processed successfully: {result.get('webhook_id')}")
        
        return webhook_handler.generate_webhook_response(
            success=True,
            message="Fraud webhook processed successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process fraud webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fraud webhook processing failed: {str(e)}"
        )


@router.post(
    "/webhooks/chargeback",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Chargeback webhook processed successfully"},
        400: {"model": Dict[str, Any], "description": "Invalid webhook data"},
        401: {"model": Dict[str, Any], "description": "Invalid webhook signature"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Receive Chargeback Webhook",
    description="""
    Receive and process chargeback-related webhooks.
    
    ### Chargeback Events
    - `chargeback.created`: New chargeback created
    - `chargeback.updated`: Chargeback status updated
    - `chargeback.resolved`: Chargeback resolved
    - `dispute.created`: Dispute created
    
    ### Payload Format
    ```json
    {
        "event_type": "chargeback.created",
        "event_id": "cb_123456789",
        "data": {
            "chargeback_id": "cb_123456789",
            "payment_id": "pay_123456789",
            "amount": "10.00",
            "currency": "USD",
            "reason": "fraudulent",
            "status": "open"
        },
        "created_at": "2024-01-01T00:00:00Z"
    }
    ```
    """,
    tags=["webhook-receiver"]
)
async def receive_chargeback_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Receive and process chargeback webhook.
    
    Args:
        request: FastAPI request object
        db: Database session dependency
        
    Returns:
        Dictionary containing processing result
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        webhook_handler = WebhookHandler(db)
        result = await webhook_handler.process_webhook_request(request, "chargeback")
        
        logger.info(f"Chargeback webhook processed successfully: {result.get('webhook_id')}")
        
        return webhook_handler.generate_webhook_response(
            success=True,
            message="Chargeback webhook processed successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process chargeback webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chargeback webhook processing failed: {str(e)}"
        )


@router.post(
    "/webhooks/test",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Test webhook processed successfully"},
        400: {"model": Dict[str, Any], "description": "Invalid webhook data"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Receive Test Webhook",
    description="""
    Receive and process test webhooks for development and testing.
    
    ### Test Features
    - No signature verification required
    - Simplified processing for testing
    - Logs all received data
    - Returns echo of received payload
    
    ### Use Cases
    - Development testing
    - Webhook endpoint validation
    - Integration testing
    - Debugging webhook flows
    """,
    tags=["webhook-receiver"]
)
async def receive_test_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Receive and process test webhook.
    
    Args:
        request: FastAPI request object
        db: Database session dependency
        
    Returns:
        Dictionary containing processing result
    """
    try:
        # Extract request data
        body = await request.body()
        headers = dict(request.headers)
        
        # Parse payload
        import json
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            payload = {"raw_body": body.decode('utf-8')}
        
        logger.info(f"Test webhook received: {payload}")
        
        return {
            'success': True,
            'message': 'Test webhook processed successfully',
            'timestamp': '2024-01-01T00:00:00Z',
            'data': {
                'received_payload': payload,
                'headers': headers,
                'method': request.method,
                'url': str(request.url)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to process test webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test webhook processing failed: {str(e)}"
        )
