# Payment Gateway Security & Compliance Guide

## Table of Contents
1. [PCI DSS Compliance](#pci-dss-compliance)
2. [Security Architecture](#security-architecture)
3. [Data Protection](#data-protection)
4. [Fraud Prevention](#fraud-prevention)
5. [Regulatory Compliance](#regulatory-compliance)
6. [Security Best Practices](#security-best-practices)
7. [Incident Response](#incident-response)

## PCI DSS Compliance

### Level 1 Requirements
- **Build and Maintain Secure Networks**: Firewalls, secure configurations
- **Protect Cardholder Data**: Encryption, tokenization, data retention policies
- **Maintain Vulnerability Management**: Regular updates, security patches
- **Implement Strong Access Control**: Role-based access, unique IDs
- **Regularly Monitor Networks**: Logging, monitoring, testing
- **Maintain Information Security Policy**: Documentation, training

### Implementation Checklist

#### Network Security
- [ ] Deploy firewalls between public and private networks
- [ ] Implement network segmentation
- [ ] Use strong cryptography for data transmission
- [ ] Regularly test security systems and processes

#### Data Protection
- [ ] Encrypt stored cardholder data (AES-256)
- [ ] Implement tokenization for sensitive data
- [ ] Mask PAN when displaying data
- [ ] Secure deletion of data when no longer needed

#### Access Control
- [ ] Implement multi-factor authentication
- [ ] Use role-based access control (RBAC)
- [ ] Regular access reviews and deprovisioning
- [ ] Unique user IDs and strong passwords

## Security Architecture

### 1. Defense in Depth

```
┌─────────────────────────────────────────────────────────┐
│                    External Threats                     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                WAF / DDoS Protection                    │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  Load Balancer                          │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                 API Gateway                             │
│              (Rate Limiting, Auth)                      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│              Application Layer                          │
│           (FastAPI + Security Middleware)               │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                Database Layer                           │
│            (Encrypted at Rest)                          │
└─────────────────────────────────────────────────────────┘
```

### 2. Key Security Components

#### API Gateway Security
```python
# Rate limiting and authentication
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

#### Input Validation
```python
from pydantic import BaseModel, validator, Field
import re

class PaymentRequest(BaseModel):
    amount: float = Field(gt=0, le=1000000)
    currency: str = Field(regex=r'^[A-Z]{3}$')
    card_number: str = Field(min_length=13, max_length=19)
    
    @validator('card_number')
    def validate_card_number(cls, v):
        # Remove spaces and dashes
        cleaned = re.sub(r'[\s-]', '', v)
        # Check if all digits
        if not cleaned.isdigit():
            raise ValueError('Card number must contain only digits')
        # Luhn algorithm validation
        if not luhn_checksum(cleaned):
            raise ValueError('Invalid card number')
        return cleaned
```

## Data Protection

### 1. Encryption Strategy

#### Data at Rest
```python
from cryptography.fernet import Fernet
import base64
import os

class EncryptionService:
    def __init__(self):
        self.key = os.getenv('ENCRYPTION_KEY')
        if not self.key:
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        encrypted_data = self.cipher.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        decoded_data = base64.b64decode(encrypted_data.encode())
        decrypted_data = self.cipher.decrypt(decoded_data)
        return decrypted_data.decode()
```

#### Data in Transit
```python
# HTTPS/TLS Configuration
import ssl
from fastapi import FastAPI
import uvicorn

# SSL context configuration
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
ssl_context.load_cert_chain("cert.pem", "key.pem")
ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')

# Run with SSL
uvicorn.run(app, ssl_context=ssl_context, host="0.0.0.0", port=443)
```

### 2. Tokenization

```python
import uuid
import hashlib
from typing import Dict

class TokenizationService:
    def __init__(self):
        self.token_map: Dict[str, str] = {}
    
    def tokenize_card(self, card_number: str) -> str:
        """Replace sensitive card data with token"""
        # Generate secure token
        token = str(uuid.uuid4())
        
        # Store mapping securely (in production, use secure database)
        self.token_map[token] = self._hash_card(card_number)
        
        return token
    
    def detokenize(self, token: str) -> str:
        """Retrieve original card data from token"""
        return self.token_map.get(token)
    
    def _hash_card(self, card_number: str) -> str:
        """Create secure hash of card number"""
        return hashlib.sha256(card_number.encode()).hexdigest()
```

## Fraud Prevention

### 1. Machine Learning Models

```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

class FraudDetectionModel:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def extract_features(self, transaction_data: dict) -> np.ndarray:
        """Extract features for fraud detection"""
        features = [
            transaction_data['amount'],
            transaction_data['hour_of_day'],
            transaction_data['day_of_week'],
            transaction_data['is_weekend'],
            transaction_data['merchant_category'],
            transaction_data['transaction_frequency'],
            transaction_data['avg_transaction_amount'],
            transaction_data['geographic_distance'],
            transaction_data['device_trust_score']
        ]
        return np.array(features).reshape(1, -1)
    
    def predict_fraud_probability(self, transaction_data: dict) -> float:
        """Predict fraud probability (0-1)"""
        if not self.is_trained:
            return 0.5  # Default neutral score
        
        features = self.extract_features(transaction_data)
        features_scaled = self.scaler.transform(features)
        probability = self.model.predict_proba(features_scaled)[0][1]
        return probability
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray):
        """Train the fraud detection model"""
        X_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_scaled, y_train)
        self.is_trained = True
```

### 2. Rule-Based Detection

```python
class FraudRules:
    def __init__(self):
        self.rules = {
            'high_amount': {'threshold': 10000, 'weight': 0.3},
            'velocity': {'max_transactions': 10, 'time_window': 3600, 'weight': 0.4},
            'geographic': {'max_distance': 1000, 'weight': 0.2},
            'time_anomaly': {'unusual_hours': [0, 1, 2, 3, 4, 5], 'weight': 0.1}
        }
    
    def evaluate_transaction(self, transaction: dict) -> float:
        """Evaluate transaction against fraud rules"""
        risk_score = 0.0
        
        # High amount rule
        if transaction['amount'] > self.rules['high_amount']['threshold']:
            risk_score += self.rules['high_amount']['weight']
        
        # Velocity rule
        if transaction['transaction_count_last_hour'] > self.rules['velocity']['max_transactions']:
            risk_score += self.rules['velocity']['weight']
        
        # Geographic rule
        if transaction['distance_from_home'] > self.rules['geographic']['max_distance']:
            risk_score += self.rules['geographic']['weight']
        
        # Time anomaly rule
        if transaction['hour'] in self.rules['time_anomaly']['unusual_hours']:
            risk_score += self.rules['time_anomaly']['weight']
        
        return min(risk_score, 1.0)
```

## Regulatory Compliance

### 1. GDPR Compliance

```python
class GDPRCompliance:
    def __init__(self):
        self.data_retention_period = 7 * 365 * 24 * 3600  # 7 years in seconds
    
    def anonymize_personal_data(self, user_id: str) -> bool:
        """Anonymize personal data for GDPR compliance"""
        try:
            # Replace PII with anonymized data
            self._replace_with_hashed_data(user_id)
            return True
        except Exception as e:
            logger.error(f"Failed to anonymize data for user {user_id}: {e}")
            return False
    
    def delete_user_data(self, user_id: str) -> bool:
        """Delete all user data (Right to be forgotten)"""
        try:
            # Delete from all databases
            self._delete_from_payments_db(user_id)
            self._delete_from_users_db(user_id)
            self._delete_from_analytics_db(user_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete data for user {user_id}: {e}")
            return False
    
    def export_user_data(self, user_id: str) -> dict:
        """Export all user data (Data portability)"""
        return {
            'personal_info': self._get_personal_info(user_id),
            'payment_history': self._get_payment_history(user_id),
            'preferences': self._get_user_preferences(user_id)
        }
```

### 2. SOX Compliance

```python
class SOXCompliance:
    def __init__(self):
        self.audit_log = []
    
    def log_financial_transaction(self, transaction: dict):
        """Log financial transaction for SOX compliance"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'transaction_id': transaction['id'],
            'amount': transaction['amount'],
            'currency': transaction['currency'],
            'user_id': transaction['user_id'],
            'action': 'transaction_created',
            'ip_address': transaction.get('ip_address'),
            'user_agent': transaction.get('user_agent')
        }
        self.audit_log.append(audit_entry)
    
    def generate_audit_report(self, start_date: datetime, end_date: datetime) -> list:
        """Generate audit report for specified period"""
        return [
            entry for entry in self.audit_log
            if start_date <= datetime.fromisoformat(entry['timestamp']) <= end_date
        ]
```

## Security Best Practices

### 1. Authentication & Authorization

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = 30
    
    def create_access_token(self, data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    auth_service = AuthService()
    payload = auth_service.verify_token(credentials.credentials)
    return payload
```

### 2. Input Sanitization

```python
import html
import re
from typing import Any

class InputSanitizer:
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitize string input"""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', value)
        # Escape HTML entities
        clean = html.escape(clean)
        # Remove null bytes
        clean = clean.replace('\x00', '')
        return clean.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_amount(amount: float) -> bool:
        """Validate payment amount"""
        return 0 < amount <= 1000000  # Max $1M per transaction
```

## Incident Response

### 1. Security Incident Plan

```python
class SecurityIncidentResponse:
    def __init__(self):
        self.incident_log = []
        self.escalation_levels = {
            'low': ['security_team'],
            'medium': ['security_team', 'engineering_lead'],
            'high': ['security_team', 'engineering_lead', 'cto'],
            'critical': ['security_team', 'engineering_lead', 'cto', 'ceo']
        }
    
    def handle_security_incident(self, incident_type: str, severity: str, details: dict):
        """Handle security incident"""
        incident = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'type': incident_type,
            'severity': severity,
            'details': details,
            'status': 'open'
        }
        
        self.incident_log.append(incident)
        
        # Escalate based on severity
        self._escalate_incident(incident)
        
        # Take immediate action
        self._take_immediate_action(incident)
    
    def _escalate_incident(self, incident: dict):
        """Escalate incident to appropriate team members"""
        severity = incident['severity']
        team_members = self.escalation_levels.get(severity, [])
        
        for member in team_members:
            self._notify_team_member(member, incident)
    
    def _take_immediate_action(self, incident: dict):
        """Take immediate action based on incident type"""
        if incident['type'] == 'data_breach':
            self._block_affected_accounts(incident['details']['affected_users'])
        elif incident['type'] == 'fraud_attack':
            self._increase_fraud_detection_sensitivity()
        elif incident['type'] == 'ddos_attack':
            self._activate_ddos_protection()
```

### 2. Monitoring & Alerting

```python
import logging
from datetime import datetime, timedelta

class SecurityMonitoring:
    def __init__(self):
        self.logger = logging.getLogger('security_monitoring')
        self.alert_thresholds = {
            'failed_login_attempts': 5,
            'suspicious_transactions': 10,
            'api_rate_limit_exceeded': 100
        }
    
    def monitor_failed_logins(self, user_id: str, ip_address: str):
        """Monitor failed login attempts"""
        key = f"failed_logins:{user_id}:{ip_address}"
        count = self._increment_counter(key, ttl=3600)  # 1 hour TTL
        
        if count >= self.alert_thresholds['failed_login_attempts']:
            self._trigger_alert('suspicious_login_activity', {
                'user_id': user_id,
                'ip_address': ip_address,
                'attempts': count
            })
    
    def monitor_transaction_patterns(self, transaction: dict):
        """Monitor transaction patterns for anomalies"""
        # Check for velocity attacks
        user_id = transaction['user_id']
        recent_transactions = self._get_recent_transactions(user_id, minutes=60)
        
        if len(recent_transactions) > self.alert_thresholds['suspicious_transactions']:
            self._trigger_alert('velocity_attack', {
                'user_id': user_id,
                'transaction_count': len(recent_transactions),
                'time_window': '60 minutes'
            })
    
    def _trigger_alert(self, alert_type: str, details: dict):
        """Trigger security alert"""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': alert_type,
            'details': details,
            'severity': self._determine_severity(alert_type)
        }
        
        self.logger.warning(f"Security Alert: {alert}")
        
        # Send to monitoring system
        self._send_to_monitoring_system(alert)
```

This comprehensive security and compliance guide provides the foundation for building a secure, compliant payment gateway that meets industry standards and regulatory requirements.
