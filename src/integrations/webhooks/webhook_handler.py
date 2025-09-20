"""
EasyPay Payment Gateway - Webhook Handler
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.webhook import WebhookEventType
from src.core.services.webhook_service import WebhookService
from src.core.services.request_signing_service import WebhookSigningService
from src.core.exceptions import ValidationError, AuthenticationError
from src.infrastructure.logging import get_logger
from src.infrastructure.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class WebhookHandler:
    """
    Handler for processing incoming webhook events.
    
    This class handles webhook signature verification, event processing,
    and response generation for incoming webhook requests.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize webhook handler.
        
        Args:
            db: Database session
        """
        self.db = db
        self.webhook_service = WebhookService(db, settings.webhook_secret)
        self.signing_service = WebhookSigningService(settings.webhook_secret)
    
    async def process_webhook_request(
        self,
        request: Request,
        webhook_type: str = "payment"
    ) -> Dict[str, Any]:
        """
        Process incoming webhook request.
        
        Args:
            request: FastAPI request object
            webhook_type: Type of webhook (payment, fraud, etc.)
            
        Returns:
            Dictionary containing processing result
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # Extract request data
            body = await request.body()
            headers = dict(request.headers)
            
            # Verify webhook signature
            signature_header = headers.get('X-Webhook-Signature')
            if not signature_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing webhook signature"
                )
            
            # Verify signature
            try:
                self.signing_service.verify_webhook_signature(
                    body.decode('utf-8'),
                    signature_header
                )
            except AuthenticationError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid webhook signature: {str(e)}"
                )
            
            # Parse webhook payload
            try:
                payload = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON payload"
                )
            
            # Process webhook based on type
            if webhook_type == "payment":
                result = await self._process_payment_webhook(payload, headers)
            elif webhook_type == "fraud":
                result = await self._process_fraud_webhook(payload, headers)
            elif webhook_type == "chargeback":
                result = await self._process_chargeback_webhook(payload, headers)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported webhook type: {webhook_type}"
                )
            
            logger.info(f"Webhook processed successfully: {webhook_type}")
            
            return {
                'status': 'success',
                'webhook_type': webhook_type,
                'processed_at': datetime.utcnow().isoformat(),
                'result': result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process webhook: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Webhook processing failed: {str(e)}"
            )
    
    async def _process_payment_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process payment-related webhook.
        
        Args:
            payload: Webhook payload
            headers: Request headers
            
        Returns:
            Dictionary containing processing result
        """
        try:
            # Extract payment information
            event_type = payload.get('event_type')
            event_id = payload.get('event_id')
            payment_id = payload.get('payment_id')
            payment_data = payload.get('data', {})
            
            if not event_type or not event_id:
                raise ValidationError("Missing required fields: event_type, event_id")
            
            # Validate event type
            valid_events = [event.value for event in WebhookEventType]
            if event_type not in valid_events:
                raise ValidationError(f"Invalid event type: {event_type}")
            
            # Create webhook event record
            webhook = await self.webhook_service.create_webhook_event(
                event_type=event_type,
                event_id=event_id,
                payment_id=uuid.UUID(payment_id) if payment_id else None,
                data=payment_data,
                headers=headers,
                is_test=payload.get('is_test', False)
            )
            
            # Process payment event based on type
            processing_result = await self._handle_payment_event(
                event_type, payment_data, webhook.id
            )
            
            return {
                'webhook_id': str(webhook.id),
                'event_type': event_type,
                'event_id': event_id,
                'payment_id': payment_id,
                'processing_result': processing_result
            }
            
        except Exception as e:
            logger.error(f"Failed to process payment webhook: {str(e)}")
            raise
    
    async def _process_fraud_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process fraud-related webhook.
        
        Args:
            payload: Webhook payload
            headers: Request headers
            
        Returns:
            Dictionary containing processing result
        """
        try:
            # Extract fraud information
            event_type = payload.get('event_type', 'fraud.detected')
            event_id = payload.get('event_id')
            fraud_data = payload.get('data', {})
            
            if not event_id:
                raise ValidationError("Missing required field: event_id")
            
            # Create webhook event record
            webhook = await self.webhook_service.create_webhook_event(
                event_type=event_type,
                event_id=event_id,
                data=fraud_data,
                headers=headers,
                is_test=payload.get('is_test', False)
            )
            
            # Process fraud event
            processing_result = await self._handle_fraud_event(
                fraud_data, webhook.id
            )
            
            return {
                'webhook_id': str(webhook.id),
                'event_type': event_type,
                'event_id': event_id,
                'processing_result': processing_result
            }
            
        except Exception as e:
            logger.error(f"Failed to process fraud webhook: {str(e)}")
            raise
    
    async def _process_chargeback_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process chargeback-related webhook.
        
        Args:
            payload: Webhook payload
            headers: Request headers
            
        Returns:
            Dictionary containing processing result
        """
        try:
            # Extract chargeback information
            event_type = payload.get('event_type', 'chargeback.created')
            event_id = payload.get('event_id')
            chargeback_data = payload.get('data', {})
            
            if not event_id:
                raise ValidationError("Missing required field: event_id")
            
            # Create webhook event record
            webhook = await self.webhook_service.create_webhook_event(
                event_type=event_type,
                event_id=event_id,
                data=chargeback_data,
                headers=headers,
                is_test=payload.get('is_test', False)
            )
            
            # Process chargeback event
            processing_result = await self._handle_chargeback_event(
                chargeback_data, webhook.id
            )
            
            return {
                'webhook_id': str(webhook.id),
                'event_type': event_type,
                'event_id': event_id,
                'processing_result': processing_result
            }
            
        except Exception as e:
            logger.error(f"Failed to process chargeback webhook: {str(e)}")
            raise
    
    async def _handle_payment_event(
        self,
        event_type: str,
        payment_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Handle payment event processing.
        
        Args:
            event_type: Type of payment event
            payment_data: Payment data
            webhook_id: Webhook ID
            
        Returns:
            Dictionary containing processing result
        """
        try:
            # Process based on event type
            if event_type == 'payment.authorized':
                return await self._handle_payment_authorized(payment_data, webhook_id)
            elif event_type == 'payment.captured':
                return await self._handle_payment_captured(payment_data, webhook_id)
            elif event_type == 'payment.settled':
                return await self._handle_payment_settled(payment_data, webhook_id)
            elif event_type == 'payment.refunded':
                return await self._handle_payment_refunded(payment_data, webhook_id)
            elif event_type == 'payment.voided':
                return await self._handle_payment_voided(payment_data, webhook_id)
            elif event_type == 'payment.failed':
                return await self._handle_payment_failed(payment_data, webhook_id)
            elif event_type == 'payment.declined':
                return await self._handle_payment_declined(payment_data, webhook_id)
            else:
                return {'status': 'processed', 'message': f'Event type {event_type} processed'}
                
        except Exception as e:
            logger.error(f"Failed to handle payment event {event_type}: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    async def _handle_payment_authorized(
        self,
        payment_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle payment authorized event."""
        logger.info(f"Payment authorized: {payment_data.get('id')}")
        return {
            'status': 'processed',
            'action': 'payment_authorized',
            'payment_id': payment_data.get('id'),
            'amount': payment_data.get('amount')
        }
    
    async def _handle_payment_captured(
        self,
        payment_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle payment captured event."""
        logger.info(f"Payment captured: {payment_data.get('id')}")
        return {
            'status': 'processed',
            'action': 'payment_captured',
            'payment_id': payment_data.get('id'),
            'amount': payment_data.get('amount')
        }
    
    async def _handle_payment_settled(
        self,
        payment_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle payment settled event."""
        logger.info(f"Payment settled: {payment_data.get('id')}")
        return {
            'status': 'processed',
            'action': 'payment_settled',
            'payment_id': payment_data.get('id'),
            'amount': payment_data.get('amount')
        }
    
    async def _handle_payment_refunded(
        self,
        payment_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle payment refunded event."""
        logger.info(f"Payment refunded: {payment_data.get('id')}")
        return {
            'status': 'processed',
            'action': 'payment_refunded',
            'payment_id': payment_data.get('id'),
            'refund_amount': payment_data.get('refund_amount')
        }
    
    async def _handle_payment_voided(
        self,
        payment_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle payment voided event."""
        logger.info(f"Payment voided: {payment_data.get('id')}")
        return {
            'status': 'processed',
            'action': 'payment_voided',
            'payment_id': payment_data.get('id')
        }
    
    async def _handle_payment_failed(
        self,
        payment_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle payment failed event."""
        logger.info(f"Payment failed: {payment_data.get('id')}")
        return {
            'status': 'processed',
            'action': 'payment_failed',
            'payment_id': payment_data.get('id'),
            'failure_reason': payment_data.get('failure_reason')
        }
    
    async def _handle_payment_declined(
        self,
        payment_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle payment declined event."""
        logger.info(f"Payment declined: {payment_data.get('id')}")
        return {
            'status': 'processed',
            'action': 'payment_declined',
            'payment_id': payment_data.get('id'),
            'decline_reason': payment_data.get('decline_reason')
        }
    
    async def _handle_fraud_event(
        self,
        fraud_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle fraud detection event."""
        logger.info(f"Fraud detected: {fraud_data.get('transaction_id')}")
        return {
            'status': 'processed',
            'action': 'fraud_detected',
            'transaction_id': fraud_data.get('transaction_id'),
            'risk_score': fraud_data.get('risk_score'),
            'fraud_reasons': fraud_data.get('fraud_reasons', [])
        }
    
    async def _handle_chargeback_event(
        self,
        chargeback_data: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Handle chargeback event."""
        logger.info(f"Chargeback created: {chargeback_data.get('chargeback_id')}")
        return {
            'status': 'processed',
            'action': 'chargeback_created',
            'chargeback_id': chargeback_data.get('chargeback_id'),
            'payment_id': chargeback_data.get('payment_id'),
            'chargeback_reason': chargeback_data.get('reason')
        }
    
    def generate_webhook_response(
        self,
        success: bool = True,
        message: str = "Webhook processed successfully",
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate standardized webhook response.
        
        Args:
            success: Whether processing was successful
            message: Response message
            data: Additional response data
            
        Returns:
            Dictionary containing webhook response
        """
        return {
            'success': success,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data or {}
        }
