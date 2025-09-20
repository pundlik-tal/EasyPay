"""
EasyPay Payment Gateway - Data Validator

This module provides comprehensive data validation for database operations
including schema validation, data integrity checks, and business rule validation.
"""

import re
import uuid
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from src.core.exceptions import ValidationError, DatabaseError

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation level enumeration."""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


class ValidationRule:
    """
    Represents a validation rule.
    
    Attributes:
        field_name: Name of the field to validate
        validator: Validation function
        error_message: Custom error message
        required: Whether field is required
        nullable: Whether field can be null
    """
    
    def __init__(
        self,
        field_name: str,
        validator: Callable[[Any], bool],
        error_message: str,
        required: bool = True,
        nullable: bool = False
    ):
        self.field_name = field_name
        self.validator = validator
        self.error_message = error_message
        self.required = required
        self.nullable = nullable


class DataValidator:
    """
    Comprehensive data validator for database operations.
    
    Provides validation for all data models with configurable rules
    and validation levels.
    """
    
    def __init__(self, engine: AsyncEngine, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.engine = engine
        self.validation_level = validation_level
        self.validation_rules = self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """Initialize validation rules for all models."""
        return {
            "Payment": self._get_payment_validation_rules(),
            "Webhook": self._get_webhook_validation_rules(),
            "AuditLog": self._get_audit_log_validation_rules()
        }
    
    def _get_payment_validation_rules(self) -> List[ValidationRule]:
        """Get validation rules for Payment model."""
        return [
            ValidationRule(
                "external_id",
                self._validate_external_id,
                "External ID must be a non-empty string with valid characters",
                required=True
            ),
            ValidationRule(
                "amount",
                self._validate_amount,
                "Amount must be a positive decimal number",
                required=True
            ),
            ValidationRule(
                "currency",
                self._validate_currency,
                "Currency must be a valid 3-letter ISO code",
                required=True
            ),
            ValidationRule(
                "status",
                self._validate_payment_status,
                "Status must be a valid PaymentStatus value",
                required=True
            ),
            ValidationRule(
                "payment_method",
                self._validate_payment_method,
                "Payment method must be a valid PaymentMethod value",
                required=True
            ),
            ValidationRule(
                "customer_id",
                self._validate_customer_id,
                "Customer ID must be a valid string",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "customer_email",
                self._validate_email,
                "Customer email must be a valid email address",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "customer_name",
                self._validate_customer_name,
                "Customer name must be a valid string",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "card_last_four",
                self._validate_card_last_four,
                "Card last four must be exactly 4 digits",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "card_brand",
                self._validate_card_brand,
                "Card brand must be a valid card brand",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "card_exp_month",
                self._validate_card_exp_month,
                "Card expiration month must be between 01 and 12",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "card_exp_year",
                self._validate_card_exp_year,
                "Card expiration year must be a valid 4-digit year",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "refunded_amount",
                self._validate_refunded_amount,
                "Refunded amount must be a non-negative decimal",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "refund_count",
                self._validate_refund_count,
                "Refund count must be a non-negative integer",
                required=False,
                nullable=True
            )
        ]
    
    def _get_webhook_validation_rules(self) -> List[ValidationRule]:
        """Get validation rules for Webhook model."""
        return [
            ValidationRule(
                "event_type",
                self._validate_webhook_event_type,
                "Event type must be a valid WebhookEventType value",
                required=True
            ),
            ValidationRule(
                "event_id",
                self._validate_event_id,
                "Event ID must be a non-empty string",
                required=True
            ),
            ValidationRule(
                "status",
                self._validate_webhook_status,
                "Status must be a valid WebhookStatus value",
                required=True
            ),
            ValidationRule(
                "url",
                self._validate_webhook_url,
                "URL must be a valid HTTP/HTTPS URL",
                required=True
            ),
            ValidationRule(
                "payload",
                self._validate_webhook_payload,
                "Payload must be a valid JSON object",
                required=True
            ),
            ValidationRule(
                "retry_count",
                self._validate_retry_count,
                "Retry count must be a non-negative integer",
                required=True
            ),
            ValidationRule(
                "max_retries",
                self._validate_max_retries,
                "Max retries must be a positive integer",
                required=True
            )
        ]
    
    def _get_audit_log_validation_rules(self) -> List[ValidationRule]:
        """Get validation rules for AuditLog model."""
        return [
            ValidationRule(
                "action",
                self._validate_audit_action,
                "Action must be a valid AuditLogAction value",
                required=True
            ),
            ValidationRule(
                "level",
                self._validate_audit_level,
                "Level must be a valid AuditLogLevel value",
                required=True
            ),
            ValidationRule(
                "message",
                self._validate_audit_message,
                "Message must be a non-empty string",
                required=True
            ),
            ValidationRule(
                "entity_type",
                self._validate_entity_type,
                "Entity type must be a valid string",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "entity_id",
                self._validate_entity_id,
                "Entity ID must be a valid string",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "user_id",
                self._validate_user_id,
                "User ID must be a valid string",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "ip_address",
                self._validate_ip_address,
                "IP address must be a valid IPv4 or IPv6 address",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "request_id",
                self._validate_request_id,
                "Request ID must be a valid UUID string",
                required=False,
                nullable=True
            ),
            ValidationRule(
                "correlation_id",
                self._validate_correlation_id,
                "Correlation ID must be a valid UUID string",
                required=False,
                nullable=True
            )
        ]
    
    async def validate_model_data(
        self,
        model_name: str,
        data: Dict[str, Any],
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Validate data for a specific model.
        
        Args:
            model_name: Name of the model to validate
            data: Data dictionary to validate
            session: Database session for context validation
            
        Returns:
            Dictionary with validation results
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            if model_name not in self.validation_rules:
                raise ValidationError(f"Unknown model: {model_name}")
            
            rules = self.validation_rules[model_name]
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "validated_fields": []
            }
            
            # Validate each field
            for rule in rules:
                field_value = data.get(rule.field_name)
                
                # Check if required field is missing
                if rule.required and field_value is None:
                    validation_results["valid"] = False
                    validation_results["errors"].append({
                        "field": rule.field_name,
                        "message": f"Required field '{rule.field_name}' is missing"
                    })
                    continue
                
                # Check if nullable field is None
                if not rule.nullable and field_value is None:
                    validation_results["valid"] = False
                    validation_results["errors"].append({
                        "field": rule.field_name,
                        "message": f"Field '{rule.field_name}' cannot be null"
                    })
                    continue
                
                # Skip validation if field is None and nullable
                if field_value is None and rule.nullable:
                    validation_results["validated_fields"].append(rule.field_name)
                    continue
                
                # Validate field value
                try:
                    if not rule.validator(field_value):
                        validation_results["valid"] = False
                        validation_results["errors"].append({
                            "field": rule.field_name,
                            "message": rule.error_message,
                            "value": field_value
                        })
                    else:
                        validation_results["validated_fields"].append(rule.field_name)
                        
                except Exception as e:
                    validation_results["valid"] = False
                    validation_results["errors"].append({
                        "field": rule.field_name,
                        "message": f"Validation error: {str(e)}",
                        "value": field_value
                    })
            
            # Additional context validation if session provided
            if session:
                context_validation = await self._validate_context(model_name, data, session)
                validation_results["context_validation"] = context_validation
                
                if not context_validation.get("valid", True):
                    validation_results["valid"] = False
                    validation_results["errors"].extend(context_validation.get("errors", []))
            
            return validation_results
            
        except Exception as e:
            raise ValidationError(f"Data validation failed: {str(e)}")
    
    async def _validate_context(
        self,
        model_name: str,
        data: Dict[str, Any],
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Perform context-specific validation.
        
        Args:
            model_name: Name of the model
            data: Data to validate
            session: Database session
            
        Returns:
            Context validation results
        """
        try:
            context_results = {
                "valid": True,
                "errors": []
            }
            
            if model_name == "Payment":
                # Validate payment-specific business rules
                await self._validate_payment_context(data, session, context_results)
            elif model_name == "Webhook":
                # Validate webhook-specific business rules
                await self._validate_webhook_context(data, session, context_results)
            elif model_name == "AuditLog":
                # Validate audit log-specific business rules
                await self._validate_audit_log_context(data, session, context_results)
            
            return context_results
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [{"message": f"Context validation failed: {str(e)}"}]
            }
    
    async def _validate_payment_context(
        self,
        data: Dict[str, Any],
        session: AsyncSession,
        results: Dict[str, Any]
    ):
        """Validate payment-specific business rules."""
        try:
            # Check for duplicate external_id
            external_id = data.get("external_id")
            if external_id:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM payments WHERE external_id = :external_id"),
                    {"external_id": external_id}
                )
                count = result.scalar()
                if count > 0:
                    results["valid"] = False
                    results["errors"].append({
                        "field": "external_id",
                        "message": f"External ID '{external_id}' already exists"
                    })
            
            # Validate refunded_amount against amount
            amount = data.get("amount")
            refunded_amount = data.get("refunded_amount")
            if amount and refunded_amount:
                try:
                    amount_decimal = Decimal(str(amount))
                    refunded_decimal = Decimal(str(refunded_amount))
                    if refunded_decimal > amount_decimal:
                        results["valid"] = False
                        results["errors"].append({
                            "field": "refunded_amount",
                            "message": "Refunded amount cannot exceed payment amount"
                        })
                except (InvalidOperation, ValueError):
                    pass  # Will be caught by field validation
            
            # Validate card information consistency
            card_fields = ["card_last_four", "card_brand", "card_exp_month", "card_exp_year"]
            card_values = [data.get(field) for field in card_fields]
            
            if any(card_values) and not all(card_values):
                results["valid"] = False
                results["errors"].append({
                    "field": "card_information",
                    "message": "All card fields must be provided together or none at all"
                })
            
        except Exception as e:
            results["valid"] = False
            results["errors"].append({
                "message": f"Payment context validation error: {str(e)}"
            })
    
    async def _validate_webhook_context(
        self,
        data: Dict[str, Any],
        session: AsyncSession,
        results: Dict[str, Any]
    ):
        """Validate webhook-specific business rules."""
        try:
            # Check for duplicate event_id
            event_id = data.get("event_id")
            if event_id:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM webhooks WHERE event_id = :event_id"),
                    {"event_id": event_id}
                )
                count = result.scalar()
                if count > 0:
                    results["valid"] = False
                    results["errors"].append({
                        "field": "event_id",
                        "message": f"Event ID '{event_id}' already exists"
                    })
            
            # Validate payment_id exists if provided
            payment_id = data.get("payment_id")
            if payment_id:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM payments WHERE id = :payment_id"),
                    {"payment_id": payment_id}
                )
                count = result.scalar()
                if count == 0:
                    results["valid"] = False
                    results["errors"].append({
                        "field": "payment_id",
                        "message": f"Payment ID '{payment_id}' does not exist"
                    })
            
        except Exception as e:
            results["valid"] = False
            results["errors"].append({
                "message": f"Webhook context validation error: {str(e)}"
            })
    
    async def _validate_audit_log_context(
        self,
        data: Dict[str, Any],
        session: AsyncSession,
        results: Dict[str, Any]
    ):
        """Validate audit log-specific business rules."""
        try:
            # Validate payment_id exists if provided
            payment_id = data.get("payment_id")
            if payment_id:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM payments WHERE id = :payment_id"),
                    {"payment_id": payment_id}
                )
                count = result.scalar()
                if count == 0:
                    results["valid"] = False
                    results["errors"].append({
                        "field": "payment_id",
                        "message": f"Payment ID '{payment_id}' does not exist"
                    })
            
        except Exception as e:
            results["valid"] = False
            results["errors"].append({
                "message": f"Audit log context validation error: {str(e)}"
            })
    
    # Field validation methods
    def _validate_external_id(self, value: Any) -> bool:
        """Validate external ID."""
        if not isinstance(value, str) or not value.strip():
            return False
        # Allow alphanumeric, hyphens, underscores
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', value))
    
    def _validate_amount(self, value: Any) -> bool:
        """Validate payment amount."""
        try:
            amount = Decimal(str(value))
            return amount > 0
        except (InvalidOperation, ValueError, TypeError):
            return False
    
    def _validate_currency(self, value: Any) -> bool:
        """Validate currency code."""
        if not isinstance(value, str):
            return False
        # Valid 3-letter ISO currency codes
        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "CNY"}
        return value.upper() in valid_currencies
    
    def _validate_payment_status(self, value: Any) -> bool:
        """Validate payment status."""
        if not isinstance(value, str):
            return False
        valid_statuses = [
            "pending", "authorized", "captured", "settled", 
            "refunded", "partially_refunded", "voided", "failed", "declined"
        ]
        return value in valid_statuses
    
    def _validate_payment_method(self, value: Any) -> bool:
        """Validate payment method."""
        if not isinstance(value, str):
            return False
        valid_methods = ["credit_card", "debit_card", "bank_transfer", "digital_wallet", "cryptocurrency"]
        return value in valid_methods
    
    def _validate_customer_id(self, value: Any) -> bool:
        """Validate customer ID."""
        if not isinstance(value, str):
            return False
        return bool(value.strip())
    
    def _validate_email(self, value: Any) -> bool:
        """Validate email address."""
        if not isinstance(value, str):
            return False
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))
    
    def _validate_customer_name(self, value: Any) -> bool:
        """Validate customer name."""
        if not isinstance(value, str):
            return False
        return bool(value.strip())
    
    def _validate_card_last_four(self, value: Any) -> bool:
        """Validate card last four digits."""
        if not isinstance(value, str):
            return False
        return bool(re.match(r'^\d{4}$', value))
    
    def _validate_card_brand(self, value: Any) -> bool:
        """Validate card brand."""
        if not isinstance(value, str):
            return False
        valid_brands = {"visa", "mastercard", "amex", "discover", "jcb", "diners"}
        return value.lower() in valid_brands
    
    def _validate_card_exp_month(self, value: Any) -> bool:
        """Validate card expiration month."""
        if not isinstance(value, str):
            return False
        return bool(re.match(r'^(0[1-9]|1[0-2])$', value))
    
    def _validate_card_exp_year(self, value: Any) -> bool:
        """Validate card expiration year."""
        if not isinstance(value, str):
            return False
        if not re.match(r'^\d{4}$', value):
            return False
        try:
            year = int(value)
            current_year = datetime.now().year
            return current_year <= year <= current_year + 20
        except ValueError:
            return False
    
    def _validate_refunded_amount(self, value: Any) -> bool:
        """Validate refunded amount."""
        try:
            amount = Decimal(str(value))
            return amount >= 0
        except (InvalidOperation, ValueError, TypeError):
            return False
    
    def _validate_refund_count(self, value: Any) -> bool:
        """Validate refund count."""
        try:
            count = int(value)
            return count >= 0
        except (ValueError, TypeError):
            return False
    
    def _validate_webhook_event_type(self, value: Any) -> bool:
        """Validate webhook event type."""
        if not isinstance(value, str):
            return False
        valid_event_types = [
            "payment.authorized", "payment.captured", "payment.settled",
            "payment.refunded", "payment.voided", "payment.failed", 
            "payment.declined", "fraud.detected", "chargeback.created", 
            "dispute.created"
        ]
        return value in valid_event_types
    
    def _validate_event_id(self, value: Any) -> bool:
        """Validate event ID."""
        if not isinstance(value, str):
            return False
        return bool(value.strip())
    
    def _validate_webhook_status(self, value: Any) -> bool:
        """Validate webhook status."""
        if not isinstance(value, str):
            return False
        valid_statuses = ["pending", "delivered", "failed", "retrying", "expired"]
        return value in valid_statuses
    
    def _validate_webhook_url(self, value: Any) -> bool:
        """Validate webhook URL."""
        if not isinstance(value, str):
            return False
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, value))
    
    def _validate_webhook_payload(self, value: Any) -> bool:
        """Validate webhook payload."""
        return isinstance(value, (dict, list))
    
    def _validate_retry_count(self, value: Any) -> bool:
        """Validate retry count."""
        try:
            count = int(value)
            return count >= 0
        except (ValueError, TypeError):
            return False
    
    def _validate_max_retries(self, value: Any) -> bool:
        """Validate max retries."""
        try:
            count = int(value)
            return count > 0
        except (ValueError, TypeError):
            return False
    
    def _validate_audit_action(self, value: Any) -> bool:
        """Validate audit action."""
        if not isinstance(value, str):
            return False
        valid_actions = [
            "payment.created", "payment.updated", "payment.refunded", 
            "payment.voided", "payment.captured", "webhook.received",
            "webhook.delivered", "webhook.failed", "api_key.created",
            "api_key.revoked", "user.login", "user.logout", 
            "system.error", "security.violation"
        ]
        return value in valid_actions
    
    def _validate_audit_level(self, value: Any) -> bool:
        """Validate audit level."""
        if not isinstance(value, str):
            return False
        valid_levels = ["info", "warning", "error", "critical"]
        return value in valid_levels
    
    def _validate_audit_message(self, value: Any) -> bool:
        """Validate audit message."""
        if not isinstance(value, str):
            return False
        return bool(value.strip())
    
    def _validate_entity_type(self, value: Any) -> bool:
        """Validate entity type."""
        if not isinstance(value, str):
            return False
        return bool(value.strip())
    
    def _validate_entity_id(self, value: Any) -> bool:
        """Validate entity ID."""
        if not isinstance(value, str):
            return False
        return bool(value.strip())
    
    def _validate_user_id(self, value: Any) -> bool:
        """Validate user ID."""
        if not isinstance(value, str):
            return False
        return bool(value.strip())
    
    def _validate_ip_address(self, value: Any) -> bool:
        """Validate IP address."""
        if not isinstance(value, str):
            return False
        # IPv4 pattern
        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        # IPv6 pattern (simplified)
        ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        return bool(re.match(ipv4_pattern, value) or re.match(ipv6_pattern, value))
    
    def _validate_request_id(self, value: Any) -> bool:
        """Validate request ID."""
        if not isinstance(value, str):
            return False
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    def _validate_correlation_id(self, value: Any) -> bool:
        """Validate correlation ID."""
        if not isinstance(value, str):
            return False
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False


# Import logger
import logging
