# EasyPay Payment Gateway - Project Structure

This document provides a comprehensive overview of the EasyPay Payment Gateway project structure, explaining the purpose of each folder and key modules.

## 📁 Root Directory Structure

```
easypay/
├── src/                          # Source code
├── tests/                        # Test files
├── docs/                         # Documentation
├── scripts/                      # Utility scripts
├── config/                       # Configuration files
├── migrations/                   # Database migrations
├── kong/                         # Kong API Gateway configuration
├── docker/                       # Docker configurations
├── examples/                     # Example code and integrations
├── logs/                         # Application logs
├── htmlcov/                      # Test coverage reports
├── docker-compose*.yml           # Docker Compose configurations
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
├── pytest.ini                    # Pytest configuration
├── alembic.ini                   # Alembic migration configuration
└── README.md                     # Project overview
```

## 🏗️ Source Code Structure (`src/`)

The source code follows a clean architecture pattern with clear separation of concerns:

```
src/
├── main.py                       # Application entry point
├── main_simple.py                # Simplified entry point for testing
├── main_test.py                  # Test-specific entry point
├── api/                          # API layer
│   ├── v1/                       # API version 1
│   │   ├── endpoints/            # API endpoints
│   │   ├── middleware/           # API middleware
│   │   └── schemas/              # Request/response schemas
│   └── common/                   # Shared API components
├── core/                         # Core business logic
│   ├── services/                 # Business services
│   ├── models/                   # Data models
│   ├── repositories/             # Data access layer
│   └── exceptions/               # Custom exceptions
├── integrations/                 # External integrations
│   ├── authorize_net/            # Authorize.net integration
│   ├── webhooks/                 # Webhook handlers
│   └── notifications/            # Notification services
├── infrastructure/               # Infrastructure layer
│   ├── database/                 # Database configuration
│   ├── cache/                    # Caching layer
│   ├── monitoring/               # Monitoring and logging
│   └── security/                 # Security components
└── utils/                        # Utility functions
```

### API Layer (`src/api/`)

**Purpose**: Handles HTTP requests, validation, and responses.

#### Version 1 API (`src/api/v1/`)

**Endpoints** (`src/api/v1/endpoints/`):
- `health.py` - Health check endpoints
- `payments.py` - Payment processing endpoints
- `auth.py` - Authentication endpoints
- `webhooks.py` - Webhook management endpoints
- `webhook_receiver.py` - Webhook reception endpoints
- `authorize_net_webhooks.py` - Authorize.Net specific webhooks
- `admin.py` - Administrative endpoints
- `version.py` - Version information endpoints
- `subscriptions.py` - Subscription management endpoints
- `error_management.py` - Error handling endpoints

**Middleware** (`src/api/v1/middleware/`):
- `auth.py` - Authentication middleware
- `enhanced_auth.py` - Enhanced security middleware
- `security_headers.py` - Security headers middleware
- `compression.py` - Response compression middleware
- `request_queue.py` - Request queuing middleware

**Schemas** (`src/api/v1/schemas/`):
- `payment.py` - Payment request/response schemas
- `auth.py` - Authentication schemas
- `webhook.py` - Webhook schemas
- `subscription.py` - Subscription schemas
- `common.py` - Common schemas

### Core Business Logic (`src/core/`)

**Purpose**: Contains the core business logic and domain models.

#### Services (`src/core/services/`)

**Payment Services**:
- `payment_service.py` - Core payment processing logic
- `refund_service.py` - Refund processing logic
- `subscription_service.py` - Subscription management
- `webhook_service.py` - Webhook processing

**Authentication Services**:
- `auth_service.py` - Authentication and authorization
- `rbac_service.py` - Role-based access control
- `scoping_service.py` - API key scoping
- `request_signing_service.py` - Request signing

**Utility Services**:
- `audit_logging_service.py` - Audit logging
- `notification_service.py` - Notification handling
- `fraud_detection_service.py` - Fraud detection

#### Models (`src/core/models/`)

**Domain Models**:
- `payment.py` - Payment domain model
- `webhook.py` - Webhook domain model
- `subscription.py` - Subscription domain model
- `audit_log.py` - Audit log model

**Authentication Models**:
- `auth.py` - Authentication models
- `rbac.py` - Role-based access control models

**Infrastructure Models**:
- `database.py` - Database configuration models
- `cache.py` - Cache configuration models

#### Repositories (`src/core/repositories/`)

**Data Access Layer**:
- `payment_repository.py` - Payment data access
- `webhook_repository.py` - Webhook data access
- `subscription_repository.py` - Subscription data access
- `audit_log_repository.py` - Audit log data access
- `cached_webhook_repository.py` - Cached webhook repository
- `cached_audit_log_repository.py` - Cached audit log repository

#### Exceptions (`src/core/exceptions/`)

**Custom Exceptions**:
- `base.py` - Base exception classes
- `payment.py` - Payment-specific exceptions
- `auth.py` - Authentication exceptions
- `webhook.py` - Webhook exceptions

### Infrastructure Layer (`src/infrastructure/`)

**Purpose**: Provides infrastructure services and cross-cutting concerns.

#### Database (`src/infrastructure/database/`)

- `__init__.py` - Database initialization
- `config.py` - Database configuration
- `connection_pool.py` - Connection pool management
- `query_optimizer.py` - Query optimization

#### Cache (`src/infrastructure/cache/`)

- `__init__.py` - Cache initialization
- `config.py` - Cache configuration
- `strategies.py` - Caching strategies
- `redis_client.py` - Redis client

#### Monitoring (`src/infrastructure/monitoring/`)

- `metrics.py` - Metrics collection
- `logging.py` - Logging configuration
- `health_checks.py` - Health check implementations
- `performance_monitor.py` - Performance monitoring

#### Security (`src/infrastructure/security/`)

- `encryption.py` - Encryption utilities
- `validation.py` - Input validation
- `rate_limiting.py` - Rate limiting implementation

#### Additional Infrastructure

- `metrics_middleware.py` - Metrics collection middleware
- `error_recovery.py` - Error recovery mechanisms
- `graceful_shutdown.py` - Graceful shutdown management
- `dead_letter_queue.py` - Dead letter queue service
- `circuit_breaker_service.py` - Circuit breaker implementation
- `error_reporting.py` - Error reporting service
- `async_processor.py` - Async task processing

### Integrations (`src/integrations/`)

**Purpose**: Handles external service integrations.

#### Authorize.Net Integration (`src/integrations/authorize_net/`)

- `client.py` - Authorize.Net API client
- `webhook_handler.py` - Webhook processing
- `payment_processor.py` - Payment processing
- `models.py` - Authorize.Net specific models

#### Webhook Integration (`src/integrations/webhooks/`)

- `processor.py` - Webhook processing logic
- `delivery.py` - Webhook delivery service
- `retry.py` - Retry mechanisms

#### Notification Integration (`src/integrations/notifications/`)

- `email.py` - Email notifications
- `sms.py` - SMS notifications
- `webhook_notifications.py` - Webhook notifications

### Utilities (`src/utils/`)

**Purpose**: Common utility functions and helpers.

- `helpers.py` - General helper functions
- `validators.py` - Validation utilities
- `formatters.py` - Data formatting utilities
- `constants.py` - Application constants

## 🧪 Test Structure (`tests/`)

**Purpose**: Comprehensive test coverage for all components.

```
tests/
├── __init__.py                   # Test package initialization
├── conftest.py                   # Pytest configuration and fixtures
├── conftest_comprehensive.py     # Comprehensive test fixtures
├── conftest_simple.py            # Simple test fixtures
├── unit/                         # Unit tests
│   ├── test_payment_service.py   # Payment service tests
│   ├── test_auth_service.py      # Authentication service tests
│   ├── test_webhook_service.py   # Webhook service tests
│   └── ...                       # Other unit tests
├── integration/                  # Integration tests
│   ├── test_payment_flow.py      # Payment flow tests
│   ├── test_webhook_flow.py      # Webhook flow tests
│   └── ...                       # Other integration tests
├── e2e/                          # End-to-end tests
│   ├── test_complete_flow.py     # Complete flow tests
│   └── ...                       # Other E2E tests
├── security/                     # Security tests
│   ├── test_auth_security.py     # Authentication security tests
│   └── ...                       # Other security tests
├── performance/                  # Performance tests
│   ├── test_load_performance.py  # Load testing
│   └── ...                       # Other performance tests
├── fixtures/                     # Test fixtures
│   └── test_data.py              # Test data fixtures
└── chaos/                        # Chaos engineering tests
    └── test_chaos_scenarios.py   # Chaos testing scenarios
```

## 📚 Documentation Structure (`docs/`)

**Purpose**: Comprehensive project documentation.

```
docs/
├── api/                          # API documentation
│   ├── api-reference.md          # Complete API reference
│   └── error-codes.md            # Error code documentation
├── architecture/                 # Architecture documentation
│   └── architecture-documentation.md
├── configuration/                # Configuration guides
├── deployment/                   # Deployment documentation
├── developer/                    # Developer guides
├── testing/                      # Testing documentation
├── troubleshooting/              # Troubleshooting guides
├── user/                         # User guides
├── sources/                      # Source documentation
├── research/                     # Research and analysis
├── PRD.md                        # Product Requirements Document
├── mvp-development-plan.md       # MVP development plan
└── ...                           # Other documentation files
```

## 🔧 Scripts Structure (`scripts/`)

**Purpose**: Utility scripts for development, testing, and deployment.

```
scripts/
├── dev_setup.py                  # Development environment setup
├── docker_setup.py               # Docker environment setup
├── kong_setup.py                 # Kong API Gateway setup
├── quick_payment_test.py          # Quick payment testing
├── comprehensive_payment_testing.py # Comprehensive payment tests
├── webhook_simulation.py          # Webhook simulation
├── load_testing.py               # Load testing scripts
├── monitoring_and_metrics.py     # Monitoring setup
├── health-check.sh               # Health check script
├── deploy_system.py              # System deployment
├── backup.sh                     # Backup scripts
├── restore.sh                    # Restore scripts
└── ...                           # Other utility scripts
```

## ⚙️ Configuration Structure (`config/`)

**Purpose**: Configuration files for various services.

```
config/
├── production.yml                 # Production configuration
├── prometheus.yml                # Prometheus configuration
├── prometheus/                   # Prometheus-specific configs
│   ├── alerts.yml                # Alerting rules
│   └── production.yml            # Production Prometheus config
├── grafana/                      # Grafana configuration
│   ├── dashboards/               # Dashboard definitions
│   └── provisioning/             # Provisioning configs
├── fluentd/                      # Fluentd configuration
│   └── fluent.conf               # Fluentd config
├── logstash/                     # Logstash configuration
│   └── logstash.conf             # Logstash config
└── security/                     # Security configuration
    └── production.yml            # Production security config
```

## 🗄️ Database Migrations (`migrations/`)

**Purpose**: Database schema versioning and migrations.

```
migrations/
├── env.py                        # Alembic environment configuration
├── script.py.mako                # Migration template
├── versions/                     # Migration files
│   ├── 001_initial_schema.py     # Initial database schema
│   ├── 002_add_payment_tables.py # Payment tables
│   ├── 003_add_auth_tables.py    # Authentication tables
│   └── 004_add_rbac_security_tables.py # RBAC security tables
└── README                        # Migration documentation
```

## 🐳 Docker Structure (`docker/`)

**Purpose**: Docker configurations and deployment files.

```
docker/
├── Dockerfile                    # Main application Dockerfile
├── Dockerfile.production         # Production Dockerfile
└── docker-compose*.yml           # Various Docker Compose configurations
```

## 🌐 Kong Configuration (`kong/`)

**Purpose**: Kong API Gateway configuration.

```
kong/
├── kong.yml                      # Kong declarative configuration
└── README.md                     # Kong setup documentation
```

## 📋 Key Design Principles

### 1. Separation of Concerns

- **API Layer**: Handles HTTP concerns
- **Core Layer**: Contains business logic
- **Infrastructure Layer**: Provides technical services
- **Integration Layer**: Manages external services

### 2. Dependency Inversion

- Core business logic doesn't depend on infrastructure
- Interfaces define contracts between layers
- Dependency injection for testability

### 3. Single Responsibility

- Each module has a single, well-defined purpose
- Services are focused on specific business domains
- Repositories handle only data access

### 4. Testability

- Comprehensive test coverage at all levels
- Dependency injection for easy mocking
- Clear separation of concerns for isolated testing

### 5. Scalability

- Microservices-ready architecture
- Async processing capabilities
- Horizontal scaling support

## 🔄 Data Flow

### Request Processing Flow

```
Client Request
    ↓
Kong API Gateway (Rate Limiting, CORS)
    ↓
FastAPI Application (Authentication, Validation)
    ↓
Business Services (Payment Processing)
    ↓
Repositories (Data Access)
    ↓
Database/Redis (Data Storage)
    ↓
External Services (Authorize.Net)
    ↓
Response (Client)
```

### Webhook Processing Flow

```
Authorize.Net Webhook
    ↓
Webhook Receiver (Signature Verification)
    ↓
Webhook Processor (Event Processing)
    ↓
Background Workers (Async Processing)
    ↓
Database Update (Status Changes)
    ↓
Notification Service (Client Notifications)
```

## 🚀 Development Workflow

### 1. Feature Development

1. Create feature branch
2. Implement in appropriate layer
3. Add comprehensive tests
4. Update documentation
5. Create pull request

### 2. Code Organization

- Follow the established folder structure
- Keep files under 700 lines (project rule)
- Use clear, descriptive naming
- Maintain separation of concerns

### 3. Testing Strategy

- Unit tests for business logic
- Integration tests for API endpoints
- End-to-end tests for complete flows
- Performance tests for scalability

## 📈 Monitoring and Observability

### Metrics Collection

- Prometheus metrics for all services
- Custom business metrics
- Performance monitoring
- Error tracking

### Logging Strategy

- Structured JSON logging
- Correlation IDs for request tracking
- Security event logging
- Audit trail maintenance

### Health Monitoring

- Comprehensive health checks
- Dependency monitoring
- Performance indicators
- Alerting integration

## 🔒 Security Considerations

### Authentication & Authorization

- API key management
- JWT token support
- Role-based access control
- Request signing

### Data Protection

- Encryption at rest and in transit
- PCI DSS compliance measures
- Secure secret management
- Input validation and sanitization

## 🎯 Future Enhancements

### Planned Improvements

1. **Microservices Migration**: Break down into smaller services
2. **Advanced Monitoring**: Distributed tracing with Jaeger
3. **Machine Learning**: Fraud detection algorithms
4. **Multi-Region**: Global deployment support
5. **Advanced Analytics**: Business intelligence features

### Scalability Roadmap

1. **Horizontal Scaling**: Load balancing and auto-scaling
2. **Database Sharding**: Partition data across multiple databases
3. **Caching Strategy**: Multi-level caching implementation
4. **Message Queues**: Advanced async processing
5. **Service Mesh**: Istio integration for service communication

---

This project structure provides a solid foundation for building and maintaining a scalable, secure, and maintainable payment processing system. The clear separation of concerns, comprehensive testing, and extensive documentation ensure that the system can evolve and scale with business needs.
