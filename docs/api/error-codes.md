# EasyPay API Error Codes

This document provides a comprehensive reference for all error codes returned by the EasyPay Payment Gateway API.

## Error Response Format

All API errors follow a consistent response format:

```json
{
  "error": {
    "type": "error_type",
    "code": "error_code",
    "message": "Human-readable error message",
    "param": "field_name",
    "request_id": "req_123456789"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## HTTP Status Codes

| Status Code | Description | When Used |
|-------------|-------------|-----------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no content returned |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | External service error |
| 503 | Service Unavailable | Service temporarily unavailable |

## Error Categories

### Validation Errors (400)

These errors occur when request data fails validation.

| Error Code | Description | Example |
|------------|-------------|---------|
| `validation_error` | General validation error | Request data is invalid |
| `invalid_amount` | Payment amount is invalid | Amount must be greater than 0 |
| `invalid_currency` | Currency code is invalid | Currency must be a 3-character code |
| `invalid_payment_method` | Payment method is invalid | Unsupported payment method |
| `invalid_customer_id` | Customer ID is invalid | Customer ID format is invalid |
| `invalid_date_range` | Date range is invalid | End date must be after start date |
| `invalid_card_token` | Card token is invalid | Card token format is invalid |
| `invalid_email` | Email format is invalid | Email must be a valid format |
| `invalid_phone` | Phone format is invalid | Phone number format is invalid |
| `invalid_metadata` | Metadata is invalid | Metadata must be a valid JSON object |

### Authentication Errors (401)

These errors occur when authentication fails.

| Error Code | Description | Example |
|------------|-------------|---------|
| `authentication_error` | General authentication error | Authentication failed |
| `invalid_api_key` | API key is invalid | API key not found |
| `invalid_credentials` | Invalid credentials provided | API key secret is incorrect |
| `expired_token` | Token has expired | JWT token has expired |
| `revoked_token` | Token has been revoked | Token is no longer valid |
| `missing_auth_header` | Authorization header missing | Authorization header required |
| `invalid_auth_format` | Authorization header format invalid | Bearer token format required |

### Authorization Errors (403)

These errors occur when authorization fails.

| Error Code | Description | Example |
|------------|-------------|---------|
| `authorization_error` | General authorization error | Authorization failed |
| `insufficient_permissions` | Insufficient permissions | Permission 'payments:write' required |
| `access_denied` | Access denied | Access to resource denied |
| `ip_blocked` | IP address blocked | IP address not whitelisted |
| `rate_limit_exceeded` | Rate limit exceeded | Too many requests |
| `quota_exceeded` | API quota exceeded | Monthly quota exceeded |

### Payment Errors (400/500)

These errors occur during payment processing.

| Error Code | Description | Example |
|------------|-------------|---------|
| `payment_error` | General payment error | Payment processing failed |
| `payment_not_found` | Payment not found | Payment ID not found |
| `payment_already_processed` | Payment already processed | Payment cannot be modified |
| `payment_cannot_be_refunded` | Payment cannot be refunded | Payment status does not allow refund |
| `payment_cannot_be_cancelled` | Payment cannot be cancelled | Payment status does not allow cancellation |
| `card_declined` | Card was declined | Card declined by issuer |
| `insufficient_funds` | Insufficient funds | Account has insufficient funds |
| `expired_card` | Card has expired | Card expiration date has passed |
| `invalid_card` | Invalid card information | Card number is invalid |
| `card_not_supported` | Card not supported | Card type not supported |
| `fraud_detected` | Fraud detected | Transaction flagged for fraud |
| `duplicate_transaction` | Duplicate transaction | Transaction already exists |

### External Service Errors (502)

These errors occur when external services fail.

| Error Code | Description | Example |
|------------|-------------|---------|
| `external_service_error` | General external service error | External service unavailable |
| `authorize_net_unavailable` | Authorize.net service unavailable | Authorize.net is down |
| `authorize_net_timeout` | Authorize.net service timeout | Authorize.net request timeout |
| `authorize_net_error` | Authorize.net processing error | Authorize.net returned error |
| `webhook_delivery_failed` | Webhook delivery failed | Webhook endpoint unreachable |
| `webhook_signature_invalid` | Webhook signature invalid | Webhook signature verification failed |

### System Errors (500)

These errors occur due to system issues.

| Error Code | Description | Example |
|------------|-------------|---------|
| `internal_error` | Internal server error | Unexpected server error |
| `database_error` | Database operation failed | Database connection failed |
| `cache_error` | Cache operation failed | Redis connection failed |
| `service_unavailable` | Service temporarily unavailable | Service maintenance |
| `configuration_error` | Configuration error | Invalid configuration |
| `migration_error` | Database migration error | Migration failed |

## Error Handling Best Practices

### Client-Side Error Handling

1. **Check HTTP Status Code**: Always check the HTTP status code first
2. **Parse Error Response**: Extract error details from the response body
3. **Handle Specific Errors**: Implement specific handling for different error types
4. **Retry Logic**: Implement retry logic for transient errors
5. **User-Friendly Messages**: Display user-friendly error messages

### Example Error Handling

```python
import asyncio
from easypay import EasyPayClient, EasyPayAPIError, EasyPayAuthError

async def handle_payment_error():
    client = EasyPayClient(
        api_key_id="ak_123456789",
        api_key_secret="sk_123456789"
    )
    
    try:
        payment = await client.payments.create({
            "amount": "25.99",
            "currency": "USD",
            "payment_method": "credit_card",
            "card_token": "tok_visa_4242"
        })
        
    except EasyPayAuthError as e:
        print(f"Authentication failed: {e.message}")
        # Handle authentication error
        
    except EasyPayAPIError as e:
        if e.status_code == 400:
            print(f"Validation error: {e.message}")
            if e.error_code == "card_declined":
                print("Card was declined. Please try a different card.")
            elif e.error_code == "insufficient_funds":
                print("Insufficient funds. Please check your account balance.")
        elif e.status_code == 429:
            print(f"Rate limit exceeded. Retry after {e.response_data.get('retry_after')} seconds")
        else:
            print(f"API error: {e.message}")
    
    finally:
        await client.close()
```

### Retry Logic

```python
import asyncio
import time
from easypay import EasyPayClient, EasyPayRateLimitError, EasyPayNetworkError

async def retry_request(client, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await client.payments.create(payment_data)
            
        except EasyPayRateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after or (2 ** attempt)
                print(f"Rate limited. Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
            raise
            
        except EasyPayNetworkError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Network error. Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                continue
            raise
```

## Error Monitoring

### Logging Errors

Always log errors for debugging and monitoring:

```python
import logging

logger = logging.getLogger(__name__)

try:
    payment = await client.payments.create(payment_data)
except EasyPayAPIError as e:
    logger.error(f"Payment creation failed: {e.message}", extra={
        "error_code": e.error_code,
        "status_code": e.status_code,
        "request_id": e.response_data.get("request_id")
    })
```

### Error Metrics

Track error rates and types for monitoring:

```python
# Track error metrics
error_metrics = {
    "total_errors": 0,
    "error_by_type": {},
    "error_by_code": {}
}

try:
    payment = await client.payments.create(payment_data)
except EasyPayAPIError as e:
    error_metrics["total_errors"] += 1
    error_metrics["error_by_type"][e.error_type] = error_metrics["error_by_type"].get(e.error_type, 0) + 1
    error_metrics["error_by_code"][e.error_code] = error_metrics["error_by_code"].get(e.error_code, 0) + 1
```

## Support

If you encounter an error that is not documented here or need assistance with error handling, please contact our support team:

- **Email**: support@easypay.com
- **Documentation**: https://docs.easypay.com
- **Status Page**: https://status.easypay.com
