#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Authorize.net Integration Test Runner
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.integrations.authorize_net.integration_test import main

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
