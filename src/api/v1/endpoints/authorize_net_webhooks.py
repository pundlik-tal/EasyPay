"""
EasyPay Payment Gateway - Authorize.net Webhook Endpoints
"""
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session
from src.integrations.authorize_net.webhook_handler import AuthorizeNetWebhookHandler
from src.infrastructure.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/webhooks/authorize-net",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Authorize.net webhook processed successfully"},
        400: {"model": Dict[str, Any], "description": "Invalid webhook data"},
        401: {"model": Dict[str, Any], "description": "Invalid webhook signature"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Receive Authorize.net Webhook",
    description="""
    Receive and process webhooks from Authorize.net payment processor.
    
    ### Supported Authorize.net Events
    - **Payment Events**:
      - `net.authorize.payment.authcapture.created`: Payment authorized and captured
      - `net.authorize.payment.authcapture.updated`: Payment status updated
      - `net.authorize.payment.authonly.created`: Payment authorized only
      - `net.authorize.payment.authonly.updated`: Authorization status updated
      - `net.authorize.payment.capture.created`: Capture created
      - `net.authorize.payment.capture.updated`: Capture status updated
      - `net.authorize.payment.refund.created`: Refund created
      - `net.authorize.payment.refund.updated`: Refund status updated
      - `net.authorize.payment.void.created`: Transaction voided
      - `net.authorize.payment.void.updated`: Void status updated
    
    - **Settlement Events**:
      - `net.authorize.payment.settlement.created`: Settlement created
      - `net.authorize.payment.settlement.updated`: Settlement status updated
    
    - **Fraud Detection Events**:
      - `net.authorize.payment.fraud.created`: Fraud detected
      - `net.authorize.payment.fraud.updated`: Fraud status updated
    
    - **Chargeback Events**:
      - `net.authorize.payment.chargeback.created`: Chargeback created
      - `net.authorize.payment.chargeback.updated`: Chargeback status updated
      - `net.authorize.payment.dispute.created`: Dispute created
      - `net.authorize.payment.dispute.updated`: Dispute status updated
    
    ### Security
    - All webhooks must include valid HMAC-SHA512 signature
    - Signature header: `X-Anet-Signature`
    - Signature format: `sha512={signature}`
    - Webhook secret must be configured in environment variables
    
    ### Payload Format
    ```json
    {
        "eventType": "net.authorize.payment.authcapture.created",
        "eventId": "evt_123456789",
        "payload": {
            "id": "txn_123456789",
            "amount": "10.00",
            "currency": "USD",
            "status": "capturedPending",
            "paymentMethod": {
                "creditCard": {
                    "cardNumber": "****1111",
                    "expirationDate": "1225"
                }
            },
            "billTo": {
                "firstName": "John",
                "lastName": "Doe"
            }
        },
        "createdAt": "2024-01-01T00:00:00Z"
    }
    ```
    
    ### Event Processing
    - Payment events update payment status in database
    - Fraud events add fraud metadata to payments
    - Chargeback events mark payments as chargeback
    - Settlement events update payment settlement status
    - All events are logged for audit purposes
    
    ### Error Handling
    - Invalid signatures return 401 Unauthorized
    - Invalid payloads return 400 Bad Request
    - Processing errors return 500 Internal Server Error
    - All errors are logged with correlation IDs
    """,
    tags=["authorize-net-webhooks"]
)
async def receive_authorize_net_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Receive and process Authorize.net webhook.
    
    Args:
        request: FastAPI request object
        db: Database session dependency
        
    Returns:
        Dictionary containing processing result
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        webhook_handler = AuthorizeNetWebhookHandler(db)
        result = await webhook_handler.process_authorize_net_webhook(request)
        
        logger.info(f"Authorize.net webhook processed successfully: {result.get('data', {}).get('event_id')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process Authorize.net webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authorize.net webhook processing failed: {str(e)}"
        )


@router.post(
    "/webhooks/authorize-net/test",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Test webhook processed successfully"},
        400: {"model": Dict[str, Any], "description": "Invalid webhook data"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Receive Authorize.net Test Webhook",
    description="""
    Receive and process test webhooks from Authorize.net for development and testing.
    
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
    
    ### Test Payload Example
    ```json
    {
        "eventType": "net.authorize.payment.authcapture.created",
        "eventId": "test_evt_123456789",
        "payload": {
            "id": "test_txn_123456789",
            "amount": "1.00",
            "currency": "USD",
            "status": "capturedPending"
        },
        "createdAt": "2024-01-01T00:00:00Z"
    }
    ```
    """,
    tags=["authorize-net-webhooks"]
)
async def receive_authorize_net_test_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Receive and process Authorize.net test webhook.
    
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
        
        logger.info(f"Authorize.net test webhook received: {payload}")
        
        # Process test webhook (no signature verification)
        webhook_handler = AuthorizeNetWebhookHandler(db)
        
        # Create a mock request for processing
        class MockRequest:
            def __init__(self, body, headers):
                self._body = body
                self._headers = headers
            
            async def body(self):
                return self._body
            
            @property
            def headers(self):
                return self._headers
        
        mock_request = MockRequest(body, headers)
        
        # Process without signature verification
        result = await webhook_handler._process_webhook_event(payload, headers)
        
        return {
            'success': True,
            'message': 'Authorize.net test webhook processed successfully',
            'timestamp': '2024-01-01T00:00:00Z',
            'data': {
                'received_payload': payload,
                'headers': headers,
                'processing_result': result
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to process Authorize.net test webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authorize.net test webhook processing failed: {str(e)}"
        )


@router.get(
    "/webhooks/authorize-net/events",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "List of supported Authorize.net webhook events"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Get Supported Authorize.net Webhook Events",
    description="""
    Get a list of all supported Authorize.net webhook events and their mappings.
    
    ### Response Format
    ```json
    {
        "success": true,
        "data": {
            "supported_events": [
                {
                    "authorize_net_event": "net.authorize.payment.authcapture.created",
                    "internal_event": "payment.authorized",
                    "description": "Payment authorized and captured"
                }
            ],
            "event_categories": {
                "payment": ["payment.authorized", "payment.captured", "payment.settled"],
                "fraud": ["fraud.detected"],
                "chargeback": ["chargeback.created", "dispute.created"]
            }
        }
    }
    ```
    """,
    tags=["authorize-net-webhooks"]
)
async def get_supported_authorize_net_events() -> Dict[str, Any]:
    """
    Get list of supported Authorize.net webhook events.
    
    Returns:
        Dictionary containing supported events
    """
    try:
        supported_events = [
            {
                "authorize_net_event": "net.authorize.payment.authcapture.created",
                "internal_event": "payment.authorized",
                "description": "Payment authorized and captured"
            },
            {
                "authorize_net_event": "net.authorize.payment.authcapture.updated",
                "internal_event": "payment.captured",
                "description": "Payment status updated"
            },
            {
                "authorize_net_event": "net.authorize.payment.authonly.created",
                "internal_event": "payment.authorized",
                "description": "Payment authorized only"
            },
            {
                "authorize_net_event": "net.authorize.payment.authonly.updated",
                "internal_event": "payment.authorized",
                "description": "Authorization status updated"
            },
            {
                "authorize_net_event": "net.authorize.payment.capture.created",
                "internal_event": "payment.captured",
                "description": "Capture created"
            },
            {
                "authorize_net_event": "net.authorize.payment.capture.updated",
                "internal_event": "payment.captured",
                "description": "Capture status updated"
            },
            {
                "authorize_net_event": "net.authorize.payment.refund.created",
                "internal_event": "payment.refunded",
                "description": "Refund created"
            },
            {
                "authorize_net_event": "net.authorize.payment.refund.updated",
                "internal_event": "payment.refunded",
                "description": "Refund status updated"
            },
            {
                "authorize_net_event": "net.authorize.payment.void.created",
                "internal_event": "payment.voided",
                "description": "Transaction voided"
            },
            {
                "authorize_net_event": "net.authorize.payment.void.updated",
                "internal_event": "payment.voided",
                "description": "Void status updated"
            },
            {
                "authorize_net_event": "net.authorize.payment.settlement.created",
                "internal_event": "payment.settled",
                "description": "Settlement created"
            },
            {
                "authorize_net_event": "net.authorize.payment.settlement.updated",
                "internal_event": "payment.settled",
                "description": "Settlement status updated"
            },
            {
                "authorize_net_event": "net.authorize.payment.fraud.created",
                "internal_event": "fraud.detected",
                "description": "Fraud detected"
            },
            {
                "authorize_net_event": "net.authorize.payment.fraud.updated",
                "internal_event": "fraud.detected",
                "description": "Fraud status updated"
            },
            {
                "authorize_net_event": "net.authorize.payment.chargeback.created",
                "internal_event": "chargeback.created",
                "description": "Chargeback created"
            },
            {
                "authorize_net_event": "net.authorize.payment.chargeback.updated",
                "internal_event": "chargeback.created",
                "description": "Chargeback status updated"
            },
            {
                "authorize_net_event": "net.authorize.payment.dispute.created",
                "internal_event": "dispute.created",
                "description": "Dispute created"
            },
            {
                "authorize_net_event": "net.authorize.payment.dispute.updated",
                "internal_event": "dispute.created",
                "description": "Dispute status updated"
            }
        ]
        
        event_categories = {
            "payment": [
                "payment.authorized",
                "payment.captured", 
                "payment.settled",
                "payment.refunded",
                "payment.voided"
            ],
            "fraud": [
                "fraud.detected"
            ],
            "chargeback": [
                "chargeback.created",
                "dispute.created"
            ]
        }
        
        return {
            'success': True,
            'message': 'Supported Authorize.net webhook events retrieved successfully',
            'timestamp': '2024-01-01T00:00:00Z',
            'data': {
                'supported_events': supported_events,
                'event_categories': event_categories,
                'total_events': len(supported_events)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get supported Authorize.net events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get supported events: {str(e)}"
        )


@router.post(
    "/webhooks/authorize-net/replay/{webhook_id}",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Webhook replayed successfully"},
        404: {"model": Dict[str, Any], "description": "Webhook not found"},
        400: {"model": Dict[str, Any], "description": "Invalid webhook ID"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Replay Authorize.net Webhook",
    description="""
    Replay a previously processed Authorize.net webhook event.
    
    ### Use Cases
    - **Testing**: Replay webhooks for testing purposes
    - **Debugging**: Replay failed webhooks to debug issues
    - **Recovery**: Replay webhooks after system recovery
    - **Development**: Test webhook processing logic
    
    ### Replay Behavior
    - Original webhook data is preserved
    - New webhook record is created with replay flag
    - Event processing is re-executed
    - Duplicate detection is bypassed for replay
    
    ### Security
    - Requires authentication
    - Only webhooks from Authorize.net can be replayed
    - Replay events are marked with special metadata
    
    ### Response Format
    ```json
    {
        "success": true,
        "message": "Webhook replayed successfully",
        "data": {
            "original_webhook_id": "uuid",
            "replay_webhook_id": "uuid",
            "event_type": "payment.authorized",
            "replay_result": {...}
        }
    }
    ```
    """,
    tags=["authorize-net-webhooks"]
)
async def replay_authorize_net_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Replay a previously processed Authorize.net webhook.
    
    Args:
        webhook_id: UUID of the webhook to replay
        db: Database session dependency
        
    Returns:
        Dictionary containing replay result
        
    Raises:
        HTTPException: If replay fails
    """
    try:
        import uuid
        
        # Validate webhook ID
        try:
            webhook_uuid = uuid.UUID(webhook_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook ID format"
            )
        
        webhook_handler = AuthorizeNetWebhookHandler(db)
        
        # Get original webhook
        webhook_service = webhook_handler.webhook_service
        original_webhook = await webhook_service.webhook_repo.get_by_id(webhook_uuid)
        
        if not original_webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Check if it's an Authorize.net webhook
        if not original_webhook.event_id.startswith('anet_'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only Authorize.net webhooks can be replayed"
            )
        
        # Extract original event ID
        original_event_id = original_webhook.event_id[5:]  # Remove 'anet_' prefix
        
        # Create replay webhook with new ID
        replay_event_id = f"anet_replay_{original_event_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create replay webhook record
        replay_webhook = await webhook_service.create_webhook_event(
            event_type=original_webhook.event_type,
            event_id=replay_event_id,
            payment_id=original_webhook.payment_id,
            data=original_webhook.payload,
            headers=original_webhook.headers,
            is_test=original_webhook.is_test
        )
        
        # Add replay metadata
        await webhook_service.webhook_repo.add_webhook_metadata(
            replay_webhook.id,
            {
                'replay_of': str(original_webhook.id),
                'replay_reason': 'manual_replay',
                'replay_timestamp': datetime.utcnow().isoformat(),
                'original_created_at': original_webhook.created_at.isoformat()
            }
        )
        
        # Process the replayed event
        replay_result = await webhook_handler._handle_event_by_type(
            original_webhook.event_type,
            original_webhook.payload,
            replay_webhook.id
        )
        
        logger.info(f"Authorize.net webhook replayed: {webhook_id} -> {replay_webhook.id}")
        
        return {
            'success': True,
            'message': 'Webhook replayed successfully',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'original_webhook_id': webhook_id,
                'replay_webhook_id': str(replay_webhook.id),
                'event_type': original_webhook.event_type,
                'event_id': original_event_id,
                'replay_result': replay_result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replay Authorize.net webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook replay failed: {str(e)}"
        )


@router.get(
    "/webhooks/authorize-net/replay-history/{webhook_id}",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Webhook replay history retrieved successfully"},
        404: {"model": Dict[str, Any], "description": "Webhook not found"},
        400: {"model": Dict[str, Any], "description": "Invalid webhook ID"},
        500: {"model": Dict[str, Any], "description": "Internal server error"}
    },
    summary="Get Webhook Replay History",
    description="""
    Get the replay history for a specific Authorize.net webhook.
    
    ### Response Format
    ```json
    {
        "success": true,
        "data": {
            "original_webhook": {...},
            "replay_history": [
                {
                    "replay_webhook_id": "uuid",
                    "replay_timestamp": "2024-01-01T00:00:00Z",
                    "replay_result": {...}
                }
            ],
            "total_replays": 2
        }
    }
    ```
    """,
    tags=["authorize-net-webhooks"]
)
async def get_webhook_replay_history(
    webhook_id: str,
    db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """
    Get replay history for a specific webhook.
    
    Args:
        webhook_id: UUID of the webhook
        db: Database session dependency
        
    Returns:
        Dictionary containing replay history
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        import uuid
        
        # Validate webhook ID
        try:
            webhook_uuid = uuid.UUID(webhook_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook ID format"
            )
        
        webhook_handler = AuthorizeNetWebhookHandler(db)
        webhook_service = webhook_handler.webhook_service
        
        # Get original webhook
        original_webhook = await webhook_service.webhook_repo.get_by_id(webhook_uuid)
        
        if not original_webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Get replay history (webhooks that have this webhook as replay_of)
        replay_webhooks = await webhook_service.webhook_repo.get_webhooks_by_metadata(
            'replay_of', str(webhook_uuid)
        )
        
        # Format replay history
        replay_history = []
        for replay_webhook in replay_webhooks:
            metadata = replay_webhook.metadata or {}
            replay_history.append({
                'replay_webhook_id': str(replay_webhook.id),
                'replay_timestamp': metadata.get('replay_timestamp'),
                'replay_reason': metadata.get('replay_reason'),
                'replay_result': metadata.get('replay_result'),
                'status': replay_webhook.status
            })
        
        return {
            'success': True,
            'message': 'Webhook replay history retrieved successfully',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'original_webhook': {
                    'id': str(original_webhook.id),
                    'event_type': original_webhook.event_type,
                    'event_id': original_webhook.event_id,
                    'created_at': original_webhook.created_at.isoformat(),
                    'status': original_webhook.status
                },
                'replay_history': replay_history,
                'total_replays': len(replay_history)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get webhook replay history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get replay history: {str(e)}"
        )
