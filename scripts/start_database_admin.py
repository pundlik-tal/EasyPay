#!/usr/bin/env python3
"""
EasyPay Database Admin Startup Script
This script helps you start the database admin interface.
"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def print_banner():
    """Print startup banner."""
    print("=" * 60)
    print("🗄️  EasyPay Database Admin Interface")
    print("=" * 60)
    print()

def check_docker():
    """Check if Docker is running."""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker is available")
            return True
        else:
            print("❌ Docker is not available")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed or not in PATH")
        return False

def start_services():
    """Start Docker services."""
    print("🚀 Starting EasyPay services...")
    try:
        # Start services in background
        result = subprocess.run([
            'docker-compose', 'up', '-d', 'postgres', 'redis', 'pgadmin'
        ], cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0:
            print("✅ Services started successfully")
            return True
        else:
            print("❌ Failed to start services")
            return False
    except Exception as e:
        print(f"❌ Error starting services: {e}")
        return False

def start_api():
    """Start the FastAPI application."""
    print("🚀 Starting EasyPay API...")
    try:
        # Start API in background
        result = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 'src.main:app', 
            '--host', '0.0.0.0', '--port', '8000', '--reload'
        ], cwd=Path(__file__).parent.parent)
        
        print("✅ API started successfully")
        return result
    except Exception as e:
        print(f"❌ Error starting API: {e}")
        return None

def wait_for_services():
    """Wait for services to be ready."""
    print("⏳ Waiting for services to be ready...")
    time.sleep(10)  # Give services time to start
    print("✅ Services should be ready now")

def open_admin_interface():
    """Open the admin interface in browser."""
    print("🌐 Opening database admin interface...")
    try:
        webbrowser.open('http://localhost:8000/api/v1/admin/database')
        print("✅ Admin interface opened in browser")
    except Exception as e:
        print(f"❌ Could not open browser: {e}")
        print("📝 Please manually open: http://localhost:8000/api/v1/admin/database")

def print_connection_info():
    """Print connection information."""
    print("\n" + "=" * 60)
    print("📋 Connection Information")
    print("=" * 60)
    print("Database Admin Interface: http://localhost:8000/api/v1/admin/database")
    print("API Documentation: http://localhost:8000/docs")
    print("pgAdmin (if started): http://localhost:5050")
    print("Grafana Dashboard: http://localhost:3000")
    print()
    print("Database Connection Details:")
    print("  Host: localhost")
    print("  Port: 5432")
    print("  Database: easypay")
    print("  Username: easypay")
    print("  Password: password")
    print()
    print("pgAdmin Login:")
    print("  Email: admin@easypay.com")
    print("  Password: admin")
    print("=" * 60)

def main():
    """Main function."""
    print_banner()
    
    # Check Docker
    if not check_docker():
        print("\n❌ Please install Docker and try again")
        return
    
    # Start services
    if not start_services():
        print("\n❌ Failed to start services")
        return
    
    # Start API
    api_process = start_api()
    if not api_process:
        print("\n❌ Failed to start API")
        return
    
    # Wait for services
    wait_for_services()
    
    # Print connection info
    print_connection_info()
    
    # Open admin interface
    open_admin_interface()
    
    print("\n🎉 EasyPay Database Admin is ready!")
    print("Press Ctrl+C to stop all services")
    
    try:
        # Keep the script running
        api_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        api_process.terminate()
        subprocess.run(['docker-compose', 'down'], cwd=Path(__file__).parent.parent)
        print("✅ Services stopped")

if __name__ == "__main__":
    main()
