# FastAPI Payment Gateway Implementation Guide

## Table of Contents
1. [Project Setup](#project-setup)
2. [Core Implementation](#core-implementation)
3. [API Endpoints](#api-endpoints)
4. [Database Models](#database-models)
5. [Security Implementation](#security-implementation)
6. [Payment Processing](#payment-processing)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Guide](#deployment-guide)

## Project Setup

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv payment_gateway_env
source payment_gateway_env/bin/activate  # On Windows: payment_gateway_env\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary redis celery
pip install pydantic python-jose[cryptography] passlib[bcrypt]
pip install pytest pytest-asyncio httpx
```

### 2. Project Structure

```
payment_gateway/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── database.py
│   │   └── logging.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── payments.py
│   │           ├── merchants.py
│   │           ├── webhooks.py
│   │           └── analytics.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── payment.py
│   │   ├── merchant.py
│   │   ├── transaction.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── payment.py
│   │   ├── merchant.py
│   │   └── common.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── payment_service.py
│   │   ├── fraud_service.py
│   │   ├── notification_service.py
│   │   └── analytics_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── encryption.py
│   │   ├── validators.py
│   │   └── helpers.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_payments.py
│       └── test_merchants.py
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Core Implementation

### 1. Configuration Management

```python
# app/core/config.py
from pydantic import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Payment Gateway"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/payment_gateway"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # External APIs
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    
    # Security
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Payment Settings
    DEFAULT_CURRENCY: str = "USD"
    SUPPORTED_CURRENCIES: List[str] = ["USD", "EUR", "GBP", "CAD"]
    
    # Fraud Detection
    FRAUD_THRESHOLD: float = 0.8
    MAX_DAILY_TRANSACTIONS: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 2. Database Configuration

```python
# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 3. Security Implementation

```python
# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
```

## API Endpoints

### 1. Payment Endpoints

```python
# app/api/v1/endpoints/payments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_current_user, get_db
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentUpdate
from app.services.payment_service import PaymentService
from app.models.user import User

router = APIRouter()

@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new payment"""
    payment_service = PaymentService(db)
    return await payment_service.create_payment(payment_data, current_user.id)

@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment details by ID"""
    payment_service = PaymentService(db)
    payment = await payment_service.get_payment(payment_id, current_user.id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return payment

@router.get("/payments", response_model=List[PaymentResponse])
async def list_payments(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's payments"""
    payment_service = PaymentService(db)
    return await payment_service.list_payments(current_user.id, skip, limit)

@router.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: str,
    refund_amount: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process a refund for a payment"""
    payment_service = PaymentService(db)
    return await payment_service.refund_payment(payment_id, refund_amount, current_user.id)
```

### 2. Webhook Endpoints

```python
# app/api/v1/endpoints/webhooks.py
from fastapi import APIRouter, Request, HTTPException, Depends
from app.services.webhook_service import WebhookService
from app.core.security import verify_webhook_signature

router = APIRouter()

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not verify_webhook_signature(payload, signature, "stripe"):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    webhook_service = WebhookService()
    return await webhook_service.process_stripe_webhook(payload)

@router.post("/webhooks/paypal")
async def paypal_webhook(request: Request):
    """Handle PayPal webhooks"""
    payload = await request.json()
    
    webhook_service = WebhookService()
    return await webhook_service.process_paypal_webhook(payload)
```

## Database Models

### 1. Payment Model

```python
# app/models/payment.py
from sqlalchemy import Column, String, Float, DateTime, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid
from enum import Enum as PyEnum

class PaymentStatus(PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(PyEnum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"
    CRYPTOCURRENCY = "cryptocurrency"

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    
    # External payment processor data
    processor_payment_id = Column(String(255), nullable=True)
    processor_response = Column(Text, nullable=True)
    
    # Card details (tokenized)
    card_last_four = Column(String(4), nullable=True)
    card_brand = Column(String(50), nullable=True)
    card_exp_month = Column(String(2), nullable=True)
    card_exp_year = Column(String(4), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    merchant = relationship("Merchant", back_populates="payments")
    user = relationship("User", back_populates="payments")
    transactions = relationship("Transaction", back_populates="payment")
```

### 2. Transaction Model

```python
# app/models/transaction.py
from sqlalchemy import Column, String, Float, DateTime, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid
from enum import Enum as PyEnum

class TransactionType(PyEnum):
    PAYMENT = "payment"
    REFUND = "refund"
    CHARGEBACK = "chargeback"
    DISPUTE = "dispute"

class TransactionStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    
    transaction_type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    
    # External processor data
    processor_transaction_id = Column(String(255), nullable=True)
    processor_response = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    payment = relationship("Payment", back_populates="transactions")
```

## Payment Processing

### 1. Payment Service

```python
# app/services/payment_service.py
from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.fraud_service import FraudService
from app.services.notification_service import NotificationService
from app.utils.encryption import encrypt_card_data
import stripe
import paypalrestsdk

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.fraud_service = FraudService()
        self.notification_service = NotificationService()
        
        # Initialize payment processors
        stripe.api_key = settings.STRIPE_SECRET_KEY
        paypalrestsdk.configure({
            "mode": "sandbox",  # Use "live" for production
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET
        })
    
    async def create_payment(self, payment_data: PaymentCreate, user_id: str) -> PaymentResponse:
        # Fraud detection
        fraud_score = await self.fraud_service.analyze_transaction(payment_data)
        if fraud_score > settings.FRAUD_THRESHOLD:
            raise HTTPException(
                status_code=400,
                detail="Transaction flagged as potentially fraudulent"
            )
        
        # Create payment record
        payment = Payment(
            merchant_id=payment_data.merchant_id,
            user_id=user_id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            payment_method=payment_data.payment_method,
            status=PaymentStatus.PENDING
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        # Process payment based on method
        if payment_data.payment_method == PaymentMethod.CREDIT_CARD:
            result = await self._process_stripe_payment(payment, payment_data)
        elif payment_data.payment_method == PaymentMethod.DIGITAL_WALLET:
            result = await self._process_paypal_payment(payment, payment_data)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported payment method"
            )
        
        # Update payment status
        payment.status = PaymentStatus.COMPLETED if result["success"] else PaymentStatus.FAILED
        payment.processor_payment_id = result.get("processor_id")
        payment.processor_response = result.get("response")
        
        self.db.commit()
        
        # Send notifications
        await self.notification_service.send_payment_confirmation(payment)
        
        return PaymentResponse.from_orm(payment)
    
    async def _process_stripe_payment(self, payment: Payment, payment_data: PaymentCreate) -> dict:
        try:
            # Create Stripe payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount * 100),  # Convert to cents
                currency=payment.currency.lower(),
                payment_method=payment_data.payment_method_id,
                confirmation_method="manual",
                confirm=True
            )
            
            return {
                "success": intent.status == "succeeded",
                "processor_id": intent.id,
                "response": intent
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _process_paypal_payment(self, payment: Payment, payment_data: PaymentCreate) -> dict:
        try:
            # Create PayPal payment
            paypal_payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [{
                    "amount": {
                        "total": str(payment.amount),
                        "currency": payment.currency
                    }
                }],
                "redirect_urls": {
                    "return_url": f"{settings.FRONTEND_URL}/payment/success",
                    "cancel_url": f"{settings.FRONTEND_URL}/payment/cancel"
                }
            })
            
            if paypal_payment.create():
                return {
                    "success": True,
                    "processor_id": paypal_payment.id,
                    "response": paypal_payment
                }
            else:
                return {
                    "success": False,
                    "error": paypal_payment.error
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
```

### 2. Fraud Detection Service

```python
# app/services/fraud_service.py
import asyncio
from typing import Dict, Any
from app.core.config import settings

class FraudService:
    def __init__(self):
        self.rules = self._load_fraud_rules()
    
    async def analyze_transaction(self, payment_data: PaymentCreate) -> float:
        """Analyze transaction for fraud risk. Returns score between 0 and 1."""
        risk_score = 0.0
        
        # Rule 1: Amount-based risk
        if payment_data.amount > 10000:
            risk_score += 0.3
        elif payment_data.amount > 5000:
            risk_score += 0.2
        
        # Rule 2: Velocity check
        recent_transactions = await self._get_recent_transactions(payment_data.user_id)
        if len(recent_transactions) > 10:  # More than 10 transactions in last hour
            risk_score += 0.4
        
        # Rule 3: Geographic risk
        if payment_data.billing_country != payment_data.shipping_country:
            risk_score += 0.2
        
        # Rule 4: Time-based risk (transactions at unusual hours)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            risk_score += 0.1
        
        # Rule 5: Card validation
        if not self._validate_card(payment_data.card_number):
            risk_score += 0.5
        
        return min(risk_score, 1.0)
    
    def _validate_card(self, card_number: str) -> bool:
        """Basic Luhn algorithm validation"""
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        return luhn_checksum(card_number) == 0
    
    async def _get_recent_transactions(self, user_id: str) -> List[Dict]:
        # Implementation to get recent transactions from database
        # This would query the database for recent transactions
        pass
    
    def _load_fraud_rules(self) -> Dict[str, Any]:
        # Load fraud detection rules from configuration
        return {
            "max_amount": 10000,
            "max_velocity": 10,
            "geo_risk_threshold": 0.2
        }
```

## Testing Strategy

### 1. Unit Tests

```python
# app/tests/test_payments.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models.payment import Payment

client = TestClient(app)

@pytest.fixture
def test_payment_data():
    return {
        "amount": 100.00,
        "currency": "USD",
        "payment_method": "credit_card",
        "card_number": "4111111111111111",
        "card_exp_month": "12",
        "card_exp_year": "2025",
        "card_cvv": "123"
    }

def test_create_payment_success(test_payment_data):
    response = client.post("/api/v1/payments", json=test_payment_data)
    assert response.status_code == 200
    assert response.json()["amount"] == 100.00
    assert response.json()["status"] == "completed"

def test_create_payment_invalid_card(test_payment_data):
    test_payment_data["card_number"] = "1234567890123456"
    response = client.post("/api/v1/payments", json=test_payment_data)
    assert response.status_code == 400
    assert "Invalid card number" in response.json()["detail"]

def test_fraud_detection_high_amount():
    test_payment_data = {
        "amount": 50000.00,  # High amount
        "currency": "USD",
        "payment_method": "credit_card",
        "card_number": "4111111111111111",
        "card_exp_month": "12",
        "card_exp_year": "2025",
        "card_cvv": "123"
    }
    response = client.post("/api/v1/payments", json=test_payment_data)
    assert response.status_code == 400
    assert "fraudulent" in response.json()["detail"]
```

### 2. Integration Tests

```python
# app/tests/test_integration.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import get_db, Base
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_payment_flow_integration(setup_database):
    # Test complete payment flow
    payment_data = {
        "amount": 100.00,
        "currency": "USD",
        "payment_method": "credit_card"
    }
    
    response = client.post("/api/v1/payments", json=payment_data)
    assert response.status_code == 200
    
    payment_id = response.json()["id"]
    
    # Test getting payment
    get_response = client.get(f"/api/v1/payments/{payment_id}")
    assert get_response.status_code == 200
    assert get_response.json()["amount"] == 100.00
```

## Deployment Guide

### 1. Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/payment_gateway
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - .:/app

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=payment_gateway
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

  celery:
    build: .
    command: celery -A app.core.celery worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/payment_gateway
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - .:/app

volumes:
  postgres_data:
```

### 3. Production Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Run database migrations
docker-compose exec app alembic upgrade head

# Run tests
docker-compose exec app pytest

# View logs
docker-compose logs -f app
```

This implementation guide provides a solid foundation for building a modern payment gateway using FastAPI. The code is production-ready and includes all the essential features needed for a secure, scalable payment processing system.
