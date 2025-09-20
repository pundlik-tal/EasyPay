#!/usr/bin/env python3
"""
EasyPay Payment Gateway - System Startup Script

This script provides a comprehensive startup process for the EasyPay system,
including dependency checks, service initialization, and health verification.
"""

import asyncio
import os
import sys
import time
import subprocess
import logging
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


class SystemStartupManager:
    """Manages the complete system startup process."""
    
    def __init__(self):
        self.project_root = project_root
        self.services = {
            'postgres': {'port': 5432, 'health_check': self._check_postgres},
            'redis': {'port': 6379, 'health_check': self._check_redis},
            'easypay-api': {'port': 8002, 'health_check': self._check_easypay_api},
            'kong': {'port': 8000, 'health_check': self._check_kong},
            'prometheus': {'port': 9090, 'health_check': self._check_prometheus},
            'grafana': {'port': 3000, 'health_check': self._check_grafana},
            'elasticsearch': {'port': 9200, 'health_check': self._check_elasticsearch},
            'kibana': {'port': 5601, 'health_check': self._check_kibana},
            'pgadmin': {'port': 5050, 'health_check': self._check_pgadmin}
        }
        self.startup_order = [
            'postgres',
            'redis', 
            'easypay-api',
            'kong',
            'prometheus',
            'grafana',
            'elasticsearch',
            'kibana',
            'pgadmin'
        ]
    
    async def start_system(self) -> bool:
        """Start the complete EasyPay system."""
        logger.info("🚀 Starting EasyPay Payment Gateway System...")
        
        try:
            # Step 1: Check prerequisites
            await self._check_prerequisites()
            
            # Step 2: Start Docker services
            await self._start_docker_services()
            
            # Step 3: Wait for services to be ready
            await self._wait_for_services()
            
            # Step 4: Run database migrations
            await self._run_database_migrations()
            
            # Step 5: Verify system health
            await self._verify_system_health()
            
            # Step 6: Display system information
            await self._display_system_info()
            
            logger.info("✅ EasyPay Payment Gateway System started successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start system: {e}")
            return False
    
    async def _check_prerequisites(self):
        """Check system prerequisites."""
        logger.info("🔍 Checking prerequisites...")
        
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
        
        # Check Python dependencies
        try:
            import fastapi
            import sqlalchemy
            import redis
            import prometheus_client
            logger.info("✅ Python dependencies: OK")
        except ImportError as e:
            raise Exception(f"Missing Python dependency: {e}")
        
        # Check environment file
        env_file = self.project_root / '.env'
        if not env_file.exists():
            logger.warning("⚠️  .env file not found, using defaults")
            await self._create_default_env()
        
        logger.info("✅ Prerequisites check completed")
    
    async def _create_default_env(self):
        """Create default environment file."""
        env_content = """# EasyPay Payment Gateway - Environment Configuration

# Database Configuration
DATABASE_URL=postgresql://easypay:password@postgres:5432/easypay
REDIS_URL=redis://redis:6379/0

# Authorize.net Configuration (Sandbox)
AUTHORIZE_NET_API_LOGIN_ID=your_api_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_transaction_key
AUTHORIZE_NET_SANDBOX=true

# Security Configuration
SECRET_KEY=your-secret-key-change-in-production
ENVIRONMENT=development

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring Configuration
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
"""
        
        env_file = self.project_root / '.env'
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        logger.info("✅ Created default .env file")
    
    async def _start_docker_services(self):
        """Start Docker services."""
        logger.info("🐳 Starting Docker services...")
        
        # Stop any existing containers
        logger.info("Stopping existing containers...")
        subprocess.run(['docker-compose', 'down'], cwd=self.project_root)
        
        # Start services
        logger.info("Starting services...")
        result = subprocess.run(
            ['docker-compose', 'up', '-d'],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to start Docker services: {result.stderr}")
        
        logger.info("✅ Docker services started")
    
    async def _wait_for_services(self):
        """Wait for services to be ready."""
        logger.info("⏳ Waiting for services to be ready...")
        
        for service_name in self.startup_order:
            if service_name in self.services:
                logger.info(f"Waiting for {service_name}...")
                await self._wait_for_service(service_name)
        
        logger.info("✅ All services are ready")
    
    async def _wait_for_service(self, service_name: str, timeout: int = 120):
        """Wait for a specific service to be ready."""
        service_config = self.services[service_name]
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if await service_config['health_check']():
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
    
    async def _verify_system_health(self):
        """Verify system health."""
        logger.info("🏥 Verifying system health...")
        
        health_checks = [
            ('EasyPay API', 'http://localhost:8002/health'),
            ('Kong Gateway', 'http://localhost:8000/health'),
            ('Prometheus', 'http://localhost:9090/-/healthy'),
            ('Grafana', 'http://localhost:3000/api/health'),
        ]
        
        for name, url in health_checks:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    logger.info(f"✅ {name}: Healthy")
                else:
                    logger.warning(f"⚠️  {name}: Status {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠️  {name}: {e}")
        
        logger.info("✅ System health verification completed")
    
    async def _display_system_info(self):
        """Display system information."""
        logger.info("📊 System Information:")
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
        logger.info("🎉 EasyPay Payment Gateway is ready!")
        logger.info("📖 Check the documentation at: http://localhost:8000/docs")
        logger.info("📊 Monitor the system at: http://localhost:3000")


async def main():
    """Main entry point."""
    startup_manager = SystemStartupManager()
    success = await startup_manager.start_system()
    
    if success:
        logger.info("🚀 System startup completed successfully!")
        logger.info("Press Ctrl+C to stop the system")
        
        # Keep the script running
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("👋 Shutting down...")
    else:
        logger.error("❌ System startup failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
