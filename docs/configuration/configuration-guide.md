# EasyPay Payment Gateway - Configuration Guide

This comprehensive guide covers all configuration options for the EasyPay Payment Gateway system.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Database Configuration](#database-configuration)
- [Redis Configuration](#redis-configuration)
- [Authentication Configuration](#authentication-configuration)
- [Payment Processing Configuration](#payment-processing-configuration)
- [Monitoring Configuration](#monitoring-configuration)
- [Security Configuration](#security-configuration)
- [API Gateway Configuration](#api-gateway-configuration)
- [Webhook Configuration](#webhook-configuration)
- [Logging Configuration](#logging-configuration)
- [Performance Configuration](#performance-configuration)

## Environment Variables

### Core Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Environment (development/staging/production) | `development` | Yes |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` | No |
| `SECRET_KEY` | Application secret key | - | Yes |
| `JWT_SECRET_KEY` | JWT token secret key | - | Yes |

### Database Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `DATABASE_POOL_SIZE` | Connection pool size | `20` | No |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | `30` | No |
| `DATABASE_POOL_TIMEOUT` | Pool timeout (seconds) | `30` | No |
| `DATABASE_POOL_RECYCLE` | Connection recycle time (seconds) | `3600` | No |

### Redis Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `REDIS_URL` | Redis connection string | - | Yes |
| `REDIS_POOL_SIZE` | Redis connection pool size | `10` | No |
| `REDIS_TIMEOUT` | Redis timeout (seconds) | `5` | No |
| `REDIS_MAX_CONNECTIONS` | Max Redis connections | `50` | No |

### Authorize.net Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AUTHORIZE_NET_API_LOGIN_ID` | Authorize.net API login ID | - | Yes |
| `AUTHORIZE_NET_TRANSACTION_KEY` | Authorize.net transaction key | - | Yes |
| `AUTHORIZE_NET_SANDBOX` | Use sandbox environment | `true` | No |
| `AUTHORIZE_NET_WEBHOOK_SECRET` | Webhook signature secret | - | No |

## Database Configuration

### PostgreSQL Settings

#### Connection Configuration

```python
# src/infrastructure/database.py
DATABASE_CONFIG = {
    "pool_size": int(os.getenv("DATABASE_POOL_SIZE", 20)),
    "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", 30)),
    "pool_timeout": int(os.getenv("DATABASE_POOL_TIMEOUT", 30)),
    "pool_recycle": int(os.getenv("DATABASE_POOL_RECYCLE", 3600)),
    "echo": os.getenv("ENVIRONMENT") == "development",
    "echo_pool": os.getenv("ENVIRONMENT") == "development"
}
```

#### Performance Optimization

```sql
-- postgresql.conf optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

#### Index Configuration

```sql
-- Performance indexes
CREATE INDEX CONCURRENTLY idx_payments_status ON payments(status);
CREATE INDEX CONCURRENTLY idx_payments_customer_id ON payments(customer_id);
CREATE INDEX CONCURRENTLY idx_payments_created_at ON payments(created_at);
CREATE INDEX CONCURRENTLY idx_payments_external_id ON payments(external_id);
CREATE INDEX CONCURRENTLY idx_webhooks_event_type ON webhooks(event_type);
CREATE INDEX CONCURRENTLY idx_audit_logs_action ON audit_logs(action);
```

## Redis Configuration

### Connection Settings

```python
# src/infrastructure/cache.py
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": int(os.getenv("REDIS_DB", 0)),
    "password": os.getenv("REDIS_PASSWORD"),
    "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", 50)),
    "socket_timeout": int(os.getenv("REDIS_TIMEOUT", 5)),
    "socket_connect_timeout": 5,
    "retry_on_timeout": True,
    "health_check_interval": 30
}
```

### Cache Configuration

```python
# Cache TTL settings
CACHE_TTL = {
    "payment": 3600,  # 1 hour
    "webhook": 1800,  # 30 minutes
    "auth_token": 900,  # 15 minutes
    "api_key": 7200,  # 2 hours
    "user_session": 1800  # 30 minutes
}
```

### Redis Optimization

```conf
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
tcp-keepalive 300
timeout 0
```

## Authentication Configuration

### API Key Configuration

```python
# src/core/services/auth_service.py
API_KEY_CONFIG = {
    "key_length": 32,
    "secret_length": 64,
    "default_expiry_days": 365,
    "max_rate_limit_per_minute": 100,
    "max_rate_limit_per_hour": 1000,
    "max_rate_limit_per_day": 10000
}
```

### JWT Configuration

```python
# JWT settings
JWT_CONFIG = {
    "algorithm": "HS256",
    "access_token_expire_minutes": 60,
    "refresh_token_expire_days": 30,
    "issuer": "easypay.com",
    "audience": "easypay-api"
}
```

### Permission System

```python
# Permission definitions
PERMISSIONS = {
    "payments": ["read", "write", "refund", "cancel"],
    "webhooks": ["read", "write", "manage"],
    "admin": ["read", "write", "delete"],
    "analytics": ["read"],
    "users": ["read", "write", "delete"]
}

# Role definitions
ROLES = {
    "admin": ["payments:*", "webhooks:*", "admin:*", "analytics:*", "users:*"],
    "merchant": ["payments:read", "payments:write", "webhooks:read", "analytics:read"],
    "developer": ["payments:read", "webhooks:read", "webhooks:write"],
    "viewer": ["payments:read", "analytics:read"]
}
```

## Payment Processing Configuration

### Authorize.net Settings

```python
# src/integrations/authorize_net/client.py
AUTHORIZE_NET_CONFIG = {
    "api_login_id": os.getenv("AUTHORIZE_NET_API_LOGIN_ID"),
    "transaction_key": os.getenv("AUTHORIZE_NET_TRANSACTION_KEY"),
    "sandbox": os.getenv("AUTHORIZE_NET_SANDBOX", "true").lower() == "true",
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 1
}
```

### Payment Processing Rules

```python
# Payment validation rules
PAYMENT_RULES = {
    "min_amount": 0.01,
    "max_amount": 100000.00,
    "supported_currencies": ["USD", "EUR", "GBP", "CAD", "AUD"],
    "supported_payment_methods": ["credit_card", "debit_card"],
    "card_brands": ["visa", "mastercard", "amex", "discover"],
    "max_refund_percentage": 100,
    "refund_time_limit_days": 120
}
```

### Fraud Detection

```python
# Fraud detection settings
FRAUD_CONFIG = {
    "enabled": True,
    "risk_threshold": 0.7,
    "block_threshold": 0.9,
    "max_amount_without_review": 1000.00,
    "velocity_check_enabled": True,
    "velocity_window_hours": 24,
    "max_transactions_per_window": 10
}
```

## Monitoring Configuration

### Prometheus Metrics

```python
# src/infrastructure/monitoring.py
METRICS_CONFIG = {
    "enabled": True,
    "port": 9090,
    "path": "/metrics",
    "collect_interval": 15,
    "retention_days": 30
}

# Custom metrics
CUSTOM_METRICS = {
    "payment_success_rate": "payment_success_total",
    "payment_failure_rate": "payment_failure_total",
    "api_response_time": "api_response_time_seconds",
    "database_connection_pool": "database_connections_active",
    "cache_hit_rate": "cache_hits_total"
}
```

### Health Check Configuration

```python
# Health check settings
HEALTH_CHECK_CONFIG = {
    "timeout": 5,
    "interval": 30,
    "retries": 3,
    "startup_delay": 10,
    "liveness_path": "/health/live",
    "readiness_path": "/health/ready"
}
```

### Logging Configuration

```python
# Structured logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "json",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "/var/log/easypay/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "easypay": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        }
    }
}
```

## Security Configuration

### CORS Settings

```python
# CORS configuration
CORS_CONFIG = {
    "allow_origins": [
        "https://app.easypay.com",
        "https://dashboard.easypay.com",
        "https://sandbox.easypay.com"
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": [
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With"
    ],
    "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    "max_age": 3600
}
```

### Security Headers

```python
# Security headers middleware
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin"
}
```

### Rate Limiting

```python
# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "default": {
        "per_minute": 100,
        "per_hour": 1000,
        "per_day": 10000
    },
    "payment_endpoints": {
        "per_minute": 50,
        "per_hour": 500,
        "per_day": 5000
    },
    "admin_endpoints": {
        "per_minute": 20,
        "per_hour": 200,
        "per_day": 2000
    }
}
```

## API Gateway Configuration

### Kong Configuration

```yaml
# kong/kong.yml
_format_version: "3.0"

services:
  - name: easypay-api
    url: http://easypay-api:8000
    routes:
      - name: easypay-route
        paths:
          - /
        methods:
          - GET
          - POST
          - PUT
          - DELETE
        plugins:
          - name: rate-limiting
            config:
              minute: 100
              hour: 1000
              day: 10000
              policy: redis
              redis_host: redis
              redis_port: 6379
          - name: cors
            config:
              origins:
                - https://app.easypay.com
                - https://dashboard.easypay.com
              methods:
                - GET
                - POST
                - PUT
                - DELETE
                - OPTIONS
              headers:
                - Accept
                - Authorization
                - Content-Type
              credentials: true
          - name: request-transformer
            config:
              add:
                headers:
                  - X-Forwarded-Proto:https
```

### Load Balancer Settings

```python
# Load balancer configuration
LOAD_BALANCER_CONFIG = {
    "algorithm": "round_robin",
    "health_check_interval": 30,
    "health_check_timeout": 5,
    "health_check_path": "/health",
    "max_failures": 3,
    "recovery_time": 60
}
```

## Webhook Configuration

### Webhook Settings

```python
# Webhook configuration
WEBHOOK_CONFIG = {
    "max_retry_attempts": 5,
    "retry_delays": [5, 10, 20, 40, 80],  # minutes
    "timeout": 30,
    "signature_header": "X-EasyPay-Signature",
    "signature_algorithm": "HMAC-SHA256",
    "max_payload_size": 1048576,  # 1MB
    "batch_size": 100,
    "processing_interval": 60  # seconds
}
```

### Event Types

```python
# Supported webhook events
WEBHOOK_EVENTS = {
    "payment.created": "Payment was created",
    "payment.captured": "Payment was captured",
    "payment.failed": "Payment failed",
    "payment.refunded": "Payment was refunded",
    "payment.cancelled": "Payment was cancelled",
    "payment.disputed": "Payment was disputed",
    "webhook.failed": "Webhook delivery failed",
    "webhook.retry": "Webhook retry attempted"
}
```

## Performance Configuration

### Caching Strategy

```python
# Cache configuration
CACHE_CONFIG = {
    "default_ttl": 3600,
    "max_size": 1000,
    "eviction_policy": "lru",
    "compression": True,
    "serialization": "json"
}

# Cache keys
CACHE_KEYS = {
    "payment": "payment:{id}",
    "user": "user:{id}",
    "api_key": "api_key:{key_id}",
    "webhook": "webhook:{id}",
    "rate_limit": "rate_limit:{key}:{window}"
}
```

### Connection Pooling

```python
# Connection pool settings
POOL_CONFIG = {
    "database": {
        "min_size": 5,
        "max_size": 20,
        "max_overflow": 30,
        "timeout": 30,
        "recycle": 3600
    },
    "redis": {
        "min_size": 2,
        "max_size": 10,
        "timeout": 5,
        "retry_on_timeout": True
    },
    "http": {
        "max_connections": 100,
        "max_keepalive_connections": 20,
        "keepalive_expiry": 30,
        "timeout": 30
    }
}
```

### Async Processing

```python
# Background task configuration
BACKGROUND_TASKS = {
    "webhook_delivery": {
        "max_workers": 10,
        "queue_size": 1000,
        "retry_attempts": 3,
        "retry_delay": 5
    },
    "payment_processing": {
        "max_workers": 5,
        "queue_size": 500,
        "retry_attempts": 2,
        "retry_delay": 10
    },
    "audit_logging": {
        "max_workers": 3,
        "queue_size": 2000,
        "retry_attempts": 1,
        "retry_delay": 1
    }
}
```

## Configuration Validation

### Environment Validation

```python
# src/infrastructure/config.py
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str
    jwt_secret_key: str
    
    database_url: str
    redis_url: str
    
    authorize_net_api_login_id: str
    authorize_net_transaction_key: str
    authorize_net_sandbox: bool = True
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        if v not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            raise ValueError('Log level must be DEBUG, INFO, WARNING, or ERROR')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### Configuration Testing

```python
# tests/test_config.py
import pytest
from src.infrastructure.config import settings

def test_required_settings():
    """Test that all required settings are present."""
    assert settings.secret_key is not None
    assert settings.jwt_secret_key is not None
    assert settings.database_url is not None
    assert settings.redis_url is not None
    assert settings.authorize_net_api_login_id is not None
    assert settings.authorize_net_transaction_key is not None

def test_environment_validation():
    """Test environment validation."""
    with pytest.raises(ValueError):
        settings.environment = "invalid"

def test_log_level_validation():
    """Test log level validation."""
    with pytest.raises(ValueError):
        settings.log_level = "invalid"
```

## Configuration Management

### Environment-Specific Configs

```bash
# Development
cp .env.example .env.development

# Staging
cp .env.example .env.staging

# Production
cp .env.example .env.production
```

### Configuration Deployment

```bash
# Deploy configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Validate configuration
docker-compose exec easypay-api python -c "
from src.infrastructure.config import settings
print('Configuration loaded successfully')
print(f'Environment: {settings.environment}')
print(f'Database: {settings.database_url}')
"
```

## Best Practices

### Security

1. **Never commit secrets**: Use environment variables or secret management
2. **Rotate keys regularly**: Implement key rotation policies
3. **Use strong passwords**: Enforce strong password policies
4. **Enable encryption**: Use TLS for all communications
5. **Audit access**: Log all configuration changes

### Performance

1. **Optimize database**: Tune PostgreSQL settings
2. **Use connection pooling**: Configure appropriate pool sizes
3. **Enable caching**: Use Redis for frequently accessed data
4. **Monitor resources**: Set up resource monitoring
5. **Scale horizontally**: Design for horizontal scaling

### Reliability

1. **Health checks**: Implement comprehensive health checks
2. **Circuit breakers**: Use circuit breakers for external services
3. **Retry logic**: Implement exponential backoff
4. **Graceful degradation**: Handle service failures gracefully
5. **Backup strategy**: Implement regular backups

## Support

For configuration support:

- **Documentation**: https://docs.easypay.com/configuration
- **Support Email**: support@easypay.com
- **GitHub Issues**: https://github.com/easypay/payment-gateway/issues
