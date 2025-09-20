# EasyPay Payment Gateway

A modern, secure, and scalable payment processing system built with Python FastAPI that integrates with Authorize.Net for payment processing. EasyPay provides comprehensive payment management capabilities including transaction processing, webhook handling, authentication, and monitoring.

## 🚀 Features

### Core Payment Processing
- **Credit Card Processing**: Secure payment processing via Authorize.Net
- **Transaction Management**: Complete transaction lifecycle management
- **Refunds & Cancellations**: Full and partial refunds, payment cancellations
- **Recurring Billing**: Subscription and recurring payment support
- **Webhook Integration**: Real-time event notifications from Authorize.Net

### Security & Authentication
- **API Key Management**: Secure API key generation and management
- **JWT Authentication**: Token-based authentication for web applications
- **Role-Based Access Control (RBAC)**: Granular permission system
- **Request Signing**: HMAC signature verification for webhooks
- **PCI DSS Compliance**: Security measures for payment data handling

### Monitoring & Observability
- **Health Checks**: Comprehensive health monitoring endpoints
- **Metrics Collection**: Prometheus metrics for monitoring
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Distributed Tracing**: Request tracking across services
- **Performance Monitoring**: Real-time performance metrics

### Infrastructure
- **Kong API Gateway**: Rate limiting, CORS, and request routing
- **Redis Caching**: High-performance caching layer
- **PostgreSQL Database**: ACID-compliant data storage
- **Docker Support**: Containerized deployment
- **Background Workers**: Async task processing

## 📋 Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**
- **PostgreSQL 15+**
- **Redis 7+**
- **Authorize.Net Sandbox Account** (for testing)

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/easypay-payment-gateway.git
cd easypay-payment-gateway
```

### 2. Environment Configuration

Create environment files:

```bash
# Copy example environment file
cp env.example .env

# Edit environment variables
nano .env
```

**Required Environment Variables:**

```bash
# Database Configuration
DATABASE_URL=postgresql://easypay:password@localhost:5432/easypay

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Authorize.Net Configuration
AUTHORIZE_NET_API_LOGIN_ID=your_api_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_transaction_key
AUTHORIZE_NET_SANDBOX=true
AUTHORIZE_NET_WEBHOOK_SECRET=your_webhook_secret

# Security Configuration
SECRET_KEY=your_jwt_secret_key_here

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 3. Database Setup

#### Option A: Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec easypay-api alembic upgrade head
```

#### Option B: Manual Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis services
# (Install and configure according to your system)

# Run database migrations
alembic upgrade head
```

### 4. Start the Application

#### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f easypay-api
```

#### Manual Start

```bash
# Start the application
python src/main.py

# Or using uvicorn directly
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Verify Installation

```bash
# Check application health
curl http://localhost:8000/health

# Check Kong gateway (if using Docker Compose)
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Web Apps      │    │   Admin Panel   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │     Kong API Gateway      │
                    │   (Rate Limiting, CORS)   │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │    EasyPay API Service   │
                    │   (FastAPI Application)  │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│   PostgreSQL    │    │     Redis       │    │ Authorize.net   │
│   (Database)    │    │    (Cache)      │    │   (Payment      │
│                 │    │                 │    │   Processor)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Service Ports

- **8000**: Kong API Gateway (external access)
- **8001**: Kong Admin API
- **8002**: EasyPay API (internal)
- **5432**: PostgreSQL Database
- **6379**: Redis Cache
- **9090**: Prometheus Metrics
- **3000**: Grafana Dashboards

## 🔧 Background Workers

EasyPay includes several background workers for async processing:

### 1. Webhook Processing Workers

Process incoming webhooks from Authorize.Net:

```bash
# Start webhook workers
python -m src.workers.webhook_processor
```

### 2. Dead Letter Queue Workers

Handle failed operations and retry logic:

```bash
# Start DLQ workers
python -m src.workers.dead_letter_queue
```

### 3. Audit Log Workers

Process audit logs asynchronously:

```bash
# Start audit log workers
python -m src.workers.audit_logger
```

### Docker Compose Workers

All workers are automatically started with Docker Compose:

```bash
# Start all services including workers
docker-compose up -d

# View worker logs
docker-compose logs -f easypay-workers
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# Readiness probe
curl http://localhost:8000/health/ready

# Liveness probe
curl http://localhost:8000/health/live
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Application metrics
curl http://localhost:9090/api/v1/query?query=easypay_http_requests_total
```

### Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **API Documentation**: http://localhost:8000/docs

## 🔐 Authentication

### API Key Authentication

```bash
# Create API key
curl -X POST "http://localhost:8000/api/v1/auth/api-keys" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API Key",
    "permissions": ["payments:read", "payments:write"],
    "rate_limit_per_minute": 100
  }'

# Use API key
curl -X GET "http://localhost:8000/api/v1/payments" \
  -H "X-API-Key-ID: ak_123456789" \
  -H "X-API-Key-Secret: your_secret_here"
```

### JWT Token Authentication

```bash
# Generate JWT tokens
curl -X POST "http://localhost:8000/api/v1/auth/tokens" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key_id": "ak_123456789",
    "api_key_secret": "your_secret_here"
  }'

# Use JWT token
curl -X GET "http://localhost:8000/api/v1/payments" \
  -H "Authorization: Bearer your_jwt_token_here"
```

## 💳 Payment Processing

### Create Payment

```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "25.99",
    "currency": "USD",
    "payment_method": "credit_card",
    "customer_id": "cust_123456789",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "card_token": "tok_visa_4242",
    "description": "Premium subscription payment",
    "metadata": {
      "order_id": "order_2024_001",
      "product": "premium_plan"
    },
    "is_test": true
  }'
```

### Process Refund

```bash
curl -X POST "http://localhost:8000/api/v1/payments/{payment_id}/refund" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "10.00",
    "reason": "Customer requested refund",
    "metadata": {
      "refund_reason": "customer_request"
    }
  }'
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Test Scripts

```bash
# Test authentication system
python test_auth_system.py

# Test payment processing
python scripts/quick_payment_test.py

# Test webhook processing
python test_authorize_net_webhooks.py

# Test monitoring system
python test_day18_monitoring_system.py
```

## 🚀 Deployment

### Development

```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f
```

### Production

```bash
# Use production configuration
docker-compose -f docker-compose.production.yml up -d

# Or deploy to Kubernetes
kubectl apply -f k8s/
```

### Environment-Specific Configurations

- **Development**: `docker-compose.yml`
- **Production**: `docker-compose.production.yml`
- **Minimal**: `docker-compose.minimal.yml`
- **Light**: `docker-compose.light.yml`

## 📚 API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

### API Reference

See [API Reference Documentation](docs/api/api-reference.md) for detailed endpoint documentation.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `AUTHORIZE_NET_API_LOGIN_ID` | Authorize.Net API login ID | Required |
| `AUTHORIZE_NET_TRANSACTION_KEY` | Authorize.Net transaction key | Required |
| `AUTHORIZE_NET_SANDBOX` | Use Authorize.Net sandbox | `true` |
| `SECRET_KEY` | JWT signing secret | Required |
| `ENVIRONMENT` | Application environment | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Kong Configuration

Kong API Gateway configuration is located in `kong/kong.yml`:

- Rate limiting: 100/min, 1000/hour, 10000/day
- CORS enabled for all origins
- Request/response logging
- Prometheus metrics integration

## 🛠️ Development

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Adding New Features

1. Create feature branch
2. Implement feature with tests
3. Update documentation
4. Create pull request
5. Code review and merge

## 📖 Documentation

- [Project Structure](PROJECT_STRUCTURE.md) - Detailed project organization
- [Architecture](Architecture.md) - System architecture and design decisions
- [Observability](OBSERVABILITY.md) - Monitoring and logging strategy
- [API Reference](docs/api/api-reference.md) - Complete API documentation
- [Deployment Guide](docs/deployment/) - Deployment instructions
- [Security Guide](docs/day13-security-implementation-summary.md) - Security implementation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.easypay.com](https://docs.easypay.com)
- **Issues**: [GitHub Issues](https://github.com/your-org/easypay-payment-gateway/issues)
- **Email**: support@easypay.com
- **Status Page**: [status.easypay.com](https://status.easypay.com)

## 🏆 Acknowledgments

- FastAPI for the excellent web framework
- Authorize.Net for payment processing capabilities
- Kong for API gateway functionality
- PostgreSQL and Redis for data storage
- The open-source community for various libraries and tools

---

**EasyPay Payment Gateway** - Secure, scalable, and developer-friendly payment processing.