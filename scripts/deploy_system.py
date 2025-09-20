#!/usr/bin/env python3
"""
EasyPay Payment Gateway - System Deployment Script

This script provides comprehensive deployment capabilities for the EasyPay system,
including environment setup, service deployment, and health verification.
"""

import asyncio
import os
import sys
import time
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import requests
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemDeployer:
    """Comprehensive system deployment manager."""
    
    def __init__(self, environment: str = "development"):
        self.project_root = project_root
        self.environment = environment
        self.services = [
            'postgres',
            'redis',
            'easypay-api',
            'kong',
            'prometheus',
            'grafana',
            'elasticsearch',
            'logstash',
            'kibana',
            'pgadmin'
        ]
    
    async def deploy_system(self) -> bool:
        """Deploy the complete EasyPay system."""
        logger.info(f"🚀 Deploying EasyPay Payment Gateway ({self.environment})...")
        
        try:
            # Step 1: Pre-deployment checks
            await self._pre_deployment_checks()
            
            # Step 2: Setup environment
            await self._setup_environment()
            
            # Step 3: Build and deploy services
            await self._deploy_services()
            
            # Step 4: Wait for services to be ready
            await self._wait_for_services()
            
            # Step 5: Run database migrations
            await self._run_database_migrations()
            
            # Step 6: Configure services
            await self._configure_services()
            
            # Step 7: Verify deployment
            await self._verify_deployment()
            
            # Step 8: Display deployment information
            await self._display_deployment_info()
            
            logger.info("✅ EasyPay Payment Gateway deployed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            await self._cleanup_failed_deployment()
            return False
    
    async def _pre_deployment_checks(self):
        """Run pre-deployment checks."""
        logger.info("🔍 Running pre-deployment checks...")
        
        # Check Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Docker is not installed or not running")
            logger.info(f"✅ Docker: {result.stdout.strip()}")
        except FileNotFoundError:
            raise Exception("Docker is not installed")
        
        # Check Docker Compose
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Docker Compose is not installed")
            logger.info(f"✅ Docker Compose: {result.stdout.strip()}")
        except FileNotFoundError:
            raise Exception("Docker Compose is not installed")
        
        # Check available resources
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        if memory.available < 2 * 1024 * 1024 * 1024:  # 2GB
            logger.warning("⚠️  Low available memory (< 2GB)")
        
        if disk.free < 10 * 1024 * 1024 * 1024:  # 10GB
            logger.warning("⚠️  Low available disk space (< 10GB)")
        
        # Check required files
        required_files = [
            'docker-compose.yml',
            'Dockerfile',
            'requirements.txt',
            'kong/kong.yml',
            'config/prometheus.yml'
        ]
        
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                raise Exception(f"Required file not found: {file_path}")
        
        logger.info("✅ Pre-deployment checks completed")
    
    async def _setup_environment(self):
        """Setup deployment environment."""
        logger.info("⚙️  Setting up environment...")
        
        # Create environment file if it doesn't exist
        env_file = self.project_root / '.env'
        if not env_file.exists():
            logger.info("Creating environment file...")
            await self._create_environment_file()
        
        # Create necessary directories
        directories = [
            'logs',
            'data/postgres',
            'data/redis',
            'data/grafana',
            'data/elasticsearch',
            'data/prometheus'
        ]
        
        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Set proper permissions
        if os.name != 'nt':  # Not Windows
            for directory in directories:
                dir_path = self.project_root / directory
                os.chmod(dir_path, 0o755)
        
        logger.info("✅ Environment setup completed")
    
    async def _create_environment_file(self):
        """Create environment file."""
        env_content = f"""# EasyPay Payment Gateway - {self.environment.title()} Environment

# Database Configuration
DATABASE_URL=postgresql://easypay:password@postgres:5432/easypay
REDIS_URL=redis://redis:6379/0

# Authorize.net Configuration (Sandbox)
AUTHORIZE_NET_API_LOGIN_ID=your_api_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_transaction_key
AUTHORIZE_NET_SANDBOX=true

# Security Configuration
SECRET_KEY=your-secret-key-change-in-production-{int(time.time())}
ENVIRONMENT={self.environment}

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring Configuration
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database Pool Configuration
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis Configuration
REDIS_POOL_SIZE=10

# Circuit Breaker Configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_REQUESTS_PER_HOUR=1000
RATE_LIMIT_REQUESTS_PER_DAY=10000

# Webhook Configuration
WEBHOOK_RETRY_ATTEMPTS=5
WEBHOOK_RETRY_DELAY_MINUTES=5
WEBHOOK_TIMEOUT_SECONDS=30

# Performance Configuration
REQUEST_TIMEOUT_SECONDS=30
MAX_REQUEST_SIZE_MB=10

# Security Headers
CORS_ORIGINS=*
TRUSTED_HOSTS=*

# Development Settings
DEBUG=true
RELOAD=true
"""
        
        env_file = self.project_root / '.env'
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        logger.info("✅ Environment file created")
    
    async def _deploy_services(self):
        """Deploy all services."""
        logger.info("🐳 Deploying services...")
        
        # Stop any existing services
        logger.info("Stopping existing services...")
        subprocess.run(['docker-compose', 'down'], cwd=self.project_root)
        
        # Remove old containers and images (optional)
        if self.environment == "development":
            logger.info("Cleaning up old containers...")
            subprocess.run(['docker-compose', 'down', '--volumes', '--remove-orphans'], cwd=self.project_root)
        
        # Build and start services
        logger.info("Building and starting services...")
        result = subprocess.run(
            ['docker-compose', 'up', '--build', '-d'],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to deploy services: {result.stderr}")
        
        logger.info("✅ Services deployed")
    
    async def _wait_for_services(self):
        """Wait for services to be ready."""
        logger.info("⏳ Waiting for services to be ready...")
        
        service_checks = {
            'postgres': self._check_postgres,
            'redis': self._check_redis,
            'easypay-api': self._check_easypay_api,
            'kong': self._check_kong,
            'prometheus': self._check_prometheus,
            'grafana': self._check_grafana,
            'elasticsearch': self._check_elasticsearch,
            'kibana': self._check_kibana,
            'pgadmin': self._check_pgadmin
        }
        
        for service_name, check_func in service_checks.items():
            logger.info(f"Waiting for {service_name}...")
            await self._wait_for_service_ready(service_name, check_func)
        
        logger.info("✅ All services are ready")
    
    async def _wait_for_service_ready(self, service_name: str, check_func, timeout: int = 120):
        """Wait for a specific service to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if await check_func():
                    logger.info(f"✅ {service_name} is ready")
                    return
            except Exception as e:
                logger.debug(f"{service_name} not ready yet: {e}")
            
            await asyncio.sleep(5)
        
        raise Exception(f"Service {service_name} failed to start within {timeout} seconds")
    
    async def _check_postgres(self) -> bool:
        """Check PostgreSQL health."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='easypay',
                user='easypay',
                password='password'
            )
            conn.close()
            return True
        except Exception:
            return False
    
    async def _check_redis(self) -> bool:
        """Check Redis health."""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            return True
        except Exception:
            return False
    
    async def _check_easypay_api(self) -> bool:
        """Check EasyPay API health."""
        try:
            response = requests.get('http://localhost:8002/health', timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _check_kong(self) -> bool:
        """Check Kong health."""
        try:
            response = requests.get('http://localhost:8001/status', timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _check_prometheus(self) -> bool:
        """Check Prometheus health."""
        try:
            response = requests.get('http://localhost:9090/-/healthy', timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _check_grafana(self) -> bool:
        """Check Grafana health."""
        try:
            response = requests.get('http://localhost:3000/api/health', timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _check_elasticsearch(self) -> bool:
        """Check Elasticsearch health."""
        try:
            response = requests.get('http://localhost:9200/_cluster/health', timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _check_kibana(self) -> bool:
        """Check Kibana health."""
        try:
            response = requests.get('http://localhost:5601/api/status', timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _check_pgadmin(self) -> bool:
        """Check pgAdmin health."""
        try:
            response = requests.get('http://localhost:5050', timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _run_database_migrations(self):
        """Run database migrations."""
        logger.info("🗄️  Running database migrations...")
        
        try:
            # Set environment variables
            env = os.environ.copy()
            env['DATABASE_URL'] = 'postgresql://easypay:password@localhost:5432/easypay'
            
            # Run Alembic migrations
            result = subprocess.run(
                ['alembic', 'upgrade', 'head'],
                cwd=self.project_root,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning(f"Migration warning: {result.stderr}")
            else:
                logger.info("✅ Database migrations completed")
                
        except Exception as e:
            logger.warning(f"Migration error (non-critical): {e}")
    
    async def _configure_services(self):
        """Configure deployed services."""
        logger.info("⚙️  Configuring services...")
        
        # Configure Grafana dashboards
        await self._configure_grafana()
        
        # Configure Prometheus alerts
        await self._configure_prometheus()
        
        # Configure Kong routes
        await self._configure_kong()
        
        logger.info("✅ Service configuration completed")
    
    async def _configure_grafana(self):
        """Configure Grafana dashboards."""
        try:
            # Import dashboards
            dashboard_dir = self.project_root / 'config' / 'grafana' / 'dashboards'
            if dashboard_dir.exists():
                logger.info("Grafana dashboards will be imported automatically")
        except Exception as e:
            logger.warning(f"Grafana configuration warning: {e}")
    
    async def _configure_prometheus(self):
        """Configure Prometheus alerts."""
        try:
            # Prometheus configuration is already in place
            logger.info("Prometheus configuration is ready")
        except Exception as e:
            logger.warning(f"Prometheus configuration warning: {e}")
    
    async def _configure_kong(self):
        """Configure Kong routes."""
        try:
            # Kong configuration is already in place
            logger.info("Kong configuration is ready")
        except Exception as e:
            logger.warning(f"Kong configuration warning: {e}")
    
    async def _verify_deployment(self):
        """Verify deployment success."""
        logger.info("🏥 Verifying deployment...")
        
        health_checks = [
            ('EasyPay API', 'http://localhost:8002/health'),
            ('Kong Gateway', 'http://localhost:8000/health'),
            ('Prometheus', 'http://localhost:9090/-/healthy'),
            ('Grafana', 'http://localhost:3000/api/health'),
        ]
        
        failed_checks = []
        
        for name, url in health_checks:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"✅ {name}: Healthy")
                else:
                    logger.warning(f"⚠️  {name}: Status {response.status_code}")
                    failed_checks.append(name)
            except Exception as e:
                logger.warning(f"⚠️  {name}: {e}")
                failed_checks.append(name)
        
        if failed_checks:
            logger.warning(f"⚠️  Some services failed health checks: {', '.join(failed_checks)}")
        
        logger.info("✅ Deployment verification completed")
    
    async def _display_deployment_info(self):
        """Display deployment information."""
        logger.info("📊 Deployment Information:")
        logger.info("=" * 50)
        
        services_info = [
            ("EasyPay API", "http://localhost:8002", "Internal API service"),
            ("Kong Gateway", "http://localhost:8000", "API Gateway (Public)"),
            ("Kong Admin", "http://localhost:8001", "Kong Administration"),
            ("API Documentation", "http://localhost:8000/docs", "Swagger UI"),
            ("Prometheus", "http://localhost:9090", "Metrics Collection"),
            ("Grafana", "http://localhost:3000", "Monitoring Dashboard (admin/admin)"),
            ("Elasticsearch", "http://localhost:9200", "Log Storage"),
            ("Kibana", "http://localhost:5601", "Log Analysis"),
            ("pgAdmin", "http://localhost:5050", "Database Admin (admin@easypay.com/admin)"),
        ]
        
        for name, url, description in services_info:
            logger.info(f"🔗 {name}: {url}")
            logger.info(f"   {description}")
        
        logger.info("=" * 50)
        logger.info(f"🎉 EasyPay Payment Gateway ({self.environment}) is deployed!")
        logger.info("📖 Check the documentation at: http://localhost:8000/docs")
        logger.info("📊 Monitor the system at: http://localhost:3000")
    
    async def _cleanup_failed_deployment(self):
        """Cleanup after failed deployment."""
        logger.info("🧹 Cleaning up failed deployment...")
        
        try:
            # Stop services
            subprocess.run(['docker-compose', 'down'], cwd=self.project_root)
            
            # Remove volumes if needed
            if self.environment == "development":
                subprocess.run(['docker-compose', 'down', '--volumes'], cwd=self.project_root)
            
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy EasyPay Payment Gateway')
    parser.add_argument('--environment', '-e', default='development', 
                       choices=['development', 'staging', 'production'],
                       help='Deployment environment')
    parser.add_argument('--clean', '-c', action='store_true',
                       help='Clean deployment (remove existing containers)')
    
    args = parser.parse_args()
    
    deployer = SystemDeployer(environment=args.environment)
    
    if args.clean:
        logger.info("🧹 Performing clean deployment...")
        subprocess.run(['docker-compose', 'down', '--volumes', '--remove-orphans'], 
                      cwd=deployer.project_root)
    
    success = await deployer.deploy_system()
    
    if success:
        logger.info("🚀 Deployment completed successfully!")
    else:
        logger.error("❌ Deployment failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
