# Payment Creation and Verification Guide

This guide will help you create payments using the EasyPay Payment Gateway and verify they're properly persisted in both the database and Authorize.net dashboard.

## 🚀 Prerequisites

### 1. Environment Setup

First, ensure your environment variables are configured:

```bash
# Database Configuration
DATABASE_URL=postgresql://easypay:password@localhost:5432/easypay

# Authorize.net Sandbox Credentials
AUTHORIZE_NET_API_LOGIN_ID=your_sandbox_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_sandbox_transaction_key
AUTHORIZE_NET_ENVIRONMENT=sandbox

# JWT Configuration
JWT_SECRET_KEY=your-secure-jwt-secret-key
```

### 2. Start the Services

```bash
# Start the database and services
docker-compose up -d

# Start the EasyPay application
python src/main.py
```

### 3. Create API Key and JWT Token

First, you need to create an API key and generate a JWT token for authentication.

## 📝 Step-by-Step Payment Creation

### Step 1: Create API Key

```bash
curl -X POST "http://localhost:8000/api/v1/auth/api-keys" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin-token" \
  -d '{
    "name": "Payment Test API Key",
    "description": "API key for testing payment creation",
    "permissions": ["payments:read", "payments:write"],
    "rate_limit_per_minute": 100,
    "rate_limit_per_hour": 1000,
    "rate_limit_per_day": 10000
  }'
```

**Response:**
```json
{
  "id": "uuid-here",
  "key_id": "ak_123456789",
  "key_secret": "secret-here",
  "name": "Payment Test API Key",
  "description": "API key for testing payment creation",
  "permissions": ["payments:read", "payments:write"],
  "expires_at": null,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Step 2: Generate JWT Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/tokens" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key_id": "ak_123456789",
    "api_key_secret": "secret-here",
    "expires_in": 3600
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "expires_at": "2024-01-01T01:00:00Z"
}
```

### Step 3: Create a Payment

Now you can create a payment using the JWT token:

```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "X-Correlation-ID: test-payment-001" \
  -H "X-Idempotency-Key: payment-test-001" \
  -d '{
    "amount": "25.99",
    "currency": "USD",
    "payment_method": "credit_card",
    "customer_id": "cust_test_001",
    "customer_email": "test@example.com",
    "customer_name": "Test Customer",
    "card_token": "tok_visa_4242",
    "description": "Test payment for verification",
    "metadata": {
      "order_id": "order_2024_001",
      "product": "test_product",
      "test_mode": true
    },
    "is_test": true
  }'
```

**Expected Response:**
```json
{
  "id": "pay_123456789",
  "status": "completed",
  "amount": {
    "value": "25.99",
    "currency": "USD"
  },
  "payment_method": {
    "type": "credit_card",
    "last_four": "4242"
  },
  "customer": {
    "id": "cust_test_001",
    "email": "test@example.com",
    "name": "Test Customer"
  },
  "description": "Test payment for verification",
  "metadata": {
    "order_id": "order_2024_001",
    "product": "test_product",
    "test_mode": true
  },
  "authorize_net_transaction_id": "1234567890",
  "correlation_id": "test-payment-001",
  "idempotency_key": "payment-test-001",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "processed_at": "2024-01-01T00:00:00Z"
}
```

## 🔍 Verification Steps

### Step 1: Verify Payment in Database

#### Option A: Using Database Admin Interface

1. Navigate to: `http://localhost:8000/api/v1/admin/database`
2. Use the query interface to check payments:

```sql
-- Check all payments
SELECT * FROM payments ORDER BY created_at DESC LIMIT 10;

-- Check specific payment by ID
SELECT * FROM payments WHERE id = 'pay_123456789';

-- Check payments by customer
SELECT * FROM payments WHERE customer_id = 'cust_test_001';

-- Check payments by status
SELECT * FROM payments WHERE status = 'completed';
```

#### Option B: Using API Endpoints

```bash
# Get payment by ID
curl -X GET "http://localhost:8000/api/v1/payments/pay_123456789" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# List all payments
curl -X GET "http://localhost:8000/api/v1/payments" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Search payments by customer
curl -X POST "http://localhost:8000/api/v1/payments/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "customer_id": "cust_test_001",
    "page": 1,
    "per_page": 10
  }'
```

### Step 2: Verify Payment in Authorize.net Dashboard

#### Access Authorize.net Sandbox Dashboard

1. Go to: https://sandbox.authorize.net/
2. Log in with your sandbox credentials
3. Navigate to **Reports** → **Transaction Search**

#### Search for Your Transaction

1. **Transaction ID**: Use the `authorize_net_transaction_id` from the payment response
2. **Date Range**: Set to today's date
3. **Transaction Type**: Select "All Transactions"

#### Verify Transaction Details

Look for these fields in the Authorize.net dashboard:
- **Transaction ID**: Should match `authorize_net_transaction_id`
- **Amount**: Should match your payment amount ($25.99)
- **Status**: Should show "Captured" or "Settled"
- **Card Number**: Should show last 4 digits (4242)
- **Customer Email**: Should match your test email

### Step 3: Verify Payment Status History

```bash
# Get payment status history
curl -X GET "http://localhost:8000/api/v1/payments/pay_123456789/status-history" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Expected Response:**
```json
[
  {
    "status": "pending",
    "timestamp": "2024-01-01T00:00:00Z",
    "description": "Payment created"
  },
  {
    "status": "authorized",
    "timestamp": "2024-01-01T00:00:01Z",
    "description": "Payment authorized by Authorize.net"
  },
  {
    "status": "captured",
    "timestamp": "2024-01-01T00:00:02Z",
    "description": "Payment captured successfully"
  },
  {
    "status": "completed",
    "timestamp": "2024-01-01T00:00:03Z",
    "description": "Payment processing completed"
  }
]
```

## 🧪 Test Payment Scenarios

### 1. Successful Payment (Visa Test Card)

```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "amount": "10.00",
    "currency": "USD",
    "payment_method": "credit_card",
    "customer_id": "cust_visa_test",
    "customer_email": "visa@test.com",
    "customer_name": "Visa Test Customer",
    "card_token": "tok_visa_4242",
    "description": "Visa test payment",
    "is_test": true
  }'
```

### 2. Declined Payment (Declined Test Card)

```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "amount": "10.00",
    "currency": "USD",
    "payment_method": "credit_card",
    "customer_id": "cust_declined_test",
    "customer_email": "declined@test.com",
    "customer_name": "Declined Test Customer",
    "card_token": "tok_visa_0002",
    "description": "Declined test payment",
    "is_test": true
  }'
```

### 3. Insufficient Funds Payment

```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "amount": "10.00",
    "currency": "USD",
    "payment_method": "credit_card",
    "customer_id": "cust_insufficient_test",
    "customer_email": "insufficient@test.com",
    "customer_name": "Insufficient Funds Test",
    "card_token": "tok_visa_0003",
    "description": "Insufficient funds test",
    "is_test": true
  }'
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Errors

**Error**: `401 Unauthorized`
**Solution**: 
- Verify your JWT token is valid and not expired
- Check that the API key has the correct permissions
- Ensure the Authorization header format is correct: `Bearer <token>`

#### 2. Database Connection Issues

**Error**: `500 Internal Server Error` with database connection errors
**Solution**:
- Check that PostgreSQL is running: `docker-compose ps`
- Verify database credentials in environment variables
- Check database connection: `docker-compose logs postgres`

#### 3. Authorize.net Integration Issues

**Error**: `502 Bad Gateway` or Authorize.net errors
**Solution**:
- Verify Authorize.net sandbox credentials
- Check network connectivity to Authorize.net
- Review Authorize.net client logs for detailed error messages

#### 4. Payment Not Found in Authorize.net

**Possible Causes**:
- Transaction was created in test mode but not sent to Authorize.net
- Authorize.net credentials are incorrect
- Network timeout during Authorize.net API call

**Solution**:
- Check the payment status in the database
- Review application logs for Authorize.net API calls
- Verify Authorize.net transaction ID is present in the payment record

## 📊 Monitoring and Logs

### Check Application Logs

```bash
# View application logs
docker-compose logs -f easypay

# View database logs
docker-compose logs -f postgres

# View all services
docker-compose logs -f
```

### Monitor Payment Metrics

```bash
# Get payment metrics
curl -X GET "http://localhost:8000/api/v1/payments/metrics/circuit-breakers" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Health Check

```bash
# Check system health
curl -X GET "http://localhost:8000/api/v1/health/detailed"
```

## 🎯 Best Practices

### 1. Use Idempotency Keys

Always include idempotency keys to prevent duplicate payments:

```bash
-H "X-Idempotency-Key: unique-payment-key-$(date +%s)"
```

### 2. Include Correlation IDs

Use correlation IDs for request tracking:

```bash
-H "X-Correlation-ID: payment-$(uuidgen)"
```

### 3. Test Different Scenarios

Test various payment scenarios:
- Successful payments
- Declined payments
- Insufficient funds
- Invalid card numbers
- Network timeouts

### 4. Verify Both Systems

Always verify payments in both:
- EasyPay database (for internal tracking)
- Authorize.net dashboard (for payment processor confirmation)

### 5. Monitor Error Rates

Keep an eye on error rates and failed transactions to ensure system reliability.

## 📝 Example Scripts

### Complete Payment Creation Script

```bash
#!/bin/bash

# Set variables
API_BASE_URL="http://localhost:8000/api/v1"
API_KEY_ID="ak_123456789"
API_KEY_SECRET="your-secret-here"

# Generate JWT token
JWT_RESPONSE=$(curl -s -X POST "$API_BASE_URL/auth/tokens" \
  -H "Content-Type: application/json" \
  -d "{
    \"api_key_id\": \"$API_KEY_ID\",
    \"api_key_secret\": \"$API_KEY_SECRET\",
    \"expires_in\": 3600
  }")

JWT_TOKEN=$(echo $JWT_RESPONSE | jq -r '.access_token')

# Create payment
PAYMENT_RESPONSE=$(curl -s -X POST "$API_BASE_URL/payments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-Correlation-ID: test-payment-$(date +%s)" \
  -H "X-Idempotency-Key: payment-test-$(date +%s)" \
  -d '{
    "amount": "25.99",
    "currency": "USD",
    "payment_method": "credit_card",
    "customer_id": "cust_test_001",
    "customer_email": "test@example.com",
    "customer_name": "Test Customer",
    "card_token": "tok_visa_4242",
    "description": "Test payment for verification",
    "is_test": true
  }')

# Extract payment ID
PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.id')
AUTHORIZE_NET_ID=$(echo $PAYMENT_RESPONSE | jq -r '.authorize_net_transaction_id')

echo "Payment created successfully!"
echo "Payment ID: $PAYMENT_ID"
echo "Authorize.net Transaction ID: $AUTHORIZE_NET_ID"

# Verify payment
echo "Verifying payment..."
curl -s -X GET "$API_BASE_URL/payments/$PAYMENT_ID" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.'
```

This comprehensive guide should help you create payments and verify they're properly persisted in both the database and Authorize.net dashboard. The system is designed to provide full traceability and verification capabilities for all payment transactions.
