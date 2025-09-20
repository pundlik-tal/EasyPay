#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Complete Test Suite Runner

This script runs all available tests for the payment gateway system:
- Comprehensive API Testing
- Real-time Endpoint Testing
- Payment Service Testing
- Monitoring and Metrics
- Load Testing

Usage:
    python scripts/run_all_tests.py [--base-url URL] [--quick] [--export-all]
"""

import asyncio
import json
import sys
import os
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List
import subprocess


class TestSuiteRunner:
    """Complete test suite runner for EasyPay Payment Gateway."""
    
    def __init__(self, base_url: str = "http://localhost:8000", quick_mode: bool = False):
        self.base_url = base_url
        self.quick_mode = quick_mode
        self.test_results = {}
        self.start_time = time.time()
        
        # Test scripts to run
        self.test_scripts = [
            {
                "name": "Comprehensive API Testing",
                "script": "scripts/comprehensive_payment_testing.py",
                "args": ["--base-url", self.base_url, "--save-results"],
                "quick_args": ["--base-url", self.base_url]
            },
            {
                "name": "Real-time Endpoint Testing",
                "script": "scripts/test_endpoints_realtime.py",
                "args": [],
                "quick_args": []
            },
            {
                "name": "Payment Service Testing",
                "script": "scripts/test_payment_service.py",
                "args": [],
                "quick_args": []
            },
            {
                "name": "Monitoring and Metrics",
                "script": "scripts/monitoring_and_metrics.py",
                "args": ["--base-url", self.base_url, "--duration", "60", "--interval", "10"],
                "quick_args": ["--base-url", self.base_url, "--duration", "30", "--interval", "5"]
            },
            {
                "name": "Load Testing",
                "script": "scripts/load_testing.py",
                "args": ["--base-url", self.base_url, "--concurrent-users", "10", "--duration", "60", "--export"],
                "quick_args": ["--base-url", self.base_url, "--concurrent-users", "5", "--duration", "30"]
            }
        ]
    
    def print_header(self):
        """Print test suite header."""
        print("🚀 EasyPay Payment Gateway - Complete Test Suite")
        print("=" * 80)
        print(f"📡 Testing against: {self.base_url}")
        print(f"⚡ Quick mode: {'Enabled' if self.quick_mode else 'Disabled'}")
        print(f"⏰ Test started at: {datetime.now().isoformat()}")
        print("=" * 80)
    
    def print_test_header(self, test_name: str, test_number: int, total_tests: int):
        """Print individual test header."""
        print(f"\n🧪 Test {test_number}/{total_tests}: {test_name}")
        print("-" * 60)
    
    def run_script(self, script_info: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test script."""
        script_path = script_info["script"]
        args = script_info["quick_args"] if self.quick_mode else script_info["args"]
        
        # Check if script exists
        if not os.path.exists(script_path):
            return {
                "success": False,
                "error": f"Script not found: {script_path}",
                "duration": 0.0
            }
        
        try:
            start_time = time.time()
            
            # Run the script
            cmd = [sys.executable, script_path] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300 if self.quick_mode else 600  # 5-10 minute timeout
            )
            
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "command": " ".join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test timed out",
                "duration": 300 if self.quick_mode else 600
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration": 0.0
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test scripts."""
        self.print_header()
        
        total_tests = len(self.test_scripts)
        successful_tests = 0
        failed_tests = 0
        
        for i, script_info in enumerate(self.test_scripts, 1):
            self.print_test_header(script_info["name"], i, total_tests)
            
            result = self.run_script(script_info)
            self.test_results[script_info["name"]] = result
            
            if result["success"]:
                print(f"✅ {script_info['name']} - PASSED ({result['duration']:.2f}s)")
                successful_tests += 1
            else:
                print(f"❌ {script_info['name']} - FAILED ({result['duration']:.2f}s)")
                if "error" in result:
                    print(f"   Error: {result['error']}")
                elif result.get("stderr"):
                    print(f"   Error output: {result['stderr'][:200]}...")
                failed_tests += 1
        
        # Calculate summary
        total_duration = time.time() - self.start_time
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "total_duration": total_duration,
                "base_url": self.base_url,
                "quick_mode": self.quick_mode,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": self.test_results
        }
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test suite summary."""
        summary = results["summary"]
        
        print("\n" + "=" * 80)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 80)
        
        print(f"Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['successful_tests']}")
        print(f"❌ Failed: {summary['failed_tests']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⏱️  Total Duration: {summary['total_duration']:.2f} seconds")
        print(f"📡 Base URL: {summary['base_url']}")
        print(f"⚡ Quick Mode: {'Enabled' if summary['quick_mode'] else 'Disabled'}")
        
        if summary['failed_tests'] > 0:
            print(f"\n❌ Failed Tests:")
            for test_name, result in results["test_results"].items():
                if not result["success"]:
                    error_msg = result.get("error", "Unknown error")
                    print(f"  - {test_name}: {error_msg}")
        
        # Performance assessment
        print(f"\n🎯 Overall Assessment:")
        if summary['success_rate'] >= 90:
            print("✅ Excellent - All critical tests passed")
        elif summary['success_rate'] >= 75:
            print("⚠️  Good - Most tests passed, some issues to investigate")
        elif summary['success_rate'] >= 50:
            print("❌ Poor - Significant issues detected")
        else:
            print("🚨 Critical - Major problems detected")
    
    def export_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Export test results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"complete_test_suite_results_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        return filename


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Complete Test Suite Runner")
    parser.add_argument("--base-url", default="http://localhost:8000",
                       help="Base URL for the API (default: http://localhost:8000)")
    parser.add_argument("--quick", action="store_true",
                       help="Run tests in quick mode (shorter duration)")
    parser.add_argument("--export-all", action="store_true",
                       help="Export all test results to JSON files")
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not os.path.exists("scripts"):
        print("❌ Error: Please run this script from the project root directory")
        print("   Expected to find 'scripts' directory")
        return 1
    
    # Check environment variables
    required_vars = [
        "AUTHORIZE_NET_API_LOGIN_ID",
        "AUTHORIZE_NET_TRANSACTION_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables before running the tests.")
        return 1
    
    print("✅ Environment variables configured")
    
    # Run tests
    runner = TestSuiteRunner(args.base_url, args.quick)
    results = runner.run_all_tests()
    
    # Print summary
    runner.print_summary(results)
    
    # Export results if requested
    if args.export_all:
        filename = runner.export_results(results)
        print(f"\n📄 Complete test results exported to: {filename}")
    
    # Return appropriate exit code
    return 0 if results["summary"]["failed_tests"] == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
