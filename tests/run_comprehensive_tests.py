#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Comprehensive Test Runner

This script runs comprehensive test suites including unit, integration, e2e,
performance, security, load, and chaos engineering tests.
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any


def run_command(command: List[str], description: str, timeout: int = 300) -> Dict[str, Any]:
    """Run a command and return detailed results."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True,
            timeout=timeout
        )
        end_time = time.time()
        
        return {
            "success": True,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": end_time - start_time,
            "description": description
        }
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        return {
            "success": False,
            "exit_code": e.returncode,
            "stdout": e.stdout if hasattr(e, 'stdout') else "",
            "stderr": e.stderr if hasattr(e, 'stderr') else "",
            "duration": end_time - start_time,
            "description": description,
            "error": str(e)
        }
    except subprocess.TimeoutExpired as e:
        end_time = time.time()
        return {
            "success": False,
            "exit_code": -1,
            "stdout": e.stdout if hasattr(e, 'stdout') else "",
            "stderr": e.stderr if hasattr(e, 'stderr') else "",
            "duration": end_time - start_time,
            "description": description,
            "error": f"Timeout after {timeout} seconds"
        }
    except FileNotFoundError:
        end_time = time.time()
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command not found: {command[0]}",
            "duration": end_time - start_time,
            "description": description,
            "error": f"Command not found: {command[0]}"
        }


def run_test_suite(test_type: str, coverage: bool = False, verbose: bool = False, 
                  parallel: bool = False, markers: str = None) -> Dict[str, Any]:
    """Run a specific test suite."""
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-vv")
    
    # Add parallel execution
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # Add coverage
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml",
            "--cov-fail-under=80"
        ])
    
    # Add markers
    if markers:
        cmd.extend(["-m", markers])
    
    # Add test type specific markers
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
        cmd.append("tests/integration/")
    elif test_type == "e2e":
        cmd.extend(["-m", "e2e"])
        cmd.append("tests/e2e/")
    elif test_type == "performance":
        cmd.extend(["-m", "performance"])
        cmd.append("tests/performance/")
    elif test_type == "security":
        cmd.extend(["-m", "security"])
        cmd.append("tests/security/")
    elif test_type == "load":
        cmd.extend(["-m", "load"])
        cmd.append("tests/load/")
    elif test_type == "chaos":
        cmd.extend(["-m", "chaos"])
        cmd.append("tests/chaos/")
    elif test_type == "all":
        cmd.append("tests/")
    else:
        cmd.append(f"tests/{test_type}/")
    
    # Set timeout based on test type
    timeout = 300  # 5 minutes default
    if test_type in ["performance", "load", "chaos"]:
        timeout = 1800  # 30 minutes for heavy tests
    
    return run_command(cmd, f"{test_type.title()} Tests", timeout)


def run_linting() -> Dict[str, Any]:
    """Run code linting."""
    commands = [
        (["python", "-m", "flake8", "src/", "tests/"], "Flake8 Linting"),
        (["python", "-m", "black", "--check", "src/", "tests/"], "Black Formatting Check"),
        (["python", "-m", "isort", "--check-only", "src/", "tests/"], "Import Sorting Check"),
        (["python", "-m", "mypy", "src/"], "Type Checking")
    ]
    
    results = []
    for cmd, description in commands:
        result = run_command(cmd, description, timeout=120)
        results.append(result)
    
    return {
        "success": all(r["success"] for r in results),
        "results": results,
        "description": "Code Quality Checks"
    }


def generate_test_report(results: List[Dict[str, Any]]) -> str:
    """Generate a comprehensive test report."""
    report = []
    report.append("EasyPay Comprehensive Test Report")
    report.append("=" * 50)
    report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    total_tests = len(results)
    successful_tests = len([r for r in results if r["success"]])
    failed_tests = total_tests - successful_tests
    
    report.append("Summary:")
    report.append(f"  Total Test Suites: {total_tests}")
    report.append(f"  Successful: {successful_tests}")
    report.append(f"  Failed: {failed_tests}")
    report.append(f"  Success Rate: {successful_tests/total_tests:.2%}")
    report.append("")
    
    total_duration = sum(r["duration"] for r in results)
    report.append(f"Total Duration: {total_duration:.2f} seconds")
    report.append("")
    
    report.append("Detailed Results:")
    report.append("-" * 30)
    
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        report.append(f"{status} {result['description']}")
        report.append(f"    Duration: {result['duration']:.2f}s")
        
        if not result["success"]:
            if "error" in result:
                report.append(f"    Error: {result['error']}")
            if result["stderr"]:
                report.append(f"    Stderr: {result['stderr'][:200]}...")
        
        report.append("")
    
    return "\n".join(report)


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="EasyPay Comprehensive Test Runner")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "e2e", "performance", "security", "load", "chaos", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage reporting"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Run with verbose output"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run code quality checks"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed test report"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (skip slow tests)"
    )
    parser.add_argument(
        "--markers",
        help="Run tests with specific markers (e.g., 'unit and not slow')"
    )
    
    args = parser.parse_args()
    
    print("EasyPay Comprehensive Test Runner")
    print("=" * 40)
    
    start_time = time.time()
    results = []
    
    # Run linting if requested
    if args.lint:
        print("\nRunning code quality checks...")
        lint_result = run_linting()
        results.append(lint_result)
        
        if not lint_result["success"]:
            print("❌ Code quality checks failed!")
            for result in lint_result["results"]:
                if not result["success"]:
                    print(f"  - {result['description']}: {result.get('error', 'Failed')}")
            sys.exit(1)
        else:
            print("✅ Code quality checks passed!")
    
    # Run tests
    if args.type == "all":
        test_types = ["unit", "integration", "e2e", "performance", "security", "load", "chaos"]
    else:
        test_types = [args.type]
    
    # Skip slow tests if quick mode
    if args.quick:
        test_types = [t for t in test_types if t not in ["performance", "load", "chaos"]]
        print("🚀 Quick mode: Skipping slow tests (performance, load, chaos)")
    
    for test_type in test_types:
        print(f"\nRunning {test_type} tests...")
        
        # Add markers for quick mode
        markers = args.markers
        if args.quick and not markers:
            markers = "not slow"
        
        result = run_test_suite(
            test_type=test_type,
            coverage=args.coverage,
            verbose=args.verbose,
            parallel=args.parallel,
            markers=markers
        )
        
        results.append(result)
        
        if result["success"]:
            print(f"✅ {test_type.title()} tests passed!")
        else:
            print(f"❌ {test_type.title()} tests failed!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            if result["stderr"]:
                print(f"   Stderr: {result['stderr'][:500]}...")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Generate report
    if args.report:
        report = generate_test_report(results)
        print("\n" + report)
        
        # Save report to file
        report_file = f"test_report_{int(time.time())}.txt"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\nDetailed report saved to: {report_file}")
    
    # Summary
    successful_tests = len([r for r in results if r["success"]])
    total_tests = len(results)
    
    print(f"\n{'='*50}")
    print(f"Test Summary:")
    print(f"  Total Test Suites: {total_tests}")
    print(f"  Successful: {successful_tests}")
    print(f"  Failed: {total_tests - successful_tests}")
    print(f"  Success Rate: {successful_tests/total_tests:.2%}")
    print(f"  Total Duration: {total_duration:.2f} seconds")
    print(f"{'='*50}")
    
    if successful_tests == total_tests:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
