# EasyPay Payment Gateway - Testing Scripts

This directory contains comprehensive testing scripts for the EasyPay Payment Gateway system. These scripts provide end-to-end testing capabilities for all payment gateway APIs, including real-time testing with Authorize.net sandbox integration.

## 📁 Scripts Overview

| Script | Purpose | Duration | Description |
|--------|---------|----------|-------------|
| `setup_testing_environment.py` | Setup | 2-5 min | Sets up testing environment and checks prerequisites |
| `run_all_tests.py` | Test Runner | 10-30 min | Runs all test suites in sequence |
| `comprehensive_payment_testing.py` | API Testing | 5-15 min | Comprehensive testing of all payment APIs |
| `test_endpoints_realtime.py` | Real-time Testing | 3-8 min | Real-time testing with Authorize.net sandbox |
| `test_payment_service.py` | Service Testing | 2-5 min | Tests payment service functionality |
| `monitoring_and_metrics.py` | Monitoring | 5-60 min | Real-time monitoring and metrics collection |
| `load_testing.py` | Load Testing | 1-10 min | Performance and load testing |

## 🚀 Quick Start

### 1. Setup Testing Environment

```bash
# Check prerequisites and setup environment
python scripts/setup_testing_environment.py

# Setup with automatic service startup
python scripts/setup_testing_environment.py --start-services

# Check only prerequisites
python scripts/setup_testing_environment.py --check-only
```

### 2. Run All Tests

```bash
# Run complete test suite
python scripts/run_all_tests.py

# Run in quick mode (shorter duration)
python scripts/run_all_tests.py --quick

# Export all results
python scripts/run_all_tests.py --export-all
```

### 3. Run Individual Tests

```bash
# Comprehensive API testing
python scripts/comprehensive_payment_testing.py

# Real-time endpoint testing
python scripts/test_endpoints_realtime.py

# Payment service testing
python scripts/test_payment_service.py
```

## 📋 Prerequisites

### System Requirements

- **Python**: 3.9+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Memory**: 4GB+ RAM
- **Storage**: 20GB+ free space

### Required Environment Variables

```bash
# Authorize.net Sandbox (REQUIRED)
AUTHORIZE_NET_API_LOGIN_ID=your_sandbox_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_sandbox_transaction_key
AUTHORIZE_NET_SANDBOX=true

# Database
DATABASE_URL=postgresql://easypay:password@localhost:5432/easypay_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-development-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
```

### Required Python Packages

```bash
pip install httpx aiohttp pytest pytest-asyncio pytest-cov
```

## 🧪 Test Scripts Details

### 1. Setup Testing Environment (`setup_testing_environment.py`)

**Purpose**: Sets up the testing environment and checks all prerequisites.

**Features**:
- ✅ Python version check
- ✅ Docker and Docker Compose verification
- ✅ Required package installation
- ✅ Environment variable validation
- ✅ Service status checking
- ✅ API connectivity testing
- ✅ Sample environment file creation

**Usage**:
```bash
# Full setup
python scripts/setup_testing_environment.py --start-services

# Check only
python scripts/setup_testing_environment.py --check-only
```

**Output**:
```
🔧 EasyPay Payment Gateway - Testing Environment Setup
============================================================
🐍 Checking Python version...
✅ Python 3.9.7 - OK
🐳 Checking Docker...
✅ Docker version 20.10.8 - OK
📦 Checking Python packages...
✅ httpx - OK
✅ aiohttp - OK
...
```

### 2. Complete Test Suite Runner (`run_all_tests.py`)

**Purpose**: Runs all test scripts in sequence with comprehensive reporting.

**Features**:
- 🚀 Runs all test scripts automatically
- 📊 Comprehensive test reporting
- ⚡ Quick mode for faster testing
- 📄 Export results to JSON
- 🎯 Performance assessment

**Usage**:
```bash
# Complete test suite
python scripts/run_all_tests.py

# Quick mode
python scripts/run_all_tests.py --quick

# Export results
python scripts/run_all_tests.py --export-all
```

**Output**:
```
🚀 EasyPay Payment Gateway - Complete Test Suite
================================================================================
📡 Testing against: http://localhost:8000
⚡ Quick mode: Disabled
⏰ Test started at: 2024-01-01T12:00:00Z
================================================================================

🧪 Test 1/5: Comprehensive API Testing
------------------------------------------------------------
✅ Comprehensive API Testing - PASSED (45.23s)

🧪 Test 2/5: Real-time Endpoint Testing
------------------------------------------------------------
✅ Real-time Endpoint Testing - PASSED (8.45s)
...
```

### 3. Comprehensive Payment Testing (`comprehensive_payment_testing.py`)

**Purpose**: Comprehensive testing of all payment gateway APIs with detailed metrics.

**Features**:
- 💳 Payment creation with multiple scenarios
- 🔍 Payment retrieval (by ID and external ID)
- 📋 Payment listing with filters
- ✏️ Payment updates
- 💰 Payment refunds (full and partial)
- ❌ Payment cancellation
- 🔄 Subscription endpoint testing
- 🔗 Webhook endpoint testing
- 📊 Performance metrics collection
- 📄 Detailed result export

**Usage**:
```bash
# Full comprehensive testing
python scripts/comprehensive_payment_testing.py

# With verbose output
python scripts/comprehensive_payment_testing.py --verbose

# Save detailed results
python scripts/comprehensive_payment_testing.py --save-results
```

**Test Scenarios**:
- Basic credit card payment
- High amount payment
- Payment with metadata
- Partial refund
- Full refund
- Payment cancellation
- Subscription management
- Webhook testing

### 4. Real-time Endpoint Testing (`test_endpoints_realtime.py`)

**Purpose**: Real-time testing of payment endpoints with Authorize.net sandbox integration.

**Features**:
- 🏥 Health endpoint testing
- 🔌 Authorize.net integration testing
- 💳 Payment creation and processing
- 🔍 Payment retrieval
- 💰 Payment refunds
- ❌ Payment cancellation
- 📋 Payment listing
- 🔄 Subscription testing
- 🔗 Webhook testing

**Usage**:
```bash
# Real-time testing
python scripts/test_endpoints_realtime.py
```

**Output**:
```
🚀 Starting EasyPay Payment Gateway Endpoint Tests
============================================================
✅ PASS Health Check (0.123s)
✅ PASS Authorize.net Authentication (0.456s)
✅ PASS Create Payment (0.789s)
   Payment ID: 550e8400-e29b-41d4-a716-446655440000
✅ PASS Get Payment (0.234s)
   Status: completed
✅ PASS Refund Payment (0.567s)
   Refunded: 5.00
...
```

### 5. Payment Service Testing (`test_payment_service.py`)

**Purpose**: Tests the payment service functionality directly.

**Features**:
- 💳 Payment creation
- 🔍 Payment retrieval
- 🔍 Payment retrieval by external ID
- ✏️ Payment updates
- 📋 Payment listing
- 🔍 Payment search
- 📊 Payment statistics
- ✅ Validation error testing

**Usage**:
```bash
# Payment service testing
python scripts/test_payment_service.py
```

### 6. Monitoring and Metrics (`monitoring_and_metrics.py`)

**Purpose**: Real-time monitoring and metrics collection for the payment gateway.

**Features**:
- 📊 Real-time metrics collection
- ⏱️ Response time monitoring
- 📈 Success rate tracking
- 🚨 Alert system
- 📄 Metrics export
- 📊 Performance analysis

**Usage**:
```bash
# Monitor for 5 minutes
python scripts/monitoring_and_metrics.py --duration 300

# Monitor with 5-second intervals
python scripts/monitoring_and_metrics.py --interval 5

# Export metrics
python scripts/monitoring_and_metrics.py --export
```

**Monitored Endpoints**:
- `/health` - Health checks
- `/api/v1/payments/` - Payment operations
- `/api/v1/subscriptions/` - Subscription operations
- `/api/v1/webhooks/health` - Webhook health

### 7. Load Testing (`load_testing.py`)

**Purpose**: Performance and load testing of the payment gateway APIs.

**Features**:
- 👥 Concurrent user simulation
- 📈 Ramp-up testing
- 📊 Performance metrics
- 🎯 Response time analysis
- 📄 Results export
- 🚨 Performance assessment

**Usage**:
```bash
# Load test with 10 users for 60 seconds
python scripts/load_testing.py --concurrent-users 10 --duration 60

# Load test with ramp-up
python scripts/load_testing.py --concurrent-users 20 --duration 120 --ramp-up 30

# Export results
python scripts/load_testing.py --export
```

**Test Scenarios**:
- Health check requests (20% weight)
- Payment listing (30% weight)
- Payment creation (40% weight)
- Subscription listing (10% weight)

## 📊 Test Results and Metrics

### Success Criteria

- **Success Rate**: ≥ 95% for all tests
- **Response Time**: ≤ 2.0s average
- **API Availability**: ≥ 99% uptime
- **Error Rate**: ≤ 1% for payment operations

### Performance Thresholds

- **Response Time Warning**: 1.0s
- **Response Time Critical**: 3.0s
- **Success Rate Warning**: 95%
- **Success Rate Critical**: 90%

### Metrics Collected

- Total requests
- Successful requests
- Failed requests
- Success rate
- Average response time
- Min/Max response time
- 95th/99th percentiles
- Status code distribution
- Endpoint performance
- Error distribution

## 🔧 Configuration

### Environment Variables

Create `.env.development` file:

```bash
# Copy example
cp env.example .env.development

# Edit with your values
nano .env.development
```

### Docker Services

Start required services:

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f easypay-api
```

### Test Data

The scripts use test data that's safe for sandbox environments:

- **Test Cards**: Visa, MasterCard, American Express test numbers
- **Test Customers**: Generated test customer data
- **Test Amounts**: $1.00 - $999.99 range
- **Test Metadata**: Safe test metadata

## 🚨 Troubleshooting

### Common Issues

#### 1. Environment Variables Missing

```bash
# Check environment variables
python scripts/setup_testing_environment.py --check-only

# Create sample environment file
python scripts/setup_testing_environment.py
```

#### 2. Services Not Running

```bash
# Check service status
docker-compose ps

# Start services
docker-compose up -d

# Restart services
docker-compose restart
```

#### 3. Authorize.net Connection Issues

```bash
# Check credentials
echo $AUTHORIZE_NET_API_LOGIN_ID
echo $AUTHORIZE_NET_TRANSACTION_KEY

# Test connection
python -c "
import asyncio
from src.integrations.authorize_net.client import AuthorizeNetClient
async def test():
    client = AuthorizeNetClient()
    result = await client.test_authentication()
    print(f'Auth result: {result}')
asyncio.run(test())
"
```

#### 4. Python Package Issues

```bash
# Install required packages
pip install -r requirements.txt
pip install httpx aiohttp pytest pytest-asyncio pytest-cov

# Check package installation
python -c "import httpx, aiohttp, pytest; print('All packages OK')"
```

### Debug Commands

#### Check API Connectivity

```bash
# Test basic connectivity
curl -X GET "http://localhost:8000/health"

# Test payment endpoint
curl -X GET "http://localhost:8000/api/v1/payments/"
```

#### Check Service Logs

```bash
# View API logs
docker-compose logs -f easypay-api

# View database logs
docker-compose logs -f postgres

# View Redis logs
docker-compose logs -f redis
```

#### Check System Resources

```bash
# Check Docker resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h
```

## 📈 Best Practices

### Testing Strategy

1. **Start with Setup**: Always run setup script first
2. **Test Incrementally**: Start with basic tests, then comprehensive
3. **Monitor Performance**: Use monitoring script during testing
4. **Clean Test Data**: Clean up test data after testing sessions
5. **Document Results**: Save and analyze test results

### Performance Testing

1. **Start Small**: Begin with low load, gradually increase
2. **Monitor Resources**: Watch system resources during testing
3. **Test Different Scenarios**: Peak load, sustained load, burst load
4. **Measure Consistently**: Use same metrics across all tests
5. **Analyze Results**: Look for patterns and bottlenecks

### Security Testing

1. **Use Test Data**: Never use real card data
2. **Sandbox Only**: Use Authorize.net sandbox for testing
3. **Test Authentication**: Verify auth and authorization
4. **Validate Input**: Test input validation and error handling
5. **Rate Limiting**: Test rate limiting and security headers

## 📄 Output Files

### Test Results

- `comprehensive_test_results_YYYYMMDD_HHMMSS.json` - Comprehensive test results
- `load_test_results_YYYYMMDD_HHMMSS.json` - Load test results
- `complete_test_suite_results_YYYYMMDD_HHMMSS.json` - Complete test suite results
- `payment_gateway_metrics_YYYYMMDD_HHMMSS.json` - Monitoring metrics

### Log Files

- `test_results.json` - Real-time endpoint test results
- Application logs in `logs/` directory
- Docker service logs via `docker-compose logs`

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
name: Payment Gateway Testing

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
      run: |
        pip install -r requirements.txt
        pip install httpx aiohttp pytest pytest-asyncio pytest-cov
    
    - name: Start services
      run: docker-compose up -d
    
    - name: Wait for services
      run: sleep 30
    
    - name: Run comprehensive tests
      run: python scripts/comprehensive_payment_testing.py --save-results
    
    - name: Run load tests
      run: python scripts/load_testing.py --concurrent-users 5 --duration 30 --export
    
    - name: Upload test results
      uses: actions/upload-artifact@v2
      with:
        name: test-results
        path: |
          comprehensive_test_results_*.json
          load_test_results_*.json
```

## 📞 Support

### Getting Help

1. **Check Prerequisites**: Run setup script to verify environment
2. **Review Logs**: Check service logs for errors
3. **Test Connectivity**: Verify API accessibility
4. **Check Documentation**: Review comprehensive testing guide
5. **Report Issues**: Create GitHub issue with test results

### Useful Commands

```bash
# Quick health check
curl -X GET "http://localhost:8000/health"

# Check all services
docker-compose ps

# View API documentation
open http://localhost:8000/docs

# Run setup check
python scripts/setup_testing_environment.py --check-only

# Run quick test
python scripts/run_all_tests.py --quick
```

This comprehensive testing suite provides everything needed to thoroughly test the EasyPay Payment Gateway APIs, from basic functionality to performance and load testing. Follow the quick start guide to get up and running quickly, then explore the individual scripts for detailed testing capabilities.
