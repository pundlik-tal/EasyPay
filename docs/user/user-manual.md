# EasyPay Payment Gateway - User Manual

This user manual provides comprehensive guidance for using the EasyPay Payment Gateway system.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Payment Processing](#payment-processing)
- [Webhook Management](#webhook-management)
- [Dashboard Usage](#dashboard-usage)
- [API Integration](#api-integration)
- [Monitoring](#monitoring)
- [Best Practices](#best-practices)
- [FAQ](#faq)

## Getting Started

### Account Setup

1. **Sign Up**: Create your EasyPay account
2. **Verify Email**: Confirm your email address
3. **Complete Profile**: Fill in business information
4. **Get API Keys**: Generate your API credentials
5. **Test Integration**: Use sandbox environment

### Dashboard Access

- **URL**: https://dashboard.easypay.com
- **Login**: Use your email and password
- **Two-Factor**: Enable 2FA for security

## Authentication

### API Key Management

#### Creating API Keys

1. Navigate to **Settings > API Keys**
2. Click **Create New Key**
3. Enter key name and description
4. Select permissions
5. Set rate limits
6. Save and copy credentials

#### API Key Permissions

- **payments:read** - View payments
- **payments:write** - Create payments
- **payments:refund** - Process refunds
- **webhooks:read** - View webhooks
- **webhooks:write** - Manage webhooks
- **admin:read** - View admin data
- **admin:write** - Modify admin settings

#### Using API Keys

```bash
# Include in request headers
curl -H "Authorization: Bearer ak_your_key:sk_your_secret" \
     https://api.easypay.com/api/v1/payments
```

### JWT Tokens

#### Generating Tokens

```bash
curl -X POST https://api.easypay.com/api/v1/auth/tokens \
     -H "Content-Type: application/json" \
     -d '{
       "api_key_id": "ak_your_key",
       "api_key_secret": "sk_your_secret"
     }'
```

#### Using Tokens

```bash
# Use access token
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
     https://api.easypay.com/api/v1/payments
```

## Payment Processing

### Creating Payments

#### Basic Payment

```json
{
  "amount": "25.99",
  "currency": "USD",
  "payment_method": "credit_card",
  "customer_id": "cust_123",
  "card_token": "tok_visa_4242",
  "description": "Product purchase"
}
```

#### Advanced Payment

```json
{
  "amount": "99.99",
  "currency": "USD",
  "payment_method": "credit_card",
  "customer_id": "cust_456",
  "customer_email": "customer@example.com",
  "customer_name": "John Doe",
  "card_token": "tok_mastercard_5555",
  "description": "Premium subscription",
  "metadata": {
    "order_id": "order_2024_001",
    "product": "premium_plan",
    "campaign": "summer_sale"
  },
  "is_test": true
}
```

### Payment Statuses

- **pending** - Payment created, awaiting processing
- **authorized** - Payment authorized but not captured
- **captured** - Payment successfully captured
- **failed** - Payment processing failed
- **refunded** - Payment refunded
- **cancelled** - Payment cancelled
- **disputed** - Payment disputed

### Refunding Payments

#### Full Refund

```bash
curl -X POST https://api.easypay.com/api/v1/payments/{payment_id}/refund \
     -H "Authorization: Bearer ak_your_key:sk_your_secret" \
     -H "Content-Type: application/json" \
     -d '{
       "reason": "Customer requested refund"
     }'
```

#### Partial Refund

```bash
curl -X POST https://api.easypay.com/api/v1/payments/{payment_id}/refund \
     -H "Authorization: Bearer ak_your_key:sk_your_secret" \
     -H "Content-Type: application/json" \
     -d '{
       "amount": "10.00",
       "reason": "Partial refund for damaged item"
     }'
```

### Cancelling Payments

```bash
curl -X POST https://api.easypay.com/api/v1/payments/{payment_id}/cancel \
     -H "Authorization: Bearer ak_your_key:sk_your_secret" \
     -H "Content-Type: application/json" \
     -d '{
       "reason": "Customer cancelled order"
     }'
```

## Webhook Management

### Setting Up Webhooks

1. Navigate to **Settings > Webhooks**
2. Click **Create Webhook**
3. Enter webhook URL
4. Select event types
5. Set retry preferences
6. Save configuration

### Webhook Events

- **payment.created** - Payment created
- **payment.captured** - Payment captured
- **payment.failed** - Payment failed
- **payment.refunded** - Payment refunded
- **payment.cancelled** - Payment cancelled
- **payment.disputed** - Payment disputed

### Webhook Payload

```json
{
  "id": "evt_123456789",
  "type": "payment.captured",
  "data": {
    "id": "pay_123456789",
    "amount": "25.99",
    "currency": "USD",
    "status": "captured",
    "customer_id": "cust_123"
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Webhook Security

#### Signature Verification

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

## Dashboard Usage

### Overview Dashboard

- **Total Payments** - Payment count and volume
- **Success Rate** - Payment success percentage
- **Revenue** - Total revenue and trends
- **Recent Activity** - Latest transactions

### Payment Management

#### Viewing Payments

1. Navigate to **Payments**
2. Use filters to find specific payments
3. Click payment ID for details
4. View payment history and status

#### Payment Filters

- **Date Range** - Filter by creation date
- **Status** - Filter by payment status
- **Customer** - Filter by customer ID
- **Amount** - Filter by amount range

### Analytics

#### Payment Analytics

- **Volume Trends** - Payment volume over time
- **Success Rates** - Success rate by period
- **Revenue Analysis** - Revenue trends and breakdown
- **Customer Insights** - Customer behavior analysis

#### Export Data

1. Select date range and filters
2. Click **Export**
3. Choose format (CSV, JSON)
4. Download file

## API Integration

### SDK Usage

#### Python SDK

```python
import asyncio
from easypay import EasyPayClient

async def main():
    client = EasyPayClient(
        api_key_id="ak_your_key",
        api_key_secret="sk_your_secret",
        base_url="https://api.easypay.com"
    )
    
    # Create payment
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

#### JavaScript SDK

```javascript
const EasyPay = require('easypay-sdk');

const client = new EasyPay({
  apiKeyId: 'ak_your_key',
  apiKeySecret: 'sk_your_secret',
  baseUrl: 'https://api.easypay.com'
});

// Create payment
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

### Error Handling

#### Common Errors

- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Invalid API credentials
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

#### Error Response Format

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

## Monitoring

### Health Checks

#### Basic Health Check

```bash
curl https://api.easypay.com/health
```

#### Detailed Health Check

```bash
curl https://api.easypay.com/health/detailed
```

### Metrics

#### Prometheus Metrics

```bash
curl https://api.easypay.com/metrics
```

#### Key Metrics

- **http_requests_total** - Total HTTP requests
- **http_request_duration_seconds** - Request duration
- **payments_total** - Total payments processed
- **payment_success_rate** - Payment success rate

### Alerts

#### Setting Up Alerts

1. Navigate to **Settings > Alerts**
2. Click **Create Alert**
3. Select metric and threshold
4. Set notification preferences
5. Save alert configuration

#### Alert Types

- **High Error Rate** - Error rate exceeds threshold
- **Slow Response Time** - Response time exceeds limit
- **Low Success Rate** - Success rate below threshold
- **Service Down** - Service unavailable

## Best Practices

### Security

1. **Secure API Keys** - Store keys securely
2. **Use HTTPS** - Always use HTTPS in production
3. **Validate Webhooks** - Always verify webhook signatures
4. **Rotate Keys** - Regularly rotate API keys
5. **Monitor Access** - Monitor API key usage

### Performance

1. **Implement Caching** - Cache frequently accessed data
2. **Use Pagination** - Use pagination for large datasets
3. **Handle Rate Limits** - Implement exponential backoff
4. **Optimize Queries** - Optimize database queries
5. **Monitor Performance** - Set up performance monitoring

### Reliability

1. **Implement Retries** - Retry failed requests
2. **Handle Errors** - Implement proper error handling
3. **Use Webhooks** - Use webhooks for real-time updates
4. **Test Thoroughly** - Test all integration scenarios
5. **Monitor Health** - Monitor service health

### Testing

1. **Use Sandbox** - Test with sandbox environment
2. **Test Edge Cases** - Test error scenarios
3. **Mock External Services** - Mock external dependencies
4. **Automate Tests** - Automate integration tests
5. **Monitor in Production** - Monitor production systems

## FAQ

### General Questions

**Q: How do I get started with EasyPay?**
A: Sign up for an account, verify your email, complete your profile, and generate API keys.

**Q: What payment methods are supported?**
A: We support credit cards (Visa, Mastercard, American Express, Discover).

**Q: What currencies are supported?**
A: We support USD, EUR, GBP, CAD, and AUD.

**Q: Is there a sandbox environment?**
A: Yes, use the sandbox environment for testing with test cards.

### Technical Questions

**Q: How do I handle webhook failures?**
A: Implement retry logic and verify webhook signatures. Check our webhook documentation for details.

**Q: What's the rate limit?**
A: Default rate limits are 100 requests/minute, 1000/hour, 10000/day. Custom limits can be set per API key.

**Q: How do I handle errors?**
A: Check HTTP status codes and error response format. Implement retry logic for transient errors.

**Q: Can I customize webhook events?**
A: Yes, you can select which events to receive and configure retry settings.

### Billing Questions

**Q: How is pricing calculated?**
A: Pricing is based on transaction volume and features used. Contact sales for detailed pricing.

**Q: When am I charged?**
A: Charges are processed monthly based on usage.

**Q: Can I get a refund?**
A: Refunds are handled on a case-by-case basis. Contact support for assistance.

## Support

### Getting Help

- **Documentation**: https://docs.easypay.com
- **Support Email**: support@easypay.com
- **Status Page**: https://status.easypay.com
- **Community Forum**: https://community.easypay.com

### Contact Information

- **Sales**: sales@easypay.com
- **Support**: support@easypay.com
- **Security**: security@easypay.com
- **Phone**: +1-800-EASYPAY

### Response Times

- **Critical Issues**: 1 hour
- **High Priority**: 4 hours
- **Medium Priority**: 24 hours
- **Low Priority**: 72 hours
