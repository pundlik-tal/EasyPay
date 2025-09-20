#!/usr/bin/env python3
"""
Comprehensive test runner for EasyPay Payment Gateway to achieve 80%+ coverage.
"""
import subprocess
import sys
import os
from pathlib import Path

def run_coverage_analysis():
    """Run comprehensive coverage analysis."""
    print("🚀 Starting EasyPay Payment Gateway Comprehensive Test Coverage Analysis")
    print("=" * 80)
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Test files to run
    test_files = [
        "tests/unit/test_comprehensive_coverage.py",
        "tests/unit/test_core_models_comprehensive.py",
        "tests/unit/test_core_services_comprehensive.py",
        "tests/unit/test_api_endpoints_comprehensive.py",
        "tests/unit/test_infrastructure_comprehensive.py",
        "tests/unit/test_integrations_comprehensive.py"
    ]
    
    # Check which test files exist
    existing_test_files = []
    for test_file in test_files:
        if Path(test_file).exists():
            existing_test_files.append(test_file)
            print(f"✅ Found test file: {test_file}")
        else:
            print(f"❌ Missing test file: {test_file}")
    
    if not existing_test_files:
        print("❌ No test files found!")
        return False
    
    print(f"\n📊 Running {len(existing_test_files)} test files...")
    
    # Run tests with coverage
    cmd = [
        "python", "-m", "pytest",
        *existing_test_files,
        "-v",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        "--tb=short"
    ]
    
    print(f"🔧 Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print("\n" + "=" * 80)
        print("📈 COVERAGE RESULTS")
        print("=" * 80)
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ All tests passed!")
            
            # Check if HTML coverage report was generated
            html_report = Path("htmlcov/index.html")
            if html_report.exists():
                print(f"📊 HTML coverage report generated: {html_report.absolute()}")
            
            xml_report = Path("coverage.xml")
            if xml_report.exists():
                print(f"📊 XML coverage report generated: {xml_report.absolute()}")
            
            return True
        else:
            print("❌ Some tests failed!")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Tests timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def run_simple_tests():
    """Run simple tests to verify setup."""
    print("\n🔍 Running simple tests to verify setup...")
    
    # Test basic imports
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__} is available")
    except ImportError:
        print("❌ pytest not available")
        return False
    
    try:
        import pytest_cov
        print("✅ pytest-cov is available")
    except ImportError:
        print("❌ pytest-cov not available")
        return False
    
    # Test basic functionality
    cmd = ["python", "-m", "pytest", "tests/test_basic.py", "-v"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Basic tests pass")
            return True
        else:
            print("❌ Basic tests failed")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running basic tests: {e}")
        return False

def main():
    """Main function."""
    print("🎯 EasyPay Payment Gateway - Comprehensive Test Coverage Analysis")
    print("Target: 80%+ test coverage across all modules")
    print("=" * 80)
    
    # Run simple tests first
    if not run_simple_tests():
        print("❌ Basic setup verification failed!")
        sys.exit(1)
    
    # Run comprehensive coverage analysis
    if run_coverage_analysis():
        print("\n🎉 SUCCESS! Comprehensive test coverage analysis completed!")
        print("📊 Check the generated reports for detailed coverage information.")
    else:
        print("\n❌ FAILURE! Test coverage analysis failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
