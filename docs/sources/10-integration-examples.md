# Integration Examples and Code Samples

## Overview

This guide provides practical integration examples for the EasyPay payment gateway system, including complete code samples for common use cases.

## Table of Contents
1. [Python Integration](#python-integration)
2. [JavaScript/Node.js Integration](#javascriptnodejs-integration)
3. [FastAPI Service Implementation](#fastapi-service-implementation)
4. [Database Integration](#database-integration)
5. [Webhook Handling](#webhook-handling)
6. [Testing Examples](#testing-examples)

## Python Integration

### Basic Payment Service

```python
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PaymentRequest:
    amount: float
    currency: str
    card_number: str
    expiry_date: str
    cvv: str
    billing_address: Dict[str, str]
    customer_id: Optional[str] = None

class EasyPayClient:
    def __init__(self, api_key: str, base_url: str = "https://api.easypay.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_payment(self, request: PaymentRequest) -> Dict[str, Any]:
        """Create a new payment."""
        data = {
            "amount": {
                "value": str(request.amount),
                "currency": request.currency
            },
            "payment_method": {
                "type": "card",
                "card": {
                    "number": request.card_number,
                    "expiry_date": request.expiry_date,
                    "cvv": request.cvv
                }
            },
            "billing_address": request.billing_address,
            "customer_id": request.customer_id
        }
        
        async with self.session.post(f"{self.base_url}/payments", json=data) as response:
            return await response.json()
    
    async def get_payment(self, payment_id: str) -> Dict[str, Any]:
        """Get payment details."""
        async with self.session.get(f"{self.base_url}/payments/{payment_id}") as response:
            return await response.json()
    
    async def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Refund a payment."""
        data = {}
        if amount:
            data["amount"] = str(amount)
        
        async with self.session.post(f"{self.base_url}/payments/{payment_id}/refund", json=data) as response:
            return await response.json()

# Usage example
async def main():
    async with EasyPayClient("your-api-key") as client:
        payment_request = PaymentRequest(
            amount=100.00,
            currency="USD",
            card_number="4111111111111111",
            expiry_date="12/25",
            cvv="123",
            billing_address={
                "first_name": "John",
                "last_name": "Doe",
                "address": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip": "12345",
                "country": "US"
            }
        )
        
        payment = await client.create_payment(payment_request)
        print(f"Payment created: {payment['id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Customer Profile Management

```python
class CustomerManager:
    def __init__(self, client: EasyPayClient):
        self.client = client
    
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer profile."""
        async with self.client.session.post(
            f"{self.client.base_url}/customers", 
            json=customer_data
        ) as response:
            return await response.json()
    
    async def add_payment_method(self, customer_id: str, payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Add payment method to customer profile."""
        async with self.client.session.post(
            f"{self.client.base_url}/customers/{customer_id}/payment-methods",
            json=payment_method
        ) as response:
            return await response.json()
    
    async def get_customer_payment_methods(self, customer_id: str) -> Dict[str, Any]:
        """Get customer's payment methods."""
        async with self.client.session.get(
            f"{self.client.base_url}/customers/{customer_id}/payment-methods"
        ) as response:
            return await response.json()

# Usage
async def manage_customer():
    async with EasyPayClient("your-api-key") as client:
        customer_manager = CustomerManager(client)
        
        # Create customer
        customer = await customer_manager.create_customer({
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
        
        # Add payment method
        payment_method = await customer_manager.add_payment_method(
            customer["id"],
            {
                "type": "card",
                "card": {
                    "number": "4111111111111111",
                    "expiry_date": "12/25",
                    "cvv": "123"
                }
            }
        )
```

## JavaScript/Node.js Integration

### Node.js Client

```javascript
const axios = require('axios');

class EasyPayClient {
    constructor(apiKey, baseUrl = 'https://api.easypay.com/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.client = axios.create({
            baseURL: baseUrl,
            headers: {
                'Authorization': `Bearer ${apiKey}`,
                'Content-Type': 'application/json'
            }
        });
    }
    
    async createPayment(paymentData) {
        try {
            const response = await this.client.post('/payments', paymentData);
            return response.data;
        } catch (error) {
            throw new Error(`Payment creation failed: ${error.response?.data?.message || error.message}`);
        }
    }
    
    async getPayment(paymentId) {
        try {
            const response = await this.client.get(`/payments/${paymentId}`);
            return response.data;
        } catch (error) {
            throw new Error(`Failed to get payment: ${error.response?.data?.message || error.message}`);
        }
    }
    
    async refundPayment(paymentId, amount = null) {
        try {
            const data = amount ? { amount: amount.toString() } : {};
            const response = await this.client.post(`/payments/${paymentId}/refund`, data);
            return response.data;
        } catch (error) {
            throw new Error(`Refund failed: ${error.response?.data?.message || error.message}`);
        }
    }
}

// Usage example
async function processPayment() {
    const client = new EasyPayClient('your-api-key');
    
    try {
        const payment = await client.createPayment({
            amount: {
                value: '100.00',
                currency: 'USD'
            },
            payment_method: {
                type: 'card',
                card: {
                    number: '4111111111111111',
                    expiry_date: '12/25',
                    cvv: '123'
                }
            },
            billing_address: {
                first_name: 'John',
                last_name: 'Doe',
                address: '123 Main St',
                city: 'Anytown',
                state: 'CA',
                zip: '12345',
                country: 'US'
            }
        });
        
        console.log('Payment created:', payment.id);
    } catch (error) {
        console.error('Payment failed:', error.message);
    }
}

module.exports = { EasyPayClient };
```

### Express.js Integration

```javascript
const express = require('express');
const { EasyPayClient } = require('./easypay-client');

const app = express();
app.use(express.json());

const easypay = new EasyPayClient(process.env.EASYPAY_API_KEY);

// Payment endpoint
app.post('/api/payments', async (req, res) => {
    try {
        const payment = await easypay.createPayment(req.body);
        res.json(payment);
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

// Payment status endpoint
app.get('/api/payments/:id', async (req, res) => {
    try {
        const payment = await easypay.getPayment(req.params.id);
        res.json(payment);
    } catch (error) {
        res.status(404).json({ error: error.message });
    }
});

// Refund endpoint
app.post('/api/payments/:id/refund', async (req, res) => {
    try {
        const refund = await easypay.refundPayment(req.params.id, req.body.amount);
        res.json(refund);
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

## FastAPI Service Implementation

### Payment Service

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import asyncio

app = FastAPI(title="EasyPay API", version="1.0.0")

class PaymentRequest(BaseModel):
    amount: float
    currency: str
    payment_method: dict
    billing_address: dict
    customer_id: Optional[str] = None

class PaymentResponse(BaseModel):
    id: str
    status: str
    amount: dict
    created_at: str

@app.post("/payments", response_model=PaymentResponse)
async def create_payment(payment: PaymentRequest):
    """Create a new payment."""
    try:
        # Process payment logic here
        payment_id = f"pay_{int(time.time())}"
        
        return PaymentResponse(
            id=payment_id,
            status="completed",
            amount={
                "value": str(payment.amount),
                "currency": payment.currency
            },
            created_at=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    """Get payment details."""
    # Implementation here
    pass

@app.post("/payments/{payment_id}/refund")
async def refund_payment(payment_id: str, amount: Optional[float] = None):
    """Refund a payment."""
    # Implementation here
    pass
```

### Webhook Handler

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json

@app.post("/webhooks/payments")
async def handle_payment_webhook(request: Request):
    """Handle payment webhooks."""
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature")
    
    # Verify webhook signature
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    webhook_data = json.loads(body)
    
    # Process webhook event
    await process_webhook_event(webhook_data)
    
    return {"status": "success"}

def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify webhook signature."""
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

async def process_webhook_event(event: dict):
    """Process webhook event."""
    event_type = event.get("type")
    
    if event_type == "payment.completed":
        await handle_payment_completed(event["data"])
    elif event_type == "payment.failed":
        await handle_payment_failed(event["data"])
    # Add more event handlers
```

## Database Integration

### SQLAlchemy Models

```python
from sqlalchemy import Column, String, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(20), nullable=False)
    payment_method = Column(JSON)
    billing_address = Column(JSON)
    authorize_net_transaction_id = Column(String(50))
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), nullable=False)
    email = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

### Database Operations

```python
from sqlalchemy.orm import Session
from sqlalchemy import select

class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_payment(self, payment_data: dict) -> Payment:
        """Create a new payment record."""
        payment = Payment(**payment_data)
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment
    
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()
    
    async def update_payment_status(self, payment_id: str, status: str) -> bool:
        """Update payment status."""
        payment = await self.get_payment(payment_id)
        if payment:
            payment.status = status
            payment.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False
```

## Testing Examples

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, patch
from easypay_client import EasyPayClient

@pytest.fixture
def client():
    return EasyPayClient("test-api-key")

@pytest.mark.asyncio
async def test_create_payment(client):
    """Test payment creation."""
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "pay_123",
            "status": "completed"
        }
        mock_post.return_value.__aenter__.return_value = mock_response
        
        payment_request = PaymentRequest(
            amount=100.00,
            currency="USD",
            card_number="4111111111111111",
            expiry_date="12/25",
            cvv="123",
            billing_address={}
        )
        
        result = await client.create_payment(payment_request)
        
        assert result["id"] == "pay_123"
        assert result["status"] == "completed"

@pytest.mark.asyncio
async def test_payment_creation_failure(client):
    """Test payment creation failure."""
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "error": "Invalid card number"
        }
        mock_post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(Exception):
            await client.create_payment(PaymentRequest(...))
```

### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_payment_endpoint():
    """Test payment creation endpoint."""
    payment_data = {
        "amount": 100.00,
        "currency": "USD",
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
            "last_name": "Doe"
        }
    }
    
    response = client.post("/payments", json=payment_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "completed"

def test_get_payment_endpoint():
    """Test get payment endpoint."""
    # First create a payment
    payment_data = {...}
    create_response = client.post("/payments", json=payment_data)
    payment_id = create_response.json()["id"]
    
    # Then get the payment
    response = client.get(f"/payments/{payment_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == payment_id
```

## Error Handling Examples

### Comprehensive Error Handling

```python
class PaymentError(Exception):
    def __init__(self, message: str, error_code: str, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class PaymentService:
    async def create_payment(self, payment_data: dict) -> dict:
        try:
            # Validate input
            self._validate_payment_data(payment_data)
            
            # Process payment
            result = await self._process_payment(payment_data)
            
            return result
            
        except ValidationError as e:
            raise PaymentError(
                "Invalid payment data",
                "VALIDATION_ERROR",
                {"field": str(e)}
            )
        except AuthorizeNetError as e:
            raise PaymentError(
                "Payment processing failed",
                "AUTHORIZE_NET_ERROR",
                {"original_error": str(e)}
            )
        except Exception as e:
            raise PaymentError(
                "Unexpected error occurred",
                "INTERNAL_ERROR",
                {"error": str(e)}
            )
    
    def _validate_payment_data(self, data: dict):
        """Validate payment data."""
        required_fields = ["amount", "currency", "payment_method"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
```

## Best Practices

### 1. Error Handling
- Use specific exception types
- Provide meaningful error messages
- Include error codes for programmatic handling
- Log errors with context

### 2. Security
- Validate all input data
- Use HTTPS for all communications
- Implement proper authentication
- Sanitize sensitive data in logs

### 3. Performance
- Use connection pooling
- Implement caching where appropriate
- Use async/await for I/O operations
- Monitor performance metrics

### 4. Testing
- Write comprehensive unit tests
- Include integration tests
- Test error scenarios
- Use mocking for external dependencies

## Next Steps

1. Review [Security Best Practices](11-security-guide.md)
2. Set up [Monitoring and Observability](12-monitoring-guide.md)
3. Review [Deployment Guide](13-deployment-guide.md)
4. Implement [Production Checklist](14-production-checklist.md)

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Authorize.net API Reference](https://developer.authorize.net/api/reference/)
