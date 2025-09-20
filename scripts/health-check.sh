#!/bin/bash
# EasyPay Payment Gateway - Production Health Check Script
# This script performs comprehensive health checks on the production system

set -e

# Configuration
HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-30}
HEALTH_CHECK_RETRIES=${HEALTH_CHECK_RETRIES:-3}
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-5}

# Service endpoints
API_ENDPOINT=${API_ENDPOINT:-http://localhost:8000}
KONG_ENDPOINT=${KONG_ENDPOINT:-http://localhost:8001}
PROMETHEUS_ENDPOINT=${PROMETHEUS_ENDPOINT:-http://localhost:9090}
GRAFANA_ENDPOINT=${GRAFANA_ENDPOINT:-http://localhost:3000}
ELASTICSEARCH_ENDPOINT=${ELASTICSEARCH_ENDPOINT:-http://localhost:9200}

# Database configuration
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${POSTGRES_DB:-easypay}
DB_USER=${POSTGRES_USER:-easypay}
DB_PASSWORD=${POSTGRES_PASSWORD}

# Redis configuration
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "OK")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ;;
        "INFO")
            echo -e "${YELLOW}ℹ${NC} $message"
            ;;
    esac
}

# Function to check HTTP endpoint
check_http_endpoint() {
    local url=$1
    local service_name=$2
    local expected_status=${3:-200}
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time $HEALTH_CHECK_TIMEOUT "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        print_status "OK" "$service_name is healthy (HTTP $response)"
        return 0
    else
        print_status "ERROR" "$service_name is unhealthy (HTTP $response)"
        return 1
    fi
}

# Function to check database connection
check_database() {
    print_status "INFO" "Checking database connection..."
    
    export PGPASSWORD="${DB_PASSWORD}"
    
    local result=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT 1;" 2>/dev/null || echo "ERROR")
    
    if [ "$result" = "1" ]; then
        print_status "OK" "Database connection is healthy"
        
        # Check database health function
        local health_result=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -tAc "SELECT health_check();" 2>/dev/null || echo "ERROR")
        
        if [ "$health_result" != "ERROR" ]; then
            print_status "OK" "Database health check passed"
        else
            print_status "WARNING" "Database health check function not available"
        fi
        
        unset PGPASSWORD
        return 0
    else
        print_status "ERROR" "Database connection failed"
        unset PGPASSWORD
        return 1
    fi
}

# Function to check Redis connection
check_redis() {
    print_status "INFO" "Checking Redis connection..."
    
    local result=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping 2>/dev/null || echo "ERROR")
    
    if [ "$result" = "PONG" ]; then
        print_status "OK" "Redis connection is healthy"
        
        # Check Redis info
        local info=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" info memory 2>/dev/null | grep used_memory_human || echo "ERROR")
        
        if [ "$info" != "ERROR" ]; then
            print_status "OK" "Redis memory usage: $info"
        fi
        
        return 0
    else
        print_status "ERROR" "Redis connection failed"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    print_status "INFO" "Checking disk space..."
    
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -lt 80 ]; then
        print_status "OK" "Disk usage is ${usage}%"
        return 0
    elif [ "$usage" -lt 90 ]; then
        print_status "WARNING" "Disk usage is ${usage}% (approaching limit)"
        return 1
    else
        print_status "ERROR" "Disk usage is ${usage}% (critical)"
        return 1
    fi
}

# Function to check memory usage
check_memory() {
    print_status "INFO" "Checking memory usage..."
    
    local usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$usage" -lt 80 ]; then
        print_status "OK" "Memory usage is ${usage}%"
        return 0
    elif [ "$usage" -lt 90 ]; then
        print_status "WARNING" "Memory usage is ${usage}% (approaching limit)"
        return 1
    else
        print_status "ERROR" "Memory usage is ${usage}% (critical)"
        return 1
    fi
}

# Function to check CPU usage
check_cpu() {
    print_status "INFO" "Checking CPU usage..."
    
    local usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    
    if [ "$usage" -lt 80 ]; then
        print_status "OK" "CPU usage is ${usage}%"
        return 0
    elif [ "$usage" -lt 90 ]; then
        print_status "WARNING" "CPU usage is ${usage}% (approaching limit)"
        return 1
    else
        print_status "ERROR" "CPU usage is ${usage}% (critical)"
        return 1
    fi
}

# Function to check application logs for errors
check_logs() {
    print_status "INFO" "Checking application logs for errors..."
    
    local error_count=$(find /app/logs -name "*.log" -type f -exec grep -l "ERROR\|FATAL\|CRITICAL" {} \; 2>/dev/null | wc -l)
    
    if [ "$error_count" -eq 0 ]; then
        print_status "OK" "No critical errors found in logs"
        return 0
    else
        print_status "WARNING" "Found $error_count log files with errors"
        return 1
    fi
}

# Function to check SSL certificate
check_ssl_certificate() {
    print_status "INFO" "Checking SSL certificate..."
    
    local cert_file="/ssl/cert.pem"
    
    if [ -f "$cert_file" ]; then
        local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
        local expiry_timestamp=$(date -d "$expiry_date" +%s)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [ "$days_until_expiry" -gt 30 ]; then
            print_status "OK" "SSL certificate expires in $days_until_expiry days"
            return 0
        elif [ "$days_until_expiry" -gt 7 ]; then
            print_status "WARNING" "SSL certificate expires in $days_until_expiry days"
            return 1
        else
            print_status "ERROR" "SSL certificate expires in $days_until_expiry days (critical)"
            return 1
        fi
    else
        print_status "WARNING" "SSL certificate file not found"
        return 1
    fi
}

# Function to check backup status
check_backups() {
    print_status "INFO" "Checking backup status..."
    
    local backup_dir="/backups"
    local latest_backup=$(find "$backup_dir" -name "easypay_backup_*.sql.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2)
    
    if [ -n "$latest_backup" ]; then
        local backup_age=$(($(date +%s) - $(stat -c %Y "$latest_backup")))
        local backup_age_hours=$((backup_age / 3600))
        
        if [ "$backup_age_hours" -lt 25 ]; then
            print_status "OK" "Latest backup is $backup_age_hours hours old"
            return 0
        elif [ "$backup_age_hours" -lt 48 ]; then
            print_status "WARNING" "Latest backup is $backup_age_hours hours old"
            return 1
        else
            print_status "ERROR" "Latest backup is $backup_age_hours hours old (too old)"
            return 1
        fi
    else
        print_status "ERROR" "No backups found"
        return 1
    fi
}

# Function to perform comprehensive health check
comprehensive_health_check() {
    echo "=========================================="
    echo "EasyPay Production Health Check"
    echo "=========================================="
    echo "Timestamp: $(date)"
    echo "Hostname: $(hostname)"
    echo "Uptime: $(uptime)"
    echo ""
    
    local overall_status=0
    
    # Core services
    echo "Core Services:"
    echo "--------------"
    check_http_endpoint "$API_ENDPOINT/health" "EasyPay API" || overall_status=1
    check_http_endpoint "$KONG_ENDPOINT/status" "Kong Gateway" || overall_status=1
    check_database || overall_status=1
    check_redis || overall_status=1
    echo ""
    
    # Monitoring services
    echo "Monitoring Services:"
    echo "-------------------"
    check_http_endpoint "$PROMETHEUS_ENDPOINT/-/healthy" "Prometheus" || overall_status=1
    check_http_endpoint "$GRAFANA_ENDPOINT/api/health" "Grafana" || overall_status=1
    check_http_endpoint "$ELASTICSEARCH_ENDPOINT/_cluster/health" "Elasticsearch" || overall_status=1
    echo ""
    
    # System resources
    echo "System Resources:"
    echo "----------------"
    check_disk_space || overall_status=1
    check_memory || overall_status=1
    check_cpu || overall_status=1
    echo ""
    
    # Security and compliance
    echo "Security & Compliance:"
    echo "---------------------"
    check_ssl_certificate || overall_status=1
    check_backups || overall_status=1
    check_logs || overall_status=1
    echo ""
    
    # Summary
    echo "=========================================="
    if [ $overall_status -eq 0 ]; then
        print_status "OK" "Overall system health: HEALTHY"
        echo "All critical systems are operational"
    else
        print_status "ERROR" "Overall system health: UNHEALTHY"
        echo "Some systems require attention"
    fi
    echo "=========================================="
    
    return $overall_status
}

# Main execution
case "${1:-comprehensive}" in
    "comprehensive")
        comprehensive_health_check
        ;;
    "quick")
        check_http_endpoint "$API_ENDPOINT/health" "EasyPay API"
        check_database
        check_redis
        ;;
    "services")
        check_http_endpoint "$API_ENDPOINT/health" "EasyPay API"
        check_http_endpoint "$KONG_ENDPOINT/status" "Kong Gateway"
        check_http_endpoint "$PROMETHEUS_ENDPOINT/-/healthy" "Prometheus"
        check_http_endpoint "$GRAFANA_ENDPOINT/api/health" "Grafana"
        check_http_endpoint "$ELASTICSEARCH_ENDPOINT/_cluster/health" "Elasticsearch"
        ;;
    "resources")
        check_disk_space
        check_memory
        check_cpu
        ;;
    "security")
        check_ssl_certificate
        check_backups
        check_logs
        ;;
    *)
        echo "Usage: $0 [comprehensive|quick|services|resources|security]"
        echo ""
        echo "Options:"
        echo "  comprehensive  - Full health check (default)"
        echo "  quick         - Quick health check"
        echo "  services      - Check all services"
        echo "  resources     - Check system resources"
        echo "  security      - Check security and compliance"
        exit 1
        ;;
esac
