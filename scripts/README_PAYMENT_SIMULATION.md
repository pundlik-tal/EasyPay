# EasyPay Payment Gateway - API Simulation Scripts

This directory contains comprehensive simulation scripts for testing all EasyPay payment gateway actions using APIs. These scripts allow you to simulate real-world payment scenarios and test the complete payment gateway functionality.

## 📁 Available Scripts

### 1. `comprehensive_payment_simulation.py`
**Complete payment gateway simulation covering all actions**

- **Purpose**: Comprehensive testing of all payment gateway operations
- **Features**: 
  - Purchase/Payment Creation (multiple scenarios)
  - Cancel Payment operations
  - Refund Payment (full and partial)
  - Subscription/Recurring Billing Management
  - Additional actions (webhooks, status updates, etc.)
  - Error scenarios and edge cases
  - Authentication testing

### 2. `quick_payment_test.py`
**Quick testing script for basic operations**

- **Purpose**: Fast testing of essential payment operations
- **Features**:
  - Health check
  - Create Payment
  - Cancel Payment
  - Refund Payment
  - Create Subscription
  - Cancel Subscription
  - List Payments/Subscriptions

### 3. `webhook_simulation.py`
**Webhook event simulation**

- **Purpose**: Test webhook functionality and event processing
- **Features**:
  - Payment webhook events (created, updated, cancelled, refunded)
  - Subscription webhook events (created, updated, cancelled)
  - Webhook sequence simulation
  - Custom event testing

## 🚀 Quick Start

### Prerequisites

1. **EasyPay API Server Running**
   ```bash
   # Start the EasyPay server
   python src/main.py
   # or
   docker-compose up
   ```

2. **Python Dependencies**
   ```bash
   pip install httpx asyncio
   ```

3. **API Key (Optional)**
   - Get an API key from the EasyPay admin panel
   - Or use without authentication for basic testing

### Basic Usage

#### 1. Quick Test (Recommended for beginners)
```bash
# Test basic functionality
python scripts/quick_payment_test.py

# Test with custom API URL
python scripts/quick_payment_test.py --base-url http://localhost:8000

# Test with API key
python scripts/quick_payment_test.py --api-key your_api_key_here

# Save results to file
python scripts/quick_payment_test.py --output results.json
```

#### 2. Comprehensive Simulation
```bash
# Run full simulation
python scripts/comprehensive_payment_simulation.py

# Run with custom settings
python scripts/comprehensive_payment_simulation.py \
  --base-url http://localhost:8000 \
  --api-key your_api_key_here \
  --output comprehensive_results.json \
  --verbose
```

#### 3. Webhook Testing
```bash
# Test webhook functionality
python scripts/webhook_simulation.py

# Test specific webhook events
python scripts/webhook_simulation.py --events payment.created subscription.created

# Test with custom webhook URL
python scripts/webhook_simulation.py \
  --webhook-url http://localhost:8000/api/v1/webhooks/payments \
  --output webhook_results.json
```

## 📋 Simulated Actions

### 💳 Payment Actions

#### Purchase/Payment Creation
- **Basic Credit Card Payment**: Standard payment processing
- **High-Value Payment**: Large amount transactions
- **International Payment**: Multi-currency support
- **Test Mode**: Safe testing without real money

#### Cancel Payment
- **Customer Request**: Customer-initiated cancellation
- **Business Logic**: System-initiated cancellation
- **Status Validation**: Only cancellable payments can be cancelled

#### Refund Payment
- **Full Refund**: Complete payment refund
- **Partial Refund**: Partial amount refund
- **Multiple Refunds**: Multiple partial refunds up to total amount
- **Refund Tracking**: Complete refund history

### 🔄 Subscription Actions

#### Subscription Creation
- **Monthly Subscription**: Recurring monthly billing
- **Yearly Subscription**: Annual billing with trial period
- **Weekly Subscription**: Short-term recurring billing
- **Trial Periods**: Free trial before billing starts

#### Subscription Management
- **Update Subscription**: Modify amount, interval, or description
- **Cancel Subscription**: Stop recurring billing
- **Resume Subscription**: Reactivate cancelled subscription
- **Payment History**: View all subscription payments

### 📡 Webhook Actions

#### Payment Webhooks
- `payment.created`: New payment created
- `payment.updated`: Payment status or details updated
- `payment.cancelled`: Payment cancelled
- `payment.refunded`: Payment refunded

#### Subscription Webhooks
- `subscription.created`: New subscription created
- `subscription.updated`: Subscription modified
- `subscription.cancelled`: Subscription cancelled

### 🔍 Additional Actions

#### Listing Operations
- **List Payments**: Retrieve all payments with filtering
- **List Subscriptions**: Retrieve all subscriptions
- **Payment Details**: Get specific payment information
- **Subscription Details**: Get specific subscription information

#### Error Scenarios
- **Invalid Data**: Test validation error handling
- **Non-existent Resources**: Test 404 error handling
- **Unauthorized Access**: Test authentication/authorization
- **Rate Limiting**: Test API rate limits

## 🛠️ Configuration Options

### Command Line Arguments

#### Common Arguments
- `--base-url`: Base URL of the EasyPay API (default: http://localhost:8000)
- `--api-key`: API key for authentication
- `--output`: Output file for results (JSON format)
- `--verbose`: Enable verbose logging

#### Webhook-Specific Arguments
- `--webhook-url`: Custom webhook endpoint URL
- `--events`: Specific events to simulate

### Environment Variables
```bash
# Set default values
export EASYPAY_BASE_URL="http://localhost:8000"
export EASYPAY_API_KEY="your_api_key_here"
export EASYPAY_WEBHOOK_URL="http://localhost:8000/api/v1/webhooks/payments"
```

## 📊 Understanding Results

### Success Metrics
- **Success Rate**: Percentage of successful operations
- **Total Tests**: Number of operations attempted
- **Passed Tests**: Number of successful operations
- **Failed Tests**: Number of failed operations

### Sample Output
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "base_url": "http://localhost:8000",
  "test_results": {
    "total_tests": 15,
    "passed": 14,
    "failed": 1,
    "errors": ["Payment Cancellation: Payment not found"]
  },
  "created_payments": [...],
  "created_subscriptions": [...],
  "success_rate": 93.3
}
```

### Exit Codes
- `0`: Success (≥80% success rate)
- `1`: Failure (<80% success rate)
- `130`: Interrupted by user (Ctrl+C)

## 🔧 Advanced Usage

### Custom Test Scenarios

#### 1. Modify Payment Data
```python
# Edit the script to customize payment data
payment_data = {
    "amount": "99.99",
    "currency": "EUR",
    "payment_method": "credit_card",
    "customer_id": "custom_customer_123",
    "customer_email": "custom@example.com",
    "customer_name": "Custom Customer",
    "card_token": "tok_custom_token",
    "description": "Custom test payment",
    "metadata": {
        "custom_field": "custom_value",
        "test_scenario": "custom_test"
    },
    "is_test": True
}
```

#### 2. Add Custom Webhook Events
```python
# Add custom webhook templates
custom_template = {
    "event_type": "custom.event",
    "event_id": "evt_custom_{timestamp}",
    "data": {
        "custom_field": "custom_value",
        "timestamp": "{timestamp}"
    }
}
```

### Integration with CI/CD

#### GitHub Actions Example
```yaml
name: Payment Gateway Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install httpx
      - name: Start EasyPay
        run: docker-compose up -d
      - name: Run Payment Tests
        run: python scripts/quick_payment_test.py --output test_results.json
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_results.json
```

### Monitoring and Alerting

#### Health Check Integration
```bash
# Add to cron for regular health checks
*/5 * * * * /usr/bin/python3 /path/to/scripts/quick_payment_test.py --base-url https://api.easypay.com
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Connection Errors
```
❌ Connection failed: Connection refused
```
**Solution**: Ensure EasyPay server is running on the specified URL

#### 2. Authentication Errors
```
❌ Authentication failed: 401 Unauthorized
```
**Solution**: Check API key or disable authentication for testing

#### 3. Validation Errors
```
❌ Payment creation failed: 400 Bad Request
```
**Solution**: Check payment data format and required fields

#### 4. Webhook Errors
```
❌ Webhook failed: 404 Not Found
```
**Solution**: Verify webhook endpoint URL is correct

### Debug Mode
```bash
# Enable verbose logging for debugging
python scripts/quick_payment_test.py --verbose

# Check server logs
docker-compose logs -f easypay
```

### Performance Issues
- **Slow Responses**: Check server performance and database connections
- **Timeout Errors**: Increase timeout values in the scripts
- **Rate Limiting**: Add delays between requests

## 📚 API Reference

### Payment Endpoints
- `POST /api/v1/payments` - Create payment
- `GET /api/v1/payments/{id}` - Get payment
- `GET /api/v1/payments` - List payments
- `PUT /api/v1/payments/{id}` - Update payment
- `POST /api/v1/payments/{id}/refund` - Refund payment
- `POST /api/v1/payments/{id}/cancel` - Cancel payment

### Subscription Endpoints
- `POST /api/v1/subscriptions` - Create subscription
- `GET /api/v1/subscriptions/{id}` - Get subscription
- `GET /api/v1/subscriptions` - List subscriptions
- `PUT /api/v1/subscriptions/{id}` - Update subscription
- `POST /api/v1/subscriptions/{id}/cancel` - Cancel subscription
- `POST /api/v1/subscriptions/{id}/resume` - Resume subscription

### Webhook Endpoints
- `POST /api/v1/webhooks/payments` - Receive payment webhooks
- `POST /api/v1/webhooks/subscriptions` - Receive subscription webhooks

## 🤝 Contributing

### Adding New Test Scenarios
1. Fork the repository
2. Create a new test scenario in the appropriate script
3. Add documentation for the new scenario
4. Submit a pull request

### Reporting Issues
1. Check existing issues first
2. Provide detailed error logs
3. Include system information
4. Provide steps to reproduce

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the main EasyPay documentation
- **Issues**: Report issues on GitHub
- **Discussions**: Join community discussions
- **Email**: Contact support@easypay.com

---

**Happy Testing! 🎉**

These simulation scripts provide comprehensive testing capabilities for the EasyPay payment gateway. Use them to ensure your payment processing is working correctly and to validate new features before deployment.
