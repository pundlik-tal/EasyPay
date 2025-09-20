#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Testing Environment Setup Script

This script helps set up the testing environment for the payment gateway system.
It checks prerequisites, sets up environment variables, and starts required services.

Usage:
    python scripts/setup_testing_environment.py [--check-only] [--start-services]
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path


class TestingEnvironmentSetup:
    """Setup testing environment for EasyPay Payment Gateway."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.required_packages = [
            "httpx",
            "aiohttp", 
            "pytest",
            "pytest-asyncio",
            "pytest-cov"
        ]
        
        self.required_services = [
            "postgres",
            "redis", 
            "easypay-api",
            "kong",
            "prometheus",
            "grafana",
            "elasticsearch"
        ]
        
        self.required_env_vars = [
            "AUTHORIZE_NET_API_LOGIN_ID",
            "AUTHORIZE_NET_TRANSACTION_KEY",
            "AUTHORIZE_NET_SANDBOX",
            "DATABASE_URL",
            "REDIS_URL",
            "SECRET_KEY",
            "JWT_SECRET_KEY"
        ]
    
    def print_header(self):
        """Print setup header."""
        print("🔧 EasyPay Payment Gateway - Testing Environment Setup")
        print("=" * 60)
    
    def check_python_version(self) -> bool:
        """Check Python version."""
        print("🐍 Checking Python version...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            print(f"❌ Python 3.9+ required, found {version.major}.{version.minor}")
            return False
        
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    
    def check_docker(self) -> bool:
        """Check Docker installation."""
        print("🐳 Checking Docker...")
        
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ {version} - OK")
                return True
            else:
                print("❌ Docker not found or not working")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Docker not found or not working")
            return False
    
    def check_docker_compose(self) -> bool:
        """Check Docker Compose installation."""
        print("🐳 Checking Docker Compose...")
        
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ {version} - OK")
                return True
            else:
                print("❌ Docker Compose not found or not working")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Docker Compose not found or not working")
            return False
    
    def check_python_packages(self) -> bool:
        """Check required Python packages."""
        print("📦 Checking Python packages...")
        
        missing_packages = []
        
        for package in self.required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"✅ {package} - OK")
            except ImportError:
                print(f"❌ {package} - Missing")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n📥 Installing missing packages: {', '.join(missing_packages)}")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install"
                ] + missing_packages, check=True)
                print("✅ Packages installed successfully")
                return True
            except subprocess.CalledProcessError:
                print("❌ Failed to install packages")
                return False
        
        return True
    
    def check_environment_file(self) -> bool:
        """Check if environment file exists."""
        print("📄 Checking environment configuration...")
        
        env_files = [
            ".env.development",
            ".env",
            "env.development",
            "env.example"
        ]
        
        env_file_found = False
        found_env_file = None
        for env_file in env_files:
            if (self.project_root / env_file).exists():
                print(f"✅ Environment file found: {env_file}")
                env_file_found = True
                found_env_file = env_file
                break
        
        # Load environment variables from the found file
        if found_env_file:
            self.load_env_file(found_env_file)
        
        if not env_file_found:
            print("❌ No environment file found")
            print("   Please create env.development with required variables")
            return False
        
        return True
    
    def load_env_file(self, env_file: str):
        """Load environment variables from file."""
        try:
            env_path = self.project_root / env_file
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip('"\'')
                        os.environ[key.strip()] = value
        except Exception as e:
            print(f"⚠️  Warning: Could not load environment file {env_file}: {e}")
    
    def check_environment_variables(self) -> bool:
        """Check required environment variables."""
        print("🔐 Checking environment variables...")
        
        missing_vars = []
        
        for var in self.required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
                print(f"❌ {var} - Missing")
            else:
                # Mask sensitive values
                value = os.getenv(var)
                if "KEY" in var or "SECRET" in var:
                    masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                    print(f"✅ {var} - {masked_value}")
                else:
                    print(f"✅ {var} - {value}")
        
        if missing_vars:
            print(f"\n❌ Missing required environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
            print("\nPlease set these variables in your environment file.")
            return False
        
        return True
    
    def check_docker_compose_file(self) -> bool:
        """Check if docker-compose.yml exists."""
        print("📄 Checking Docker Compose configuration...")
        
        compose_files = [
            "docker-compose.yml",
            "docker-compose.development.yml"
        ]
        
        compose_file_found = False
        for compose_file in compose_files:
            if (self.project_root / compose_file).exists():
                print(f"✅ Docker Compose file found: {compose_file}")
                compose_file_found = True
                break
        
        if not compose_file_found:
            print("❌ No Docker Compose file found")
            return False
        
        return True
    
    def check_services_status(self) -> bool:
        """Check if services are running."""
        print("🔍 Checking service status...")
        
        try:
            result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout
                running_services = []
                
                for service in self.required_services:
                    if service in output and "Up" in output:
                        running_services.append(service)
                        print(f"✅ {service} - Running")
                    else:
                        print(f"❌ {service} - Not running")
                
                if len(running_services) >= len(self.required_services) * 0.8:  # 80% of services running
                    print("✅ Most services are running")
                    return True
                else:
                    print("❌ Many services are not running")
                    return False
            else:
                print("❌ Failed to check service status")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Failed to check service status")
            return False
    
    def start_services(self) -> bool:
        """Start required services."""
        print("🚀 Starting services...")
        
        try:
            # Start services in background
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print("✅ Services started successfully")
                
                # Wait for services to be ready
                print("⏳ Waiting for services to be ready...")
                import time
                time.sleep(30)
                
                return True
            else:
                print("❌ Failed to start services")
                print(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Service startup timed out")
            return False
        except Exception as e:
            print(f"❌ Error starting services: {e}")
            return False
    
    def test_api_connectivity(self) -> bool:
        """Test API connectivity."""
        print("🌐 Testing API connectivity...")
        
        try:
            import httpx
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get("http://localhost:8000/health")
                
                if response.status_code == 200:
                    print("✅ API is accessible")
                    return True
                else:
                    print(f"❌ API returned status {response.status_code}")
                    return False
                    
        except ImportError:
            print("❌ httpx not available for connectivity test")
            return False
        except Exception as e:
            print(f"❌ API connectivity test failed: {e}")
            return False
    
    def create_sample_env_file(self):
        """Create a sample environment file."""
        print("📄 Creating sample environment file...")
        
        sample_env = """# EasyPay Payment Gateway - Development Environment

# Database Configuration
DATABASE_URL=postgresql://easypay:password@localhost:5432/easypay_dev
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=10
REDIS_TIMEOUT=5

# Authorize.net Configuration (REQUIRED FOR TESTING)
AUTHORIZE_NET_API_LOGIN_ID=your_sandbox_login_id
AUTHORIZE_NET_TRANSACTION_KEY=your_sandbox_transaction_key
AUTHORIZE_NET_SANDBOX=true

# Security
SECRET_KEY=your-development-secret-key-change-this
JWT_SECRET_KEY=your-jwt-secret-key-change-this

# Environment
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# API Gateway
KONG_ADMIN_URL=http://localhost:8001
KONG_PROXY_URL=http://localhost:8000

# Monitoring
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000

# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200
"""
        
        env_file = self.project_root / "env.development"
        with open(env_file, "w") as f:
            f.write(sample_env)
        
        print(f"✅ Sample environment file created: {env_file}")
        print("   Please update the Authorize.net credentials before running tests")
    
    def run_setup(self, check_only: bool = False, start_services: bool = False) -> bool:
        """Run the complete setup process."""
        self.print_header()
        
        checks = [
            ("Python Version", self.check_python_version),
            ("Docker", self.check_docker),
            ("Docker Compose", self.check_docker_compose),
            ("Python Packages", self.check_python_packages),
            ("Environment File", self.check_environment_file),
            ("Environment Variables", self.check_environment_variables),
            ("Docker Compose File", self.check_docker_compose_file),
        ]
        
        if not check_only:
            checks.extend([
                ("Service Status", self.check_services_status),
                ("API Connectivity", self.test_api_connectivity),
            ])
        
        all_passed = True
        
        for check_name, check_func in checks:
            try:
                if not check_func():
                    all_passed = False
                    if check_name == "Environment File":
                        self.create_sample_env_file()
                        print("   Please update the environment file and run setup again")
                        return False
            except Exception as e:
                print(f"❌ {check_name} check failed: {e}")
                all_passed = False
        
        if not check_only and start_services:
            if not self.start_services():
                all_passed = False
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 SETUP SUMMARY")
        print("=" * 60)
        
        if all_passed:
            print("✅ All checks passed - Environment is ready for testing!")
            print("\n🚀 Next steps:")
            print("   1. Run comprehensive tests: python scripts/run_all_tests.py")
            print("   2. Run individual tests: python scripts/comprehensive_payment_testing.py")
            print("   3. Monitor performance: python scripts/monitoring_and_metrics.py")
        else:
            print("❌ Some checks failed - Please fix the issues above")
            print("\n🔧 Common fixes:")
            print("   1. Install missing packages: pip install -r requirements.txt")
            print("   2. Start services: docker-compose up -d")
            print("   3. Set environment variables in env.development")
        
        return all_passed


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Testing Environment Setup")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check prerequisites, don't start services")
    parser.add_argument("--start-services", action="store_true",
                       help="Start services after checking prerequisites")
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not os.path.exists("scripts"):
        print("❌ Error: Please run this script from the project root directory")
        print("   Expected to find 'scripts' directory")
        return 1
    
    setup = TestingEnvironmentSetup()
    success = setup.run_setup(args.check_only, args.start_services)
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
