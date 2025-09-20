#!/usr/bin/env python3
"""
Coverage Analysis Script for EasyPay Payment Gateway
"""
import subprocess
import sys
import os
from pathlib import Path

def run_coverage_analysis():
    """Run comprehensive test coverage analysis."""
    print("=== EasyPay Payment Gateway - Test Coverage Analysis ===\n")
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Commands to run
    commands = [
        {
            "name": "Unit Tests with Coverage",
            "cmd": [sys.executable, "-m", "pytest", "tests/unit/", "--cov=src", 
                   "--cov-report=term-missing", "--cov-report=html:htmlcov", 
                   "--cov-report=xml", "--cov-fail-under=80", "-v"],
            "output_file": "unit_test_coverage.txt"
        },
        {
            "name": "Integration Tests with Coverage", 
            "cmd": [sys.executable, "-m", "pytest", "tests/integration/", "--cov=src",
                   "--cov-report=term-missing", "--cov-report=html:htmlcov_integration",
                   "--cov-report=xml:coverage_integration.xml", "-v"],
            "output_file": "integration_test_coverage.txt"
        },
        {
            "name": "All Tests with Coverage",
            "cmd": [sys.executable, "-m", "pytest", "tests/", "--cov=src",
                   "--cov-report=term-missing", "--cov-report=html:htmlcov_all",
                   "--cov-report=xml:coverage_all.xml", "--cov-fail-under=80", "-v"],
            "output_file": "all_tests_coverage.txt"
        }
    ]
    
    results = {}
    
    for test_config in commands:
        print(f"Running: {test_config['name']}")
        print("=" * 60)
        
        try:
            result = subprocess.run(
                test_config["cmd"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Save output to file
            with open(test_config["output_file"], "w", encoding="utf-8") as f:
                f.write(f"=== {test_config['name']} ===\n")
                f.write(f"Exit Code: {result.returncode}\n")
                f.write(f"Command: {' '.join(test_config['cmd'])}\n\n")
                f.write("=== STDOUT ===\n")
                f.write(result.stdout)
                f.write("\n=== STDERR ===\n")
                f.write(result.stderr)
            
            results[test_config["name"]] = {
                "exit_code": result.returncode,
                "output_file": test_config["output_file"],
                "success": result.returncode == 0
            }
            
            print(f"✅ Completed: {test_config['name']}")
            print(f"   Exit Code: {result.returncode}")
            print(f"   Output saved to: {test_config['output_file']}")
            
            # Print key metrics if successful
            if result.returncode == 0 and "TOTAL" in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "TOTAL" in line and "%" in line:
                        print(f"   Coverage: {line.strip()}")
                        break
                        
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout: {test_config['name']}")
            results[test_config["name"]] = {
                "exit_code": -1,
                "output_file": test_config["output_file"],
                "success": False,
                "error": "Timeout"
            }
        except Exception as e:
            print(f"❌ Error: {test_config['name']} - {str(e)}")
            results[test_config["name"]] = {
                "exit_code": -1,
                "output_file": test_config["output_file"], 
                "success": False,
                "error": str(e)
            }
        
        print()
    
    # Summary
    print("=== SUMMARY ===")
    print("=" * 60)
    for name, result in results.items():
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{name}: {status}")
        if not result["success"] and "error" in result:
            print(f"  Error: {result['error']}")
        print(f"  Details: {result['output_file']}")
    
    # Check for coverage reports
    print("\n=== COVERAGE REPORTS ===")
    reports = ["htmlcov", "htmlcov_integration", "htmlcov_all", "coverage.xml", "coverage_integration.xml", "coverage_all.xml"]
    for report in reports:
        if os.path.exists(report):
            print(f"✅ Generated: {report}")
        else:
            print(f"❌ Missing: {report}")
    
    return results

if __name__ == "__main__":
    results = run_coverage_analysis()
    
    # Exit with error code if any tests failed
    success = all(r["success"] for r in results.values())
    sys.exit(0 if success else 1)
