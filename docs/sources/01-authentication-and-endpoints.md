# Authorize.net API Authentication & Endpoints Guide

## Overview

Authorize.net provides a robust payment processing API that supports both XML and JSON formats. This guide covers everything you need to know about authentication, endpoints, and basic API structure for building a fault-tolerant payment gateway.

## Table of Contents
1. [API Endpoints](#api-endpoints)
2. [Authentication](#authentication)
3. [Request Format](#request-format)
4. [Response Format](#response-format)
5. [Testing Your Setup](#testing-your-setup)
6. [Best Practices](#best-practices)

## API Endpoints

### Production vs Sandbox

**Sandbox Endpoint (Testing):**
```
https://apitest.authorize.net/xml/v1/request.api
```

**Production Endpoint (Live):**
```
https://api.authorize.net/xml/v1/request.api
```

### Important Notes
- All requests use **HTTP POST** method
- Content-Type for XML: `text/xml`
- Content-Type for JSON: `application/json`
- API Schema: `https://api.authorize.net/xml/v1/schema/AnetApiSchema.xsd`

## Authentication

### Required Credentials

You need two pieces of information to authenticate with Authorize.net:

1. **API Login ID** (merchant's unique identifier)
   - Maximum 20 characters
   - Found in your Merchant Interface
   - Must be stored securely

2. **Transaction Key** (merchant's unique transaction key)
   - Maximum 16 characters
   - Found in your Merchant Interface
   - Must be stored securely

### Authentication Structure

```json
{
  "merchantAuthentication": {
    "name": "YOUR_API_LOGIN_ID",
    "transactionKey": "YOUR_TRANSACTION_KEY"
  }
}
```

```xml
<merchantAuthentication>
    <name>YOUR_API_LOGIN_ID</name>
    <transactionKey>YOUR_TRANSACTION_KEY</transactionKey>
</merchantAuthentication>
```

## Request Format

### JSON Format
- While Authorize.net supports JSON, it's actually translated to XML internally
- **Important**: JSON elements must be in the correct order (unlike typical JSON)
- Consider using Authorize.net SDKs for seamless integration

### XML Format
- Native format for Authorize.net API
- Requires strict element ordering
- More reliable for complex transactions

### Basic Request Structure

```json
{
  "authenticateTestRequest": {
    "merchantAuthentication": {
      "name": "API_LOGIN_ID",
      "transactionKey": "API_TRANSACTION_KEY"
    },
    "refId": "optional-reference-id"
  }
}
```

## Response Format

### Standard Response Structure

```json
{
  "messages": {
    "resultCode": "Ok",
    "message": [
      {
        "code": "I00001",
        "text": "Successful."
      }
    ]
  },
  "refId": "your-reference-id"
}
```

### Response Codes

- **resultCode**: Either "Ok" or "Error"
- **code**: Up to 6 characters
  - First character: "I" for informational, "E" for error
  - Example: "I00001" (success) or "E00001" (error)
- **text**: Human-readable explanation
- **refId**: Your reference ID (if provided in request)

## Testing Your Setup

### Authentication Test Request

Use this to verify your credentials work:

```json
{
  "authenticateTestRequest": {
    "merchantAuthentication": {
      "name": "YOUR_API_LOGIN_ID",
      "transactionKey": "YOUR_TRANSACTION_KEY"
    }
  }
}
```

### Expected Success Response

```json
{
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

### Security
1. **Never expose credentials** in client-side code
2. **Store credentials securely** using environment variables or secure vaults
3. **Use HTTPS** for all API communications
4. **Implement proper logging** without exposing sensitive data

### Reliability
1. **Always include refId** for tracking requests
2. **Implement retry logic** for network failures
3. **Handle timeouts** appropriately
4. **Validate responses** before processing

### Performance
1. **Use connection pooling** for HTTP requests
2. **Implement caching** where appropriate
3. **Monitor API response times**
4. **Use async/await** patterns for non-blocking operations

### Error Handling
1. **Check resultCode** first in every response
2. **Log error codes** for debugging
3. **Implement fallback mechanisms** for critical failures
4. **Provide user-friendly error messages**

## Common Issues and Solutions

### Issue: Authentication Failed
- **Cause**: Invalid API Login ID or Transaction Key
- **Solution**: Verify credentials in Merchant Interface

### Issue: Invalid Request Format
- **Cause**: Incorrect JSON element ordering
- **Solution**: Use XML format or Authorize.net SDKs

### Issue: Network Timeouts
- **Cause**: Slow network or server issues
- **Solution**: Implement retry logic with exponential backoff

### Issue: Rate Limiting
- **Cause**: Too many requests per second
- **Solution**: Implement request throttling and queuing

## Next Steps

After setting up authentication:
1. Review [Payment Transactions Guide](02-payment-transactions.md)
2. Learn about [Customer Profiles](03-customer-profiles.md)
3. Implement [Fault Tolerance Strategies](04-fault-tolerance.md)
4. Optimize for [Low Latency](05-performance-optimization.md)

## Resources

- [Authorize.net Developer Center](https://developer.authorize.net/)
- [API Reference](https://developer.authorize.net/api/reference/index.html)
- [Response Code Tool](https://developer.authorize.net/api/reference/responseCodes.html)
- [SDKs on GitHub](https://github.com/AuthorizeNet)
