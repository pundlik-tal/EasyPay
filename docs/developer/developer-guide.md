# EasyPay Payment Gateway - Developer Guide

This guide helps developers understand, contribute to, and extend the EasyPay Payment Gateway system.

## Table of Contents

- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [API Development](#api-development)
- [Database Development](#database-development)
- [Integration Development](#integration-development)
- [Contributing](#contributing)

## Getting Started

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Git

### Quick Start

```bash
# Clone repository
git clone https://github.com/easypay/payment-gateway.git
cd payment-gateway

# Setup environment
cp .env.example .env.development

# Start services
docker-compose up -d

# Run migrations
docker-compose exec easypay-api alembic upgrade head

# Run tests
docker-compose exec easypay-api pytest
```

## Project Structure

```
src/
├── api/                    # API layer
│   ├── v1/endpoints/       # API endpoints
│   ├── v1/middleware/      # Middleware
│   └── v1/schemas/         # Request/response schemas
├── core/                   # Business logic
│   ├── services/           # Business services
│   ├── models/             # Data models
│   └── repositories/       # Data access
├── infrastructure/         # Infrastructure
│   ├── database/           # Database config
│   ├── cache/              # Cache config
│   └── monitoring/         # Monitoring setup
├── integrations/           # External integrations
│   └── authorize_net/      # Authorize.net client
└── utils/                  # Utilities
```

## Development Setup

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Setup pre-commit hooks
pre-commit install

# Run development server
python src/main.py
```

### Docker Development

```bash
# Build development image
docker build -t easypay-api:dev .

# Run with hot reload
docker-compose -f docker-compose.dev.yml up
```

## Code Standards

### Python Style Guide

- Follow PEP 8
- Use Black for formatting
- Use isort for import sorting
- Use flake8 for linting
- Use mypy for type checking

### Code Organization

```python
# File structure example
"""
Module docstring describing purpose.
"""
# Standard library imports
import os
import sys

# Third-party imports
import fastapi
import pydantic

# Local imports
from src.core.models import Payment
from src.core.services import PaymentService
```

### Type Hints

```python
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class PaymentCreate(BaseModel):
    amount: str
    currency: str
    customer_id: str

async def create_payment(
    payment_data: PaymentCreate,
    user_id: str
) -> Payment:
    """Create a new payment."""
    pass
```

## Testing

### Test Structure

```
tests/
├── unit/                   # Unit tests
├── integration/            # Integration tests
├── e2e/                   # End-to-end tests
└── fixtures/              # Test data
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with markers
pytest -m "not slow"
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock
from src.core.services.payment_service import PaymentService

@pytest.fixture
async def payment_service():
    """Payment service fixture."""
    return PaymentService()

@pytest.mark.asyncio
async def test_create_payment(payment_service):
    """Test payment creation."""
    payment_data = {
        "amount": "10.00",
        "currency": "USD",
        "customer_id": "cust_123"
    }
    
    result = await payment_service.create_payment(payment_data)
    
    assert result.amount == "10.00"
    assert result.currency == "USD"
    assert result.status == "pending"
```

## API Development

### Creating Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from src.api.v1.schemas.payment import PaymentCreate, PaymentResponse
from src.core.services.payment_service import PaymentService

router = APIRouter()

@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Create a new payment."""
    try:
        payment = await payment_service.create_payment(payment_data.dict())
        return PaymentResponse.from_orm(payment)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Request/Response Schemas

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime

class PaymentCreate(BaseModel):
    amount: str = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    customer_id: str = Field(..., description="Customer ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('amount')
    def validate_amount(cls, v):
        try:
            amount = float(v)
            if amount <= 0:
                raise ValueError('Amount must be greater than 0')
            return v
        except ValueError:
            raise ValueError('Invalid amount format')

class PaymentResponse(BaseModel):
    id: str
    amount: str
    currency: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### Error Handling

```python
from src.core.exceptions import EasyPayException

class PaymentError(EasyPayException):
    """Payment processing error."""
    
    def __init__(self, message: str, error_code: str = "payment_error"):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            error_type="payment_error"
        )

# Usage
if payment_amount <= 0:
    raise PaymentError("Amount must be greater than 0", "invalid_amount")
```

## Database Development

### Models

```python
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(255), unique=True, nullable=False)
    amount = Column(String(20), nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add payment table"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Repositories

```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.models.payment import Payment

class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, payment_data: dict) -> Payment:
        """Create a new payment."""
        payment = Payment(**payment_data)
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment
    
    async def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        return await self.db.get(Payment, payment_id)
    
    async def get_by_external_id(self, external_id: str) -> Optional[Payment]:
        """Get payment by external ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.external_id == external_id)
        )
        return result.scalar_one_or_none()
```

## Integration Development

### External API Clients

```python
import httpx
from typing import Dict, Any
from src.core.exceptions import ExternalServiceError

class AuthorizeNetClient:
    def __init__(self, api_login_id: str, transaction_key: str, sandbox: bool = True):
        self.api_login_id = api_login_id
        self.transaction_key = transaction_key
        self.base_url = "https://apitest.authorize.net" if sandbox else "https://api.authorize.net"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def charge_credit_card(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Charge a credit card."""
        try:
            response = await self.client.post(
                f"{self.base_url}/xml/v1/request.api",
                json=self._build_request(payment_data)
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise ExternalServiceError(f"Authorize.net request failed: {e}")
    
    def _build_request(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build Authorize.net request."""
        return {
            "createTransactionRequest": {
                "merchantAuthentication": {
                    "name": self.api_login_id,
                    "transactionKey": self.transaction_key
                },
                "transactionRequest": {
                    "transactionType": "authCaptureTransaction",
                    "amount": payment_data["amount"],
                    "payment": {
                        "creditCard": {
                            "cardNumber": payment_data["card_number"],
                            "expirationDate": payment_data["expiry_date"],
                            "cardCode": payment_data["cvv"]
                        }
                    }
                }
            }
        }
```

### Webhook Handlers

```python
from fastapi import Request, HTTPException
import hmac
import hashlib

class WebhookHandler:
    def __init__(self, secret: str):
        self.secret = secret
    
    async def handle_webhook(self, request: Request) -> dict:
        """Handle incoming webhook."""
        payload = await request.body()
        signature = request.headers.get("X-EasyPay-Signature")
        
        if not self._verify_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        data = await request.json()
        return await self._process_webhook(data)
    
    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature."""
        expected_signature = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
```

## Contributing

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** changes following code standards
4. **Write** tests for new functionality
5. **Run** all tests and ensure they pass
6. **Submit** a pull request

### Pull Request Guidelines

- Clear description of changes
- Reference related issues
- Include tests for new features
- Update documentation as needed
- Ensure all CI checks pass

### Code Review Process

1. **Automated checks** (linting, tests, type checking)
2. **Peer review** by team members
3. **Security review** for sensitive changes
4. **Performance review** for critical paths
5. **Documentation review** for API changes

### Release Process

1. **Version bump** in setup.py
2. **Update** CHANGELOG.md
3. **Create** release tag
4. **Deploy** to staging environment
5. **Run** integration tests
6. **Deploy** to production
7. **Monitor** deployment

## Resources

- **API Documentation**: https://docs.easypay.com/api
- **Architecture Guide**: https://docs.easypay.com/architecture
- **Deployment Guide**: https://docs.easypay.com/deployment
- **GitHub Repository**: https://github.com/easypay/payment-gateway
- **Issue Tracker**: https://github.com/easypay/payment-gateway/issues
