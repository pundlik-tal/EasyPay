#!/usr/bin/env python3
"""
Test script for Kong API Gateway functionality
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any


class KongGatewayTester:
    """Test Kong API Gateway functionality"""
    
    def __init__(self, base_url: str = "http://localhost:8000", admin_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.admin_url = admin_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_kong_health(self) -> Dict[str, Any]:
        """Test Kong gateway health"""
        try:
            async with self.session.get(f"{self.admin_url}/status") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "kong_version": data.get("version"),
                        "database": data.get("database"),
                        "server": data.get("server")
                    }
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def test_proxy_health(self) -> Dict[str, Any]:
        """Test proxy health endpoint"""
        try:
            start_time = time.time()
            async with self.session.get(f"{self.base_url}/health") as response:
                end_time = time.time()
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "response_time_ms": round((end_time - start_time) * 1000, 2),
                        "data": data
                    }
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def test_cors_headers(self) -> Dict[str, Any]:
        """Test CORS headers"""
        try:
            headers = {
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
            async with self.session.options(f"{self.base_url}/api/v1/payments", headers=headers) as response:
                cors_headers = {
                    "access_control_allow_origin": response.headers.get("Access-Control-Allow-Origin"),
                    "access_control_allow_methods": response.headers.get("Access-Control-Allow-Methods"),
                    "access_control_allow_headers": response.headers.get("Access-Control-Allow-Headers"),
                    "access_control_allow_credentials": response.headers.get("Access-Control-Allow-Credentials")
                }
                return {
                    "status": "success" if response.status == 200 else "failed",
                    "cors_headers": cors_headers,
                    "response_status": response.status
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting"""
        try:
            requests_made = 0
            rate_limited = False
            
            # Make multiple requests quickly
            for i in range(5):
                async with self.session.get(f"{self.base_url}/api/v1/payments") as response:
                    requests_made += 1
                    if response.status == 429:
                        rate_limited = True
                        break
                    await asyncio.sleep(0.1)
            
            return {
                "status": "success",
                "requests_made": requests_made,
                "rate_limited": rate_limited,
                "rate_limit_working": rate_limited
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_correlation_id(self) -> Dict[str, Any]:
        """Test correlation ID handling"""
        try:
            correlation_id = f"test-{int(time.time())}"
            headers = {"X-Correlation-ID": correlation_id}
            
            async with self.session.get(f"{self.base_url}/health", headers=headers) as response:
                response_correlation_id = response.headers.get("X-Correlation-ID")
                return {
                    "status": "success",
                    "sent_correlation_id": correlation_id,
                    "received_correlation_id": response_correlation_id,
                    "correlation_id_preserved": correlation_id == response_correlation_id
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_response_headers(self) -> Dict[str, Any]:
        """Test response headers"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                headers = dict(response.headers)
                return {
                    "status": "success",
                    "response_headers": headers,
                    "has_response_time": "X-Response-Time" in headers,
                    "has_upstream_latency": "X-Kong-Upstream-Latency" in headers
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_prometheus_metrics(self) -> Dict[str, Any]:
        """Test Prometheus metrics endpoint"""
        try:
            async with self.session.get(f"{self.base_url}/metrics") as response:
                if response.status == 200:
                    content = await response.text()
                    return {
                        "status": "success",
                        "metrics_available": "kong_" in content or "http_" in content,
                        "content_length": len(content)
                    }
                else:
                    return {"status": "failed", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests"""
        print("🚀 Starting Kong API Gateway Tests...")
        
        results = {}
        
        # Test Kong health
        print("📊 Testing Kong health...")
        results["kong_health"] = await self.test_kong_health()
        
        # Test proxy health
        print("🔍 Testing proxy health...")
        results["proxy_health"] = await self.test_proxy_health()
        
        # Test CORS
        print("🌐 Testing CORS headers...")
        results["cors"] = await self.test_cors_headers()
        
        # Test rate limiting
        print("⏱️ Testing rate limiting...")
        results["rate_limiting"] = await self.test_rate_limiting()
        
        # Test correlation ID
        print("🔗 Testing correlation ID...")
        results["correlation_id"] = await self.test_correlation_id()
        
        # Test response headers
        print("📋 Testing response headers...")
        results["response_headers"] = await self.test_response_headers()
        
        # Test Prometheus metrics
        print("📈 Testing Prometheus metrics...")
        results["prometheus_metrics"] = await self.test_prometheus_metrics()
        
        return results


async def main():
    """Main test function"""
    async with KongGatewayTester() as tester:
        results = await tester.run_all_tests()
        
        print("\n" + "="*60)
        print("📋 KONG API GATEWAY TEST RESULTS")
        print("="*60)
        
        for test_name, result in results.items():
            status = result.get("status", "unknown")
            status_emoji = "✅" if status in ["success", "healthy"] else "❌" if status in ["error", "unhealthy", "failed"] else "⚠️"
            print(f"{status_emoji} {test_name.replace('_', ' ').title()}: {status}")
            
            if "error" in result:
                print(f"   Error: {result['error']}")
            elif test_name == "proxy_health" and "response_time_ms" in result:
                print(f"   Response Time: {result['response_time_ms']}ms")
            elif test_name == "rate_limiting" and "rate_limit_working" in result:
                print(f"   Rate Limit Working: {result['rate_limit_working']}")
            elif test_name == "correlation_id" and "correlation_id_preserved" in result:
                print(f"   Correlation ID Preserved: {result['correlation_id_preserved']}")
        
        print("\n" + "="*60)
        
        # Summary
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() 
                          if result.get("status") in ["success", "healthy"])
        
        print(f"📊 Summary: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! Kong API Gateway is working correctly.")
        else:
            print("⚠️ Some tests failed. Please check the configuration.")
        
        return results


if __name__ == "__main__":
    asyncio.run(main())
