# Authorize.net Fraud Management Guide

## Overview

Fraud management is critical for payment processing systems. Authorize.net provides built-in fraud detection tools and allows integration with third-party fraud detection services to protect against fraudulent transactions.

## Table of Contents
1. [Built-in Fraud Detection](#built-in-fraud-detection)
2. [Advanced Fraud Detection Suite](#advanced-fraud-detection-suite)
3. [Fraud Detection Rules](#fraud-detection-rules)
4. [Risk Scoring](#risk-scoring)
5. [Fraud Management APIs](#fraud-management-apis)
6. [Best Practices](#best-practices)
7. [Integration Examples](#integration-examples)

## Built-in Fraud Detection

### Address Verification Service (AVS)

**Purpose**: Verify billing address matches cardholder's address.

**AVS Codes**:
| Code | Description | Action |
|------|-------------|---------|
| A | Address matches, ZIP doesn't | Review |
| B | Address info unavailable | Review |
| E | AVS error | Review |
| G | Non-US card, AVS not supported | Accept |
| N | No match on address or ZIP | Decline |
| P | AVS not applicable | Accept |
| R | Retry, system unavailable | Retry |
| S | AVS not supported | Accept |
| U | Address info unavailable | Review |
| W | ZIP matches, address doesn't | Review |
| X | Address and ZIP match | Accept |
| Y | Address and ZIP match | Accept |
| Z | ZIP matches, address doesn't | Review |

**Implementation**:
```json
{
  "createTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "transactionRequest": {
      "transactionType": "authCaptureTransaction",
      "amount": "10.00",
      "payment": {
        "creditCard": {
          "cardNumber": "4111111111111111",
          "expirationDate": "1225",
          "cardCode": "123"
        }
      },
      "billTo": {
        "firstName": "John",
        "lastName": "Doe",
        "address": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345",
        "country": "US"
      }
    }
  }
}
```

### Card Code Verification (CVV)

**Purpose**: Verify the security code on the card.

**CVV Codes**:
| Code | Description | Action |
|------|-------------|---------|
| M | Match | Accept |
| N | No match | Decline |
| P | Not processed | Review |
| S | Should have been present | Review |
| U | Issuer unable to process | Review |

**Implementation**:
```json
{
  "payment": {
    "creditCard": {
      "cardNumber": "4111111111111111",
      "expirationDate": "1225",
      "cardCode": "123"
    }
  }
}
```

## Advanced Fraud Detection Suite

### Fraud Detection Filters

**Purpose**: Advanced fraud detection using multiple data points.

**Available Filters**:
- **Velocity Filter**: Detect rapid transactions
- **Amount Filter**: Flag unusual transaction amounts
- **Suspicious Transaction Filter**: Detect suspicious patterns
- **International AVS Filter**: Enhanced AVS for international cards
- **Tax ID Filter**: Validate tax identification numbers

**Configuration**:
```json
{
  "createTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "transactionRequest": {
      "transactionType": "authCaptureTransaction",
      "amount": "10.00",
      "payment": {
        "creditCard": {
          "cardNumber": "4111111111111111",
          "expirationDate": "1225",
          "cardCode": "123"
        }
      },
      "billTo": {
        "firstName": "John",
        "lastName": "Doe",
        "address": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345",
        "country": "US"
      },
      "customer": {
        "id": "CUST_123456",
        "email": "john.doe@example.com"
      },
      "order": {
        "invoiceNumber": "INV-001",
        "description": "Test transaction"
      }
    }
  }
}
```

### Fraud Detection Response

**Successful Transaction**:
```json
{
  "transactionResponse": {
    "responseCode": "1",
    "authCode": "AUTH123",
    "avsResultCode": "Y",
    "cvvResultCode": "M",
    "cavvResultCode": "2",
    "transId": "40000000001",
    "testRequest": "0",
    "accountNumber": "XXXX1111",
    "accountType": "Visa",
    "messages": [
      {
        "code": "1",
        "description": "This transaction has been approved."
      }
    ]
  }
}
```

**Fraud Detection Triggered**:
```json
{
  "transactionResponse": {
    "responseCode": "4",
    "authCode": "",
    "avsResultCode": "N",
    "cvvResultCode": "N",
    "cavvResultCode": "",
    "transId": "0",
    "testRequest": "0",
    "accountNumber": "XXXX1111",
    "accountType": "Visa",
    "errors": [
      {
        "errorCode": "44",
        "errorText": "The transaction was held for review."
      }
    ]
  }
}
```

## Fraud Detection Rules

### Velocity Rules

**Purpose**: Detect rapid-fire transactions from same source.

**Configuration**:
- **Time Window**: 1 hour, 24 hours, 7 days
- **Transaction Count**: Maximum allowed transactions
- **Amount Threshold**: Maximum transaction amount

**Example Rule**:
```json
{
  "rule": {
    "name": "Velocity Check",
    "type": "velocity",
    "timeWindow": "1h",
    "maxTransactions": 5,
    "maxAmount": 1000.00,
    "action": "hold"
  }
}
```

### Amount Rules

**Purpose**: Flag transactions above certain thresholds.

**Configuration**:
- **Minimum Amount**: Flag transactions below minimum
- **Maximum Amount**: Flag transactions above maximum
- **Average Amount**: Flag deviations from average

**Example Rule**:
```json
{
  "rule": {
    "name": "Amount Check",
    "type": "amount",
    "minAmount": 1.00,
    "maxAmount": 5000.00,
    "action": "review"
  }
}
```

### Geographic Rules

**Purpose**: Detect transactions from suspicious locations.

**Configuration**:
- **Country Restrictions**: Block specific countries
- **State Restrictions**: Block specific states
- **IP Geolocation**: Verify IP location matches billing address

**Example Rule**:
```json
{
  "rule": {
    "name": "Geographic Check",
    "type": "geographic",
    "blockedCountries": ["XX", "YY"],
    "blockedStates": ["CA", "NY"],
    "action": "block"
  }
}
```

## Risk Scoring

### Risk Score Calculation

**Factors Considered**:
- **Transaction Amount**: Higher amounts = higher risk
- **Time of Day**: Unusual hours = higher risk
- **Geographic Location**: Foreign transactions = higher risk
- **Device Fingerprint**: New devices = higher risk
- **Transaction History**: Unusual patterns = higher risk

**Risk Score Ranges**:
- **0-30**: Low risk (Accept)
- **31-70**: Medium risk (Review)
- **71-100**: High risk (Decline)

### Risk Score Implementation

```python
def calculate_risk_score(transaction_data):
    """Calculate fraud risk score for transaction."""
    risk_score = 0
    
    # Amount factor
    amount = float(transaction_data['amount'])
    if amount > 1000:
        risk_score += 20
    elif amount > 500:
        risk_score += 10
    
    # Time factor
    hour = datetime.now().hour
    if hour < 6 or hour > 22:
        risk_score += 15
    
    # Geographic factor
    if transaction_data['country'] != 'US':
        risk_score += 25
    
    # Device factor
    if transaction_data.get('device_fingerprint') is None:
        risk_score += 20
    
    # History factor
    if transaction_data.get('customer_id'):
        history_score = get_customer_history_score(transaction_data['customer_id'])
        risk_score += history_score
    
    return min(risk_score, 100)
```

## Fraud Management APIs

### Get Held Transaction List

**Purpose**: Retrieve transactions held for review.

**Request**:
```json
{
  "getHeldTransactionListRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    }
  }
}
```

**Response**:
```json
{
  "heldTransactionList": [
    {
      "transId": "40000000001",
      "amount": "100.00",
      "submitTimeUTC": "2024-01-01T12:00:00Z",
      "firstName": "John",
      "lastName": "Doe",
      "accountNumber": "XXXX1111",
      "accountType": "Visa",
      "avsResultCode": "N",
      "cvvResultCode": "N"
    }
  ],
  "messages": {
    "resultCode": "Ok",
    "message": [
      {
        "code": "I00001",
        "text": "Successful."
      }
    ]
  }
}
```

### Approve Held Transaction

**Purpose**: Approve a transaction held for review.

**Request**:
```json
{
  "approveHeldTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "heldTransactionList": {
      "transactionId": "40000000001"
    }
  }
}
```

### Decline Held Transaction

**Purpose**: Decline a transaction held for review.

**Request**:
```json
{
  "declineHeldTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "heldTransactionList": {
      "transactionId": "40000000001"
    }
  }
}
```

## Best Practices

### Fraud Prevention

1. **Implement Multiple Layers**:
   - AVS and CVV verification
   - Velocity checks
   - Geographic restrictions
   - Device fingerprinting
   - Behavioral analysis

2. **Real-time Monitoring**:
   - Monitor transactions in real-time
   - Set up alerts for suspicious activity
   - Use machine learning for pattern detection
   - Implement automated responses

3. **Data Collection**:
   - Collect device information
   - Track user behavior
   - Monitor transaction patterns
   - Analyze customer history

### Risk Management

1. **Risk Scoring**:
   - Implement comprehensive risk scoring
   - Use multiple data points
   - Regularly update scoring algorithms
   - Monitor score accuracy

2. **Threshold Management**:
   - Set appropriate thresholds
   - Adjust based on business needs
   - Monitor false positive rates
   - Balance security and user experience

3. **Review Process**:
   - Manual review for medium-risk transactions
   - Clear escalation procedures
   - Regular review of held transactions
   - Document decision rationale

### Compliance

1. **PCI DSS Compliance**:
   - Never store card data
   - Use secure transmission
   - Implement access controls
   - Regular security audits

2. **Data Protection**:
   - Encrypt sensitive data
   - Implement data retention policies
   - Secure data transmission
   - Regular security updates

## Integration Examples

### Python Fraud Detection Service

```python
import requests
import json
from datetime import datetime

class FraudDetectionService:
    def __init__(self, api_login_id, transaction_key):
        self.api_login_id = api_login_id
        self.transaction_key = transaction_key
        self.base_url = "https://apitest.authorize.net/xml/v1/request.api"
    
    def check_fraud_risk(self, transaction_data):
        """Check fraud risk for transaction."""
        risk_score = self.calculate_risk_score(transaction_data)
        
        if risk_score > 70:
            return {"action": "decline", "reason": "High fraud risk"}
        elif risk_score > 30:
            return {"action": "hold", "reason": "Medium fraud risk"}
        else:
            return {"action": "approve", "reason": "Low fraud risk"}
    
    def calculate_risk_score(self, transaction_data):
        """Calculate fraud risk score."""
        risk_score = 0
        
        # Amount check
        amount = float(transaction_data['amount'])
        if amount > 1000:
            risk_score += 20
        
        # AVS check
        if transaction_data.get('avs_result') == 'N':
            risk_score += 30
        
        # CVV check
        if transaction_data.get('cvv_result') == 'N':
            risk_score += 25
        
        # Geographic check
        if transaction_data.get('country') != 'US':
            risk_score += 15
        
        return min(risk_score, 100)
    
    def get_held_transactions(self):
        """Get list of held transactions."""
        request_data = {
            "getHeldTransactionListRequest": {
                "merchantAuthentication": {
                    "name": self.api_login_id,
                    "transactionKey": self.transaction_key
                }
            }
        }
        
        response = requests.post(
            self.base_url,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()
    
    def approve_transaction(self, transaction_id):
        """Approve held transaction."""
        request_data = {
            "approveHeldTransactionRequest": {
                "merchantAuthentication": {
                    "name": self.api_login_id,
                    "transactionKey": self.transaction_key
                },
                "heldTransactionList": {
                    "transactionId": transaction_id
                }
            }
        }
        
        response = requests.post(
            self.base_url,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()
```

### JavaScript Fraud Detection

```javascript
class FraudDetectionService {
    constructor(apiLoginId, transactionKey) {
        this.apiLoginId = apiLoginId;
        this.transactionKey = transactionKey;
        this.baseUrl = "https://apitest.authorize.net/xml/v1/request.api";
    }
    
    async checkFraudRisk(transactionData) {
        const riskScore = this.calculateRiskScore(transactionData);
        
        if (riskScore > 70) {
            return { action: "decline", reason: "High fraud risk" };
        } else if (riskScore > 30) {
            return { action: "hold", reason: "Medium fraud risk" };
        } else {
            return { action: "approve", reason: "Low fraud risk" };
        }
    }
    
    calculateRiskScore(transactionData) {
        let riskScore = 0;
        
        // Amount check
        const amount = parseFloat(transactionData.amount);
        if (amount > 1000) {
            riskScore += 20;
        }
        
        // AVS check
        if (transactionData.avsResult === 'N') {
            riskScore += 30;
        }
        
        // CVV check
        if (transactionData.cvvResult === 'N') {
            riskScore += 25;
        }
        
        // Geographic check
        if (transactionData.country !== 'US') {
            riskScore += 15;
        }
        
        return Math.min(riskScore, 100);
    }
    
    async getHeldTransactions() {
        const requestData = {
            getHeldTransactionListRequest: {
                merchantAuthentication: {
                    name: this.apiLoginId,
                    transactionKey: this.transactionKey
                }
            }
        };
        
        const response = await fetch(this.baseUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        return await response.json();
    }
}
```

## Monitoring and Alerting

### Key Metrics

1. **Fraud Detection Rate**: Percentage of transactions flagged
2. **False Positive Rate**: Percentage of legitimate transactions flagged
3. **False Negative Rate**: Percentage of fraudulent transactions missed
4. **Review Time**: Average time to review held transactions
5. **Approval Rate**: Percentage of held transactions approved

### Alert Thresholds

1. **High Fraud Rate**: > 5% of transactions flagged
2. **High False Positive Rate**: > 2% false positives
3. **Long Review Time**: > 24 hours average review time
4. **Unusual Patterns**: Sudden changes in fraud patterns

### Dashboard Metrics

```json
{
  "fraud_metrics": {
    "total_transactions": 10000,
    "flagged_transactions": 150,
    "fraud_detection_rate": 1.5,
    "false_positive_rate": 0.3,
    "average_review_time": "2.5 hours",
    "approval_rate": 85.0
  }
}
```

## Common Issues and Solutions

### Issue: High False Positive Rate
- **Cause**: Overly strict fraud rules
- **Solution**: Adjust thresholds and review rules

### Issue: Missed Fraudulent Transactions
- **Cause**: Insufficient fraud detection
- **Solution**: Add more detection layers and improve algorithms

### Issue: Slow Review Process
- **Cause**: Manual review bottlenecks
- **Solution**: Implement automated review for low-risk transactions

### Issue: Customer Complaints
- **Cause**: Legitimate transactions declined
- **Solution**: Improve fraud detection accuracy and customer communication

## Next Steps

1. Review [Fault Tolerance Guide](08-fault-tolerance.md)
2. Learn about [Performance Optimization](09-performance-optimization.md)
3. Create [Integration Examples](10-integration-examples.md)
4. Implement [Security Best Practices](11-security-guide.md)

## Resources

- [Authorize.net Fraud Detection](https://developer.authorize.net/api/reference/index.html#fraud-management)
- [Fraud Detection Suite](https://developer.authorize.net/api/reference/features/fraud-detection-suite.html)
- [Risk Management](https://developer.authorize.net/api/reference/features/risk-management.html)
- [PCI Compliance](https://developer.authorize.net/api/reference/features/pci-compliance.html)
