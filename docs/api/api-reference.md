# EasyPay Payment Gateway API Reference

Welcome to the EasyPay Payment Gateway API documentation. This comprehensive guide provides everything you need to integrate with our payment processing platform.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Error Handling](#error-handling)
- [SDKs and Libraries](#sdks-and-libraries)
- [Webhooks](#webhooks)
- [Rate Limiting](#rate-limiting)
- [Best Practices](#best-practices)

## Getting Started

### Base URL

- **Production**: `https://api.easypay.com`
- **Sandbox**: `https://api-sandbox.easypay.com`
- **Development**: `http://localhost:8000`

### API Versioning

The API uses URL-based versioning. The current version is `v1`:

```
https://api.easypay.com/api/v1/payments
```

### Content Type

All requests must include the `Content-Type: application/json` header.

### Response Format

All responses are returned in JSON format with the following structure:

```json
{
  "data": {
    // Response data
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Authentication

EasyPay supports two authentication methods:

### 1. API Key Authentication

Include your API key in the request headers:

```bash
curl -H "Authorization: Bearer ak_123456789:sk_123456789" \
     https://api.easypay.com/api/v1/payments
```

### 2. JWT Token Authentication

First, generate JWT tokens using your API key:

```bash
curl -X POST https://api.easypay.com/api/v1/auth/tokens \
     -H "Content-Type: application/json" \
     -d '{
       "api_key_id": "ak_123456789",
       "api_key_secret": "sk_123456789"
     }'
```

Then use the access token:

```bash
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
     https://api.easypay.com/api/v1/payments
```

## API Endpoints

### Payments

#### Create Payment

Create a new payment.

```http
POST /api/v1/payments
```

**Request Body:**

```json
{
  "amount": "25.99",
  "currency": "USD",
  "payment_method": "credit_card",
  "customer_id": "cust_123456789",
  "customer_email": "customer@example.com",
  "customer_name": "John Doe",
  "card_token": "tok_visa_4242",
  "description": "Premium subscription payment",
  "metadata": {
    "order_id": "order_2024_001",
    "product": "premium_plan"
  },
  "is_test": true
}
```

**Response:**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "external_id": "pay_2024_001",
    "amount": "25.99",
    "currency": "USD",
    "status": "captured",
    "payment_method": "credit_card",
    "customer_id": "cust_123456789",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "card_last_four": "4242",
    "card_brand": "visa",
    "description": "Premium subscription payment",
    "metadata": {
      "order_id": "order_2024_001",
      "product": "premium_plan"
    },
    "processor_response_code": "1",
    "processor_response_message": "This transaction has been approved",
    "processor_transaction_id": "1234567890",
    "refunded_amount": "0.00",
    "refund_count": 0,
    "created_at": "2024-01-01T12:00:00Z",
    "updated_at": "2024-01-01T12:00:05Z",
    "processed_at": "2024-01-01T12:00:05Z",
    "settled_at": "2024-01-02T08:00:00Z",
    "is_test": true
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-01T12:00:05Z"
}
```

#### Get Payment

Retrieve a payment by ID.

```http
GET /api/v1/payments/{payment_id}
```

**Parameters:**
- `payment_id` (path): Payment ID (UUID or external ID)

**Response:** Same as create payment response.

#### List Payments

Retrieve a paginated list of payments.

```http
GET /api/v1/payments
```

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `per_page` (integer): Items per page (default: 20, max: 100)
- `customer_id` (string): Filter by customer ID
- `status` (string): Filter by payment status

**Response:**

```json
{
  "data": {
    "payments": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "external_id": "pay_2024_001",
        "amount": "25.99",
        "currency": "USD",
        "status": "captured",
        "created_at": "2024-01-01T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "per_page": 20,
    "total_pages": 1
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Refund Payment

Refund a payment (full or partial).

```http
POST /api/v1/payments/{payment_id}/refund
```

**Request Body:**

```json
{
  "amount": "10.00",
  "reason": "Customer requested refund",
  "metadata": {
    "refund_reason": "customer_request"
  }
}
```

**Response:** Updated payment object.

#### Cancel Payment

Cancel a payment.

```http
POST /api/v1/payments/{payment_id}/cancel
```

**Request Body:**

```json
{
  "reason": "Customer requested cancellation",
  "metadata": {
    "cancel_reason": "customer_request"
  }
}
```

**Response:** Updated payment object.

### Authentication

#### Create API Key

Create a new API key.

```http
POST /api/v1/auth/api-keys
```

**Request Body:**

```json
{
  "name": "Production API Key",
  "description": "API key for production payment processing",
  "permissions": ["payments:read", "payments:write"],
  "rate_limit_per_minute": 100,
  "rate_limit_per_hour": 1000,
  "rate_limit_per_day": 10000
}
```

**Response:**

```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "key_id": "ak_123456789",
    "key_secret": "sk_123456789",
    "name": "Production API Key",
    "description": "API key for production payment processing",
    "permissions": ["payments:read", "payments:write"],
    "expires_at": null,
    "created_at": "2024-01-01T00:00:00Z"
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Generate JWT Tokens

Generate JWT access and refresh tokens.

```http
POST /api/v1/auth/tokens
```

**Request Body:**

```json
{
  "api_key_id": "ak_123456789",
  "api_key_secret": "sk_123456789",
  "expires_in": 3600
}
```

**Response:**

```json
{
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "expires_at": "2024-01-01T01:00:00Z"
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Health Checks

#### Basic Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "service": "EasyPay Payment Gateway",
  "version": "1.0.0"
}
```

#### Readiness Check

```http
GET /health/ready
```

**Response:**

```json
{
  "status": "ready",
  "database": true,
  "cache": true,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Error Handling

All API errors follow a consistent format:

```json
{
  "error": {
    "type": "validation_error",
    "code": "invalid_amount",
    "message": "Amount must be greater than 0",
    "param": "amount",
    "request_id": "req_123456789"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common Error Codes

- `validation_error`: Request data validation failed
- `authentication_error`: Authentication failed
- `authorization_error`: Insufficient permissions
- `payment_error`: Payment processing failed
- `rate_limit_exceeded`: Rate limit exceeded
- `external_service_error`: External service unavailable

See [Error Codes Documentation](error-codes.md) for a complete list.

## SDKs and Libraries

### Python SDK

```python
import asyncio
from easypay import EasyPayClient

async def main():
    client = EasyPayClient(
        api_key_id="ak_123456789",
        api_key_secret="sk_123456789",
        base_url="https://api.easypay.com"
    )
    
    # Create a payment
    payment = await client.payments.create({
        "amount": "25.99",
        "currency": "USD",
        "payment_method": "credit_card",
        "customer_id": "cust_123",
        "card_token": "tok_visa_4242"
    })
    
    print(f"Payment created: {payment['id']}")
    
    await client.close()

asyncio.run(main())
```

### JavaScript SDK

```javascript
const EasyPay = require('easypay-sdk');

const client = new EasyPay({
  apiKeyId: 'ak_123456789',
  apiKeySecret: 'sk_123456789',
  baseUrl: 'https://api.easypay.com'
});

// Create a payment
client.payments.create({
  amount: '25.99',
  currency: 'USD',
  payment_method: 'credit_card',
  customer_id: 'cust_123',
  card_token: 'tok_visa_4242'
}).then(payment => {
  console.log(`Payment created: ${payment.id}`);
}).catch(error => {
  console.error('Error:', error.message);
});
```

## Webhooks

EasyPay sends webhooks to notify your application of payment events.

### Webhook Events

- `payment.created`: Payment was created
- `payment.captured`: Payment was captured
- `payment.failed`: Payment failed
- `payment.refunded`: Payment was refunded
- `payment.cancelled`: Payment was cancelled

### Webhook Security

All webhooks are signed with HMAC-SHA256. Verify the signature:

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
```

## Rate Limiting

API requests are rate limited per API key:

- **Default**: 100 requests/minute, 1000/hour, 10000/day
- **Configurable**: Per API key settings
- **Headers**: Rate limit information in response headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Best Practices

### Security

1. **Store API keys securely**: Use environment variables
2. **Use HTTPS**: Always use HTTPS in production
3. **Validate webhooks**: Always verify webhook signatures
4. **Rotate keys regularly**: Implement key rotation

### Performance

1. **Use pagination**: For large data sets
2. **Implement caching**: Cache frequently accessed data
3. **Handle rate limits**: Implement exponential backoff
4. **Use async operations**: For better performance

### Error Handling

1. **Check status codes**: Always check HTTP status codes
2. **Implement retries**: For transient errors
3. **Log errors**: For debugging and monitoring
4. **Handle edge cases**: Plan for all error scenarios

### Testing

1. **Use sandbox**: Test with sandbox environment
2. **Mock external services**: For unit tests
3. **Test error scenarios**: Test all error conditions
4. **Monitor in production**: Set up monitoring and alerts

## Support

- **Documentation**: https://docs.easypay.com
- **Support Email**: support@easypay.com
- **Status Page**: https://status.easypay.com
- **GitHub**: https://github.com/easypay/api-examples
