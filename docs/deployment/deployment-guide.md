# EasyPay Payment Gateway - Deployment Guide

This comprehensive guide covers deploying the EasyPay Payment Gateway in various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Monitoring Setup](#monitoring-setup)
- [Security Configuration](#security-configuration)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Memory**: Minimum 4GB RAM (8GB recommended for production)
  - **Development**: 4GB RAM (optimized ELK stack)
  - **Production**: 8GB RAM (optimized ELK stack)
  - **Ultra-Light**: 2GB RAM (OpenSearch + Fluentd stack)
- **Storage**: Minimum 20GB free space
- **Network**: HTTPS-capable network access

### Required Services

- PostgreSQL 15+
- Redis 7+
- Authorize.net account (sandbox/production)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/easypay/payment-gateway.git
cd payment-gateway
```

### 2. Environment Variables

Create environment files for different environments:

#### Development Environment (.env.development)

```bash
# Database Configuration
DATABASE_URL=postgresql://easypay:password@localhost:5432/easypay_dev
REDIS_URL=redis://localhost:6379/0

# Authorize.net Configuration
AUTHORIZE_NET_API_LOGIN_ID=your_sandbox_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_sandbox_transaction_key
AUTHORIZE_NET_SANDBOX=true

# Security
SECRET_KEY=your-development-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# API Gateway
KONG_ADMIN_URL=http://localhost:8001
KONG_PROXY_URL=http://localhost:8000
```

#### Production Environment (.env.production)

```bash
# Database Configuration
DATABASE_URL=postgresql://easypay:secure_password@db-host:5432/easypay_prod
REDIS_URL=redis://redis-host:6379/0

# Authorize.net Configuration
AUTHORIZE_NET_API_LOGIN_ID=your_production_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_production_transaction_key
AUTHORIZE_NET_SANDBOX=false

# Security
SECRET_KEY=your-super-secure-production-secret-key
JWT_SECRET_KEY=your-super-secure-jwt-secret-key

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# API Gateway
KONG_ADMIN_URL=https://api-admin.easypay.com
KONG_PROXY_URL=https://api.easypay.com
```

## Docker Deployment

### 1. Quick Start (Development)

#### Standard Development Setup (Optimized ELK Stack)
```bash
# Start all services with optimized ELK stack
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f easypay-api
```

#### Ultra-Lightweight Development Setup (OpenSearch + Fluentd)
```bash
# Start all services with ultra-lightweight stack
docker-compose -f docker-compose.light.yml up -d

# Check service status
docker-compose -f docker-compose.light.yml ps

# View logs
docker-compose -f docker-compose.light.yml logs -f easypay-api
```

#### Resource Usage Comparison
| Configuration | Memory Usage | CPU Usage | Storage |
|---------------|--------------|-----------|---------|
| **Standard ELK** | ~1.3GB | Medium | ~2GB |
| **Ultra-Light** | ~0.6GB | Low | ~1GB |

### 2. Production Deployment

#### Build Production Images

```bash
# Build production image
docker build -t easypay-api:latest .

# Tag for registry
docker tag easypay-api:latest your-registry/easypay-api:latest

# Push to registry
docker push your-registry/easypay-api:latest
```

#### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  easypay-api:
    image: your-registry/easypay-api:latest
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - AUTHORIZE_NET_API_LOGIN_ID=${AUTHORIZE_NET_API_LOGIN_ID}
      - AUTHORIZE_NET_TRANSACTION_KEY=${AUTHORIZE_NET_TRANSACTION_KEY}
      - AUTHORIZE_NET_SANDBOX=${AUTHORIZE_NET_SANDBOX}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=easypay
      - POSTGRES_USER=easypay
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## Production Deployment

### 1. Server Setup

#### Ubuntu 20.04+ Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

### 2. SSL/TLS Configuration

#### Using Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot

# Generate certificate
sudo certbot certonly --standalone -d api.easypay.com

# Auto-renewal setup
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### Nginx Configuration

```nginx
# /etc/nginx/sites-available/easypay
server {
    listen 80;
    server_name api.easypay.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.easypay.com;

    ssl_certificate /etc/letsencrypt/live/api.easypay.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.easypay.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Load Balancer Setup

#### HAProxy Configuration

```haproxy
# /etc/haproxy/haproxy.cfg
global
    daemon
    user haproxy
    group haproxy

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend easypay_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/easypay.pem
    redirect scheme https if !{ ssl_fc }
    
    acl is_health_check path_beg /health
    use_backend health_check if is_health_check
    
    default_backend easypay_backend

backend easypay_backend
    balance roundrobin
    option httpchk GET /health
    server easypay1 127.0.0.1:8000 check
    server easypay2 127.0.0.1:8001 check

backend health_check
    server health 127.0.0.1:8000
```

## Environment Configuration

### 1. Database Configuration

#### PostgreSQL Optimization

```sql
-- /etc/postgresql/15/main/postgresql.conf
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

#### Connection Pooling

```python
# Database connection pool configuration
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

### 2. Redis Configuration

#### Redis Optimization

```conf
# /etc/redis/redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Database Setup

### 1. Database Migration

```bash
# Run migrations
docker-compose exec easypay-api alembic upgrade head

# Check migration status
docker-compose exec easypay-api alembic current

# Create new migration
docker-compose exec easypay-api alembic revision --autogenerate -m "Description"
```

### 2. Database Backup

#### Automated Backup Script

```bash
#!/bin/bash
# backup-database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
DB_NAME="easypay"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create backup
docker-compose exec -T postgres pg_dump -U easypay $DB_NAME > $BACKUP_DIR/easypay_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/easypay_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: easypay_$DATE.sql.gz"
```

#### Cron Job Setup

```bash
# Add to crontab
0 2 * * * /path/to/backup-database.sh
```

## Monitoring Setup

### 1. ELK Stack Configuration Options

#### Standard ELK Stack (Optimized)
The standard configuration uses optimized versions of Elasticsearch, Logstash, and Kibana with reduced memory allocation:

```yaml
# docker-compose.yml - Optimized ELK Stack
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - "ES_JAVA_OPTS=-Xms256m -Xmx256m"  # Reduced from 512MB
      - bootstrap.memory_lock=false        # Disabled for lighter operation
    deploy:
      resources:
        limits:
          memory: 1G                       # Reduced from 2G
          cpus: '1.0'                      # Reduced from 2.0

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    environment:
      - LS_JAVA_OPTS=-Xmx128m -Xms128m    # Reduced from 256MB
    deploy:
      resources:
        limits:
          memory: 512M                     # Reduced from 1G
          cpus: '0.5'                      # Reduced from 1.0

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    deploy:
      resources:
        limits:
          memory: 512M                     # Reduced from 1G
          cpus: '0.5'                      # Reduced from 1.0
```

#### Ultra-Lightweight Stack (OpenSearch + Fluentd)
For maximum resource efficiency, use the ultra-lightweight configuration:

```yaml
# docker-compose.light.yml - Ultra-Lightweight Stack
services:
  opensearch:
    image: opensearchproject/opensearch:2.11.0
    environment:
      - "OPENSEARCH_JAVA_OPTS=-Xms256m -Xmx256m"
      - plugins.security.disabled=true
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:2.11.0
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

  fluentd:
    image: fluent/fluentd:v1.16-debian-1
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.25'
```

#### Choosing the Right Configuration

| Use Case | Configuration | Memory | CPU | Features |
|----------|---------------|--------|-----|----------|
| **Development** | Standard ELK | 1.3GB | Medium | Full features |
| **Production** | Standard ELK | 1.3GB | Medium | Full features |
| **Resource Constrained** | Ultra-Light | 0.6GB | Low | Core features |
| **Testing** | Ultra-Light | 0.6GB | Low | Core features |

### 2. Prometheus Configuration

```yaml
# config/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'easypay-api'
    static_configs:
      - targets: ['easypay-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### 2. Grafana Dashboards

#### Import Dashboard

```bash
# Import EasyPay dashboard
curl -X POST \
  -H "Content-Type: application/json" \
  -d @config/grafana/dashboards/easypay-dashboard.json \
  http://admin:admin@localhost:3000/api/dashboards/db
```

### 3. Alerting Rules

```yaml
# config/alert-rules.yml
groups:
  - name: easypay-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"
          description: "PostgreSQL database is not responding"
```

## Security Configuration

### 1. Firewall Setup

```bash
# UFW configuration
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. API Security

#### Rate Limiting

```python
# Kong rate limiting configuration
rate_limits:
  per_minute: 100
  per_hour: 1000
  per_day: 10000
```

#### CORS Configuration

```python
# CORS settings
CORS_ORIGINS = [
    "https://app.easypay.com",
    "https://dashboard.easypay.com"
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE"]
CORS_ALLOW_HEADERS = ["*"]
```

### 3. Secrets Management

#### Using Docker Secrets

```yaml
# docker-compose.secrets.yml
version: '3.8'

services:
  easypay-api:
    image: easypay-api:latest
    secrets:
      - database_password
      - api_secret_key
    environment:
      - DATABASE_PASSWORD_FILE=/run/secrets/database_password
      - SECRET_KEY_FILE=/run/secrets/api_secret_key

secrets:
  database_password:
    file: ./secrets/database_password.txt
  api_secret_key:
    file: ./secrets/api_secret_key.txt
```

## Backup and Recovery

### 1. Database Backup Strategy

#### Full Backup

```bash
# Daily full backup
pg_dump -h localhost -U easypay -d easypay > backup_$(date +%Y%m%d).sql
```

#### Incremental Backup

```bash
# WAL archiving setup
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'
```

### 2. Application Backup

#### Configuration Backup

```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  config/ \
  .env.production
```

### 3. Recovery Procedures

#### Database Recovery

```bash
# Restore from backup
psql -h localhost -U easypay -d easypay < backup_20240101.sql

# Point-in-time recovery
pg_basebackup -h localhost -U easypay -D /restore/data
```

## Troubleshooting

### 1. Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs easypay-api

# Check service status
docker-compose ps

# Restart service
docker-compose restart easypay-api
```

#### Database Connection Issues

```bash
# Test database connection
docker-compose exec easypay-api python -c "
from src.infrastructure.database import get_database_url
print('Database URL:', get_database_url())
"

# Check database status
docker-compose exec postgres pg_isready -U easypay
```

#### Redis Connection Issues

```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

### 2. Performance Issues

#### High Memory Usage

```bash
# Check memory usage
docker stats

# Optimize PostgreSQL
# Increase shared_buffers in postgresql.conf
```

#### Slow Response Times

```bash
# Check application metrics
curl http://localhost:8000/metrics

# Check database performance
docker-compose exec postgres psql -U easypay -d easypay -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"
```

### 3. Monitoring and Debugging

#### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# Readiness check
curl http://localhost:8000/health/ready
```

#### Log Analysis

```bash
# View application logs
docker-compose logs -f easypay-api

# Search for errors
docker-compose logs easypay-api | grep ERROR

# Monitor logs in real-time
docker-compose logs -f --tail=100 easypay-api
```

## Support

For deployment support and troubleshooting:

- **Documentation**: https://docs.easypay.com/deployment
- **Support Email**: support@easypay.com
- **Status Page**: https://status.easypay.com
- **GitHub Issues**: https://github.com/easypay/payment-gateway/issues
