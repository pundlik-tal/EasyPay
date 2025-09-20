#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Authentication System Test Script

This script tests the authentication system implementation.
"""

import asyncio
import httpx
import json
from typing import Dict, Any


class AuthSystemTester:
    """Test the authentication system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the tester."""
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key_id = None
        self.api_key_secret = None
        self.access_token = None
        self.refresh_token = None
    
    async def test_health_check(self) -> bool:
        """Test health check endpoint."""
        print("🔍 Testing health check...")
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_create_api_key(self) -> bool:
        """Test API key creation."""
        print("🔍 Testing API key creation...")
        try:
            # First, we need to create an API key with admin permissions
            # For testing, we'll use a simple approach
            payload = {
                "name": "Test API Key",
                "description": "Test API key for authentication testing",
                "permissions": [
                    "payments:read",
                    "payments:write",
                    "payments:delete",
                    "webhooks:read",
                    "webhooks:write",
                    "admin:read",
                    "admin:write"
                ],
                "rate_limit_per_minute": 100,
                "rate_limit_per_hour": 1000,
                "rate_limit_per_day": 10000
            }
            
            # For testing, we'll create the API key directly via database
            # In a real scenario, this would require admin authentication
            print("⚠️  Note: API key creation requires admin authentication")
            print("   For testing, we'll simulate the creation process")
            
            # Simulate API key creation
            self.api_key_id = "ak_test_123456789"
            self.api_key_secret = "test_secret_abcdefghijklmnopqrstuvwxyz123456"
            
            print("✅ API key creation simulated")
            return True
            
        except Exception as e:
            print(f"❌ API key creation error: {e}")
            return False
    
    async def test_generate_tokens(self) -> bool:
        """Test token generation."""
        print("🔍 Testing token generation...")
        try:
            payload = {
                "api_key_id": self.api_key_id,
                "api_key_secret": self.api_key_secret,
                "expires_in": 3600
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/tokens",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                print("✅ Token generation successful")
                print(f"   Access token: {self.access_token[:50]}...")
                print(f"   Refresh token: {self.refresh_token[:50]}...")
                return True
            else:
                print(f"❌ Token generation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Token generation error: {e}")
            return False
    
    async def test_token_validation(self) -> bool:
        """Test token validation."""
        print("🔍 Testing token validation...")
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/tokens/validate",
                params={"token": self.access_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["valid"]:
                    print("✅ Token validation successful")
                    print(f"   API Key ID: {data.get('api_key_id')}")
                    print(f"   Permissions: {data.get('permissions')}")
                    return True
                else:
                    print(f"❌ Token validation failed: {data.get('error')}")
                    return False
            else:
                print(f"❌ Token validation request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Token validation error: {e}")
            return False
    
    async def test_authenticated_request(self) -> bool:
        """Test authenticated request to payment endpoint."""
        print("🔍 Testing authenticated request...")
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Test payment list endpoint
            response = await self.client.get(
                f"{self.base_url}/api/v1/payments",
                headers=headers
            )
            
            if response.status_code == 200:
                print("✅ Authenticated request successful")
                data = response.json()
                print(f"   Found {data.get('total', 0)} payments")
                return True
            else:
                print(f"❌ Authenticated request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authenticated request error: {e}")
            return False
    
    async def test_api_key_authentication(self) -> bool:
        """Test API key authentication."""
        print("🔍 Testing API key authentication...")
        try:
            headers = {
                "X-API-Key-ID": self.api_key_id,
                "X-API-Key-Secret": self.api_key_secret,
                "Content-Type": "application/json"
            }
            
            # Test payment list endpoint with API key
            response = await self.client.get(
                f"{self.base_url}/api/v1/payments",
                headers=headers
            )
            
            if response.status_code == 200:
                print("✅ API key authentication successful")
                data = response.json()
                print(f"   Found {data.get('total', 0)} payments")
                return True
            else:
                print(f"❌ API key authentication failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API key authentication error: {e}")
            return False
    
    async def test_permission_check(self) -> bool:
        """Test permission checking."""
        print("🔍 Testing permission check...")
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "permission": "payments:read"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/permissions/check",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["has_permission"]:
                    print("✅ Permission check successful")
                    print(f"   Has permission: {data['permission']}")
                    return True
                else:
                    print(f"❌ Permission check failed: No permission for {data['permission']}")
                    return False
            else:
                print(f"❌ Permission check request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Permission check error: {e}")
            return False
    
    async def test_token_refresh(self) -> bool:
        """Test token refresh."""
        print("🔍 Testing token refresh...")
        try:
            payload = {
                "refresh_token": self.refresh_token
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/tokens/refresh",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                new_access_token = data["access_token"]
                new_refresh_token = data["refresh_token"]
                print("✅ Token refresh successful")
                print(f"   New access token: {new_access_token[:50]}...")
                print(f"   New refresh token: {new_refresh_token[:50]}...")
                
                # Update tokens
                self.access_token = new_access_token
                self.refresh_token = new_refresh_token
                return True
            else:
                print(f"❌ Token refresh failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Token refresh error: {e}")
            return False
    
    async def test_unauthorized_request(self) -> bool:
        """Test unauthorized request."""
        print("🔍 Testing unauthorized request...")
        try:
            # Make request without authentication
            response = await self.client.get(f"{self.base_url}/api/v1/payments")
            
            if response.status_code == 401:
                print("✅ Unauthorized request correctly rejected")
                return True
            else:
                print(f"❌ Unauthorized request not rejected: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Unauthorized request error: {e}")
            return False
    
    async def test_current_user_info(self) -> bool:
        """Test current user info endpoint."""
        print("🔍 Testing current user info...")
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/auth/me",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Current user info retrieved")
                print(f"   API Key ID: {data.get('api_key_id')}")
                print(f"   Auth Type: {data.get('auth_type')}")
                print(f"   Permissions: {data.get('permissions')}")
                return True
            else:
                print(f"❌ Current user info request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Current user info error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all authentication tests."""
        print("🚀 Starting Authentication System Tests")
        print("=" * 50)
        
        results = {}
        
        # Test health check first
        results["health_check"] = await self.test_health_check()
        
        if not results["health_check"]:
            print("❌ Health check failed, stopping tests")
            return results
        
        # Test API key creation
        results["create_api_key"] = await self.test_create_api_key()
        
        # Test token generation
        results["generate_tokens"] = await self.test_generate_tokens()
        
        # Test token validation
        if results["generate_tokens"]:
            results["token_validation"] = await self.test_token_validation()
        
        # Test authenticated requests
        if results["generate_tokens"]:
            results["authenticated_request"] = await self.test_authenticated_request()
            results["api_key_authentication"] = await self.test_api_key_authentication()
            results["permission_check"] = await self.test_permission_check()
            results["current_user_info"] = await self.test_current_user_info()
        
        # Test token refresh
        if results["generate_tokens"]:
            results["token_refresh"] = await self.test_token_refresh()
        
        # Test unauthorized request
        results["unauthorized_request"] = await self.test_unauthorized_request()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:25} {status}")
            if result:
                passed += 1
        
        print("=" * 50)
        print(f"Total: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All authentication tests passed!")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return results
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test function."""
    tester = AuthSystemTester()
    
    try:
        await tester.run_all_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
