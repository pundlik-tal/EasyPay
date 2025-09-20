"""
EasyPay Payment Gateway - Comprehensive Exception Tests
"""
import pytest
from datetime import datetime

from src.core.exceptions import (
    EasyPayException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    RateLimitError,
    PaymentError,
    ExternalServiceError,
    DatabaseError,
    CacheError,
    WebhookError,
    PaymentNotFoundError,
    WebhookNotFoundError,
    TransactionError,
    MigrationError
)


class TestEasyPayException:
    """Test suite for EasyPayException base class."""

    def test_easypay_exception_creation_with_minimal_params(self):
        """Test EasyPayException creation with minimal parameters."""
        # Act
        exception = EasyPayException(
            message="Test error message",
            error_code="test_error"
        )
        
        # Assert
        assert exception.message == "Test error message"
        assert exception.error_code == "test_error"
        assert exception.error_type == "api_error"
        assert exception.status_code == 400
        assert isinstance(exception.timestamp, datetime)
        assert str(exception) == "Test error message"

    def test_easypay_exception_creation_with_all_params(self):
        """Test EasyPayException creation with all parameters."""
        # Arrange
        custom_timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        # Act
        exception = EasyPayException(
            message="Custom error message",
            error_code="custom_error",
            error_type="custom_type",
            status_code=500,
            timestamp=custom_timestamp
        )
        
        # Assert
        assert exception.message == "Custom error message"
        assert exception.error_code == "custom_error"
        assert exception.error_type == "custom_type"
        assert exception.status_code == 500
        assert exception.timestamp == custom_timestamp

    def test_easypay_exception_inheritance(self):
        """Test that EasyPayException inherits from Exception."""
        # Act
        exception = EasyPayException(
            message="Test message",
            error_code="test_code"
        )
        
        # Assert
        assert isinstance(exception, Exception)
        assert issubclass(EasyPayException, Exception)

    def test_easypay_exception_timestamp_auto_generation(self):
        """Test that timestamp is automatically generated when not provided."""
        # Act
        exception = EasyPayException(
            message="Test message",
            error_code="test_code"
        )
        
        # Assert
        assert exception.timestamp is not None
        assert isinstance(exception.timestamp, datetime)
        assert exception.timestamp <= datetime.utcnow()

    def test_easypay_exception_string_representation(self):
        """Test EasyPayException string representation."""
        # Act
        exception = EasyPayException(
            message="Test error message",
            error_code="test_error"
        )
        
        # Assert
        assert str(exception) == "Test error message"
        assert repr(exception) == "EasyPayException('Test error message')"


class TestValidationError:
    """Test suite for ValidationError class."""

    def test_validation_error_creation_with_message_only(self):
        """Test ValidationError creation with message only."""
        # Act
        exception = ValidationError("Invalid input data")
        
        # Assert
        assert exception.message == "Invalid input data"
        assert exception.error_code == "validation_error"
        assert exception.error_type == "validation_error"
        assert exception.status_code == 400
        assert isinstance(exception.timestamp, datetime)

    def test_validation_error_creation_with_custom_code(self):
        """Test ValidationError creation with custom error code."""
        # Act
        exception = ValidationError(
            message="Invalid email format",
            error_code="invalid_email"
        )
        
        # Assert
        assert exception.message == "Invalid email format"
        assert exception.error_code == "invalid_email"
        assert exception.error_type == "validation_error"
        assert exception.status_code == 400

    def test_validation_error_inheritance(self):
        """Test that ValidationError inherits from EasyPayException."""
        # Act
        exception = ValidationError("Test validation error")
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(ValidationError, EasyPayException)

    def test_validation_error_default_values(self):
        """Test ValidationError default values."""
        # Act
        exception = ValidationError("Test message")
        
        # Assert
        assert exception.error_type == "validation_error"
        assert exception.status_code == 400


class TestAuthenticationError:
    """Test suite for AuthenticationError class."""

    def test_authentication_error_creation_with_default_message(self):
        """Test AuthenticationError creation with default message."""
        # Act
        exception = AuthenticationError()
        
        # Assert
        assert exception.message == "Authentication failed"
        assert exception.error_code == "authentication_error"
        assert exception.error_type == "authentication_error"
        assert exception.status_code == 401

    def test_authentication_error_creation_with_custom_message(self):
        """Test AuthenticationError creation with custom message."""
        # Act
        exception = AuthenticationError("Invalid API key")
        
        # Assert
        assert exception.message == "Invalid API key"
        assert exception.error_code == "authentication_error"
        assert exception.error_type == "authentication_error"
        assert exception.status_code == 401

    def test_authentication_error_creation_with_custom_code(self):
        """Test AuthenticationError creation with custom error code."""
        # Act
        exception = AuthenticationError(
            message="Token expired",
            error_code="token_expired"
        )
        
        # Assert
        assert exception.message == "Token expired"
        assert exception.error_code == "token_expired"
        assert exception.error_type == "authentication_error"
        assert exception.status_code == 401

    def test_authentication_error_inheritance(self):
        """Test that AuthenticationError inherits from EasyPayException."""
        # Act
        exception = AuthenticationError()
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(AuthenticationError, EasyPayException)


class TestAuthorizationError:
    """Test suite for AuthorizationError class."""

    def test_authorization_error_creation_with_default_message(self):
        """Test AuthorizationError creation with default message."""
        # Act
        exception = AuthorizationError()
        
        # Assert
        assert exception.message == "Access denied"
        assert exception.error_code == "authorization_error"
        assert exception.error_type == "authorization_error"
        assert exception.status_code == 403

    def test_authorization_error_creation_with_custom_message(self):
        """Test AuthorizationError creation with custom message."""
        # Act
        exception = AuthorizationError("Insufficient permissions")
        
        # Assert
        assert exception.message == "Insufficient permissions"
        assert exception.error_code == "authorization_error"
        assert exception.error_type == "authorization_error"
        assert exception.status_code == 403

    def test_authorization_error_inheritance(self):
        """Test that AuthorizationError inherits from EasyPayException."""
        # Act
        exception = AuthorizationError()
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(AuthorizationError, EasyPayException)


class TestNotFoundError:
    """Test suite for NotFoundError class."""

    def test_not_found_error_creation_with_default_message(self):
        """Test NotFoundError creation with default message."""
        # Act
        exception = NotFoundError()
        
        # Assert
        assert exception.message == "Resource not found"
        assert exception.error_code == "not_found"
        assert exception.error_type == "not_found"
        assert exception.status_code == 404

    def test_not_found_error_creation_with_custom_message(self):
        """Test NotFoundError creation with custom message."""
        # Act
        exception = NotFoundError("Payment not found")
        
        # Assert
        assert exception.message == "Payment not found"
        assert exception.error_code == "not_found"
        assert exception.error_type == "not_found"
        assert exception.status_code == 404

    def test_not_found_error_inheritance(self):
        """Test that NotFoundError inherits from EasyPayException."""
        # Act
        exception = NotFoundError()
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(NotFoundError, EasyPayException)


class TestConflictError:
    """Test suite for ConflictError class."""

    def test_conflict_error_creation_with_default_message(self):
        """Test ConflictError creation with default message."""
        # Act
        exception = ConflictError()
        
        # Assert
        assert exception.message == "Resource conflict"
        assert exception.error_code == "conflict"
        assert exception.error_type == "conflict"
        assert exception.status_code == 409

    def test_conflict_error_creation_with_custom_message(self):
        """Test ConflictError creation with custom message."""
        # Act
        exception = ConflictError("Payment already processed")
        
        # Assert
        assert exception.message == "Payment already processed"
        assert exception.error_code == "conflict"
        assert exception.error_type == "conflict"
        assert exception.status_code == 409

    def test_conflict_error_inheritance(self):
        """Test that ConflictError inherits from EasyPayException."""
        # Act
        exception = ConflictError()
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(ConflictError, EasyPayException)


class TestRateLimitError:
    """Test suite for RateLimitError class."""

    def test_rate_limit_error_creation_with_default_message(self):
        """Test RateLimitError creation with default message."""
        # Act
        exception = RateLimitError()
        
        # Assert
        assert exception.message == "Rate limit exceeded"
        assert exception.error_code == "rate_limit_exceeded"
        assert exception.error_type == "rate_limit_error"
        assert exception.status_code == 429

    def test_rate_limit_error_creation_with_custom_message(self):
        """Test RateLimitError creation with custom message."""
        # Act
        exception = RateLimitError("API rate limit exceeded")
        
        # Assert
        assert exception.message == "API rate limit exceeded"
        assert exception.error_code == "rate_limit_exceeded"
        assert exception.error_type == "rate_limit_error"
        assert exception.status_code == 429

    def test_rate_limit_error_inheritance(self):
        """Test that RateLimitError inherits from EasyPayException."""
        # Act
        exception = RateLimitError()
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(RateLimitError, EasyPayException)


class TestPaymentError:
    """Test suite for PaymentError class."""

    def test_payment_error_creation_with_message_only(self):
        """Test PaymentError creation with message only."""
        # Act
        exception = PaymentError("Payment processing failed")
        
        # Assert
        assert exception.message == "Payment processing failed"
        assert exception.error_code == "payment_error"
        assert exception.error_type == "payment_error"
        assert exception.status_code == 400

    def test_payment_error_creation_with_custom_code(self):
        """Test PaymentError creation with custom error code."""
        # Act
        exception = PaymentError(
            message="Card declined",
            error_code="card_declined"
        )
        
        # Assert
        assert exception.message == "Card declined"
        assert exception.error_code == "card_declined"
        assert exception.error_type == "payment_error"
        assert exception.status_code == 400

    def test_payment_error_inheritance(self):
        """Test that PaymentError inherits from EasyPayException."""
        # Act
        exception = PaymentError("Test payment error")
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(PaymentError, EasyPayException)


class TestExternalServiceError:
    """Test suite for ExternalServiceError class."""

    def test_external_service_error_creation_with_message_only(self):
        """Test ExternalServiceError creation with message only."""
        # Act
        exception = ExternalServiceError("External API unavailable")
        
        # Assert
        assert exception.message == "External API unavailable"
        assert exception.error_code == "external_service_error"
        assert exception.error_type == "external_service_error"
        assert exception.status_code == 502

    def test_external_service_error_creation_with_custom_code(self):
        """Test ExternalServiceError creation with custom error code."""
        # Act
        exception = ExternalServiceError(
            message="Authorize.net timeout",
            error_code="authorize_net_timeout"
        )
        
        # Assert
        assert exception.message == "Authorize.net timeout"
        assert exception.error_code == "authorize_net_timeout"
        assert exception.error_type == "external_service_error"
        assert exception.status_code == 502

    def test_external_service_error_inheritance(self):
        """Test that ExternalServiceError inherits from EasyPayException."""
        # Act
        exception = ExternalServiceError("Test external service error")
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(ExternalServiceError, EasyPayException)


class TestDatabaseError:
    """Test suite for DatabaseError class."""

    def test_database_error_creation_with_message_only(self):
        """Test DatabaseError creation with message only."""
        # Act
        exception = DatabaseError("Database connection failed")
        
        # Assert
        assert exception.message == "Database connection failed"
        assert exception.error_code == "database_error"
        assert exception.error_type == "database_error"
        assert exception.status_code == 500

    def test_database_error_creation_with_custom_code(self):
        """Test DatabaseError creation with custom error code."""
        # Act
        exception = DatabaseError(
            message="Query timeout",
            error_code="query_timeout"
        )
        
        # Assert
        assert exception.message == "Query timeout"
        assert exception.error_code == "query_timeout"
        assert exception.error_type == "database_error"
        assert exception.status_code == 500

    def test_database_error_inheritance(self):
        """Test that DatabaseError inherits from EasyPayException."""
        # Act
        exception = DatabaseError("Test database error")
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(DatabaseError, EasyPayException)


class TestCacheError:
    """Test suite for CacheError class."""

    def test_cache_error_creation_with_message_only(self):
        """Test CacheError creation with message only."""
        # Act
        exception = CacheError("Redis connection failed")
        
        # Assert
        assert exception.message == "Redis connection failed"
        assert exception.error_code == "cache_error"
        assert exception.error_type == "cache_error"
        assert exception.status_code == 500

    def test_cache_error_creation_with_custom_code(self):
        """Test CacheError creation with custom error code."""
        # Act
        exception = CacheError(
            message="Cache key not found",
            error_code="cache_key_not_found"
        )
        
        # Assert
        assert exception.message == "Cache key not found"
        assert exception.error_code == "cache_key_not_found"
        assert exception.error_type == "cache_error"
        assert exception.status_code == 500

    def test_cache_error_inheritance(self):
        """Test that CacheError inherits from EasyPayException."""
        # Act
        exception = CacheError("Test cache error")
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(CacheError, EasyPayException)


class TestWebhookError:
    """Test suite for WebhookError class."""

    def test_webhook_error_creation_with_message_only(self):
        """Test WebhookError creation with message only."""
        # Act
        exception = WebhookError("Webhook signature verification failed")
        
        # Assert
        assert exception.message == "Webhook signature verification failed"
        assert exception.error_code == "webhook_error"
        assert exception.error_type == "webhook_error"
        assert exception.status_code == 400

    def test_webhook_error_creation_with_custom_code(self):
        """Test WebhookError creation with custom error code."""
        # Act
        exception = WebhookError(
            message="Webhook delivery failed",
            error_code="webhook_delivery_failed"
        )
        
        # Assert
        assert exception.message == "Webhook delivery failed"
        assert exception.error_code == "webhook_delivery_failed"
        assert exception.error_type == "webhook_error"
        assert exception.status_code == 400

    def test_webhook_error_inheritance(self):
        """Test that WebhookError inherits from EasyPayException."""
        # Act
        exception = WebhookError("Test webhook error")
        
        # Assert
        assert isinstance(exception, EasyPayException)
        assert issubclass(WebhookError, EasyPayException)


class TestPaymentNotFoundError:
    """Test suite for PaymentNotFoundError class."""

    def test_payment_not_found_error_creation_with_default_message(self):
        """Test PaymentNotFoundError creation with default message."""
        # Act
        exception = PaymentNotFoundError()
        
        # Assert
        assert exception.message == "Payment not found"
        assert exception.error_code == "payment_not_found"
        assert exception.error_type == "not_found"
        assert exception.status_code == 404

    def test_payment_not_found_error_creation_with_custom_message(self):
        """Test PaymentNotFoundError creation with custom message."""
        # Act
        exception = PaymentNotFoundError("Payment with ID 123 not found")
        
        # Assert
        assert exception.message == "Payment with ID 123 not found"
        assert exception.error_code == "payment_not_found"
        assert exception.error_type == "not_found"
        assert exception.status_code == 404

    def test_payment_not_found_error_inheritance(self):
        """Test that PaymentNotFoundError inherits from NotFoundError."""
        # Act
        exception = PaymentNotFoundError()
        
        # Assert
        assert isinstance(exception, NotFoundError)
        assert isinstance(exception, EasyPayException)
        assert issubclass(PaymentNotFoundError, NotFoundError)


class TestWebhookNotFoundError:
    """Test suite for WebhookNotFoundError class."""

    def test_webhook_not_found_error_creation_with_default_message(self):
        """Test WebhookNotFoundError creation with default message."""
        # Act
        exception = WebhookNotFoundError()
        
        # Assert
        assert exception.message == "Webhook not found"
        assert exception.error_code == "webhook_not_found"
        assert exception.error_type == "not_found"
        assert exception.status_code == 404

    def test_webhook_not_found_error_creation_with_custom_message(self):
        """Test WebhookNotFoundError creation with custom message."""
        # Act
        exception = WebhookNotFoundError("Webhook with ID 456 not found")
        
        # Assert
        assert exception.message == "Webhook with ID 456 not found"
        assert exception.error_code == "webhook_not_found"
        assert exception.error_type == "not_found"
        assert exception.status_code == 404

    def test_webhook_not_found_error_inheritance(self):
        """Test that WebhookNotFoundError inherits from NotFoundError."""
        # Act
        exception = WebhookNotFoundError()
        
        # Assert
        assert isinstance(exception, NotFoundError)
        assert isinstance(exception, EasyPayException)
        assert issubclass(WebhookNotFoundError, NotFoundError)


class TestTransactionError:
    """Test suite for TransactionError class."""

    def test_transaction_error_creation_with_message_only(self):
        """Test TransactionError creation with message only."""
        # Act
        exception = TransactionError("Transaction rollback failed")
        
        # Assert
        assert exception.message == "Transaction rollback failed"
        assert exception.error_code == "transaction_error"
        assert exception.error_type == "transaction_error"
        assert exception.status_code == 500

    def test_transaction_error_creation_with_custom_code(self):
        """Test TransactionError creation with custom error code."""
        # Act
        exception = TransactionError(
            message="Deadlock detected",
            error_code="deadlock_detected"
        )
        
        # Assert
        assert exception.message == "Deadlock detected"
        assert exception.error_code == "deadlock_detected"
        assert exception.error_type == "transaction_error"
        assert exception.status_code == 500

    def test_transaction_error_inheritance(self):
        """Test that TransactionError inherits from DatabaseError."""
        # Act
        exception = TransactionError("Test transaction error")
        
        # Assert
        assert isinstance(exception, DatabaseError)
        assert isinstance(exception, EasyPayException)
        assert issubclass(TransactionError, DatabaseError)


class TestMigrationError:
    """Test suite for MigrationError class."""

    def test_migration_error_creation_with_message_only(self):
        """Test MigrationError creation with message only."""
        # Act
        exception = MigrationError("Migration script failed")
        
        # Assert
        assert exception.message == "Migration script failed"
        assert exception.error_code == "migration_error"
        assert exception.error_type == "migration_error"
        assert exception.status_code == 500

    def test_migration_error_creation_with_custom_code(self):
        """Test MigrationError creation with custom error code."""
        # Act
        exception = MigrationError(
            message="Schema version mismatch",
            error_code="schema_version_mismatch"
        )
        
        # Assert
        assert exception.message == "Schema version mismatch"
        assert exception.error_code == "schema_version_mismatch"
        assert exception.error_type == "migration_error"
        assert exception.status_code == 500

    def test_migration_error_inheritance(self):
        """Test that MigrationError inherits from DatabaseError."""
        # Act
        exception = MigrationError("Test migration error")
        
        # Assert
        assert isinstance(exception, DatabaseError)
        assert isinstance(exception, EasyPayException)
        assert issubclass(MigrationError, DatabaseError)


class TestExceptionHierarchy:
    """Test suite for exception hierarchy and relationships."""

    def test_exception_hierarchy_structure(self):
        """Test the overall exception hierarchy structure."""
        # Test base exception
        base_exception = EasyPayException("Base error", "base_error")
        assert isinstance(base_exception, Exception)
        
        # Test validation error
        validation_error = ValidationError("Validation failed")
        assert isinstance(validation_error, EasyPayException)
        assert isinstance(validation_error, Exception)
        
        # Test authentication error
        auth_error = AuthenticationError("Auth failed")
        assert isinstance(auth_error, EasyPayException)
        assert isinstance(auth_error, Exception)
        
        # Test payment error
        payment_error = PaymentError("Payment failed")
        assert isinstance(payment_error, EasyPayException)
        assert isinstance(payment_error, Exception)
        
        # Test payment not found error
        payment_not_found = PaymentNotFoundError("Payment not found")
        assert isinstance(payment_not_found, NotFoundError)
        assert isinstance(payment_not_found, EasyPayException)
        assert isinstance(payment_not_found, Exception)
        
        # Test transaction error
        transaction_error = TransactionError("Transaction failed")
        assert isinstance(transaction_error, DatabaseError)
        assert isinstance(transaction_error, EasyPayException)
        assert isinstance(transaction_error, Exception)

    def test_exception_status_codes(self):
        """Test that exceptions have correct HTTP status codes."""
        assert ValidationError("test").status_code == 400
        assert AuthenticationError("test").status_code == 401
        assert AuthorizationError("test").status_code == 403
        assert NotFoundError("test").status_code == 404
        assert ConflictError("test").status_code == 409
        assert RateLimitError("test").status_code == 429
        assert PaymentError("test").status_code == 400
        assert ExternalServiceError("test").status_code == 502
        assert DatabaseError("test").status_code == 500
        assert CacheError("test").status_code == 500
        assert WebhookError("test").status_code == 400

    def test_exception_error_types(self):
        """Test that exceptions have correct error types."""
        assert ValidationError("test").error_type == "validation_error"
        assert AuthenticationError("test").error_type == "authentication_error"
        assert AuthorizationError("test").error_type == "authorization_error"
        assert NotFoundError("test").error_type == "not_found"
        assert ConflictError("test").error_type == "conflict"
        assert RateLimitError("test").error_type == "rate_limit_error"
        assert PaymentError("test").error_type == "payment_error"
        assert ExternalServiceError("test").error_type == "external_service_error"
        assert DatabaseError("test").error_type == "database_error"
        assert CacheError("test").error_type == "cache_error"
        assert WebhookError("test").error_type == "webhook_error"

    def test_exception_error_codes(self):
        """Test that exceptions have correct error codes."""
        assert ValidationError("test").error_code == "validation_error"
        assert AuthenticationError("test").error_code == "authentication_error"
        assert AuthorizationError("test").error_code == "authorization_error"
        assert NotFoundError("test").error_code == "not_found"
        assert ConflictError("test").error_code == "conflict"
        assert RateLimitError("test").error_code == "rate_limit_exceeded"
        assert PaymentError("test").error_code == "payment_error"
        assert ExternalServiceError("test").error_code == "external_service_error"
        assert DatabaseError("test").error_code == "database_error"
        assert CacheError("test").error_code == "cache_error"
        assert WebhookError("test").error_code == "webhook_error"
        assert PaymentNotFoundError("test").error_code == "payment_not_found"
        assert WebhookNotFoundError("test").error_code == "webhook_not_found"
        assert TransactionError("test").error_code == "transaction_error"
        assert MigrationError("test").error_code == "migration_error"


class TestExceptionEdgeCases:
    """Test suite for exception edge cases."""

    def test_exception_with_empty_message(self):
        """Test exception creation with empty message."""
        # Act
        exception = EasyPayException(message="", error_code="empty_message")
        
        # Assert
        assert exception.message == ""
        assert str(exception) == ""

    def test_exception_with_very_long_message(self):
        """Test exception creation with very long message."""
        # Arrange
        long_message = "x" * 1000
        
        # Act
        exception = EasyPayException(message=long_message, error_code="long_message")
        
        # Assert
        assert exception.message == long_message
        assert len(str(exception)) == 1000

    def test_exception_with_special_characters(self):
        """Test exception creation with special characters."""
        # Arrange
        special_message = "Error with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        # Act
        exception = EasyPayException(message=special_message, error_code="special_chars")
        
        # Assert
        assert exception.message == special_message
        assert str(exception) == special_message

    def test_exception_with_unicode_characters(self):
        """Test exception creation with unicode characters."""
        # Arrange
        unicode_message = "Error with unicode: 你好世界 🌍"
        
        # Act
        exception = EasyPayException(message=unicode_message, error_code="unicode")
        
        # Assert
        assert exception.message == unicode_message
        assert str(exception) == unicode_message

    def test_exception_with_none_timestamp(self):
        """Test exception creation with None timestamp (should auto-generate)."""
        # Act
        exception = EasyPayException(
            message="Test message",
            error_code="test_code",
            timestamp=None
        )
        
        # Assert
        assert exception.timestamp is not None
        assert isinstance(exception.timestamp, datetime)

    def test_exception_timestamp_ordering(self):
        """Test that exception timestamps are ordered correctly."""
        # Arrange
        timestamp1 = datetime(2024, 1, 1, 12, 0, 0)
        timestamp2 = datetime(2024, 1, 1, 12, 0, 1)
        
        # Act
        exception1 = EasyPayException(
            message="First error",
            error_code="first",
            timestamp=timestamp1
        )
        exception2 = EasyPayException(
            message="Second error",
            error_code="second",
            timestamp=timestamp2
        )
        
        # Assert
        assert exception1.timestamp < exception2.timestamp
        assert exception1.timestamp == timestamp1
        assert exception2.timestamp == timestamp2

    def test_exception_inheritance_chain(self):
        """Test the complete inheritance chain for all exceptions."""
        # Test all exception types
        exceptions = [
            EasyPayException("base", "base"),
            ValidationError("validation"),
            AuthenticationError("auth"),
            AuthorizationError("authorization"),
            NotFoundError("not_found"),
            ConflictError("conflict"),
            RateLimitError("rate_limit"),
            PaymentError("payment"),
            ExternalServiceError("external"),
            DatabaseError("database"),
            CacheError("cache"),
            WebhookError("webhook"),
            PaymentNotFoundError("payment_not_found"),
            WebhookNotFoundError("webhook_not_found"),
            TransactionError("transaction"),
            MigrationError("migration")
        ]
        
        # All should inherit from Exception
        for exc in exceptions:
            assert isinstance(exc, Exception)
        
        # Specific inheritance tests
        assert isinstance(PaymentNotFoundError("test"), NotFoundError)
        assert isinstance(WebhookNotFoundError("test"), NotFoundError)
        assert isinstance(TransactionError("test"), DatabaseError)
        assert isinstance(MigrationError("test"), DatabaseError)
        
        # All should inherit from EasyPayException
        for exc in exceptions:
            assert isinstance(exc, EasyPayException)
