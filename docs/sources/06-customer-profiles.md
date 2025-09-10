# Authorize.net Customer Profiles Guide

## Overview

Customer Profiles allow you to store customer information and payment methods securely for future use. This eliminates the need to collect payment information repeatedly and improves the checkout experience.

## Table of Contents
1. [Customer Profile Management](#customer-profile-management)
2. [Payment Profile Management](#payment-profile-management)
3. [Shipping Address Management](#shipping-address-management)
4. [API Endpoints](#api-endpoints)
5. [Best Practices](#best-practices)
6. [Security Considerations](#security-considerations)

## Customer Profile Management

### Create Customer Profile

**Purpose**: Store customer information for future transactions.

**Request Structure**:
```json
{
  "createCustomerProfileRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "profile": {
      "merchantCustomerId": "CUST_123456",
      "description": "Customer profile for John Doe",
      "email": "john.doe@example.com",
      "paymentProfiles": {
        "customerType": "individual",
        "billTo": {
          "firstName": "John",
          "lastName": "Doe",
          "address": "123 Main St",
          "city": "Anytown",
          "state": "CA",
          "zip": "12345",
          "country": "US",
          "phoneNumber": "555-123-4567"
        },
        "payment": {
          "creditCard": {
            "cardNumber": "4111111111111111",
            "expirationDate": "1225",
            "cardCode": "123"
          }
        }
      },
      "shipToList": {
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

**Key Fields**:
- `merchantCustomerId`: Your unique customer identifier
- `description`: Customer profile description
- `email`: Customer email address
- `paymentProfiles`: Payment method information
- `shipToList`: Shipping address information

### Get Customer Profile

**Purpose**: Retrieve customer profile information.

**Request Structure**:
```json
{
  "getCustomerProfileRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID"
  }
}
```

### Update Customer Profile

**Purpose**: Update customer profile information.

**Request Structure**:
```json
{
  "updateCustomerProfileRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "profile": {
      "customerProfileId": "CUSTOMER_PROFILE_ID",
      "merchantCustomerId": "CUST_123456",
      "description": "Updated customer profile",
      "email": "john.doe@example.com"
    }
  }
}
```

### Delete Customer Profile

**Purpose**: Remove customer profile and all associated data.

**Request Structure**:
```json
{
  "deleteCustomerProfileRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID"
  }
}
```

## Payment Profile Management

### Create Payment Profile

**Purpose**: Add a new payment method to existing customer profile.

**Request Structure**:
```json
{
  "createCustomerPaymentProfileRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID",
    "paymentProfile": {
      "customerType": "individual",
      "billTo": {
        "firstName": "John",
        "lastName": "Doe",
        "address": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345",
        "country": "US"
      },
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

### Get Payment Profile

**Purpose**: Retrieve specific payment profile information.

**Request Structure**:
```json
{
  "getCustomerPaymentProfileRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID",
    "customerPaymentProfileId": "PAYMENT_PROFILE_ID"
  }
}
```

### Update Payment Profile

**Purpose**: Update existing payment profile information.

**Request Structure**:
```json
{
  "updateCustomerPaymentProfileRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID",
    "paymentProfile": {
      "customerPaymentProfileId": "PAYMENT_PROFILE_ID",
      "billTo": {
        "firstName": "John",
        "lastName": "Doe",
        "address": "456 Oak Ave",
        "city": "Newtown",
        "state": "NY",
        "zip": "67890",
        "country": "US"
      }
    }
  }
}
```

### Delete Payment Profile

**Purpose**: Remove payment profile from customer profile.

**Request Structure**:
```json
{
  "deleteCustomerPaymentProfileRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID",
    "customerPaymentProfileId": "PAYMENT_PROFILE_ID"
  }
}
```

## Shipping Address Management

### Create Shipping Address

**Purpose**: Add shipping address to customer profile.

**Request Structure**:
```json
{
  "createCustomerShippingAddressRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID",
    "address": {
      "firstName": "John",
      "lastName": "Doe",
      "company": "Acme Corp",
      "address": "789 Pine St",
      "city": "Springfield",
      "state": "IL",
      "zip": "62701",
      "country": "US",
      "phoneNumber": "555-987-6543"
    }
  }
}
```

### Get Shipping Address

**Purpose**: Retrieve shipping address information.

**Request Structure**:
```json
{
  "getCustomerShippingAddressRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID",
    "customerAddressId": "ADDRESS_ID"
  }
}
```

### Update Shipping Address

**Purpose**: Update existing shipping address.

**Request Structure**:
```json
{
  "updateCustomerShippingAddressRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID",
    "address": {
      "customerAddressId": "ADDRESS_ID",
      "firstName": "John",
      "lastName": "Doe",
      "address": "789 Pine St",
      "city": "Springfield",
      "state": "IL",
      "zip": "62701",
      "country": "US"
    }
  }
}
```

### Delete Shipping Address

**Purpose**: Remove shipping address from customer profile.

**Request Structure**:
```json
{
  "deleteCustomerShippingAddressRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "customerProfileId": "CUSTOMER_PROFILE_ID",
    "customerAddressId": "ADDRESS_ID"
  }
}
```

## API Endpoints

### Customer Profile Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/customers` | Create customer profile |
| GET | `/api/v1/customers/{id}` | Get customer profile |
| PUT | `/api/v1/customers/{id}` | Update customer profile |
| DELETE | `/api/v1/customers/{id}` | Delete customer profile |

### Payment Profile Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/customers/{id}/payment-methods` | Add payment method |
| GET | `/api/v1/customers/{id}/payment-methods` | List payment methods |
| GET | `/api/v1/customers/{id}/payment-methods/{pm_id}` | Get payment method |
| PUT | `/api/v1/customers/{id}/payment-methods/{pm_id}` | Update payment method |
| DELETE | `/api/v1/customers/{id}/payment-methods/{pm_id}` | Delete payment method |

### Shipping Address Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/customers/{id}/addresses` | Add shipping address |
| GET | `/api/v1/customers/{id}/addresses` | List shipping addresses |
| GET | `/api/v1/customers/{id}/addresses/{addr_id}` | Get shipping address |
| PUT | `/api/v1/customers/{id}/addresses/{addr_id}` | Update shipping address |
| DELETE | `/api/v1/customers/{id}/addresses/{addr_id}` | Delete shipping address |

## Response Examples

### Successful Customer Profile Creation

```json
{
  "customerProfileId": "12345678",
  "customerPaymentProfileIdList": ["87654321"],
  "customerShippingAddressIdList": ["11223344"],
  "validationDirectResponseList": ["1,1,1,This transaction has been approved."],
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

### Customer Profile Information

```json
{
  "profile": {
    "customerProfileId": "12345678",
    "merchantCustomerId": "CUST_123456",
    "description": "Customer profile for John Doe",
    "email": "john.doe@example.com",
    "paymentProfiles": [
      {
        "customerPaymentProfileId": "87654321",
        "customerType": "individual",
        "billTo": {
          "firstName": "John",
          "lastName": "Doe",
          "address": "123 Main St",
          "city": "Anytown",
          "state": "CA",
          "zip": "12345",
          "country": "US"
        },
        "payment": {
          "creditCard": {
            "cardNumber": "XXXX1111",
            "expirationDate": "XXXX"
          }
        }
      }
    ],
    "shipToList": [
      {
        "customerAddressId": "11223344",
        "firstName": "John",
        "lastName": "Doe",
        "address": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345",
        "country": "US"
      }
    ]
  },
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

## Best Practices

### Data Management
1. **Use unique customer IDs** - Generate unique identifiers for each customer
2. **Validate input data** - Ensure all required fields are present and valid
3. **Handle duplicates** - Check for existing profiles before creating new ones
4. **Regular cleanup** - Remove inactive or outdated profiles

### Security
1. **Never store card data** - Use Authorize.net's secure storage
2. **Encrypt sensitive data** - Use encryption for any stored sensitive information
3. **Access control** - Implement proper authentication and authorization
4. **Audit logging** - Log all profile access and modifications

### Performance
1. **Cache frequently accessed profiles** - Use Redis for profile caching
2. **Batch operations** - Group multiple operations when possible
3. **Pagination** - Implement pagination for large profile lists
4. **Async processing** - Use async operations for non-critical updates

### Error Handling
1. **Validate responses** - Check for errors in all API responses
2. **Retry logic** - Implement retry for transient failures
3. **Fallback mechanisms** - Provide alternatives when profiles are unavailable
4. **User feedback** - Provide clear error messages to users

## Security Considerations

### PCI Compliance
- **Never store card data** - Authorize.net handles secure storage
- **Use tokenization** - Store only payment tokens, not actual card data
- **Secure transmission** - Use HTTPS for all API communications
- **Access logging** - Log all access to customer profiles

### Data Protection
- **Encryption at rest** - Encrypt stored customer data
- **Encryption in transit** - Use TLS 1.3 for all communications
- **Data minimization** - Store only necessary customer information
- **Retention policies** - Implement data retention and deletion policies

### Access Control
- **Authentication** - Verify user identity before profile access
- **Authorization** - Check permissions for profile operations
- **Session management** - Implement secure session handling
- **API key security** - Protect API keys and credentials

## Integration Examples

### Python Integration

```python
import requests
import json

class CustomerProfileManager:
    def __init__(self, api_login_id, transaction_key):
        self.api_login_id = api_login_id
        self.transaction_key = transaction_key
        self.base_url = "https://apitest.authorize.net/xml/v1/request.api"
    
    def create_customer_profile(self, customer_data):
        """Create a new customer profile."""
        request_data = {
            "createCustomerProfileRequest": {
                "merchantAuthentication": {
                    "name": self.api_login_id,
                    "transactionKey": self.transaction_key
                },
                "profile": customer_data
            }
        }
        
        response = requests.post(
            self.base_url,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()
    
    def get_customer_profile(self, profile_id):
        """Retrieve customer profile information."""
        request_data = {
            "getCustomerProfileRequest": {
                "merchantAuthentication": {
                    "name": self.api_login_id,
                    "transactionKey": self.transaction_key
                },
                "customerProfileId": profile_id
            }
        }
        
        response = requests.post(
            self.base_url,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        return response.json()
```

### JavaScript Integration

```javascript
class CustomerProfileManager {
    constructor(apiLoginId, transactionKey) {
        this.apiLoginId = apiLoginId;
        this.transactionKey = transactionKey;
        this.baseUrl = "https://apitest.authorize.net/xml/v1/request.api";
    }
    
    async createCustomerProfile(customerData) {
        const requestData = {
            createCustomerProfileRequest: {
                merchantAuthentication: {
                    name: this.apiLoginId,
                    transactionKey: this.transactionKey
                },
                profile: customerData
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
    
    async getCustomerProfile(profileId) {
        const requestData = {
            getCustomerProfileRequest: {
                merchantAuthentication: {
                    name: this.apiLoginId,
                    transactionKey: this.transactionKey
                },
                customerProfileId: profileId
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

## Common Issues and Solutions

### Issue: Duplicate Customer Profile
- **Cause**: Customer already exists with same merchant ID
- **Solution**: Check for existing profile before creating new one

### Issue: Invalid Payment Profile
- **Cause**: Card information is invalid or expired
- **Solution**: Validate card data before creating payment profile

### Issue: Profile Not Found
- **Cause**: Profile ID doesn't exist or has been deleted
- **Solution**: Check profile ID and handle gracefully

### Issue: Permission Denied
- **Cause**: Insufficient permissions for profile operation
- **Solution**: Verify API credentials and permissions

## Next Steps

1. Review [Fraud Management Guide](07-fraud-management.md)
2. Learn about [Fault Tolerance Strategies](08-fault-tolerance.md)
3. Implement [Performance Optimization](09-performance-optimization.md)
4. Create [Integration Examples](10-integration-examples.md)

## Resources

- [Authorize.net Customer Profiles](https://developer.authorize.net/api/reference/index.html#customer-profiles)
- [API Reference](https://developer.authorize.net/api/reference/index.html)
- [Test Data](https://developer.authorize.net/api/reference/index.html#testing-guide)
