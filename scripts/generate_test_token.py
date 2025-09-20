#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Generate Test JWT Token

This script creates a test API key and generates a JWT token for testing purposes.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import httpx
from httpx import AsyncClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TokenGenerator:
    """Generate JWT tokens for testing."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the token generator."""
        self.base_url = base_url.rstrip('/')
        self.client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            follow_redirects=True,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "EasyPay-TokenGenerator/1.0"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def create_api_key(self) -> Dict[str, Any]:
        """Create a test API key."""
        logger.info("🔑 Creating test API key...")
        
        api_key_data = {
            "name": "Test API Key",
            "description": "API key for testing payments and subscriptions",
            "permissions": [
                "payments:read",
                "payments:write", 
                "payments:delete",
                "webhooks:read",
                "webhooks:write",
                "admin:read",
                "admin:write"
            ],
            "rate_limit_per_minute": 1000,
            "rate_limit_per_hour": 10000,
            "rate_limit_per_day": 100000
        }
        
        try:
            response = await self.client.post("/api/v1/auth/api-keys", json=api_key_data)
            
            if response.status_code in [200, 201]:
                api_key = response.json()
                logger.info(f"✅ API key created: {api_key.get('key_id')}")
                return api_key
            else:
                logger.error(f"❌ API key creation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ API key creation failed: {str(e)}")
            return None
    
    async def generate_jwt_token(self, api_key_id: str, api_key_secret: str) -> Dict[str, Any]:
        """Generate JWT token using API key credentials."""
        logger.info("🎫 Generating JWT token...")
        
        token_data = {
            "api_key_id": api_key_id,
            "api_key_secret": api_key_secret,
            "expires_in": 3600  # 1 hour
        }
        
        try:
            response = await self.client.post("/api/v1/auth/tokens", json=token_data)
            
            if response.status_code in [200, 201]:
                token = response.json()
                logger.info(f"✅ JWT token generated successfully")
                logger.info(f"   Access token expires in: {token.get('expires_in')} seconds")
                return token
            else:
                logger.error(f"❌ JWT token generation failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ JWT token generation failed: {str(e)}")
            return None
    
    async def generate_test_token(self) -> Dict[str, Any]:
        """Generate a complete test token setup."""
        logger.info("🚀 Starting JWT token generation...")
        
        # Create API key
        api_key = await self.create_api_key()
        if not api_key:
            return None
        
        # Generate JWT token
        token = await self.generate_jwt_token(
            api_key["key_id"],
            api_key["key_secret"]
        )
        
        if not token:
            return None
        
        # Return complete setup
        return {
            "api_key": api_key,
            "token": token,
            "authorization_header": f"Bearer {token['access_token']}"
        }


async def main():
    """Main function to generate test token."""
    try:
        async with TokenGenerator() as generator:
            result = await generator.generate_test_token()
            
            if result:
                logger.info("🎉 Token generation completed successfully!")
                logger.info("=" * 50)
                logger.info("📋 Test Configuration:")
                logger.info(f"   API Key ID: {result['api_key']['key_id']}")
                logger.info(f"   Access Token: {result['token']['access_token'][:50]}...")
                logger.info(f"   Authorization Header: {result['authorization_header']}")
                logger.info("=" * 50)
                
                # Save to file for easy access
                with open("test_token.json", "w") as f:
                    json.dump(result, f, indent=2, default=str)
                logger.info("💾 Token saved to test_token.json")
                
                return result
            else:
                logger.error("❌ Token generation failed")
                return None
                
    except Exception as e:
        logger.error(f"❌ Token generation failed: {str(e)}")
        return None


if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print(f"\nAuthorization Header: {result['authorization_header']}")
        sys.exit(0)
    else:
        sys.exit(1)
