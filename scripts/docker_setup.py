#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Docker Setup Script
"""
import subprocess
import sys
from pathlib import Path


def check_docker():
    """Check if Docker is available and running."""
    print("🐳 Checking Docker availability...")
    try:
        result = subprocess.run(
            ["docker", "info"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            print("✅ Docker is running")
            return True
        else:
            print("❌ Docker is installed but not running")
            print("💡 Please start Docker Desktop and try again")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        print("❌ Docker is not available")
        print("💡 Please install Docker Desktop from: https://www.docker.com/products/docker-desktop")
        return False


def start_services():
    """Start database services using Docker Compose."""
    if not check_docker():
        return False
    
    print("🚀 Starting database services...")
    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d", "postgres", "redis"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Database services started successfully")
        print("📊 Services running:")
        print("   - PostgreSQL: localhost:5432")
        print("   - Redis: localhost:6379")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start services: {e.stderr}")
        return False


def stop_services():
    """Stop database services."""
    print("🛑 Stopping database services...")
    try:
        result = subprocess.run(
            ["docker-compose", "down"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Database services stopped")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to stop services: {e.stderr}")
        return False


def show_status():
    """Show status of Docker services."""
    print("📊 Docker services status:")
    try:
        result = subprocess.run(
            ["docker-compose", "ps"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to get status: {e.stderr}")
        return False


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("🚀 EasyPay Payment Gateway - Docker Setup")
        print("=" * 50)
        print("Usage:")
        print("  python scripts/docker_setup.py start    - Start database services")
        print("  python scripts/docker_setup.py stop     - Stop database services")
        print("  python scripts/docker_setup.py status  - Show service status")
        print("  python scripts/docker_setup.py check    - Check Docker availability")
        return
    
    command = sys.argv[1].lower()
    
    if command == "start":
        start_services()
    elif command == "stop":
        stop_services()
    elif command == "status":
        show_status()
    elif command == "check":
        check_docker()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: start, stop, status, check")


if __name__ == "__main__":
    main()
