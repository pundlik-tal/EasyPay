# EasyPay Payment Gateway - Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the EasyPay Payment Gateway to production. The deployment process includes setting up the production environment, configuring security, implementing monitoring, and establishing backup systems.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **CPU**: Minimum 4 cores, 8 cores recommended
- **Memory**: Minimum 8GB RAM, 16GB recommended
- **Storage**: Minimum 100GB SSD, 500GB recommended
- **Network**: Stable internet connection with static IP

### Software Requirements

- Docker 20.10+
- Docker Compose 2.0+
- Git
- curl
- jq (for JSON processing)

### External Services

- PostgreSQL 15+ (managed service recommended)
- Redis 7+ (managed service recommended)
- SSL Certificate (Let's Encrypt or commercial)
- Domain name with DNS control
- Authorize.net sandbox/production account

## Pre-Deployment Setup

### 1. Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y docker.io docker-compose git curl jq

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

### 2. Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/easypay.git
cd easypay

# Checkout production branch
git checkout production
```

### 3. Environment Configuration

```bash
# Copy environment template
cp env.production.template .env.production

# Edit environment variables
nano .env.production
```

**Required Environment Variables:**

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database
POSTGRES_DB=easypay
POSTGRES_USER=easypay
POSTGRES_PASSWORD=your-secure-password

# Redis Configuration
REDIS_URL=redis://username:password@host:port/database

# Security Keys
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Authorize.net Configuration
AUTHORIZE_NET_API_LOGIN_ID=your-api-login-id
AUTHORIZE_NET_TRANSACTION_KEY=your-transaction-key
AUTHORIZE_NET_SANDBOX=false
AUTHORIZE_NET_WEBHOOK_SECRET=your-webhook-secret

# Monitoring
GRAFANA_ADMIN_PASSWORD=your-grafana-password

# Backup Configuration (Optional)
BACKUP_S3_BUCKET=your-backup-bucket
BACKUP_S3_ACCESS_KEY=your-s3-access-key
BACKUP_S3_SECRET_KEY=your-s3-secret-key
```

### 4. SSL Certificate Setup

```bash
# Create SSL directory
sudo mkdir -p /ssl
sudo chown $USER:$USER /ssl

# Copy SSL certificates
sudo cp your-cert.pem /ssl/cert.pem
sudo cp your-key.pem /ssl/key.pem
sudo cp your-ca.pem /ssl/ca.pem

# Set proper permissions
sudo chmod 600 /ssl/*.pem
sudo chown root:root /ssl/*.pem
```

## Deployment Process

### 1. Automated Deployment

The easiest way to deploy is using the automated deployment script:

```bash
# Make deployment script executable
chmod +x scripts/deploy-production.sh

# Run deployment
./scripts/deploy-production.sh
```

### 2. Manual Deployment Steps

If you prefer manual deployment, follow these steps:

#### Step 1: Build Production Images

```bash
# Build main application image
docker build -f docker/Dockerfile.production -t easypay-api:production .

# Build all service images
docker-compose -f docker-compose.production.yml build
```

#### Step 2: Start Database Services

```bash
# Start database and cache services
docker-compose -f docker-compose.production.yml up -d postgres redis

# Wait for services to be ready
sleep 30
```

#### Step 3: Run Database Migrations

```bash
# Run Alembic migrations
docker-compose -f docker-compose.production.yml run --rm easypay-api alembic upgrade head
```

#### Step 4: Deploy All Services

```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check service status
docker-compose -f docker-compose.production.yml ps
```

#### Step 5: Verify Deployment

```bash
# Run health checks
./scripts/health-check.sh comprehensive

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8001/status
```

## Post-Deployment Configuration

### 1. DNS Configuration

Update your DNS records to point to your server:

```
# A Records
api.yourdomain.com    -> YOUR_SERVER_IP
dashboard.yourdomain.com -> YOUR_SERVER_IP

# CNAME Records
www.yourdomain.com    -> yourdomain.com
```

### 2. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # Kong Gateway
sudo ufw allow 8001/tcp  # Kong Admin (restrict to admin IPs)
sudo ufw allow 9090/tcp  # Prometheus (restrict to admin IPs)
sudo ufw allow 3000/tcp  # Grafana (restrict to admin IPs)
```

### 3. SSL/TLS Configuration

Update Kong configuration for SSL termination:

```bash
# Edit Kong configuration
nano kong/kong.yml

# Add SSL configuration
services:
  - name: easypay-api
    url: http://easypay-api:8000
    routes:
      - name: easypay-route
        paths:
          - "/"
        protocols:
          - "https"
    plugins:
      - name: ssl
        config:
          cert: /ssl/cert.pem
          key: /ssl/key.pem
```

### 4. Monitoring Setup

#### Prometheus Configuration

```bash
# Update Prometheus configuration
nano config/prometheus/production.yml

# Add your server IP to targets
scrape_configs:
  - job_name: 'easypay-api'
    static_configs:
      - targets: ['YOUR_SERVER_IP:8000']
```

#### Grafana Dashboard Setup

1. Access Grafana: `http://yourdomain.com:3000`
2. Login with admin credentials
3. Import dashboards from `config/grafana/dashboards/`
4. Configure data sources

### 5. Backup Configuration

#### Automated Backups

```bash
# Set up cron job for daily backups
crontab -e

# Add backup schedule (daily at 2 AM)
0 2 * * * /path/to/easypay/scripts/backup.sh
```

#### S3 Backup Configuration

If using S3 for backups:

```bash
# Install AWS CLI
sudo apt install awscli

# Configure AWS credentials
aws configure
```

## Security Configuration

### 1. API Key Management

```bash
# Generate API keys for production
docker-compose -f docker-compose.production.yml exec easypay-api python -c "
from src.core.services.auth_service import AuthService
auth_service = AuthService()
api_key = auth_service.create_api_key('production-client', 'production')
print(f'API Key: {api_key}')
"
```

### 2. Security Headers

Verify security headers are properly configured:

```bash
# Test security headers
curl -I https://api.yourdomain.com/health

# Expected headers:
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# Content-Security-Policy: default-src 'self'
```

### 3. Rate Limiting

Configure rate limiting in Kong:

```bash
# Update Kong configuration
nano kong/kong.yml

# Add rate limiting plugin
plugins:
  - name: rate-limiting
    config:
      minute: 1000
      hour: 10000
      day: 100000
```

## Monitoring and Alerting

### 1. Prometheus Alerts

Configure alerting rules:

```bash
# Edit alerting rules
nano config/prometheus/alerts.yml

# Update alert manager configuration
nano config/prometheus/alertmanager.yml
```

### 2. Grafana Dashboards

Import production dashboards:

1. **Operational Dashboard**: System metrics, service health
2. **Business Dashboard**: Payment metrics, success rates
3. **Security Dashboard**: Authentication, authorization events

### 3. Log Aggregation

Configure ELK stack for log aggregation:

```bash
# Check Elasticsearch status
curl http://localhost:9200/_cluster/health

# Access Kibana
open http://localhost:5601
```

## Backup and Recovery

### 1. Database Backups

```bash
# Manual backup
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh backup_file.sql.gz
```

### 2. Configuration Backups

```bash
# Backup configuration files
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/ scripts/ docker-compose.production.yml
```

### 3. Disaster Recovery

In case of complete system failure:

1. **Restore from backup**:
   ```bash
   ./scripts/restore.sh latest-backup.sql.gz
   ```

2. **Redeploy services**:
   ```bash
   ./scripts/deploy-production.sh
   ```

3. **Verify functionality**:
   ```bash
   ./scripts/health-check.sh comprehensive
   ```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database status
docker-compose -f docker-compose.production.yml ps postgres

# Check database logs
docker-compose -f docker-compose.production.yml logs postgres

# Test database connection
docker-compose -f docker-compose.production.yml exec postgres psql -U easypay -d easypay -c "SELECT 1;"
```

#### 2. SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in /ssl/cert.pem -text -noout

# Test SSL connection
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

#### 3. Service Startup Issues

```bash
# Check service logs
docker-compose -f docker-compose.production.yml logs easypay-api

# Restart specific service
docker-compose -f docker-compose.production.yml restart easypay-api
```

### Performance Optimization

#### 1. Database Optimization

```bash
# Run database optimization
docker-compose -f docker-compose.production.yml exec postgres psql -U easypay -d easypay -c "VACUUM ANALYZE;"
```

#### 2. Cache Optimization

```bash
# Check Redis memory usage
docker-compose -f docker-compose.production.yml exec redis redis-cli info memory
```

#### 3. Application Optimization

```bash
# Check application metrics
curl http://localhost:8000/metrics
```

## Maintenance

### 1. Regular Maintenance Tasks

- **Daily**: Check health status, review logs
- **Weekly**: Review performance metrics, update dependencies
- **Monthly**: Security updates, backup verification
- **Quarterly**: Full security audit, disaster recovery test

### 2. Updates and Upgrades

```bash
# Update application code
git pull origin production

# Rebuild and redeploy
./scripts/deploy-production.sh
```

### 3. Scaling

For high-traffic scenarios:

1. **Horizontal Scaling**: Add more application instances
2. **Database Scaling**: Use read replicas, connection pooling
3. **Cache Scaling**: Redis cluster, distributed caching
4. **Load Balancing**: Multiple Kong instances

## Support and Documentation

### Resources

- **API Documentation**: `http://yourdomain.com/docs`
- **Health Check**: `http://yourdomain.com/health`
- **Metrics**: `http://yourdomain.com/metrics`
- **Monitoring**: `http://yourdomain.com:3000`

### Contact Information

- **Technical Support**: support@easypay.com
- **Security Issues**: security@easypay.com
- **Documentation**: docs@easypay.com

## Conclusion

This deployment guide provides comprehensive instructions for deploying EasyPay to production. Follow all steps carefully and perform thorough testing before going live. Regular monitoring and maintenance are essential for a successful production deployment.

For additional support or questions, please refer to the troubleshooting section or contact the support team.
