# Authentication and API Endpoints Guide

## Overview

This guide covers authentication mechanisms and API endpoint documentation for the EasyPay payment gateway system.

## Table of Contents
1. [Authentication Methods](#authentication-methods)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Formats](#requestresponse-formats)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Security Best Practices](#security-best-practices)

## Authentication Methods

### API Key Authentication

**Header-based authentication using API keys.**

```http
Authorization: Bearer your-api-key-here
```

**Implementation:**
```python
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate API key and return user information."""
    api_key = credentials.credentials
    
    # Validate API key
    user = await validate_api_key(api_key)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

async def validate_api_key(api_key: str) -> Optional[dict]:
    """Validate API key against database."""
    # Implementation here
    pass
```

### JWT Token Authentication

**JSON Web Token authentication for user sessions.**

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Implementation:**
```python
import jwt
from datetime import datetime, timedelta

class JWTManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_token(self, user_id: str, expires_delta: timedelta = None) -> str:
        """Create JWT token for user."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
```

### HMAC Signature Authentication

**HMAC-based authentication for webhook verification.**

```python
import hmac
import hashlib
import hashlib

def verify_hmac_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature for webhook requests."""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

# Usage in webhook handler
@app.post("/webhooks")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature")
    
    if not verify_hmac_signature(body, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process webhook
    pass
```

## API Endpoints

### Base URL
```
https://api.easypay.com/v1
```

### Authentication Endpoints

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

#### Refresh Token
```http
POST /auth/refresh
Authorization: Bearer your-refresh-token
```

#### Logout
```http
POST /auth/logout
Authorization: Bearer your-access-token
```

### Payment Endpoints

#### Create Payment
```http
POST /payments
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "amount": {
    "value": "100.00",
    "currency": "USD"
  },
  "payment_method": {
    "type": "card",
    "card": {
      "number": "4111111111111111",
      "expiry_date": "12/25",
      "cvv": "123"
    }
  },
  "billing_address": {
    "first_name": "John",
    "last_name": "Doe",
    "address": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "zip": "12345",
    "country": "US"
  }
}
```

**Response:**
```json
{
  "id": "pay_123456789",
  "status": "completed",
  "amount": {
    "value": "100.00",
    "currency": "USD"
  },
  "payment_method": {
    "type": "card",
    "last_four": "1111"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "authorize_net_transaction_id": "40000000001"
}
```

#### Get Payment
```http
GET /payments/{payment_id}
Authorization: Bearer your-api-key
```

#### Refund Payment
```http
POST /payments/{payment_id}/refund
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "amount": "50.00"
}
```

#### Cancel Payment
```http
POST /payments/{payment_id}/cancel
Authorization: Bearer your-api-key
```

### Customer Endpoints

#### Create Customer
```http
POST /customers
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "email": "customer@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}
```

#### Get Customer
```http
GET /customers/{customer_id}
Authorization: Bearer your-api-key
```

#### Update Customer
```http
PUT /customers/{customer_id}
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith"
}
```

#### Delete Customer
```http
DELETE /customers/{customer_id}
Authorization: Bearer your-api-key
```

### Payment Method Endpoints

#### Add Payment Method
```http
POST /customers/{customer_id}/payment-methods
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "type": "card",
  "card": {
    "number": "4111111111111111",
    "expiry_date": "12/25",
    "cvv": "123"
  }
}
```

#### List Payment Methods
```http
GET /customers/{customer_id}/payment-methods
Authorization: Bearer your-api-key
```

#### Update Payment Method
```http
PUT /customers/{customer_id}/payment-methods/{method_id}
Authorization: Bearer your-api-key
Content-Type: application/json

{
  "card": {
    "expiry_date": "12/26"
  }
}
```

#### Delete Payment Method
```http
DELETE /customers/{customer_id}/payment-methods/{method_id}
Authorization: Bearer your-api-key
```

## Request/Response Formats

### Standard Request Headers

```http
Authorization: Bearer your-api-key
Content-Type: application/json
Accept: application/json
X-Request-ID: req_123456789
X-Idempotency-Key: idem_123456789
User-Agent: EasyPay-Client/1.0.0
```

### Standard Response Headers

```http
Content-Type: application/json
X-Request-ID: req_123456789
X-Rate-Limit-Limit: 1000
X-Rate-Limit-Remaining: 999
X-Rate-Limit-Reset: 1640995200
```

### Pagination

**Request:**
```http
GET /payments?page=1&size=20&sort=created_at&order=desc
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 100,
    "pages": 5
  }
}
```

### Filtering and Sorting

**Request:**
```http
GET /payments?status=completed&amount_min=10.00&amount_max=100.00&created_after=2024-01-01
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `size`: Items per page (default: 20, max: 100)
- `sort`: Sort field (default: created_at)
- `order`: Sort order (asc/desc, default: desc)
- `status`: Filter by status
- `amount_min`: Minimum amount filter
- `amount_max`: Maximum amount filter
- `created_after`: Filter by creation date
- `created_before`: Filter by creation date

## Error Handling

### Error Response Format

```json
{
  "error": {
    "type": "validation_error",
    "code": "INVALID_AMOUNT",
    "message": "Amount must be greater than 0",
    "field": "amount",
    "details": {
      "min_value": 0.01,
      "provided_value": 0
    }
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | Successful request |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Invalid or missing authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 502 | Bad Gateway | External service error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Common Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| INVALID_API_KEY | Invalid API key | Check API key |
| INVALID_TOKEN | Invalid JWT token | Refresh token |
| INSUFFICIENT_PERMISSIONS | Insufficient permissions | Check user role |
| VALIDATION_ERROR | Request validation failed | Fix request data |
| PAYMENT_FAILED | Payment processing failed | Check payment data |
| RATE_LIMIT_EXCEEDED | Rate limit exceeded | Wait and retry |
| SERVICE_UNAVAILABLE | Service temporarily unavailable | Retry later |

## Rate Limiting

### Rate Limit Headers

```http
X-Rate-Limit-Limit: 1000
X-Rate-Limit-Remaining: 999
X-Rate-Limit-Reset: 1640995200
X-Rate-Limit-Window: 3600
```

### Rate Limit Tiers

| Tier | Requests per Hour | Burst Limit |
|------|------------------|-------------|
| Free | 100 | 10 |
| Basic | 1,000 | 100 |
| Pro | 10,000 | 1,000 |
| Enterprise | 100,000 | 10,000 |

### Rate Limit Implementation

```python
from fastapi import Request, HTTPException
import time
import redis

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_rate_limit(self, request: Request, user_id: str) -> bool:
        """Check if user has exceeded rate limit."""
        key = f"rate_limit:{user_id}"
        current_time = int(time.time())
        window = 3600  # 1 hour
        
        # Get current count
        current_count = await self.redis.get(key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)
        
        # Check if limit exceeded
        if current_count >= 1000:  # Example limit
            return False
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
        
        return True
```

## Security Best Practices

### 1. API Key Management
- Store API keys securely
- Rotate keys regularly
- Use different keys for different environments
- Implement key expiration

### 2. Token Security
- Use short-lived access tokens
- Implement refresh token rotation
- Store tokens securely
- Implement token revocation

### 3. Request Security
- Validate all input data
- Use HTTPS for all communications
- Implement request signing
- Sanitize sensitive data in logs

### 4. Response Security
- Don't expose sensitive data
- Use appropriate HTTP status codes
- Implement proper error handling
- Add security headers

### 5. Rate Limiting
- Implement per-user rate limiting
- Use different limits for different endpoints
- Implement burst protection
- Monitor rate limit usage

## Implementation Examples

### FastAPI Authentication Middleware

```python
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
import jwt

app = FastAPI()
security = HTTPBearer()

async def get_current_user(request: Request, credentials = Depends(security)):
    """Get current authenticated user."""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {"user_id": user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"message": "This is a protected route", "user": current_user}
```

### API Key Validation

```python
async def validate_api_key(api_key: str) -> Optional[dict]:
    """Validate API key and return user info."""
    # Check if API key exists and is active
    user = await database.get_user_by_api_key(api_key)
    
    if not user or not user.is_active:
        return None
    
    # Update last used timestamp
    await database.update_api_key_usage(api_key)
    
    return {
        "user_id": user.id,
        "merchant_id": user.merchant_id,
        "permissions": user.permissions
    }
```

## Testing Authentication

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_valid_api_key():
    """Test with valid API key."""
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer valid-api-key"}
    )
    assert response.status_code == 200

def test_invalid_api_key():
    """Test with invalid API key."""
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid-api-key"}
    )
    assert response.status_code == 401

def test_missing_api_key():
    """Test without API key."""
    response = client.get("/protected")
    assert response.status_code == 401
```

## Next Steps

1. Review [Payment Transactions Guide](02-payment-transactions.md)
2. Learn about [Customer Profiles](06-customer-profiles.md)
3. Implement [Fraud Management](07-fraud-management.md)
4. Set up [Monitoring and Observability](12-monitoring-guide.md)

## Resources

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OAuth 2.0](https://tools.ietf.org/html/rfc6749)
- [API Security Best Practices](https://owasp.org/www-project-api-security/)
