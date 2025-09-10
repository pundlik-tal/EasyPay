# Authorize.net Integration

This module provides a comprehensive integration with the Authorize.net payment processing API for the EasyPay payment gateway.

## Features

- **Complete Transaction Support**: All major Authorize.net transaction types
- **Async/Await Support**: Built with modern Python async patterns
- **Comprehensive Error Handling**: Detailed exception handling with proper error codes
- **Data Validation**: Pydantic models with built-in validation
- **Testing**: Complete unit tests and integration test suite
- **Configuration**: Environment-based configuration management

## Supported Transaction Types

1. **Charge Credit Card** (`authCaptureTransaction`) - Authorize and capture in one step
2. **Authorize Only** (`authOnlyTransaction`) - Authorize without capturing funds
3. **Capture** (`priorAuthCaptureTransaction`) - Capture previously authorized funds
4. **Refund** (`refundTransaction`) - Refund a completed transaction
5. **Void** (`voidTransaction`) - Cancel a transaction before settlement

## Quick Start

### 1. Configuration

Set up your environment variables:

```bash
# Required
AUTHORIZE_NET_API_LOGIN_ID=your_api_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_transaction_key

# Optional
AUTHORIZE_NET_SANDBOX=true  # Use sandbox environment
AUTHORIZE_NET_API_URL=https://apitest.authorize.net/xml/v1/request.api
```

### 2. Basic Usage

```python
import asyncio
from src.integrations.authorize_net import AuthorizeNetClient, CreditCard, BillingAddress

async def process_payment():
    # Create client
    async with AuthorizeNetClient() as client:
        # Test authentication
        auth_success = await client.test_authentication()
        print(f"Authentication: {'Success' if auth_success else 'Failed'}")
        
        # Create payment data
        credit_card = CreditCard(
            card_number="4111111111111111",  # Test Visa card
            expiration_date="1225",  # December 2025
            card_code="123"
        )
        
        billing_address = BillingAddress(
            first_name="John",
            last_name="Doe",
            address="123 Main St",
            city="Anytown",
            state="CA",
            zip="12345",
            country="US"
        )
        
        # Charge credit card
        result = await client.charge_credit_card(
            amount="10.00",
            credit_card=credit_card,
            billing_address=billing_address,
            order_info={"invoiceNumber": "INV-001", "description": "Test payment"}
        )
        
        print(f"Transaction ID: {result.transaction_id}")
        print(f"Status: {result.status}")
        print(f"Response: {result.response_text}")

# Run the example
asyncio.run(process_payment())
```

### 3. Two-Step Authorization

```python
async def two_step_payment():
    async with AuthorizeNetClient() as client:
        # Step 1: Authorize only
        auth_result = await client.authorize_only(
            amount="10.00",
            credit_card=credit_card,
            billing_address=billing_address
        )
        
        if auth_result.status == TransactionStatus.CAPTURED:
            # Step 2: Capture the funds
            capture_result = await client.capture(
                transaction_id=auth_result.transaction_id,
                amount="10.00"
            )
            print(f"Capture successful: {capture_result.transaction_id}")
```

### 4. Refunds and Voids

```python
async def refund_and_void():
    async with AuthorizeNetClient() as client:
        # Process a payment first
        payment_result = await client.charge_credit_card(...)
        
        if payment_result.status == TransactionStatus.CAPTURED:
            # Refund the payment
            refund_result = await client.refund(
                transaction_id=payment_result.transaction_id,
                amount="5.00",  # Partial refund
                credit_card=credit_card
            )
            
            # Or void the transaction (before settlement)
            void_result = await client.void_transaction(
                transaction_id=payment_result.transaction_id
            )
```

## Error Handling

The integration provides comprehensive error handling with specific exception types:

```python
from src.integrations.authorize_net.exceptions import (
    AuthorizeNetError,
    AuthorizeNetAuthenticationError,
    AuthorizeNetTransactionError,
    AuthorizeNetNetworkError
)

try:
    result = await client.charge_credit_card(...)
except AuthorizeNetAuthenticationError as e:
    print(f"Authentication failed: {e.message}")
except AuthorizeNetTransactionError as e:
    print(f"Transaction failed: {e.message}")
    print(f"Response code: {e.details.get('response_code')}")
except AuthorizeNetNetworkError as e:
    print(f"Network error: {e.message}")
except AuthorizeNetError as e:
    print(f"General error: {e.message}")
```

## Testing

### Unit Tests

Run the unit tests:

```bash
pytest src/integrations/authorize_net/test_client.py -v
```

### Integration Tests

Run the integration test script:

```bash
python test_authorize_net.py
```

Or run directly:

```bash
python -m src.integrations.authorize_net.integration_test
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTHORIZE_NET_API_LOGIN_ID` | Your Authorize.net API Login ID | Required |
| `AUTHORIZE_NET_TRANSACTION_KEY` | Your Authorize.net Transaction Key | Required |
| `AUTHORIZE_NET_SANDBOX` | Use sandbox environment | `true` |
| `AUTHORIZE_NET_API_URL` | Custom API URL | Auto-detected |

### Programmatic Configuration

```python
from src.integrations.authorize_net.models import AuthorizeNetCredentials

credentials = AuthorizeNetCredentials(
    api_login_id="your_login_id",
    transaction_key="your_transaction_key",
    sandbox=True
)

client = AuthorizeNetClient(credentials)
```

## Test Cards

For testing in sandbox mode, use these test card numbers:

| Card Number | Card Type | Description |
|-------------|-----------|-------------|
| `4111111111111111` | Visa | Approved |
| `4007000000027` | Visa | Declined |
| `5424000000000015` | MasterCard | Approved |
| `370000000000002` | American Express | Approved |

## Response Codes

Common Authorize.net response codes:

| Code | Description |
|------|-------------|
| `1` | Approved |
| `2` | Declined |
| `3` | Error |
| `4` | Held for Review |

## Best Practices

1. **Always test authentication** before processing payments
2. **Use proper error handling** for all API calls
3. **Validate input data** using the provided Pydantic models
4. **Log all transactions** for audit purposes
5. **Use async context managers** to ensure proper resource cleanup
6. **Test with sandbox** before going to production

## Security Considerations

1. **Never log sensitive data** (card numbers, CVV codes)
2. **Use HTTPS** for all communications
3. **Store credentials securely** using environment variables
4. **Implement proper access controls** for your API endpoints
5. **Follow PCI DSS guidelines** for handling card data

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify your API Login ID and Transaction Key
2. **Network Errors**: Check your internet connection and firewall settings
3. **Validation Errors**: Ensure all required fields are provided and valid
4. **Transaction Declines**: Check card details and available funds

### Debug Mode

Enable debug logging to see detailed request/response information:

```python
import logging
logging.getLogger("src.integrations.authorize_net").setLevel(logging.DEBUG)
```

## Support

For issues with this integration, please check:

1. The unit tests for usage examples
2. The Authorize.net API documentation
3. The integration test script for working examples

For Authorize.net API issues, consult the [Authorize.net Developer Center](https://developer.authorize.net/).
