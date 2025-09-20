# Quick Start: Payment Creation and Verification

## 🚀 Quick Setup (5 minutes)

### Step 1: Start the Services

```bash
# Start the database and services
docker-compose up -d

# Start the EasyPay application
python src/main.py
```

### Step 2: Run the Setup Script

```bash
# Run the automated setup script
python setup_payment_testing.py
```

This script will:
- ✅ Create a test API key
- ✅ Generate a JWT token
- ✅ Create a test payment
- ✅ Generate ready-to-use test scripts
- ✅ Provide verification instructions

### Step 3: Verify Payment Creation

The setup script will create test scripts for you. You can then:

```bash
# Run the Python test script
python test_payment_python.py

# Or run the comprehensive test
python test_payment_creation.py
```

## 🔍 Manual Verification

### 1. Database Verification

**Option A: Using Admin Interface**
- Go to: `http://localhost:8000/api/v1/admin/database`
- Run query: `SELECT * FROM payments ORDER BY created_at DESC LIMIT 10;`

**Option B: Using API**
```bash
# Get payment by ID (replace with actual payment ID)
curl -X GET "http://localhost:8000/api/v1/payments/{payment_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. Authorize.net Dashboard Verification

1. Go to: https://sandbox.authorize.net/
2. Login with your sandbox credentials
3. Navigate to **Reports** → **Transaction Search**
4. Search for transactions created today
5. Look for the transaction ID from your payment response

### 3. API Verification

```bash
# Check payment status history
curl -X GET "http://localhost:8000/api/v1/payments/{payment_id}/status-history" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Search payments by customer
curl -X POST "http://localhost:8000/api/v1/payments/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "customer_id": "cust_test_001",
    "page": 1,
    "per_page": 10
  }'
```

## 📝 Example Payment Creation

### Using cURL

```bash
# 1. Generate JWT token
curl -X POST "http://localhost:8000/api/v1/auth/tokens" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key_id": "ak_your_api_key_id",
    "api_key_secret": "your_api_key_secret",
    "expires_in": 3600
  }'

# 2. Create payment (replace YOUR_JWT_TOKEN with actual token)
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
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
      "product": "test_product"
    },
    "is_test": true
  }'
```

### Using Python

```python
import asyncio
import httpx
import uuid
from datetime import datetime

async def create_payment():
    async with httpx.AsyncClient() as client:
        # Generate JWT token
        token_response = await client.post(
            "http://localhost:8000/api/v1/auth/tokens",
            json={
                "api_key_id": "ak_your_api_key_id",
                "api_key_secret": "your_api_key_secret",
                "expires_in": 3600
            }
        )
        
        access_token = token_response.json()["access_token"]
        
        # Create payment
        payment_response = await client.post(
            "http://localhost:8000/api/v1/payments",
            json={
                "amount": "25.99",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_test_{uuid.uuid4().hex[:8]}",
                "customer_email": "test@example.com",
                "customer_name": "Test Customer",
                "card_token": "tok_visa_4242",
                "description": "Test payment",
                "is_test": True
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Correlation-ID": f"test-{uuid.uuid4().hex[:8]}",
                "X-Idempotency-Key": f"payment-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
        )
        
        payment_data = payment_response.json()
        print(f"Payment created: {payment_data['id']}")
        print(f"Status: {payment_data['status']}")
        print(f"Authorize.net ID: {payment_data.get('authorize_net_transaction_id')}")

asyncio.run(create_payment())
```

## 🧪 Test Scenarios

### 1. Successful Payment (Visa Test Card)
- **Card Token**: `tok_visa_4242`
- **Expected Status**: `completed`
- **Description**: Standard successful payment

### 2. Declined Payment
- **Card Token**: `tok_visa_0002`
- **Expected Status**: `declined`
- **Description**: Card declined by processor

### 3. Insufficient Funds
- **Card Token**: `tok_visa_0003`
- **Expected Status**: `failed`
- **Description**: Insufficient funds

### 4. Invalid Card
- **Card Token**: `tok_visa_0004`
- **Expected Status**: `failed`
- **Description**: Invalid card number

## 🔧 Troubleshooting

### Common Issues

**1. Authentication Errors (401)**
- Verify JWT token is valid and not expired
- Check API key permissions
- Ensure Authorization header format: `Bearer <token>`

**2. Database Connection Issues (500)**
- Check PostgreSQL is running: `docker-compose ps`
- Verify database credentials
- Check logs: `docker-compose logs postgres`

**3. Authorize.net Integration Issues (502)**
- Verify Authorize.net sandbox credentials
- Check network connectivity
- Review application logs for detailed errors

**4. Payment Not Found in Authorize.net**
- Check if transaction was created in test mode
- Verify Authorize.net credentials are correct
- Check for network timeouts during API calls

### Health Checks

```bash
# Check system health
curl -X GET "http://localhost:8000/api/v1/health/detailed"

# Check database health
curl -X GET "http://localhost:8000/api/v1/admin/database/health"

# Check Authorize.net integration
curl -X GET "http://localhost:8000/api/v1/payments/metrics/circuit-breakers"
```

## 📊 Monitoring

### View Logs
```bash
# Application logs
docker-compose logs -f easypay

# Database logs
docker-compose logs -f postgres

# All services
docker-compose logs -f
```

### Check Metrics
```bash
# Payment metrics
curl -X GET "http://localhost:8000/api/v1/payments/metrics/circuit-breakers" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🎯 Expected Results

### Successful Payment Response
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
  "authorize_net_transaction_id": "1234567890",
  "correlation_id": "test-payment-001",
  "idempotency_key": "payment-test-001",
  "created_at": "2024-01-01T00:00:00Z",
  "processed_at": "2024-01-01T00:00:00Z"
}
```

### Database Record
- Payment record created in `payments` table
- Status history in `payment_status_history` table
- Audit log entry in `audit_logs` table

### Authorize.net Dashboard
- Transaction visible in sandbox dashboard
- Status shows as "Captured" or "Settled"
- Amount and customer details match

## 🚀 Next Steps

1. **Run the setup script**: `python setup_payment_testing.py`
2. **Test different scenarios**: Use the generated test scripts
3. **Verify in both systems**: Check database and Authorize.net dashboard
4. **Monitor logs**: Watch for any errors or issues
5. **Scale testing**: Create multiple payments to test system performance

The EasyPay Payment Gateway provides comprehensive payment processing with full traceability and verification capabilities. All payments are properly persisted in the database and processed through Authorize.net for reliable payment processing.
