# EasyPay Payment Gateway

A modern, scalable payment gateway system built with FastAPI, designed to handle payment processing with high reliability and performance.

## Features

- **Payment Processing**: Secure credit card processing via Authorize.net
- **RESTful API**: Clean, well-documented API endpoints
- **Authentication**: API key and JWT-based authentication
- **Webhooks**: Real-time payment notifications
- **Monitoring**: Comprehensive metrics and health checks
- **Caching**: Redis-based caching for improved performance
- **Database**: PostgreSQL with connection pooling
- **Docker**: Containerized deployment with Docker Compose

## Quick Start

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- PostgreSQL 13+
- Redis 6+

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/easypay.git
   cd easypay
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Or run locally**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run the application
   python -m src.main
   ```

### API Documentation

Once the application is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## API Endpoints

### Health Endpoints

- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check with dependencies
- `GET /health/live` - Liveness check
- `GET /health/detailed` - Detailed health information

### Payment Endpoints

- `POST /api/v1/payments` - Create a new payment
- `GET /api/v1/payments/{id}` - Get payment by ID
- `GET /api/v1/payments` - List payments with filtering
- `POST /api/v1/payments/{id}/refund` - Refund a payment
- `POST /api/v1/payments/{id}/cancel` - Cancel a payment

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://easypay:password@localhost:5432/easypay` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `AUTHORIZE_NET_API_LOGIN_ID` | Authorize.net API login ID | Required |
| `AUTHORIZE_NET_TRANSACTION_KEY` | Authorize.net transaction key | Required |
| `AUTHORIZE_NET_SANDBOX` | Use sandbox environment | `true` |
| `SECRET_KEY` | Application secret key | Required |
| `LOG_LEVEL` | Logging level | `INFO` |

### Docker Services

- **easypay-api**: Main FastAPI application
- **postgres**: PostgreSQL database
- **redis**: Redis cache
- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboard

## Development

### Project Structure

```
easypay/
├── src/                          # Source code
│   ├── api/                      # API layer
│   │   ├── v1/                   # API version 1
│   │   │   ├── endpoints/        # API endpoints
│   │   │   ├── middleware/       # API middleware
│   │   │   └── schemas/          # Request/response schemas
│   │   └── common/               # Shared API components
│   ├── core/                     # Core business logic
│   │   ├── services/             # Business services
│   │   ├── models/               # Data models
│   │   ├── repositories/         # Data access layer
│   │   └── exceptions/           # Custom exceptions
│   ├── integrations/             # External integrations
│   │   ├── authorize_net/        # Authorize.net integration
│   │   ├── webhooks/             # Webhook handlers
│   │   └── notifications/        # Notification services
│   ├── infrastructure/           # Infrastructure layer
│   │   ├── database/             # Database configuration
│   │   ├── cache/                # Caching layer
│   │   ├── monitoring/           # Monitoring and logging
│   │   └── security/             # Security components
│   └── utils/                    # Utility functions
├── tests/                        # Test files
├── docs/                         # Documentation
├── config/                       # Configuration files
├── migrations/                   # Database migrations
└── docker/                       # Docker configurations
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_payments.py
```

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

## Monitoring

### Health Checks

The application provides several health check endpoints:

- **Basic Health**: `/health` - Simple status check
- **Readiness**: `/health/ready` - Checks all dependencies
- **Liveness**: `/health/live` - Kubernetes liveness probe
- **Detailed**: `/health/detailed` - Comprehensive system information

### Metrics

Prometheus metrics are available at `/metrics`:

- HTTP request metrics
- Payment processing metrics
- Database connection metrics
- Cache hit/miss ratios
- Custom business metrics

### Grafana Dashboard

Access the Grafana dashboard at http://localhost:3000 (admin/admin) to view:

- Application performance metrics
- Payment processing statistics
- System resource usage
- Error rates and response times

## Security

### Authentication

- API key authentication for service-to-service communication
- JWT tokens for user authentication
- Request signing for webhook verification

### Data Protection

- No sensitive data stored in logs
- Encrypted communication (HTTPS)
- PCI DSS compliance considerations
- Secure credential management

## Deployment

### Production Deployment

1. **Set up production environment**
   ```bash
   # Update environment variables
   export ENVIRONMENT=production
   export DEBUG=false
   export SECRET_KEY=your-production-secret-key
   ```

2. **Deploy with Docker**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

### Scaling

- Horizontal scaling with multiple API instances
- Database read replicas for read-heavy workloads
- Redis clustering for cache distribution
- Load balancing with Kong API Gateway

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation in `/docs`
- Contact the development team

## Roadmap

- [ ] Advanced fraud detection
- [ ] Subscription management
- [ ] Multi-currency support
- [ ] Mobile SDKs
- [ ] Advanced analytics dashboard
- [ ] Webhook management UI
- [ ] Customer portal
- [ ] Advanced reporting
