#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Create Test API Key Directly

This script creates a test API key directly in the database for testing purposes.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.infrastructure.database import get_db_session
from src.core.services.auth_service import AuthService
from src.api.v1.schemas.auth import APIKeyCreateRequest
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_test_api_key():
    """Create a test API key directly in the database."""
    logger.info("🔑 Creating test API key directly in database...")
    
    try:
        async for db in get_db_session():
            auth_service = AuthService(db)
            
            # Create API key request
            api_key_request = APIKeyCreateRequest(
                name="Test API Key",
                description="API key for testing payments and subscriptions",
                permissions=[
                    "payments:read",
                    "payments:write", 
                    "payments:delete",
                    "webhooks:read",
                    "webhooks:write",
                    "admin:read",
                    "admin:write"
                ],
                rate_limit_per_minute=1000,
                rate_limit_per_hour=10000,
                rate_limit_per_day=100000
            )
            
            # Create the API key
            result = await auth_service.create_api_key(api_key_request)
            
            logger.info("✅ Test API key created successfully!")
            logger.info(f"   Key ID: {result['key_id']}")
            logger.info(f"   Key Secret: {result['key_secret']}")
            
            # Generate JWT token
            logger.info("🎫 Generating JWT token...")
            token_request = {
                "api_key_id": result['key_id'],
                "api_key_secret": result['key_secret'],
                "expires_in": 3600
            }
            
            token_result = await auth_service.generate_tokens(token_request)
            
            logger.info("✅ JWT token generated successfully!")
            logger.info(f"   Access Token: {token_result['access_token'][:50]}...")
            logger.info(f"   Expires in: {token_result['expires_in']} seconds")
            
            return {
                "api_key": result,
                "token": token_result,
                "authorization_header": f"Bearer {token_result['access_token']}"
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to create test API key: {str(e)}")
        return None


async def main():
    """Main function."""
    result = await create_test_api_key()
    
    if result:
        print("\n" + "="*50)
        print("🎉 Test API Key and Token Created Successfully!")
        print("="*50)
        print(f"API Key ID: {result['api_key']['key_id']}")
        print(f"API Key Secret: {result['api_key']['key_secret']}")
        print(f"Authorization Header: {result['authorization_header']}")
        print("="*50)
        
        # Save to file
        import json
        with open("test_credentials.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        print("💾 Credentials saved to test_credentials.json")
        
        return result
    else:
        print("❌ Failed to create test credentials")
        return None


if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
