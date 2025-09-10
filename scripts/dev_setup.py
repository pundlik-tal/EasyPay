#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Development Setup Script
"""
import os
import subprocess
import sys
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is compatible")


def create_virtual_environment():
    """Create Python virtual environment."""
    if not run_command("python -m venv venv", "Creating virtual environment"):
        return False
    
    # Determine activation script path
    if os.name == 'nt':  # Windows
        activate_script = "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        activate_script = "venv/bin/activate"
    
    print(f"📝 To activate the virtual environment, run:")
    print(f"   {activate_script}")
    
    return True


def install_dependencies():
    """Install Python dependencies."""
    # Determine pip path
    if os.name == 'nt':  # Windows
        pip_path = "venv\\Scripts\\pip"
        python_path = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        pip_path = "venv/bin/pip"
        python_path = "venv/bin/python"
    
    # Try to upgrade pip using python -m pip (more reliable)
    print("🔄 Upgrading pip...")
    try:
        result = subprocess.run(
            [python_path, "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Upgrading pip completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Upgrading pip failed, but continuing: {e.stderr}")
        # Don't fail the entire setup if pip upgrade fails
    
    # Install dependencies
    if not run_command(f"{pip_path} install -r requirements.txt", "Installing dependencies"):
        return False
    
    return True


def setup_environment():
    """Set up environment configuration."""
    print("🔧 Setting up environment configuration...")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists() and env_example.exists():
        env_file.write_text(env_example.read_text())
        print("✅ Created .env file from env.example")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("⚠️  No env.example file found, you'll need to create .env manually")
    
    return True


def check_docker():
    """Check if Docker is available."""
    print("🐳 Checking Docker availability...")
    try:
        # Check if Docker is running
        result = subprocess.run(
            ["docker", "info"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            print("✅ Docker is running")
            if run_command("docker-compose --version", "Checking Docker Compose version"):
                return True
        else:
            print("⚠️  Docker is installed but not running")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        print("⚠️  Docker is not available or not running")
        return False


def setup_database():
    """Set up database (if using Docker)."""
    if check_docker():
        print("🗄️  Setting up database with Docker...")
        if run_command("docker-compose up -d postgres redis", "Starting database services"):
            print("✅ Database services started")
            return True
    else:
        print("⚠️  Docker not available, you'll need to set up PostgreSQL and Redis manually")
    
    return False


def run_tests():
    """Run basic tests to verify setup."""
    print("🧪 Running tests to verify setup...")
    
    # Check if tests directory exists and has test files
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("⚠️  No tests directory found - skipping tests")
        return True
    
    # Look for test files
    test_files = list(tests_dir.rglob("test_*.py"))
    if not test_files:
        print("⚠️  No test files found - skipping tests")
        return True
    
    # Determine python path
    if os.name == 'nt':  # Windows
        python_path = "venv\\Scripts\\python"
    else:  # Unix/Linux/macOS
        python_path = "venv/bin/python"
    
    if run_command(f"{python_path} -m pytest tests/ -v", "Running tests"):
        print("✅ All tests passed")
        return True
    else:
        print("⚠️  Some tests failed, but setup is complete")
        return False


def main():
    """Main setup function."""
    print("🚀 EasyPay Payment Gateway - Development Setup")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Create virtual environment
    if not create_virtual_environment():
        print("❌ Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        print("💡 Try running the following commands manually:")
        if os.name == 'nt':
            print("   venv\\Scripts\\activate")
            print("   venv\\Scripts\\python -m pip install --upgrade pip")
            print("   venv\\Scripts\\pip install -r requirements.txt")
        else:
            print("   source venv/bin/activate")
            print("   venv/bin/python -m pip install --upgrade pip")
            print("   venv/bin/pip install -r requirements.txt")
        sys.exit(1)
    
    # Set up environment
    if not setup_environment():
        print("❌ Failed to set up environment")
        sys.exit(1)
    
    # Check Docker
    docker_available = check_docker()
    
    # Set up database
    if docker_available:
        setup_database()
    
    # Run tests
    run_tests()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Activate the virtual environment:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    
    print("2. Update .env file with your configuration")
    print("3. Start the application:")
    print("   python -m src.main")
    
    if docker_available:
        print("4. Or start with Docker Compose:")
        print("   docker-compose up -d")
    
    print("\n📚 Documentation:")
    print("- API docs: http://localhost:8000/docs")
    print("- Health check: http://localhost:8000/health")
    print("- Metrics: http://localhost:8000/metrics")


if __name__ == "__main__":
    main()
