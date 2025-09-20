# EasyPay Payment Gateway - Troubleshooting Guide

This comprehensive troubleshooting guide helps you diagnose and resolve common issues with the EasyPay Payment Gateway.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Service-Specific Issues](#service-specific-issues)
- [Performance Issues](#performance-issues)
- [Security Issues](#security-issues)
- [Database Issues](#database-issues)
- [Network Issues](#network-issues)
- [Monitoring and Debugging](#monitoring-and-debugging)
- [Emergency Procedures](#emergency-procedures)
- [Support Resources](#support-resources)

## Quick Diagnostics

### Health Check Commands

```bash
# Check overall system health
curl http://localhost:8000/health

# Check detailed health status
curl http://localhost:8000/health/detailed

# Check service readiness
curl http://localhost:8000/health/ready

# Check service liveness
curl http://localhost:8000/health/live

# Check Prometheus metrics
curl http://localhost:8000/metrics
```

### Service Status Commands

```bash
# Check Docker services
docker-compose ps

# Check service logs
docker-compose logs -f easypay-api
docker-compose logs -f postgres
docker-compose logs -f redis

# Check resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h
```

## Common Issues

### 1. Service Won't Start

#### Symptoms
- Docker containers fail to start
- Application crashes on startup
- Health checks fail

#### Diagnosis

```bash
# Check Docker logs
docker-compose logs easypay-api

# Check container status
docker-compose ps

# Check resource availability
docker system df
```

#### Solutions

**Insufficient Resources:**
```bash
# Clean up Docker resources
docker system prune -a
docker volume prune

# Increase memory limits in docker-compose.yml
services:
  easypay-api:
    deploy:
      resources:
        limits:
          memory: 2G
```

**Configuration Issues:**
```bash
# Validate environment variables
docker-compose exec easypay-api env | grep -E "(DATABASE|REDIS|AUTHORIZE)"

# Check configuration file
docker-compose exec easypay-api python -c "
from src.infrastructure.config import settings
print('Configuration loaded successfully')
"
```

**Port Conflicts:**
```bash
# Check port usage
netstat -tulpn | grep :8000
lsof -i :8000

# Change ports in docker-compose.yml
ports:
  - "8001:8000"  # Use different external port
```

### 2. Database Connection Issues

#### Symptoms
- "Database connection failed" errors
- Slow response times
- Connection timeout errors

#### Diagnosis

```bash
# Test database connectivity
docker-compose exec easypay-api python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://easypay:password@postgres:5432/easypay')
    print('Database connection successful')
    conn.close()
except Exception as e:
    print(f'Database connection failed: {e}')
"

# Check PostgreSQL status
docker-compose exec postgres pg_isready -U easypay

# Check database logs
docker-compose logs postgres
```

#### Solutions

**Connection Pool Exhaustion:**
```python
# Increase connection pool size
DATABASE_POOL_SIZE = 30
DATABASE_MAX_OVERFLOW = 50
```

**Database Performance:**
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Optimize PostgreSQL settings
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
SELECT pg_reload_conf();
```

**Network Issues:**
```bash
# Test network connectivity
docker-compose exec easypay-api ping postgres
docker-compose exec easypay-api nc -zv postgres 5432
```

### 3. Redis Connection Issues

#### Symptoms
- Cache operations failing
- "Redis connection refused" errors
- Session management issues

#### Diagnosis

```bash
# Test Redis connectivity
docker-compose exec redis redis-cli ping

# Check Redis status
docker-compose exec redis redis-cli info

# Check Redis logs
docker-compose logs redis
```

#### Solutions

**Memory Issues:**
```bash
# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Configure Redis memory limits
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

**Connection Issues:**
```python
# Increase Redis connection pool
REDIS_POOL_SIZE = 20
REDIS_MAX_CONNECTIONS = 100
```

### 4. Authentication Issues

#### Symptoms
- "Invalid API key" errors
- JWT token validation failures
- Permission denied errors

#### Diagnosis

```bash
# Test API key authentication
curl -H "Authorization: Bearer ak_test:sk_test" \
     http://localhost:8000/api/v1/payments

# Check authentication logs
docker-compose logs easypay-api | grep -i auth

# Validate JWT token
python -c "
import jwt
token = 'your_jwt_token'
try:
    decoded = jwt.decode(token, 'your_secret', algorithms=['HS256'])
    print('JWT token valid')
except Exception as e:
    print(f'JWT token invalid: {e}')
"
```

#### Solutions

**API Key Issues:**
```bash
# Create new API key
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test API Key",
       "permissions": ["payments:read", "payments:write"]
     }'
```

**JWT Token Issues:**
```python
# Check JWT configuration
JWT_SECRET_KEY = "your-secret-key"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
```

## Service-Specific Issues

### Payment Processing Issues

#### Authorize.net Connection Problems

**Symptoms:**
- Payment processing timeouts
- "External service unavailable" errors
- Transaction failures

**Diagnosis:**
```bash
# Test Authorize.net connectivity
curl -X POST https://apitest.authorize.net/xml/v1/request.api \
     -H "Content-Type: application/json" \
     -d '{
       "authenticateTestRequest": {
         "merchantAuthentication": {
           "name": "your_login_id",
           "transactionKey": "your_transaction_key"
         }
       }
     }'

# Check Authorize.net configuration
docker-compose exec easypay-api python -c "
from src.integrations.authorize_net.client import AuthorizeNetClient
client = AuthorizeNetClient()
print('Authorize.net client initialized')
"
```

**Solutions:**
```python
# Increase timeout settings
AUTHORIZE_NET_TIMEOUT = 60
AUTHORIZE_NET_RETRY_ATTEMPTS = 5
AUTHORIZE_NET_RETRY_DELAY = 2
```

#### Payment Validation Errors

**Symptoms:**
- "Invalid payment data" errors
- Card declined errors
- Amount validation failures

**Diagnosis:**
```bash
# Test payment creation
curl -X POST http://localhost:8000/api/v1/payments \
     -H "Authorization: Bearer ak_test:sk_test" \
     -H "Content-Type: application/json" \
     -d '{
       "amount": "10.00",
       "currency": "USD",
       "payment_method": "credit_card",
       "card_token": "tok_test"
     }'
```

**Solutions:**
```python
# Validate payment data
PAYMENT_VALIDATION_RULES = {
    "min_amount": 0.01,
    "max_amount": 100000.00,
    "supported_currencies": ["USD", "EUR", "GBP"],
    "required_fields": ["amount", "currency", "payment_method"]
}
```

### Webhook Issues

#### Webhook Delivery Failures

**Symptoms:**
- Webhooks not being delivered
- "Webhook delivery failed" errors
- Retry attempts exhausting

**Diagnosis:**
```bash
# Check webhook status
curl http://localhost:8000/api/v1/webhooks

# Check webhook logs
docker-compose logs easypay-api | grep -i webhook

# Test webhook endpoint
curl -X POST http://your-webhook-url.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'
```

**Solutions:**
```python
# Increase webhook retry settings
WEBHOOK_MAX_RETRIES = 10
WEBHOOK_RETRY_DELAYS = [5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560]
WEBHOOK_TIMEOUT = 60
```

#### Webhook Signature Validation

**Symptoms:**
- "Invalid webhook signature" errors
- Webhook processing failures

**Diagnosis:**
```python
# Test webhook signature validation
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)
```

**Solutions:**
```python
# Configure webhook secrets
WEBHOOK_SECRETS = {
    "payment_events": "your-payment-webhook-secret",
    "fraud_events": "your-fraud-webhook-secret"
}
```

## Performance Issues

### High Response Times

#### Symptoms
- API responses > 2 seconds
- Timeout errors
- User complaints about slow performance

#### Diagnosis

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Monitor metrics
curl http://localhost:8000/metrics | grep response_time

# Check database performance
docker-compose exec postgres psql -U easypay -d easypay -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"
```

#### Solutions

**Database Optimization:**
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_payments_status_created ON payments(status, created_at);
CREATE INDEX CONCURRENTLY idx_payments_customer_status ON payments(customer_id, status);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM payments WHERE status = 'captured' AND created_at > '2024-01-01';
```

**Caching Optimization:**
```python
# Increase cache TTL
CACHE_TTL = {
    "payment": 7200,  # 2 hours
    "user": 3600,     # 1 hour
    "api_key": 14400  # 4 hours
}
```

**Connection Pool Tuning:**
```python
# Optimize connection pools
DATABASE_POOL_SIZE = 30
DATABASE_MAX_OVERFLOW = 50
REDIS_POOL_SIZE = 20
```

### Memory Issues

#### Symptoms
- Out of memory errors
- Slow garbage collection
- High memory usage

#### Diagnosis

```bash
# Check memory usage
docker stats

# Check application memory
docker-compose exec easypay-api python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"

# Check system memory
free -h
```

#### Solutions

**Memory Optimization:**
```python
# Optimize memory usage
import gc
gc.set_threshold(700, 10, 10)  # More aggressive garbage collection

# Use memory-efficient data structures
from collections import deque
cache = deque(maxlen=1000)  # Bounded cache
```

**Resource Limits:**
```yaml
# docker-compose.yml
services:
  easypay-api:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

## Security Issues

### Authentication Bypass

#### Symptoms
- Unauthorized access to endpoints
- Missing authentication errors
- Security audit failures

#### Diagnosis

```bash
# Test authentication bypass
curl http://localhost:8000/api/v1/payments  # Should return 401

# Check authentication middleware
docker-compose logs easypay-api | grep -i "authentication"

# Verify API key validation
python -c "
from src.api.v1.middleware.auth import validate_api_key
result = validate_api_key('invalid_key')
print(f'API key validation: {result}')
"
```

#### Solutions

**Strengthen Authentication:**
```python
# Implement stronger authentication
AUTHENTICATION_CONFIG = {
    "require_https": True,
    "api_key_length": 32,
    "jwt_expiry_minutes": 60,
    "refresh_token_expiry_days": 30
}
```

### Rate Limiting Issues

#### Symptoms
- API abuse
- Service overload
- Legitimate users blocked

#### Diagnosis

```bash
# Test rate limiting
for i in {1..110}; do
  curl http://localhost:8000/api/v1/payments
done

# Check rate limit headers
curl -I http://localhost:8000/api/v1/payments
```

#### Solutions

**Adjust Rate Limits:**
```python
# Configure appropriate rate limits
RATE_LIMITS = {
    "default": {"per_minute": 100, "per_hour": 1000},
    "payment": {"per_minute": 50, "per_hour": 500},
    "admin": {"per_minute": 20, "per_hour": 200}
}
```

## Database Issues

### Connection Pool Exhaustion

#### Symptoms
- "Too many connections" errors
- Database connection timeouts
- Application hangs

#### Diagnosis

```sql
-- Check active connections
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- Check connection limits
SHOW max_connections;

-- Check connection pool status
SELECT * FROM pg_stat_bgwriter;
```

#### Solutions

**Optimize Connection Pool:**
```python
# Adjust connection pool settings
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

### Slow Queries

#### Symptoms
- High database CPU usage
- Slow API responses
- Query timeouts

#### Diagnosis

```sql
-- Identify slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats 
WHERE schemaname = 'public' 
AND n_distinct > 100;
```

#### Solutions

**Query Optimization:**
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_payments_customer_created 
ON payments(customer_id, created_at);

-- Optimize queries
EXPLAIN ANALYZE SELECT * FROM payments 
WHERE customer_id = 'cust_123' 
AND created_at > '2024-01-01';
```

## Network Issues

### DNS Resolution Problems

#### Symptoms
- "Name or service not known" errors
- Service discovery failures
- Connection timeouts

#### Diagnosis

```bash
# Test DNS resolution
docker-compose exec easypay-api nslookup postgres
docker-compose exec easypay-api nslookup redis

# Check network connectivity
docker-compose exec easypay-api ping postgres
docker-compose exec easypay-api ping redis
```

#### Solutions

**Network Configuration:**
```yaml
# docker-compose.yml
services:
  easypay-api:
    networks:
      - easypay-network
    extra_hosts:
      - "postgres:172.20.0.2"
      - "redis:172.20.0.3"

networks:
  easypay-network:
    driver: bridge
```

### Firewall Issues

#### Symptoms
- Connection refused errors
- Port access denied
- Service unreachable

#### Diagnosis

```bash
# Check port accessibility
netstat -tulpn | grep :8000
lsof -i :8000

# Test port connectivity
telnet localhost 8000
nc -zv localhost 8000
```

#### Solutions

**Firewall Configuration:**
```bash
# Configure UFW
sudo ufw allow 8000/tcp
sudo ufw allow 5432/tcp
sudo ufw allow 6379/tcp

# Configure iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5432 -j ACCEPT
```

## Monitoring and Debugging

### Log Analysis

#### Application Logs

```bash
# View application logs
docker-compose logs -f easypay-api

# Filter error logs
docker-compose logs easypay-api | grep ERROR

# Search for specific patterns
docker-compose logs easypay-api | grep -E "(payment|webhook|auth)"
```

#### Database Logs

```bash
# View PostgreSQL logs
docker-compose logs postgres

# Enable query logging
# postgresql.conf
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000
```

#### Redis Logs

```bash
# View Redis logs
docker-compose logs redis

# Enable Redis logging
# redis.conf
loglevel notice
logfile /var/log/redis/redis.log
```

### Metrics Analysis

#### Prometheus Metrics

```bash
# Query metrics
curl "http://localhost:9090/api/v1/query?query=up"

# Check specific metrics
curl "http://localhost:9090/api/v1/query?query=http_requests_total"

# Monitor error rates
curl "http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~'5..'}[5m])"
```

#### Custom Metrics

```python
# Add custom metrics
from prometheus_client import Counter, Histogram

payment_counter = Counter('payments_total', 'Total payments', ['status'])
response_time = Histogram('api_response_time_seconds', 'API response time')

# Use in application
payment_counter.labels(status='success').inc()
response_time.observe(0.5)
```

### Debugging Tools

#### Application Debugging

```python
# Enable debug mode
import logging
logging.basicConfig(level=logging.DEBUG)

# Add debug logging
logger = logging.getLogger(__name__)
logger.debug(f"Processing payment: {payment_id}")

# Use debugger
import pdb; pdb.set_trace()
```

#### Database Debugging

```sql
-- Enable query logging
SET log_statement = 'all';
SET log_duration = on;

-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM payments WHERE id = 'payment_id';

-- Check table statistics
ANALYZE payments;
```

## Emergency Procedures

### Service Recovery

#### Complete Service Restart

```bash
# Stop all services
docker-compose down

# Clean up resources
docker system prune -f

# Restart services
docker-compose up -d

# Verify services
docker-compose ps
curl http://localhost:8000/health
```

#### Database Recovery

```bash
# Stop application
docker-compose stop easypay-api

# Backup database
docker-compose exec postgres pg_dump -U easypay easypay > backup.sql

# Restore database if needed
docker-compose exec -T postgres psql -U easypay easypay < backup.sql

# Restart application
docker-compose start easypay-api
```

#### Cache Recovery

```bash
# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Restart Redis
docker-compose restart redis

# Verify cache
docker-compose exec redis redis-cli ping
```

### Rollback Procedures

#### Application Rollback

```bash
# Rollback to previous version
docker tag easypay-api:latest easypay-api:broken
docker tag easypay-api:previous easypay-api:latest

# Restart with previous version
docker-compose up -d easypay-api
```

#### Database Rollback

```bash
# Rollback database migration
docker-compose exec easypay-api alembic downgrade -1

# Verify rollback
docker-compose exec easypay-api alembic current
```

### Incident Response

#### High Priority Issues

1. **Service Down**: Immediate restart and investigation
2. **Security Breach**: Isolate service and investigate
3. **Data Loss**: Stop writes and restore from backup
4. **Performance Degradation**: Scale resources and optimize

#### Communication Plan

1. **Internal**: Notify team via Slack/email
2. **External**: Update status page
3. **Customers**: Send incident notifications
4. **Post-Incident**: Conduct post-mortem

## Support Resources

### Documentation

- **API Documentation**: https://docs.easypay.com/api
- **Deployment Guide**: https://docs.easypay.com/deployment
- **Configuration Guide**: https://docs.easypay.com/configuration

### Monitoring Tools

- **Grafana Dashboards**: http://localhost:3000
- **Prometheus Metrics**: http://localhost:9090
- **Kibana Logs**: http://localhost:5601

### Contact Information

- **Support Email**: support@easypay.com
- **Emergency Hotline**: +1-800-EASYPAY
- **Status Page**: https://status.easypay.com
- **GitHub Issues**: https://github.com/easypay/payment-gateway/issues

### Escalation Procedures

1. **Level 1**: Check documentation and run diagnostics
2. **Level 2**: Contact support team
3. **Level 3**: Escalate to engineering team
4. **Level 4**: Contact vendor support (Authorize.net, etc.)

### Post-Incident Actions

1. **Document**: Record incident details and resolution
2. **Analyze**: Identify root cause and contributing factors
3. **Improve**: Implement preventive measures
4. **Share**: Communicate lessons learned to team
