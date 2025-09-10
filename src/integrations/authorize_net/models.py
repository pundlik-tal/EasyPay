"""
EasyPay Payment Gateway - Authorize.net Data Models
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class TransactionType(str, Enum):
    """Authorize.net transaction types."""
    AUTH_CAPTURE = "authCaptureTransaction"
    AUTH_ONLY = "authOnlyTransaction"
    PRIOR_AUTH_CAPTURE = "priorAuthCaptureTransaction"
    REFUND = "refundTransaction"
    VOID = "voidTransaction"


class TransactionStatus(str, Enum):
    """Transaction status values."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    DECLINED = "declined"
    ERROR = "error"
    VOIDED = "voided"
    REFUNDED = "refunded"


class CreditCard(BaseModel):
    """Credit card information."""
    card_number: str = Field(..., min_length=13, max_length=19, description="Credit card number")
    expiration_date: str = Field(..., pattern=r"^\d{4}$", description="Expiration date in MMYY format")
    card_code: Optional[str] = Field(None, min_length=3, max_length=4, description="CVV/CVC code")
    
    @field_validator('card_number')
    @classmethod
    def validate_card_number(cls, v):
        """Validate credit card number using Luhn algorithm."""
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
        
        if luhn_checksum(v) != 0:
            raise ValueError('Invalid credit card number')
        return v
    
    @field_validator('expiration_date')
    @classmethod
    def validate_expiration_date(cls, v):
        """Validate expiration date format and ensure it's not expired."""
        if len(v) != 4:
            raise ValueError('Expiration date must be in MMYY format')
        
        month = int(v[:2])
        year = int(v[2:])
        
        if month < 1 or month > 12:
            raise ValueError('Invalid month in expiration date')
        
        # Convert YY to full year
        current_year = datetime.now().year
        current_month = datetime.now().month
        full_year = 2000 + year if year < 100 else year
        
        if full_year < current_year or (full_year == current_year and month < current_month):
            raise ValueError('Credit card has expired')
        
        return v


class BillingAddress(BaseModel):
    """Billing address information."""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    address: str = Field(..., min_length=1, max_length=60)
    city: str = Field(..., min_length=1, max_length=40)
    state: str = Field(..., min_length=2, max_length=40)
    zip: str = Field(..., min_length=5, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=2)


class PaymentRequest(BaseModel):
    """Payment request model."""
    transaction_type: TransactionType
    amount: str = Field(..., pattern=r"^\d+\.\d{2}$", description="Amount in decimal format (e.g., '10.00')")
    payment: Dict[str, Any] = Field(..., description="Payment method information")
    bill_to: Optional[BillingAddress] = None
    order: Optional[Dict[str, str]] = None
    ref_id: Optional[str] = None
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Validate amount is positive."""
        amount_float = float(v)
        if amount_float <= 0:
            raise ValueError('Amount must be greater than 0')
        if amount_float > 999999.99:
            raise ValueError('Amount exceeds maximum limit')
        return v


class PaymentResponse(BaseModel):
    """Payment response model."""
    transaction_id: Optional[str] = None
    status: TransactionStatus
    response_code: str
    response_text: str
    auth_code: Optional[str] = None
    avs_response: Optional[str] = None
    cvv_response: Optional[str] = None
    amount: Optional[str] = None
    ref_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_response: Optional[Dict[str, Any]] = None


class AuthorizeNetCredentials(BaseModel):
    """Authorize.net API credentials."""
    api_login_id: str = Field(..., min_length=1, max_length=20)
    transaction_key: str = Field(..., min_length=1, max_length=16)
    sandbox: bool = True
    api_url: Optional[str] = None
