"""
EasyPay Payment Gateway - Authorize.net Webhook Handler
"""
import json
import uuid
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models.webhook import WebhookEventType
from src.core.services.webhook_service import WebhookService
from src.core.services.payment_service import PaymentService
from src.core.exceptions import ValidationError, AuthenticationError
from src.infrastructure.logging import get_logger
from src.infrastructure.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class AuthorizeNetWebhookHandler:
    """
    Handler for processing Authorize.net webhook events.
    
    This class handles Authorize.net specific webhook processing including:
    - Signature verification using Authorize.net's webhook signing
    - Event type mapping to internal webhook events
    - Payment status updates based on webhook events
    - Settlement and fraud detection webhook processing
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize Authorize.net webhook handler.
        
        Args:
            db: Database session
        """
        self.db = db
        self.webhook_service = WebhookService(db, settings.webhook_secret)
        self.payment_service = PaymentService(db)
    
    async def process_authorize_net_webhook(
        self,
        request: Request
    ) -> Dict[str, Any]:
        """
        Process incoming Authorize.net webhook.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dictionary containing processing result
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # Extract request data
            body = await request.body()
            headers = dict(request.headers)
            
            # Parse payload
            try:
                payload = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON payload: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON payload"
                )
            
            # Verify webhook signature
            signature_header = headers.get('X-Anet-Signature')
            if not signature_header:
                logger.warning("Missing Authorize.net signature header")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing webhook signature"
                )
            
            if not await self._verify_authorize_net_signature(body, signature_header):
                logger.warning("Invalid Authorize.net webhook signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid webhook signature"
                )
            
            # Process webhook event
            result = await self._process_webhook_event(payload, headers)
            
            logger.info(f"Authorize.net webhook processed successfully: {result.get('event_id')}")
            
            return {
                'success': True,
                'message': 'Authorize.net webhook processed successfully',
                'timestamp': datetime.utcnow().isoformat(),
                'data': result
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to process Authorize.net webhook: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Webhook processing failed: {str(e)}"
            )
    
    async def _verify_authorize_net_signature(
        self,
        payload: bytes,
        signature_header: str
    ) -> bool:
        """
        Verify Authorize.net webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature_header: Signature header value
            
        Returns:
            True if signature is valid
        """
        try:
            # Authorize.net uses HMAC-SHA512 with the webhook secret
            # Format: "sha512={signature}"
            if not signature_header.startswith('sha512='):
                logger.error("Invalid signature format")
                return False
            
            signature = signature_header[7:]  # Remove 'sha512=' prefix
            
            # Get webhook secret from settings
            webhook_secret = settings.AUTHORIZE_NET_WEBHOOK_SECRET
            if not webhook_secret:
                logger.error("Authorize.net webhook secret not configured")
                return False
            
            # Calculate expected signature
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha512
            ).hexdigest()
            
            # Compare signatures using constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return False
    
    async def _process_webhook_event(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process Authorize.net webhook event.
        
        Args:
            payload: Webhook payload
            headers: Request headers
            
        Returns:
            Dictionary containing processing result
        """
        try:
            # Extract event information
            event_type = payload.get('eventType')
            event_id = payload.get('eventId')
            
            if not event_type or not event_id:
                raise ValidationError("Missing required event fields")
            
            # Check for duplicate events
            duplicate_check = await self._check_duplicate_event(event_id)
            if duplicate_check['is_duplicate']:
                logger.info(f"Duplicate webhook event detected: {event_id}")
                return {
                    'webhook_id': str(duplicate_check['existing_webhook_id']),
                    'event_type': duplicate_check['event_type'],
                    'event_id': event_id,
                    'processing_result': {'status': 'duplicate', 'message': 'Event already processed'},
                    'is_duplicate': True
                }
            
            # Map Authorize.net event types to internal event types
            internal_event_type = self._map_event_type(event_type)
            
            # Create webhook record
            webhook = await self.webhook_service.create_webhook_event(
                event_type=internal_event_type,
                event_id=f"anet_{event_id}",
                data=payload,
                headers=headers,
                is_test=settings.AUTHORIZE_NET_SANDBOX
            )
            
            # Process event based on type
            processing_result = await self._handle_event_by_type(
                internal_event_type,
                payload,
                webhook.id
            )
            
            return {
                'webhook_id': str(webhook.id),
                'event_type': internal_event_type,
                'event_id': event_id,
                'processing_result': processing_result,
                'is_duplicate': False
            }
            
        except Exception as e:
            logger.error(f"Failed to process webhook event: {str(e)}")
            raise
    
    async def _check_duplicate_event(self, event_id: str) -> Dict[str, Any]:
        """
        Check if webhook event has already been processed.
        
        Args:
            event_id: Authorize.net event ID
            
        Returns:
            Dictionary containing duplicate check result
        """
        try:
            # Check if webhook with this event ID already exists
            existing_webhooks = await self.webhook_service.list_webhooks(
                event_type=None,
                status=None,
                payment_id=None,
                start_date=None,
                end_date=None,
                page=1,
                per_page=1
            )
            
            # Look for webhook with matching event ID
            internal_event_id = f"anet_{event_id}"
            for webhook in existing_webhooks.get('webhooks', []):
                if webhook.event_id == internal_event_id:
                    return {
                        'is_duplicate': True,
                        'existing_webhook_id': webhook.id,
                        'event_type': webhook.event_type,
                        'created_at': webhook.created_at.isoformat()
                    }
            
            return {
                'is_duplicate': False,
                'existing_webhook_id': None,
                'event_type': None,
                'created_at': None
            }
            
        except Exception as e:
            logger.error(f"Failed to check for duplicate event: {str(e)}")
            # If check fails, assume not duplicate to avoid blocking legitimate events
            return {
                'is_duplicate': False,
                'existing_webhook_id': None,
                'event_type': None,
                'created_at': None
            }
    
    def _map_event_type(self, authorize_net_event: str) -> str:
        """
        Map Authorize.net event types to internal event types.
        
        Args:
            authorize_net_event: Authorize.net event type
            
        Returns:
            Internal event type
        """
        event_mapping = {
            # Payment events
            'net.authorize.payment.authcapture.created': 'payment.authorized',
            'net.authorize.payment.authcapture.updated': 'payment.captured',
            'net.authorize.payment.authonly.created': 'payment.authorized',
            'net.authorize.payment.authonly.updated': 'payment.authorized',
            'net.authorize.payment.capture.created': 'payment.captured',
            'net.authorize.payment.capture.updated': 'payment.captured',
            'net.authorize.payment.refund.created': 'payment.refunded',
            'net.authorize.payment.refund.updated': 'payment.refunded',
            'net.authorize.payment.void.created': 'payment.voided',
            'net.authorize.payment.void.updated': 'payment.voided',
            
            # Settlement events
            'net.authorize.payment.settlement.created': 'payment.settled',
            'net.authorize.payment.settlement.updated': 'payment.settled',
            
            # Fraud detection events
            'net.authorize.payment.fraud.created': 'fraud.detected',
            'net.authorize.payment.fraud.updated': 'fraud.detected',
            
            # Chargeback events
            'net.authorize.payment.chargeback.created': 'chargeback.created',
            'net.authorize.payment.chargeback.updated': 'chargeback.created',
            'net.authorize.payment.dispute.created': 'dispute.created',
            'net.authorize.payment.dispute.updated': 'dispute.created',
        }
        
        return event_mapping.get(authorize_net_event, 'payment.unknown')
    
    async def _handle_event_by_type(
        self,
        event_type: str,
        payload: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Handle webhook event based on type.
        
        Args:
            event_type: Internal event type
            payload: Webhook payload
            webhook_id: Webhook ID
            
        Returns:
            Dictionary containing processing result
        """
        try:
            if event_type.startswith('payment.'):
                return await self._handle_payment_event(event_type, payload, webhook_id)
            elif event_type.startswith('fraud.'):
                return await self._handle_fraud_event(event_type, payload, webhook_id)
            elif event_type.startswith('chargeback.') or event_type.startswith('dispute.'):
                return await self._handle_chargeback_event(event_type, payload, webhook_id)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return {'status': 'ignored', 'message': f'Unknown event type: {event_type}'}
                
        except Exception as e:
            logger.error(f"Failed to handle event {event_type}: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    async def _handle_payment_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Handle payment-related webhook events.
        
        Args:
            event_type: Payment event type
            payload: Webhook payload
            webhook_id: Webhook ID
            
        Returns:
            Dictionary containing processing result
        """
        try:
            # Extract payment information
            payment_data = payload.get('payload', {})
            transaction_id = payment_data.get('id')
            
            if not transaction_id:
                logger.warning("Missing transaction ID in payment webhook")
                return {'status': 'error', 'message': 'Missing transaction ID'}
            
            # Find payment by transaction ID
            payment = await self.payment_service.get_payment_by_external_id(transaction_id)
            if not payment:
                logger.warning(f"Payment not found for transaction ID: {transaction_id}")
                return {'status': 'error', 'message': 'Payment not found'}
            
            # Update payment status based on event type
            if event_type == 'payment.authorized':
                await self.payment_service.update_payment_status(
                    payment.id, 'authorized', 'Webhook notification'
                )
            elif event_type == 'payment.captured':
                await self.payment_service.update_payment_status(
                    payment.id, 'captured', 'Webhook notification'
                )
            elif event_type == 'payment.settled':
                await self.payment_service.update_payment_status(
                    payment.id, 'settled', 'Webhook notification'
                )
            elif event_type == 'payment.refunded':
                await self.payment_service.update_payment_status(
                    payment.id, 'refunded', 'Webhook notification'
                )
            elif event_type == 'payment.voided':
                await self.payment_service.update_payment_status(
                    payment.id, 'voided', 'Webhook notification'
                )
            
            logger.info(f"Payment {payment.id} status updated to {event_type}")
            
            return {
                'status': 'processed',
                'payment_id': str(payment.id),
                'transaction_id': transaction_id,
                'event_type': event_type
            }
            
        except Exception as e:
            logger.error(f"Failed to handle payment event: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    async def _handle_fraud_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Handle fraud detection webhook events.
        
        Args:
            event_type: Fraud event type
            payload: Webhook payload
            webhook_id: Webhook ID
            
        Returns:
            Dictionary containing processing result
        """
        try:
            # Extract fraud information
            fraud_data = payload.get('payload', {})
            transaction_id = fraud_data.get('id')
            
            if not transaction_id:
                logger.warning("Missing transaction ID in fraud webhook")
                return {'status': 'error', 'message': 'Missing transaction ID'}
            
            # Find payment by transaction ID
            payment = await self.payment_service.get_payment_by_external_id(transaction_id)
            if not payment:
                logger.warning(f"Payment not found for transaction ID: {transaction_id}")
                return {'status': 'error', 'message': 'Payment not found'}
            
            # Update payment with fraud information
            fraud_score = fraud_data.get('fraudScore', 0)
            fraud_reasons = fraud_data.get('fraudReasons', [])
            
            # Add fraud metadata to payment
            await self.payment_service.add_payment_metadata(
                payment.id,
                {
                    'fraud_score': fraud_score,
                    'fraud_reasons': fraud_reasons,
                    'fraud_detected_at': datetime.utcnow().isoformat(),
                    'webhook_id': str(webhook_id)
                }
            )
            
            # Update payment status if fraud detected
            if fraud_score > 75:  # High fraud score threshold
                await self.payment_service.update_payment_status(
                    payment.id, 'fraud_detected', 'Fraud detection webhook'
                )
            
            logger.info(f"Fraud event processed for payment {payment.id}: score={fraud_score}")
            
            return {
                'status': 'processed',
                'payment_id': str(payment.id),
                'transaction_id': transaction_id,
                'fraud_score': fraud_score,
                'fraud_reasons': fraud_reasons
            }
            
        except Exception as e:
            logger.error(f"Failed to handle fraud event: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    async def _handle_chargeback_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        webhook_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Handle chargeback/dispute webhook events.
        
        Args:
            event_type: Chargeback event type
            payload: Webhook payload
            webhook_id: Webhook ID
            
        Returns:
            Dictionary containing processing result
        """
        try:
            # Extract chargeback information
            chargeback_data = payload.get('payload', {})
            transaction_id = chargeback_data.get('id')
            
            if not transaction_id:
                logger.warning("Missing transaction ID in chargeback webhook")
                return {'status': 'error', 'message': 'Missing transaction ID'}
            
            # Find payment by transaction ID
            payment = await self.payment_service.get_payment_by_external_id(transaction_id)
            if not payment:
                logger.warning(f"Payment not found for transaction ID: {transaction_id}")
                return {'status': 'error', 'message': 'Payment not found'}
            
            # Extract chargeback details
            chargeback_id = chargeback_data.get('chargebackId')
            chargeback_reason = chargeback_data.get('reason')
            chargeback_amount = chargeback_data.get('amount')
            
            # Add chargeback metadata to payment
            await self.payment_service.add_payment_metadata(
                payment.id,
                {
                    'chargeback_id': chargeback_id,
                    'chargeback_reason': chargeback_reason,
                    'chargeback_amount': chargeback_amount,
                    'chargeback_created_at': datetime.utcnow().isoformat(),
                    'webhook_id': str(webhook_id)
                }
            )
            
            # Update payment status
            await self.payment_service.update_payment_status(
                payment.id, 'chargeback', 'Chargeback webhook'
            )
            
            logger.info(f"Chargeback event processed for payment {payment.id}: {chargeback_id}")
            
            return {
                'status': 'processed',
                'payment_id': str(payment.id),
                'transaction_id': transaction_id,
                'chargeback_id': chargeback_id,
                'chargeback_reason': chargeback_reason
            }
            
        except Exception as e:
            logger.error(f"Failed to handle chargeback event: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def generate_webhook_response(
        self,
        success: bool,
        message: str,
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
