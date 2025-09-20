# Kong API Gateway Configuration

This directory contains the Kong API Gateway configuration for the EasyPay Payment Gateway system.

## Overview

Kong is configured as a reverse proxy and API gateway that sits in front of the EasyPay API service, providing:

- **Rate Limiting**: Prevents API abuse with configurable limits
- **CORS Handling**: Manages cross-origin requests
- **Request/Response Logging**: Comprehensive logging for monitoring
- **Load Balancing**: Distributes requests across multiple backend instances
- **SSL/TLS Termination**: Handles HTTPS termination
- **Health Checks**: Monitors backend service health
- **Prometheus Metrics**: Exposes metrics for monitoring
- **Correlation ID**: Tracks requests across services

## Configuration Files

### `kong.yml`

The main Kong configuration file using declarative configuration format. This file defines:

- **Services**: Backend services (EasyPay API)
- **Routes**: URL patterns and HTTP methods
- **Plugins**: Rate limiting, CORS, logging, metrics, etc.
- **Consumers**: API consumers (for future authentication)
- **Upstreams**: Load balancing configuration

## Services Configuration

### EasyPay API Service

The main backend service is configured with multiple routes:

1. **Health Endpoints** (`/health*`)
   - No rate limiting
   - CORS enabled
   - Request logging enabled
   - Prometheus metrics enabled

2. **Payment Endpoints** (`/api/v1/payments`)
   - Rate limiting: 100/minute, 1000/hour, 10000/day
   - CORS enabled
   - Request logging enabled
   - Prometheus metrics enabled
   - Response transformation (adds timing headers)
   - Correlation ID handling

3. **Admin Endpoints** (`/api/v1/admin`)
   - Rate limiting: 50/minute, 500/hour, 5000/day
   - CORS enabled
   - Request logging enabled
   - Prometheus metrics enabled
   - Response transformation
   - Correlation ID handling

4. **Metrics Endpoint** (`/metrics`)
   - No rate limiting
   - CORS enabled
   - Request logging enabled
   - Prometheus metrics enabled

5. **Documentation Endpoints** (`/docs`, `/redoc`, `/openapi.json`)
   - No rate limiting
   - CORS enabled
   - Request logging enabled

6. **Root Endpoint** (`/`)
   - No rate limiting
   - CORS enabled
   - Request logging enabled

## Plugins Configuration

### Global Plugins

Applied to all services:

- **Prometheus**: Metrics collection
- **Request Logging**: Comprehensive request/response logging
- **Correlation ID**: Request tracking

### Service-Specific Plugins

- **Rate Limiting**: Redis-based rate limiting with different limits per service
- **CORS**: Cross-origin resource sharing configuration
- **Response Transformer**: Adds timing and latency headers

## Rate Limiting

Rate limiting is configured using Redis as the backend:

- **Payment API**: 100 requests/minute, 1000/hour, 10000/day
- **Admin API**: 50 requests/minute, 500/hour, 5000/day
- **Health/Metrics**: No rate limiting

## CORS Configuration

CORS is configured to allow:

- **Origins**: All origins (`*`) - configure for production
- **Methods**: GET, POST, PUT, DELETE, OPTIONS
- **Headers**: Standard headers plus custom headers
- **Credentials**: Enabled
- **Max Age**: 3600 seconds

## Monitoring and Metrics

### Prometheus Metrics

Kong exposes Prometheus metrics at `/metrics` endpoint:

- Request count and duration
- Status code metrics
- Bandwidth metrics
- Upstream health metrics
- Per-consumer metrics

### Health Checks

- Kong health: `GET /status` (Admin API)
- Service health: `GET /health` (Proxy)
- Backend health: Monitored via Kong health checks

## Security Features

### Request Logging

All requests and responses are logged with:

- Request body
- Request arguments
- Request headers
- Response body
- Timing information

### Correlation ID

- Automatically generates correlation IDs
- Preserves existing correlation IDs
- Adds correlation ID to response headers

## Deployment

### Docker Compose

Kong is deployed via Docker Compose with:

- Kong container with declarative configuration
- Redis for rate limiting
- Health checks
- Proper service dependencies

### Ports

- **8000**: Kong proxy port (external access)
- **8001**: Kong admin API port (management)
- **8002**: EasyPay API internal port (Kong backend)

## Testing

### Test Scripts

1. **`scripts/kong_setup.py`**: Setup and validation script
2. **`scripts/test_kong_gateway.py`**: Comprehensive testing script

### Manual Testing

```bash
# Test Kong health
curl http://localhost:8001/status

# Test proxy health
curl http://localhost:8000/health

# Test CORS
curl -H "Origin: https://example.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8000/api/v1/payments

# Test rate limiting
for i in {1..10}; do curl http://localhost:8000/api/v1/payments; done

# Test correlation ID
curl -H "X-Correlation-ID: test-123" http://localhost:8000/health

# Test metrics
curl http://localhost:8000/metrics
```

## Configuration Management

### Environment Variables

Kong configuration can be customized via environment variables:

- `KONG_DATABASE`: Database mode (off for declarative)
- `KONG_DECLARATIVE_CONFIG`: Path to declarative config
- `KONG_PROXY_LISTEN`: Proxy port
- `KONG_ADMIN_LISTEN`: Admin API port

### Updating Configuration

To update Kong configuration:

1. Modify `kong.yml`
2. Restart Kong container: `docker-compose restart kong`
3. Validate configuration: `python scripts/kong_setup.py`

## Troubleshooting

### Common Issues

1. **Kong not starting**: Check Docker logs and configuration syntax
2. **Service not accessible**: Verify backend service is running
3. **Rate limiting issues**: Check Redis connectivity
4. **CORS issues**: Verify CORS configuration

### Debugging

```bash
# Check Kong logs
docker-compose logs kong

# Check Kong status
curl http://localhost:8001/status

# Check services
curl http://localhost:8001/services

# Check routes
curl http://localhost:8001/routes

# Check plugins
curl http://localhost:8001/plugins
```

## Future Enhancements

### Authentication

- API key authentication
- JWT token validation
- OAuth2 integration

### Advanced Features

- Request/response transformation
- Advanced rate limiting policies
- Circuit breaker patterns
- Request caching
- API versioning

### Monitoring

- Grafana dashboards
- Alerting rules
- Performance monitoring
- Security monitoring
