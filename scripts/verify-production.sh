#!/bin/bash
# EasyPay Payment Gateway - Production Verification Script
# This script verifies that the production deployment is working correctly

set -e

# Configuration
API_BASE_URL=${API_BASE_URL:-http://localhost:8000}
KONG_ADMIN_URL=${KONG_ADMIN_URL:-http://localhost:8001}
PROMETHEUS_URL=${PROMETHEUS_URL:-http://localhost:9090}
GRAFANA_URL=${GRAFANA_URL:-http://localhost:3000}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "PASS")
            echo -e "${GREEN}✓ PASS${NC} $message"
            ((TESTS_PASSED++))
            ;;
        "FAIL")
            echo -e "${RED}✗ FAIL${NC} $message"
            ((TESTS_FAILED++))
            ;;
        "INFO")
            echo -e "${BLUE}ℹ INFO${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠ WARN${NC} $message"
            ;;
    esac
    ((TOTAL_TESTS++))
}

# Function to test HTTP endpoint
test_endpoint() {
    local url=$1
    local expected_status=${2:-200}
    local test_name=$3
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        print_status "PASS" "$test_name (HTTP $response)"
        return 0
    else
        print_status "FAIL" "$test_name (HTTP $response, expected $expected_status)"
        return 1
    fi
}

# Function to test API functionality
test_api_functionality() {
    print_status "INFO" "Testing API functionality..."
    
    # Test health endpoint
    test_endpoint "$API_BASE_URL/health" 200 "Health endpoint"
    
    # Test metrics endpoint
    test_endpoint "$API_BASE_URL/metrics" 200 "Metrics endpoint"
    
    # Test API documentation
    test_endpoint "$API_BASE_URL/docs" 200 "API documentation"
    
    # Test OpenAPI spec
    test_endpoint "$API_BASE_URL/openapi.json" 200 "OpenAPI specification"
    
    # Test version endpoint
    test_endpoint "$API_BASE_URL/version" 200 "Version endpoint"
}

# Function to test Kong Gateway
test_kong_gateway() {
    print_status "INFO" "Testing Kong Gateway..."
    
    # Test Kong admin API
    test_endpoint "$KONG_ADMIN_URL/status" 200 "Kong admin status"
    
    # Test Kong services
    local services_response=$(curl -s "$KONG_ADMIN_URL/services" 2>/dev/null || echo "ERROR")
    if [ "$services_response" != "ERROR" ]; then
        print_status "PASS" "Kong services endpoint"
    else
        print_status "FAIL" "Kong services endpoint"
    fi
    
    # Test Kong routes
    local routes_response=$(curl -s "$KONG_ADMIN_URL/routes" 2>/dev/null || echo "ERROR")
    if [ "$routes_response" != "ERROR" ]; then
        print_status "PASS" "Kong routes endpoint"
    else
        print_status "FAIL" "Kong routes endpoint"
    fi
    
    # Test Kong plugins
    local plugins_response=$(curl -s "$KONG_ADMIN_URL/plugins" 2>/dev/null || echo "ERROR")
    if [ "$plugins_response" != "ERROR" ]; then
        print_status "PASS" "Kong plugins endpoint"
    else
        print_status "FAIL" "Kong plugins endpoint"
    fi
}

# Function to test monitoring stack
test_monitoring_stack() {
    print_status "INFO" "Testing monitoring stack..."
    
    # Test Prometheus
    test_endpoint "$PROMETHEUS_URL/-/healthy" 200 "Prometheus health"
    test_endpoint "$PROMETHEUS_URL/api/v1/targets" 200 "Prometheus targets"
    
    # Test Grafana
    test_endpoint "$GRAFANA_URL/api/health" 200 "Grafana health"
    test_endpoint "$GRAFANA_URL/api/datasources" 200 "Grafana datasources"
    
    # Test Elasticsearch
    test_endpoint "http://localhost:9200/_cluster/health" 200 "Elasticsearch health"
    
    # Test Kibana
    test_endpoint "http://localhost:5601/api/status" 200 "Kibana status"
}

# Function to test database connectivity
test_database_connectivity() {
    print_status "INFO" "Testing database connectivity..."
    
    # Test PostgreSQL connection
    local db_test=$(docker-compose -f docker-compose.production.yml exec -T postgres psql -U easypay -d easypay -c "SELECT 1;" 2>/dev/null | grep -c "1" || echo "0")
    
    if [ "$db_test" -gt 0 ]; then
        print_status "PASS" "PostgreSQL connection"
    else
        print_status "FAIL" "PostgreSQL connection"
    fi
    
    # Test Redis connection
    local redis_test=$(docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping 2>/dev/null || echo "ERROR")
    
    if [ "$redis_test" = "PONG" ]; then
        print_status "PASS" "Redis connection"
    else
        print_status "FAIL" "Redis connection"
    fi
}

# Function to test security features
test_security_features() {
    print_status "INFO" "Testing security features..."
    
    # Test SSL/TLS (if configured)
    local ssl_test=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 "https://localhost:443" 2>/dev/null || echo "000")
    
    if [ "$ssl_test" = "200" ] || [ "$ssl_test" = "000" ]; then
        if [ "$ssl_test" = "200" ]; then
            print_status "PASS" "SSL/TLS configuration"
        else
            print_status "WARN" "SSL/TLS not configured or not accessible"
        fi
    else
        print_status "FAIL" "SSL/TLS configuration (HTTP $ssl_test)"
    fi
    
    # Test security headers
    local headers_response=$(curl -s -I "$API_BASE_URL/health" 2>/dev/null || echo "")
    
    if echo "$headers_response" | grep -q "X-Frame-Options"; then
        print_status "PASS" "Security headers present"
    else
        print_status "WARN" "Security headers not detected"
    fi
    
    # Test CORS configuration
    local cors_response=$(curl -s -H "Origin: https://example.com" -I "$API_BASE_URL/health" 2>/dev/null || echo "")
    
    if echo "$cors_response" | grep -q "Access-Control-Allow-Origin"; then
        print_status "PASS" "CORS configuration"
    else
        print_status "WARN" "CORS configuration not detected"
    fi
}

# Function to test backup functionality
test_backup_functionality() {
    print_status "INFO" "Testing backup functionality..."
    
    # Check if backup script exists and is executable
    if [ -f "scripts/backup.sh" ] && [ -x "scripts/backup.sh" ]; then
        print_status "PASS" "Backup script available and executable"
    else
        print_status "FAIL" "Backup script not available or not executable"
    fi
    
    # Check if restore script exists and is executable
    if [ -f "scripts/restore.sh" ] && [ -x "scripts/restore.sh" ]; then
        print_status "PASS" "Restore script available and executable"
    else
        print_status "FAIL" "Restore script not available or not executable"
    fi
    
    # Check if backup directory exists
    if [ -d "/backups" ]; then
        print_status "PASS" "Backup directory exists"
    else
        print_status "WARN" "Backup directory not found"
    fi
}

# Function to test performance
test_performance() {
    print_status "INFO" "Testing performance..."
    
    # Test response time
    local response_time=$(curl -s -o /dev/null -w "%{time_total}" --connect-timeout 10 --max-time 30 "$API_BASE_URL/health" 2>/dev/null || echo "999")
    
    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        print_status "PASS" "Response time acceptable (${response_time}s)"
    else
        print_status "WARN" "Response time slow (${response_time}s)"
    fi
    
    # Test concurrent requests
    local concurrent_test=$(for i in {1..10}; do curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/health" & done; wait)
    local success_count=$(echo "$concurrent_test" | grep -c "200" || echo "0")
    
    if [ "$success_count" -ge 8 ]; then
        print_status "PASS" "Concurrent request handling ($success_count/10 successful)"
    else
        print_status "WARN" "Concurrent request handling issues ($success_count/10 successful)"
    fi
}

# Function to test logging
test_logging() {
    print_status "INFO" "Testing logging functionality..."
    
    # Check if log files exist
    if [ -d "/app/logs" ]; then
        print_status "PASS" "Log directory exists"
        
        # Check if log files are being written
        local log_files=$(find /app/logs -name "*.log" -type f -mmin -5 2>/dev/null | wc -l)
        if [ "$log_files" -gt 0 ]; then
            print_status "PASS" "Log files are being written"
        else
            print_status "WARN" "No recent log files found"
        fi
    else
        print_status "WARN" "Log directory not found"
    fi
    
    # Test structured logging
    local log_response=$(curl -s "$API_BASE_URL/health" > /dev/null 2>&1 && sleep 2)
    local structured_logs=$(find /app/logs -name "*.log" -type f -exec grep -l "timestamp\|level\|message" {} \; 2>/dev/null | wc -l)
    
    if [ "$structured_logs" -gt 0 ]; then
        print_status "PASS" "Structured logging detected"
    else
        print_status "WARN" "Structured logging not detected"
    fi
}

# Function to generate verification report
generate_report() {
    echo ""
    echo "=========================================="
    echo "EasyPay Production Verification Report"
    echo "=========================================="
    echo "Verification Time: $(date)"
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $TESTS_PASSED"
    echo "Failed: $TESTS_FAILED"
    echo ""
    
    local success_rate=$((TESTS_PASSED * 100 / TOTAL_TESTS))
    echo "Success Rate: $success_rate%"
    echo ""
    
    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo "🎉 All tests passed! Production deployment is ready."
        echo ""
        echo "Next Steps:"
        echo "1. Configure SSL certificates"
        echo "2. Update DNS records"
        echo "3. Set up monitoring alerts"
        echo "4. Configure backup schedules"
        echo "5. Run security scans"
    else
        echo "⚠️  Some tests failed. Please review and fix issues before going live."
        echo ""
        echo "Failed Tests:"
        echo "- Review the output above for specific failures"
        echo "- Check service logs for detailed error information"
        echo "- Verify configuration files are correct"
    fi
    
    echo "=========================================="
}

# Main verification function
main() {
    echo "=========================================="
    echo "EasyPay Production Verification"
    echo "=========================================="
    echo "Starting verification process..."
    echo "Timestamp: $(date)"
    echo ""
    
    # Run all verification tests
    test_api_functionality
    test_kong_gateway
    test_monitoring_stack
    test_database_connectivity
    test_security_features
    test_backup_functionality
    test_performance
    test_logging
    
    # Generate final report
    generate_report
    
    # Exit with appropriate code
    if [ "$TESTS_FAILED" -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url)
            API_BASE_URL="$2"
            shift 2
            ;;
        --kong-url)
            KONG_ADMIN_URL="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --api-url URL      API base URL (default: http://localhost:8000)"
            echo "  --kong-url URL     Kong admin URL (default: http://localhost:8001)"
            echo "  --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main verification
main
