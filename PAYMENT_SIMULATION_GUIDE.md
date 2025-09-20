# EasyPay Payment Gateway - Complete API Simulation Guide

## 🎯 Overview

I've created a comprehensive set of simulation scripts that allow you to test **ALL** payment gateway actions using APIs. These scripts simulate real-world payment scenarios and test the complete functionality of the EasyPay payment gateway.

## 📁 Created Scripts

### 1. **`scripts/comprehensive_payment_simulation.py`** 
**Complete payment gateway simulation covering all actions**

**Features:**
- ✅ **Purchase/Payment Creation** (multiple scenarios)
- ✅ **Cancel Payment** operations  
- ✅ **Refund Payment** (full and partial)
- ✅ **Subscription/Recurring Billing** Management
- ✅ **Additional Actions** (webhooks, status updates, etc.)
- ✅ **Error Scenarios** and edge cases
- ✅ **Authentication** testing

### 2. **`scripts/quick_payment_test.py`**
**Quick testing script for basic operations**

**Features:**
- ✅ Health check
- ✅ Create Payment
- ✅ Cancel Payment  
- ✅ Refund Payment
- ✅ Create Subscription
- ✅ Cancel Subscription
- ✅ List Payments/Subscriptions

### 3. **`scripts/webhook_simulation.py`**
**Webhook event simulation**

**Features:**
- ✅ Payment webhook events (created, updated, cancelled, refunded)
- ✅ Subscription webhook events (created, updated, cancelled)
- ✅ Webhook sequence simulation
- ✅ Custom event testing

### 4. **`scripts/run_all_simulations.py`**
**Demo script to run all simulations**

**Features:**
- ✅ Runs all simulation scripts in sequence
- ✅ Provides comprehensive overview
- ✅ Generates combined results

## 🚀 Quick Start Guide

### Prerequisites
1. **Start EasyPay Server:**
   ```bash
   python src/main.py
   # OR
   docker-compose up
   ```

2. **Install Dependencies:**
   ```bash
   pip install httpx asyncio
   ```

### Basic Usage Examples

#### 1. **Quick Test (Recommended for beginners)**
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

#### 2. **Comprehensive Simulation**
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

#### 3. **Webhook Testing**
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

#### 4. **Run All Simulations**
```bash
# Run all simulations
python scripts/run_all_simulations.py

# Run only quick test
python scripts/run_all_simulations.py --quick-only

# Run only webhook simulation
python scripts/run_all_simulations.py --webhook-only
```

## 📋 Simulated Actions

### 💳 **Payment Actions**

#### **Purchase/Payment Creation**
- **Basic Credit Card Payment**: Standard payment processing
- **High-Value Payment**: Large amount transactions ($999.99)
- **International Payment**: Multi-currency support (EUR, USD)
- **Test Mode**: Safe testing without real money

#### **Cancel Payment**
- **Customer Request**: Customer-initiated cancellation
- **Business Logic**: System-initiated cancellation
- **Status Validation**: Only cancellable payments can be cancelled

#### **Refund Payment**
- **Full Refund**: Complete payment refund
- **Partial Refund**: Partial amount refund ($10.00)
- **Multiple Refunds**: Multiple partial refunds up to total amount
- **Refund Tracking**: Complete refund history

### 🔄 **Subscription Actions**

#### **Subscription Creation**
- **Monthly Subscription**: Recurring monthly billing ($29.99)
- **Yearly Subscription**: Annual billing with trial period ($299.99)
- **Weekly Subscription**: Short-term recurring billing ($9.99)
- **Trial Periods**: Free trial before billing starts (14 days)

#### **Subscription Management**
- **Update Subscription**: Modify amount, interval, or description
- **Cancel Subscription**: Stop recurring billing
- **Resume Subscription**: Reactivate cancelled subscription
- **Payment History**: View all subscription payments

### 📡 **Webhook Actions**

#### **Payment Webhooks**
- `payment.created`: New payment created
- `payment.updated`: Payment status or details updated
- `payment.cancelled`: Payment cancelled
- `payment.refunded`: Payment refunded

#### **Subscription Webhooks**
- `subscription.created`: New subscription created
- `subscription.updated`: Subscription modified
- `subscription.cancelled`: Subscription cancelled

### 🔍 **Additional Actions**

#### **Listing Operations**
- **List Payments**: Retrieve all payments with filtering
- **List Subscriptions**: Retrieve all subscriptions
- **Payment Details**: Get specific payment information
- **Subscription Details**: Get specific subscription information

#### **Error Scenarios**
- **Invalid Data**: Test validation error handling
- **Non-existent Resources**: Test 404 error handling
- **Unauthorized Access**: Test authentication/authorization
- **Rate Limiting**: Test API rate limits

## 📊 **Understanding Results**

### **Success Metrics**
- **Success Rate**: Percentage of successful operations
- **Total Tests**: Number of operations attempted
- **Passed Tests**: Number of successful operations
- **Failed Tests**: Number of failed operations

### **Sample Output**
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

### **Exit Codes**
- `0`: Success (≥80% success rate)
- `1`: Failure (<80% success rate)
- `130`: Interrupted by user (Ctrl+C)

## 🛠️ **Configuration Options**

### **Command Line Arguments**
- `--base-url`: Base URL of the EasyPay API (default: http://localhost:8000)
- `--api-key`: API key for authentication
- `--output`: Output file for results (JSON format)
- `--verbose`: Enable verbose logging

### **Environment Variables**
```bash
export EASYPAY_BASE_URL="http://localhost:8000"
export EASYPAY_API_KEY="your_api_key_here"
export EASYPAY_WEBHOOK_URL="http://localhost:8000/api/v1/webhooks/payments"
```

## 🎯 **Demo Scenarios**

### **Scenario 1: Basic Payment Flow**
```bash
# 1. Create a payment
python scripts/quick_payment_test.py

# 2. Check the results
cat quick_test_results.json
```

### **Scenario 2: Complete Payment Lifecycle**
```bash
# 1. Run comprehensive simulation
python scripts/comprehensive_payment_simulation.py --verbose

# 2. Review all operations
cat comprehensive_results.json
```

### **Scenario 3: Webhook Testing**
```bash
# 1. Test webhook events
python scripts/webhook_simulation.py --events payment.created payment.refunded

# 2. Check webhook results
cat webhook_results.json
```

### **Scenario 4: Full System Test**
```bash
# 1. Run all simulations
python scripts/run_all_simulations.py --verbose

# 2. Review comprehensive results
cat all_simulation_results.json
```

## 🔧 **Advanced Usage**

### **Custom Test Scenarios**
You can modify the scripts to test custom scenarios:

```python
# Example: Custom payment data
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

### **Integration with CI/CD**
```yaml
# GitHub Actions example
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

## 🐛 **Troubleshooting**

### **Common Issues**

#### **1. Connection Errors**
```
❌ Connection failed: Connection refused
```
**Solution**: Ensure EasyPay server is running on the specified URL

#### **2. Authentication Errors**
```
❌ Authentication failed: 401 Unauthorized
```
**Solution**: Check API key or disable authentication for testing

#### **3. Validation Errors**
```
❌ Payment creation failed: 400 Bad Request
```
**Solution**: Check payment data format and required fields

#### **4. Webhook Errors**
```
❌ Webhook failed: 404 Not Found
```
**Solution**: Verify webhook endpoint URL is correct

### **Debug Mode**
```bash
# Enable verbose logging for debugging
python scripts/quick_payment_test.py --verbose

# Check server logs
docker-compose logs -f easypay
```

## 📚 **API Reference**

### **Payment Endpoints**
- `POST /api/v1/payments` - Create payment
- `GET /api/v1/payments/{id}` - Get payment
- `GET /api/v1/payments` - List payments
- `PUT /api/v1/payments/{id}` - Update payment
- `POST /api/v1/payments/{id}/refund` - Refund payment
- `POST /api/v1/payments/{id}/cancel` - Cancel payment

### **Subscription Endpoints**
- `POST /api/v1/subscriptions` - Create subscription
- `GET /api/v1/subscriptions/{id}` - Get subscription
- `GET /api/v1/subscriptions` - List subscriptions
- `PUT /api/v1/subscriptions/{id}` - Update subscription
- `POST /api/v1/subscriptions/{id}/cancel` - Cancel subscription
- `POST /api/v1/subscriptions/{id}/resume` - Resume subscription

### **Webhook Endpoints**
- `POST /api/v1/webhooks/payments` - Receive payment webhooks
- `POST /api/v1/webhooks/subscriptions` - Receive subscription webhooks

## 🎉 **Summary**

I've created a **complete payment gateway simulation suite** that covers:

✅ **Purchase/Payment Creation** - Multiple scenarios with different payment methods and amounts  
✅ **Cancel Payment** - Test cancellation logic and status validation  
✅ **Refund Payment** - Full and partial refunds with proper tracking  
✅ **Subscription/Recurring Billing** - Complete subscription lifecycle management  
✅ **Additional Actions** - Webhooks, listing, error handling, and edge cases  
✅ **Authentication** - API key and JWT token testing  
✅ **Error Scenarios** - Comprehensive error handling and validation testing  

### **Key Features:**
- 🚀 **Easy to use** - Simple command-line interface
- 🔧 **Highly configurable** - Customizable URLs, API keys, and test scenarios
- 📊 **Comprehensive reporting** - Detailed results with success rates and error details
- 🎯 **Multiple test levels** - From quick tests to full comprehensive simulations
- 📡 **Webhook testing** - Complete webhook event simulation
- 🐛 **Error handling** - Robust error scenarios and edge case testing

### **Ready to Use:**
All scripts are **executable** and **ready to run**. Simply start your EasyPay server and run any of the simulation scripts to test your payment gateway functionality!

---

**Happy Testing! 🎉**

These simulation scripts provide comprehensive testing capabilities for the EasyPay payment gateway. Use them to ensure your payment processing is working correctly and to validate new features before deployment.
