#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Run All Simulations Demo

This script demonstrates all payment gateway simulation capabilities by running
all simulation scripts in sequence and providing a comprehensive overview.

Usage:
    python scripts/run_all_simulations.py [--base-url BASE_URL] [--api-key API_KEY]
"""

import asyncio
import json
import subprocess
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimulationRunner:
    """Runner for all payment gateway simulations."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        """Initialize the simulation runner."""
        self.base_url = base_url
        self.api_key = api_key
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": base_url,
            "simulations": {},
            "summary": {
                "total_simulations": 0,
                "successful_simulations": 0,
                "failed_simulations": 0,
                "overall_success_rate": 0.0
            }
        }
    
    def _run_script(self, script_name: str, args: List[str] = None) -> Dict[str, Any]:
        """Run a simulation script and return results."""
        logger.info(f"🚀 Running {script_name}...")
        
        try:
            # Build command
            cmd = [sys.executable, f"scripts/{script_name}"]
            
            # Add common arguments
            cmd.extend(["--base-url", self.base_url])
            if self.api_key:
                cmd.extend(["--api-key", self.api_key])
            
            # Add custom arguments
            if args:
                cmd.extend(args)
            
            # Run the script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse results
            simulation_result = {
                "script": script_name,
                "command": " ".join(cmd),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if result.returncode == 0:
                logger.info(f"✅ {script_name} completed successfully")
            else:
                logger.error(f"❌ {script_name} failed with return code {result.returncode}")
            
            return simulation_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {script_name} timed out after 5 minutes")
            return {
                "script": script_name,
                "success": False,
                "error": "Timeout after 5 minutes",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"💥 {script_name} failed with error: {str(e)}")
            return {
                "script": script_name,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def run_quick_test(self) -> Dict[str, Any]:
        """Run the quick payment test."""
        logger.info("📋 Running Quick Payment Test...")
        return self._run_script("quick_payment_test.py", ["--output", "quick_test_results.json"])
    
    def run_comprehensive_simulation(self) -> Dict[str, Any]:
        """Run the comprehensive payment simulation."""
        logger.info("🔬 Running Comprehensive Payment Simulation...")
        return self._run_script("comprehensive_payment_simulation.py", 
                               ["--output", "comprehensive_results.json"])
    
    def run_webhook_simulation(self) -> Dict[str, Any]:
        """Run the webhook simulation."""
        logger.info("📡 Running Webhook Simulation...")
        return self._run_script("webhook_simulation.py", 
                               ["--output", "webhook_results.json"])
    
    def run_all_simulations(self) -> Dict[str, Any]:
        """Run all simulation scripts."""
        logger.info("🎯 Starting All Payment Gateway Simulations")
        logger.info(f"Base URL: {self.base_url}")
        logger.info("=" * 60)
        
        # Run all simulations
        simulations = [
            ("Quick Test", self.run_quick_test),
            ("Comprehensive Simulation", self.run_comprehensive_simulation),
            ("Webhook Simulation", self.run_webhook_simulation)
        ]
        
        for name, simulation_func in simulations:
            logger.info(f"\n🔄 Running {name}...")
            result = simulation_func()
            self.results["simulations"][name.lower().replace(" ", "_")] = result
        
        # Calculate summary
        self.results["summary"]["total_simulations"] = len(simulations)
        self.results["summary"]["successful_simulations"] = sum(
            1 for sim in self.results["simulations"].values() if sim.get("success", False)
        )
        self.results["summary"]["failed_simulations"] = (
            self.results["summary"]["total_simulations"] - 
            self.results["summary"]["successful_simulations"]
        )
        self.results["summary"]["overall_success_rate"] = (
            self.results["summary"]["successful_simulations"] / 
            self.results["summary"]["total_simulations"] * 100
        ) if self.results["summary"]["total_simulations"] > 0 else 0
        
        return self.results
    
    def print_summary(self):
        """Print simulation summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 SIMULATION SUMMARY")
        logger.info("=" * 60)
        
        summary = self.results["summary"]
        logger.info(f"Total Simulations: {summary['total_simulations']}")
        logger.info(f"Successful: {summary['successful_simulations']}")
        logger.info(f"Failed: {summary['failed_simulations']}")
        logger.info(f"Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        
        logger.info("\n📋 Individual Results:")
        for name, result in self.results["simulations"].items():
            status = "✅ SUCCESS" if result.get("success", False) else "❌ FAILED"
            logger.info(f"  {name.replace('_', ' ').title()}: {status}")
            
            if not result.get("success", False) and result.get("error"):
                logger.info(f"    Error: {result['error']}")
        
        logger.info(f"\n📁 Results saved to:")
        logger.info(f"  - quick_test_results.json")
        logger.info(f"  - comprehensive_results.json")
        logger.info(f"  - webhook_results.json")
    
    def save_results(self, output_file: str = "all_simulation_results.json"):
        """Save all results to a file."""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"📄 All results saved to {output_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {str(e)}")


def main():
    """Main function to run all simulations."""
    parser = argparse.ArgumentParser(description="EasyPay All Simulations Runner")
    parser.add_argument("--base-url", default="http://localhost:8000", 
                       help="Base URL of the EasyPay API")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--output", default="all_simulation_results.json",
                       help="Output file for combined results")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    parser.add_argument("--quick-only", action="store_true",
                       help="Run only the quick test")
    parser.add_argument("--webhook-only", action="store_true",
                       help="Run only the webhook simulation")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        runner = SimulationRunner(args.base_url, args.api_key)
        
        if args.quick_only:
            logger.info("🚀 Running Quick Test Only...")
            result = runner.run_quick_test()
            runner.results["simulations"]["quick_test"] = result
        elif args.webhook_only:
            logger.info("🚀 Running Webhook Simulation Only...")
            result = runner.run_webhook_simulation()
            runner.results["simulations"]["webhook_simulation"] = result
        else:
            # Run all simulations
            runner.run_all_simulations()
        
        # Print summary
        runner.print_summary()
        
        # Save results
        runner.save_results(args.output)
        
        # Exit with appropriate code
        success_rate = runner.results["summary"]["overall_success_rate"]
        if success_rate >= 80:
            logger.info("🎉 All simulations completed successfully!")
            sys.exit(0)
        else:
            logger.warning("⚠️ Some simulations failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Simulations interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Simulation runner failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
