#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Comprehensive Unit Test Runner
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional


def run_command(command: List[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {command[0]}")
        return False


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    print("Checking dependencies...")
    
    required_packages = [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-mock",
        "pytest-xdist"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is not installed")
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    return True


def run_unit_tests(
    test_path: str = "tests/unit",
    coverage: bool = True,
    parallel: bool = False,
    verbose: bool = True,
    markers: Optional[str] = None
) -> bool:
    """Run unit tests with optional coverage."""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test path
    cmd.append(test_path)
    
    # Add verbosity
    if verbose:
        cmd.extend(["-v", "-s"])
    
    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=80",
            "--cov-branch"
        ])
    
    # Add parallel execution
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # Add markers
    if markers:
        cmd.extend(["-m", markers])
    
    # Add unit test marker
    cmd.extend(["-m", "unit"])
    
    # Add additional options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    return run_command(cmd, "Unit Tests")


def run_specific_test_files(test_files: List[str], coverage: bool = True) -> bool:
    """Run specific test files."""
    
    cmd = ["python", "-m", "pytest"]
    
    # Add test files
    cmd.extend(test_files)
    
    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=80",
            "--cov-branch"
        ])
    
    # Add additional options
    cmd.extend([
        "-v",
        "-s",
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    return run_command(cmd, f"Specific Tests: {', '.join(test_files)}")


def run_coverage_report() -> bool:
    """Generate coverage report."""
    cmd = ["python", "-m", "coverage", "report"]
    return run_command(cmd, "Coverage Report")


def run_coverage_html() -> bool:
    """Generate HTML coverage report."""
    cmd = ["python", "-m", "coverage", "html"]
    return run_command(cmd, "HTML Coverage Report")


def run_coverage_xml() -> bool:
    """Generate XML coverage report."""
    cmd = ["python", "-m", "coverage", "xml"]
    return run_command(cmd, "XML Coverage Report")


def run_linting() -> bool:
    """Run code linting."""
    linting_commands = [
        (["python", "-m", "flake8", "src"], "Flake8 Linting"),
        (["python", "-m", "black", "--check", "src"], "Black Format Check"),
        (["python", "-m", "isort", "--check-only", "src"], "Import Sort Check"),
        (["python", "-m", "mypy", "src"], "Type Checking")
    ]
    
    success = True
    for cmd, description in linting_commands:
        if not run_command(cmd, description):
            success = False
    
    return success


def run_all_tests() -> bool:
    """Run all tests and checks."""
    print("🚀 Starting comprehensive test suite for EasyPay Payment Gateway")
    print("=" * 80)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    success = True
    
    # Run unit tests
    if not run_unit_tests():
        success = False
    
    # Run specific comprehensive tests
    comprehensive_tests = [
        "tests/unit/test_payment_service_comprehensive.py",
        "tests/unit/test_payment_model_comprehensive.py",
        "tests/unit/test_authorize_net_client_comprehensive.py",
        "tests/unit/test_exceptions_comprehensive.py"
    ]
    
    for test_file in comprehensive_tests:
        if os.path.exists(test_file):
            if not run_specific_test_files([test_file]):
                success = False
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    # Run linting
    if not run_linting():
        success = False
    
    # Generate coverage reports
    if not run_coverage_report():
        success = False
    
    if not run_coverage_html():
        success = False
    
    if not run_coverage_xml():
        success = False
    
    # Print summary
    print("\n" + "=" * 80)
    if success:
        print("🎉 All tests and checks passed!")
        print("📊 Coverage reports generated in htmlcov/ and coverage.xml")
        print("📁 HTML coverage report: htmlcov/index.html")
    else:
        print("❌ Some tests or checks failed!")
        print("🔍 Check the output above for details")
    
    print("=" * 80)
    
    return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="EasyPay Payment Gateway - Comprehensive Unit Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_comprehensive_unit_tests.py                    # Run all tests
  python run_comprehensive_unit_tests.py --no-coverage     # Run without coverage
  python run_comprehensive_unit_tests.py --parallel        # Run with parallel execution
  python run_comprehensive_unit_tests.py --file test_payment_service_comprehensive.py
  python run_comprehensive_unit_tests.py --lint-only       # Run only linting
  python run_comprehensive_unit_tests.py --coverage-only   # Run only coverage reports
        """
    )
    
    parser.add_argument(
        "--file", "-f",
        action="append",
        help="Run specific test files"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Run tests without coverage"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--lint-only",
        action="store_true",
        help="Run only linting checks"
    )
    
    parser.add_argument(
        "--coverage-only",
        action="store_true",
        help="Run only coverage reports"
    )
    
    parser.add_argument(
        "--markers", "-m",
        help="Run tests with specific markers"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    success = True
    
    if args.lint_only:
        success = run_linting()
    elif args.coverage_only:
        success = run_coverage_report() and run_coverage_html() and run_coverage_xml()
    elif args.file:
        success = run_specific_test_files(args.file, not args.no_coverage)
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
