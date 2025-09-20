#!/bin/bash
# EasyPay Payment Gateway - Production Deployment Script
# This script deploys the EasyPay system to production

set -e

# Configuration
DEPLOYMENT_ENV=${DEPLOYMENT_ENV:-production}
DOCKER_COMPOSE_FILE="docker-compose.production.yml"
BACKUP_BEFORE_DEPLOY=${BACKUP_BEFORE_DEPLOY:-true}
HEALTH_CHECK_AFTER_DEPLOY=${HEALTH_CHECK_AFTER_DEPLOY:-true}
ROLLBACK_ON_FAILURE=${ROLLBACK_ON_FAILURE:-true}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✓${NC} $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}✗${NC} $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
        "STEP")
            echo -e "${BLUE}→${NC} $message"
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    print_status "STEP" "Checking deployment prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        print_status "ERROR" "Docker is not installed"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_status "ERROR" "Docker daemon is not running"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_status "ERROR" "Docker Compose is not available"
        exit 1
    fi
    
    # Check if required files exist
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_status "ERROR" "Production Docker Compose file not found: $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    
    if [ ! -f "docker/Dockerfile.production" ]; then
        print_status "ERROR" "Production Dockerfile not found"
        exit 1
    fi
    
    if [ ! -f "env.production.template" ]; then
        print_status "ERROR" "Production environment template not found"
        exit 1
    fi
    
    # Check if environment variables are set
    local required_vars=("DATABASE_URL" "REDIS_URL" "SECRET_KEY" "JWT_SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            print_status "ERROR" "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    print_status "SUCCESS" "Prerequisites check passed"
}

# Function to create backup before deployment
create_backup() {
    if [ "$BACKUP_BEFORE_DEPLOY" = true ]; then
        print_status "STEP" "Creating backup before deployment..."
        
        # Check if database is running
        if docker-compose -f "$DOCKER_COMPOSE_FILE" ps postgres | grep -q "Up"; then
            print_status "INFO" "Creating database backup..."
            
            # Create backup using the backup script
            docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres /backup.sh
            
            if [ $? -eq 0 ]; then
                print_status "SUCCESS" "Backup created successfully"
            else
                print_status "WARNING" "Backup creation failed, but continuing with deployment"
            fi
        else
            print_status "WARNING" "Database not running, skipping backup"
        fi
    fi
}

# Function to build production images
build_images() {
    print_status "STEP" "Building production Docker images..."
    
    # Build the main application image
    print_status "INFO" "Building EasyPay API image..."
    docker build -f docker/Dockerfile.production -t easypay-api:production .
    
    if [ $? -eq 0 ]; then
        print_status "SUCCESS" "EasyPay API image built successfully"
    else
        print_status "ERROR" "Failed to build EasyPay API image"
        exit 1
    fi
    
    # Build any additional images if needed
    print_status "INFO" "Building additional service images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    
    if [ $? -eq 0 ]; then
        print_status "SUCCESS" "All images built successfully"
    else
        print_status "ERROR" "Failed to build some images"
        exit 1
    fi
}

# Function to run database migrations
run_migrations() {
    print_status "STEP" "Running database migrations..."
    
    # Start only the database service first
    print_status "INFO" "Starting database service..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres redis
    
    # Wait for database to be ready
    print_status "INFO" "Waiting for database to be ready..."
    sleep 30
    
    # Run migrations
    print_status "INFO" "Running Alembic migrations..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" run --rm easypay-api alembic upgrade head
    
    if [ $? -eq 0 ]; then
        print_status "SUCCESS" "Database migrations completed successfully"
    else
        print_status "ERROR" "Database migrations failed"
        exit 1
    fi
}

# Function to deploy services
deploy_services() {
    print_status "STEP" "Deploying production services..."
    
    # Deploy all services
    print_status "INFO" "Starting all production services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    if [ $? -eq 0 ]; then
        print_status "SUCCESS" "All services started successfully"
    else
        print_status "ERROR" "Failed to start some services"
        exit 1
    fi
    
    # Wait for services to be ready
    print_status "INFO" "Waiting for services to be ready..."
    sleep 60
}

# Function to perform health checks
perform_health_checks() {
    if [ "$HEALTH_CHECK_AFTER_DEPLOY" = true ]; then
        print_status "STEP" "Performing post-deployment health checks..."
        
        # Run comprehensive health check
        ./scripts/health-check.sh comprehensive
        
        if [ $? -eq 0 ]; then
            print_status "SUCCESS" "Health checks passed"
        else
            print_status "ERROR" "Health checks failed"
            if [ "$ROLLBACK_ON_FAILURE" = true ]; then
                print_status "WARNING" "Initiating rollback due to health check failures"
                rollback_deployment
            fi
            exit 1
        fi
    fi
}

# Function to rollback deployment
rollback_deployment() {
    print_status "STEP" "Rolling back deployment..."
    
    # Stop all services
    print_status "INFO" "Stopping all services..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Restore from backup if available
    if [ "$BACKUP_BEFORE_DEPLOY" = true ]; then
        print_status "INFO" "Restoring from backup..."
        # Find the latest backup
        local latest_backup=$(find /backups -name "easypay_backup_*.sql.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2)
        
        if [ -n "$latest_backup" ]; then
            ./scripts/restore.sh --force "$latest_backup"
            if [ $? -eq 0 ]; then
                print_status "SUCCESS" "Rollback completed successfully"
            else
                print_status "ERROR" "Rollback failed"
            fi
        else
            print_status "WARNING" "No backup found for rollback"
        fi
    fi
}

# Function to verify deployment
verify_deployment() {
    print_status "STEP" "Verifying deployment..."
    
    # Check service status
    print_status "INFO" "Checking service status..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    # Check logs for any errors
    print_status "INFO" "Checking service logs for errors..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" logs --tail=50 | grep -i error || print_status "SUCCESS" "No errors found in logs"
    
    # Test API endpoints
    print_status "INFO" "Testing API endpoints..."
    
    # Test health endpoint
    local health_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
    if [ "$health_response" = "200" ]; then
        print_status "SUCCESS" "Health endpoint is responding"
    else
        print_status "ERROR" "Health endpoint is not responding (HTTP $health_response)"
    fi
    
    # Test Kong gateway
    local kong_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/status 2>/dev/null || echo "000")
    if [ "$kong_response" = "200" ]; then
        print_status "SUCCESS" "Kong gateway is responding"
    else
        print_status "ERROR" "Kong gateway is not responding (HTTP $kong_response)"
    fi
    
    # Test monitoring endpoints
    local prometheus_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090/-/healthy 2>/dev/null || echo "000")
    if [ "$prometheus_response" = "200" ]; then
        print_status "SUCCESS" "Prometheus is responding"
    else
        print_status "ERROR" "Prometheus is not responding (HTTP $prometheus_response)"
    fi
    
    local grafana_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health 2>/dev/null || echo "000")
    if [ "$grafana_response" = "200" ]; then
        print_status "SUCCESS" "Grafana is responding"
    else
        print_status "ERROR" "Grafana is not responding (HTTP $grafana_response)"
    fi
}

# Function to display deployment summary
display_summary() {
    echo ""
    echo "=========================================="
    echo "EasyPay Production Deployment Summary"
    echo "=========================================="
    echo "Deployment Environment: $DEPLOYMENT_ENV"
    echo "Deployment Time: $(date)"
    echo "Docker Compose File: $DOCKER_COMPOSE_FILE"
    echo ""
    echo "Services Deployed:"
    echo "------------------"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "Access URLs:"
    echo "-----------"
    echo "API Gateway (Kong): http://localhost:8000"
    echo "API Admin (Kong):   http://localhost:8001"
    echo "Prometheus:         http://localhost:9090"
    echo "Grafana:            http://localhost:3000"
    echo "Elasticsearch:      http://localhost:9200"
    echo "Kibana:             http://localhost:5601"
    echo ""
    echo "Next Steps:"
    echo "----------"
    echo "1. Configure SSL certificates in /ssl directory"
    echo "2. Update DNS records to point to your server"
    echo "3. Set up monitoring alerts"
    echo "4. Configure backup schedules"
    echo "5. Run security scans"
    echo ""
    echo "Documentation:"
    echo "-------------"
    echo "API Documentation: http://localhost:8000/docs"
    echo "Health Check:      http://localhost:8000/health"
    echo "Metrics:          http://localhost:8000/metrics"
    echo "=========================================="
}

# Function to cleanup on exit
cleanup() {
    print_status "INFO" "Cleaning up..."
    # Add any cleanup tasks here
}

# Set up signal handlers
trap cleanup EXIT

# Main deployment function
main() {
    echo "=========================================="
    echo "EasyPay Production Deployment"
    echo "=========================================="
    echo "Starting deployment to: $DEPLOYMENT_ENV"
    echo "Timestamp: $(date)"
    echo ""
    
    # Execute deployment steps
    check_prerequisites
    create_backup
    build_images
    run_migrations
    deploy_services
    perform_health_checks
    verify_deployment
    display_summary
    
    print_status "SUCCESS" "Production deployment completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup)
            BACKUP_BEFORE_DEPLOY=false
            shift
            ;;
        --no-health-check)
            HEALTH_CHECK_AFTER_DEPLOY=false
            shift
            ;;
        --no-rollback)
            ROLLBACK_ON_FAILURE=false
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-backup       Skip backup before deployment"
            echo "  --no-health-check Skip health checks after deployment"
            echo "  --no-rollback     Disable automatic rollback on failure"
            echo "  --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main deployment
main
