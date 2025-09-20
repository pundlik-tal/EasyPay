# EasyPay Payment Gateway - ELK Stack Optimization Guide

This document provides comprehensive information about the optimized ELK stack configurations available in the EasyPay Payment Gateway system.

## Table of Contents

- [Overview](#overview)
- [Configuration Options](#configuration-options)
- [Resource Optimization](#resource-optimization)
- [Performance Comparison](#performance-comparison)
- [Migration Guide](#migration-guide)
- [Troubleshooting](#troubleshooting)

## Overview

The EasyPay Payment Gateway offers multiple ELK stack configurations to meet different resource requirements and use cases:

1. **Standard ELK Stack (Optimized)**: Full-featured with reduced resource usage
2. **Ultra-Lightweight Stack**: OpenSearch + Fluentd for maximum efficiency
3. **Production ELK Stack**: Optimized for production workloads

## Configuration Options

### 1. Standard ELK Stack (Optimized)

**File**: `docker-compose.yml`

**Components**:
- Elasticsearch 8.11.0 (optimized)
- Logstash 8.11.0 (optimized)
- Kibana 8.11.0 (optimized)

**Key Optimizations**:
```yaml
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

**Usage**:
```bash
# Start optimized ELK stack
docker-compose up -d

# Check resource usage
docker stats elasticsearch logstash kibana
```

### 2. Ultra-Lightweight Stack (OpenSearch + Fluentd)

**File**: `docker-compose.light.yml`

**Components**:
- OpenSearch 2.11.0
- OpenSearch Dashboards 2.11.0
- Fluentd v1.16-debian-1

**Configuration**:
```yaml
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

**Usage**:
```bash
# Start ultra-lightweight stack
docker-compose -f docker-compose.light.yml up -d

# Check resource usage
docker stats opensearch opensearch-dashboards fluentd
```

### 3. Production ELK Stack (Optimized)

**File**: `docker-compose.production.yml`

**Components**:
- Elasticsearch 8.11.0 (production optimized)
- Logstash 8.11.0 (production optimized)
- Kibana 8.11.0 (production optimized)

**Production Optimizations**:
```yaml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - "ES_JAVA_OPTS=-Xms512m -Xmx512m"  # Production-optimized
    - bootstrap.memory_lock=false        # Disabled for lighter operation
  deploy:
    resources:
      limits:
        memory: 1G                       # Production limit
        cpus: '1.0'                      # Production limit
      reservations:
        memory: 512M                     # Guaranteed memory
        cpus: '0.5'                      # Guaranteed CPU

logstash:
  image: docker.elastic.co/logstash/logstash:8.11.0
  environment:
    - LS_JAVA_OPTS=-Xmx256m -Xms256m    # Production-optimized
  deploy:
    resources:
      limits:
        memory: 512M                     # Production limit
        cpus: '0.5'                      # Production limit
      reservations:
        memory: 256M                     # Guaranteed memory
        cpus: '0.25'                     # Guaranteed CPU

kibana:
  image: docker.elastic.co/kibana/kibana:8.11.0
  deploy:
    resources:
      limits:
        memory: 512M                     # Production limit
        cpus: '0.5'                      # Production limit
      reservations:
        memory: 256M                     # Guaranteed memory
        cpus: '0.25'                     # Guaranteed CPU
```

## Resource Optimization

### Memory Optimization

#### Elasticsearch Memory Settings
```bash
# Standard ELK Stack
ES_JAVA_OPTS=-Xms256m -Xmx256m

# Production ELK Stack
ES_JAVA_OPTS=-Xms512m -Xmx512m

# Ultra-Lightweight Stack
OPENSEARCH_JAVA_OPTS=-Xms256m -Xmx256m
```

#### Logstash Memory Settings
```bash
# Standard ELK Stack
LS_JAVA_OPTS=-Xmx128m -Xms128m

# Production ELK Stack
LS_JAVA_OPTS=-Xmx256m -Xms256m

# Ultra-Lightweight Stack (Fluentd)
# No Java heap settings (Ruby-based)
```

### CPU Optimization

#### Resource Limits
```yaml
# Standard ELK Stack
elasticsearch:
  deploy:
    resources:
      limits:
        cpus: '1.0'
logstash:
  deploy:
    resources:
      limits:
        cpus: '0.5'
kibana:
  deploy:
    resources:
      limits:
        cpus: '0.5'

# Ultra-Lightweight Stack
opensearch:
  deploy:
    resources:
      limits:
        cpus: '0.5'
opensearch-dashboards:
  deploy:
    resources:
      limits:
        cpus: '0.25'
fluentd:
  deploy:
    resources:
      limits:
        cpus: '0.25'
```

### Storage Optimization

#### Data Retention
```yaml
# Elasticsearch/OpenSearch settings
elasticsearch:
  environment:
    - "ES_JAVA_OPTS=-Xms256m -Xmx256m"
    - "indices.lifecycle.poll_interval=1m"
    - "indices.lifecycle.check_interval=1m"
```

#### Log Rotation
```yaml
# Logstash settings
logstash:
  environment:
    - "LS_JAVA_OPTS=-Xmx128m -Xms128m"
    - "pipeline.workers=2"
    - "pipeline.batch.size=125"
```

## Performance Comparison

### Resource Usage Comparison

| Configuration | Total Memory | Total CPU | Storage | Startup Time |
|---------------|--------------|-----------|---------|--------------|
| **Standard ELK** | 1.3GB | 2.0 cores | ~2GB | 2-3 minutes |
| **Production ELK** | 1.3GB | 2.0 cores | ~2GB | 2-3 minutes |
| **Ultra-Light** | 0.6GB | 1.0 cores | ~1GB | 1-2 minutes |

### Feature Comparison

| Feature | Standard ELK | Production ELK | Ultra-Light |
|---------|--------------|----------------|-------------|
| **Log Storage** | ✅ Elasticsearch | ✅ Elasticsearch | ✅ OpenSearch |
| **Log Processing** | ✅ Logstash | ✅ Logstash | ✅ Fluentd |
| **Visualization** | ✅ Kibana | ✅ Kibana | ✅ OpenSearch Dashboards |
| **Security** | ✅ X-Pack | ✅ X-Pack | ✅ OpenSearch Security |
| **Machine Learning** | ✅ X-Pack ML | ✅ X-Pack ML | ❌ Not Available |
| **APM** | ✅ X-Pack APM | ✅ X-Pack APM | ❌ Not Available |

### Performance Metrics

#### Query Performance
```bash
# Standard ELK Stack
curl -X GET "localhost:9200/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match_all": {}
  }
}'

# Ultra-Lightweight Stack
curl -X GET "localhost:9200/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match_all": {}
  }
}'
```

#### Index Performance
```bash
# Check index performance
curl -X GET "localhost:9200/_cat/indices?v"

# Check cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"
```

## Migration Guide

### From Standard ELK to Ultra-Lightweight

#### Step 1: Backup Data
```bash
# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup_repo/snapshot_1" -H 'Content-Type: application/json' -d'
{
  "indices": "*",
  "ignore_unavailable": true,
  "include_global_state": false
}'
```

#### Step 2: Stop Standard ELK
```bash
docker-compose down
```

#### Step 3: Start Ultra-Lightweight Stack
```bash
docker-compose -f docker-compose.light.yml up -d
```

#### Step 4: Restore Data
```bash
# Restore snapshot to OpenSearch
curl -X POST "localhost:9200/_snapshot/backup_repo/snapshot_1/_restore" -H 'Content-Type: application/json' -d'
{
  "indices": "*",
  "ignore_unavailable": true,
  "include_global_state": false
}'
```

### From Ultra-Lightweight to Standard ELK

#### Step 1: Export Data
```bash
# Export OpenSearch data
curl -X GET "localhost:9200/_search?scroll=1m" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match_all": {}
  }
}'
```

#### Step 2: Stop Ultra-Lightweight Stack
```bash
docker-compose -f docker-compose.light.yml down
```

#### Step 3: Start Standard ELK
```bash
docker-compose up -d
```

#### Step 4: Import Data
```bash
# Import data to Elasticsearch
curl -X POST "localhost:9200/_bulk" -H 'Content-Type: application/json' --data-binary @exported_data.json
```

## Troubleshooting

### Common Issues

#### 1. High Memory Usage

**Problem**: ELK stack consuming too much memory

**Solution**:
```bash
# Check memory usage
docker stats elasticsearch logstash kibana

# Reduce heap size
ES_JAVA_OPTS=-Xms128m -Xmx128m
LS_JAVA_OPTS=-Xmx64m -Xms64m
```

#### 2. Slow Query Performance

**Problem**: Queries taking too long

**Solution**:
```bash
# Check cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Optimize indices
curl -X POST "localhost:9200/_forcemerge?max_num_segments=1"
```

#### 3. Service Startup Issues

**Problem**: Services failing to start

**Solution**:
```bash
# Check logs
docker-compose logs elasticsearch
docker-compose logs logstash
docker-compose logs kibana

# Check resource limits
docker-compose config
```

### Performance Tuning

#### Elasticsearch Tuning
```yaml
# Optimize for low memory
elasticsearch:
  environment:
    - "ES_JAVA_OPTS=-Xms256m -Xmx256m"
    - "indices.memory.index_buffer_size=10%"
    - "indices.memory.min_index_buffer_size=48mb"
    - "indices.queries.cache.size=10%"
```

#### Logstash Tuning
```yaml
# Optimize for low memory
logstash:
  environment:
    - "LS_JAVA_OPTS=-Xmx128m -Xms128m"
    - "pipeline.workers=2"
    - "pipeline.batch.size=125"
    - "pipeline.batch.delay=50"
```

#### Kibana Tuning
```yaml
# Optimize for low memory
kibana:
  environment:
    - "NODE_OPTIONS=--max-old-space-size=512"
    - "KIBANA_OPTS=--optimize"
```

### Monitoring

#### Health Checks
```bash
# Elasticsearch health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Logstash health
curl -X GET "localhost:9600/_node/stats?pretty"

# Kibana health
curl -X GET "localhost:5601/api/status"
```

#### Resource Monitoring
```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Monitor disk usage
docker system df
```

## Best Practices

### 1. Resource Planning

- **Development**: Use ultra-lightweight stack
- **Staging**: Use standard ELK stack
- **Production**: Use production ELK stack

### 2. Monitoring

- Monitor memory usage regularly
- Set up alerts for resource thresholds
- Use health checks for service monitoring

### 3. Maintenance

- Regular index optimization
- Log rotation and cleanup
- Regular backup and restore testing

### 4. Security

- Enable security features in production
- Use proper authentication and authorization
- Regular security updates

## Conclusion

The optimized ELK stack configurations provide flexible options for different resource requirements and use cases. Choose the appropriate configuration based on your specific needs:

- **Ultra-Lightweight**: For development and resource-constrained environments
- **Standard ELK**: For most production use cases
- **Production ELK**: For high-traffic production environments

Regular monitoring and maintenance are essential for optimal performance and reliability.
