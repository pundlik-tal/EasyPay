#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Simple Unit Test Runner
"""
import subprocess
import sys
from pathlib import Path


def main():
    """Run unit tests with coverage."""
    # Change to project root
    project_root = Path(__file__).parent
    import os
    os.chdir(project_root)
    
    print("🚀 Running EasyPay Payment Gateway Unit Tests")
    print("=" * 60)
    
    # Run comprehensive unit tests
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/test_payment_service_comprehensive.py",
        "tests/unit/test_payment_model_comprehensive.py", 
        "tests/unit/test_authorize_net_client_comprehensive.py",
        "tests/unit/test_exceptions_comprehensive.py",
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-fail-under=80",
        "--cov-branch",
        "--tb=short",
        "--disable-warnings"
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n🎉 All tests passed!")
        print("📊 Coverage reports generated:")
        print("   - Terminal: Coverage summary above")
        print("   - HTML: htmlcov/index.html")
        print("   - XML: coverage.xml")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
