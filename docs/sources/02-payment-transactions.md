# Authorize.net Payment Transactions Guide

## Overview

This guide covers all payment transaction types available in the Authorize.net API, including credit card processing, bank account transactions, and mobile payments. Understanding these transactions is crucial for building a robust payment gateway.

## Table of Contents
1. [Credit Card Transactions](#credit-card-transactions)
2. [Bank Account Transactions](#bank-account-transactions)
3. [Mobile Payment Transactions](#mobile-payment-transactions)
4. [Transaction Workflows](#transaction-workflows)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)

## Credit Card Transactions

### 1. Charge a Credit Card (Authorization + Capture)

This is the most common transaction type - it authorizes and captures funds in one step.

**Request Structure:**
```json
{
  "createTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "refId": "ref123456",
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
      "order": {
        "invoiceNumber": "INV-001",
        "description": "Test transaction"
      }
    }
  }
}
```

**Key Fields:**
- `transactionType`: "authCaptureTransaction" for immediate charge
- `amount`: Transaction amount (string format with 2 decimal places)
- `cardNumber`: Credit card number (test: 4111111111111111)
- `expirationDate`: MMYY format
- `cardCode`: CVV/CVC code
- `billTo`: Billing address information

### 2. Authorize Only (Hold Funds)

Authorize funds without capturing them. Useful for pre-authorization scenarios.

**Request Structure:**
```json
{
  "createTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "transactionRequest": {
      "transactionType": "authOnlyTransaction",
      "amount": "10.00",
      "payment": {
        "creditCard": {
          "cardNumber": "4111111111111111",
          "expirationDate": "1225",
          "cardCode": "123"
        }
      }
    }
  }
}
```

### 3. Capture Previously Authorized Amount

Capture funds from a previous authorization.

**Request Structure:**
```json
{
  "createTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "transactionRequest": {
      "transactionType": "priorAuthCaptureTransaction",
      "amount": "10.00",
      "refTransId": "AUTH_CODE_FROM_PREVIOUS_TRANSACTION"
    }
  }
}
```

### 4. Refund a Transaction

Refund a previously captured transaction.

**Request Structure:**
```json
{
  "createTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "transactionRequest": {
      "transactionType": "refundTransaction",
      "amount": "5.00",
      "payment": {
        "creditCard": {
          "cardNumber": "4111111111111111",
          "expirationDate": "1225"
        }
      },
      "refTransId": "TRANSACTION_ID_TO_REFUND"
    }
  }
}
```

### 5. Void a Transaction

Cancel a transaction before it's settled (usually within 24 hours).

**Request Structure:**
```json
{
  "createTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "transactionRequest": {
      "transactionType": "voidTransaction",
      "refTransId": "TRANSACTION_ID_TO_VOID"
    }
  }
}
```

## Bank Account Transactions

### 1. Debit a Bank Account (ACH)

Process ACH debit transactions.

**Request Structure:**
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
        "bankAccount": {
          "accountType": "checking",
          "routingNumber": "125000024",
          "accountNumber": "1234567890",
          "nameOnAccount": "John Doe"
        }
      }
    }
  }
}
```

### 2. Credit a Bank Account (ACH)

Process ACH credit transactions.

**Request Structure:**
```json
{
  "createTransactionRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "transactionRequest": {
      "transactionType": "refundTransaction",
      "amount": "10.00",
      "payment": {
        "bankAccount": {
          "accountType": "checking",
          "routingNumber": "125000024",
          "accountNumber": "1234567890",
          "nameOnAccount": "John Doe"
        }
      }
    }
  }
}
```

## Mobile Payment Transactions

### 1. Apple Pay Transaction

Process Apple Pay transactions.

**Request Structure:**
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
        "opaqueData": {
          "dataDescriptor": "COMMON.APPLE.INAPP.PAYMENT",
          "dataValue": "APPLE_PAY_TOKEN_DATA"
        }
      }
    }
  }
}
```

### 2. Google Pay Transaction

Process Google Pay transactions.

**Request Structure:**
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
        "opaqueData": {
          "dataDescriptor": "COMMON.GOOGLE.INAPP.PAYMENT",
          "dataValue": "GOOGLE_PAY_TOKEN_DATA"
        }
      }
    }
  }
}
```

## Transaction Workflows

### Standard E-commerce Flow

1. **Customer places order** → Your application
2. **Create transaction** → Authorize.net API
3. **Process response** → Handle success/failure
4. **Update order status** → Your database
5. **Send confirmation** → Customer

### Pre-authorization Flow

1. **Authorize funds** → authOnlyTransaction
2. **Hold authorization** → Store auth code
3. **Capture when ready** → priorAuthCaptureTransaction
4. **Handle settlement** → Monitor batch processing

### Refund Flow

1. **Customer requests refund** → Your application
2. **Validate refund** → Check original transaction
3. **Process refund** → refundTransaction
4. **Update records** → Your database
5. **Notify customer** → Refund confirmation

## Response Handling

### Successful Transaction Response

```json
{
  "transactionResponse": {
    "responseCode": "1",
    "authCode": "AUTH123",
    "avsResultCode": "Y",
    "cvvResultCode": "M",
    "cavvResultCode": "2",
    "transId": "40000000001",
    "refTransID": "ref123456",
    "transHash": "HASH_VALUE",
    "testRequest": "0",
    "accountNumber": "XXXX1111",
    "accountType": "Visa",
    "messages": [
      {
        "code": "1",
        "description": "This transaction has been approved."
      }
    ],
    "transHashSha2": "SHA2_HASH_VALUE",
    "userFields": [
      {
        "name": "favorite_color",
        "value": "blue"
      }
    ]
  },
  "refId": "ref123456",
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

### Failed Transaction Response

```json
{
  "transactionResponse": {
    "responseCode": "2",
    "authCode": "",
    "avsResultCode": "P",
    "cvvResultCode": "",
    "cavvResultCode": "",
    "transId": "0",
    "refTransID": "",
    "transHash": "",
    "testRequest": "0",
    "accountNumber": "XXXX1111",
    "accountType": "Visa",
    "errors": [
      {
        "errorCode": "6",
        "errorText": "The credit card number is invalid."
      }
    ]
  },
  "refId": "ref123456",
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

## Error Handling

### Common Error Codes

| Code | Description | Action |
|------|-------------|---------|
| 1 | Approved | Success |
| 2 | Declined | Show decline message |
| 3 | Error | System error, retry |
| 4 | Held for Review | Manual review needed |

### AVS (Address Verification Service) Codes

| Code | Description |
|------|-------------|
| A | Address matches, ZIP doesn't |
| B | Address info unavailable |
| E | AVS error |
| G | Non-US card, AVS not supported |
| N | No match on address or ZIP |
| P | AVS not applicable |
| R | Retry, system unavailable |
| S | AVS not supported |
| U | Address info unavailable |
| W | ZIP matches, address doesn't |
| X | Address and ZIP match |
| Y | Address and ZIP match |
| Z | ZIP matches, address doesn't |

### CVV Result Codes

| Code | Description |
|------|-------------|
| M | Match |
| N | No match |
| P | Not processed |
| S | Should have been present |
| U | Issuer unable to process |

## Best Practices

### Security
1. **Never store card data** - Use tokenization
2. **Validate all inputs** before sending to API
3. **Use HTTPS** for all communications
4. **Implement PCI compliance** measures

### Performance
1. **Use connection pooling** for HTTP requests
2. **Implement request queuing** for high volume
3. **Cache merchant authentication** tokens
4. **Use async processing** for non-critical operations

### Reliability
1. **Implement retry logic** with exponential backoff
2. **Handle network timeouts** gracefully
3. **Log all transactions** for audit trails
4. **Implement circuit breakers** for API failures

### Monitoring
1. **Track response times** and success rates
2. **Monitor error rates** by type
3. **Set up alerts** for critical failures
4. **Regular health checks** of API connectivity

## Testing

### Test Card Numbers

| Card Type | Number | Description |
|-----------|--------|-------------|
| Visa | 4111111111111111 | Approved |
| Visa | 4000000000000002 | Declined |
| Mastercard | 5555555555554444 | Approved |
| American Express | 378282246310005 | Approved |
| Discover | 6011111111111117 | Approved |

### Test Scenarios

1. **Successful transaction** with valid test card
2. **Declined transaction** with invalid card
3. **AVS failure** with mismatched address
4. **CVV failure** with invalid security code
5. **Network timeout** simulation
6. **Invalid credentials** test

## Next Steps

1. Review [Customer Profiles Guide](03-customer-profiles.md)
2. Learn about [Fraud Management](04-fraud-management.md)
3. Implement [Fault Tolerance Strategies](05-fault-tolerance.md)
4. Optimize for [Low Latency](06-performance-optimization.md)

## Resources

- [Authorize.net Payment Transactions](https://developer.authorize.net/api/reference/index.html#payment-transactions)
- [Test Card Numbers](https://developer.authorize.net/api/reference/index.html#testing-guide)
- [Response Codes](https://developer.authorize.net/api/reference/responseCodes.html)
