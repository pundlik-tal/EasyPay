#!/usr/bin/env python3
"""
Kong API Gateway Setup and Configuration Script
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List


class KongSetup:
    """Kong API Gateway setup and configuration"""
    
    def __init__(self, admin_url: str = "http://localhost:8001"):
        self.admin_url = admin_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def wait_for_kong(self, max_retries: int = 30) -> bool:
        """Wait for Kong to be ready"""
        print("⏳ Waiting for Kong to be ready...")
        
        for i in range(max_retries):
            try:
                async with self.session.get(f"{self.admin_url}/status") as response:
                    if response.status == 200:
                        print("✅ Kong is ready!")
                        return True
            except Exception:
                pass
            
            print(f"   Attempt {i+1}/{max_retries}...")
            await asyncio.sleep(2)
        
        print("❌ Kong failed to start within timeout")
        return False
    
    async def get_kong_info(self) -> Dict[str, Any]:
        """Get Kong information"""
        try:
            async with self.session.get(f"{self.admin_url}/") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_services(self) -> List[Dict[str, Any]]:
        """Get all services"""
        try:
            async with self.session.get(f"{self.admin_url}/services") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    return []
        except Exception as e:
            print(f"Error getting services: {e}")
            return []
    
    async def get_routes(self) -> List[Dict[str, Any]]:
        """Get all routes"""
        try:
            async with self.session.get(f"{self.admin_url}/routes") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    return []
        except Exception as e:
            print(f"Error getting routes: {e}")
            return []
    
    async def get_plugins(self) -> List[Dict[str, Any]]:
        """Get all plugins"""
        try:
            async with self.session.get(f"{self.admin_url}/plugins") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    return []
        except Exception as e:
            print(f"Error getting plugins: {e}")
            return []
    
    async def test_service_connectivity(self, service_url: str) -> Dict[str, Any]:
        """Test service connectivity"""
        try:
            start_time = time.time()
            async with self.session.get(f"{service_url}/health", timeout=5) as response:
                end_time = time.time()
                return {
                    "status": "success",
                    "response_time_ms": round((end_time - start_time) * 1000, 2),
                    "status_code": response.status,
                    "accessible": response.status == 200
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "accessible": False
            }
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """Validate Kong configuration"""
        print("🔍 Validating Kong configuration...")
        
        results = {
            "kong_info": await self.get_kong_info(),
            "services": await self.get_services(),
            "routes": await self.get_routes(),
            "plugins": await self.get_plugins()
        }
        
        # Test service connectivity
        services = results["services"]
        for service in services:
            service_name = service.get("name", "unknown")
            service_url = service.get("url", "")
            print(f"🔗 Testing connectivity to {service_name}...")
            results[f"service_{service_name}_connectivity"] = await self.test_service_connectivity(service_url)
        
        return results
    
    async def print_status_report(self):
        """Print comprehensive status report"""
        print("\n" + "="*80)
        print("📊 KONG API GATEWAY STATUS REPORT")
        print("="*80)
        
        # Kong info
        kong_info = await self.get_kong_info()
        if "error" not in kong_info:
            print(f"🚀 Kong Version: {kong_info.get('version', 'Unknown')}")
            print(f"📅 Kong Started: {kong_info.get('started_at', 'Unknown')}")
            print(f"🗄️ Database: {kong_info.get('database', 'Unknown')}")
        else:
            print(f"❌ Kong Info Error: {kong_info['error']}")
        
        # Services
        services = await self.get_services()
        print(f"\n🔧 Services ({len(services)}):")
        for service in services:
            name = service.get("name", "Unknown")
            url = service.get("url", "Unknown")
            print(f"   • {name}: {url}")
        
        # Routes
        routes = await self.get_routes()
        print(f"\n🛣️ Routes ({len(routes)}):")
        for route in routes:
            name = route.get("name", "Unknown")
            paths = route.get("paths", [])
            methods = route.get("methods", [])
            print(f"   • {name}: {paths} [{', '.join(methods)}]")
        
        # Plugins
        plugins = await self.get_plugins()
        print(f"\n🔌 Plugins ({len(plugins)}):")
        plugin_counts = {}
        for plugin in plugins:
            plugin_name = plugin.get("name", "Unknown")
            plugin_counts[plugin_name] = plugin_counts.get(plugin_name, 0) + 1
        
        for plugin_name, count in plugin_counts.items():
            print(f"   • {plugin_name}: {count} instance(s)")
        
        # Service connectivity
        print(f"\n🌐 Service Connectivity:")
        for service in services:
            service_name = service.get("name", "Unknown")
            service_url = service.get("url", "")
            connectivity = await self.test_service_connectivity(service_url)
            status = "✅" if connectivity.get("accessible", False) else "❌"
            response_time = connectivity.get("response_time_ms", "N/A")
            print(f"   {status} {service_name}: {response_time}ms")
        
        print("\n" + "="*80)


async def main():
    """Main setup function"""
    print("🚀 Kong API Gateway Setup")
    print("="*40)
    
    async with KongSetup() as kong:
        # Wait for Kong to be ready
        if not await kong.wait_for_kong():
            print("❌ Kong setup failed - service not ready")
            return
        
        # Print status report
        await kong.print_status_report()
        
        # Validate configuration
        print("\n🔍 Configuration Validation:")
        validation_results = await kong.validate_configuration()
        
        # Summary
        services_count = len(validation_results.get("services", []))
        routes_count = len(validation_results.get("routes", []))
        plugins_count = len(validation_results.get("plugins", []))
        
        print(f"\n📊 Configuration Summary:")
        print(f"   • Services: {services_count}")
        print(f"   • Routes: {routes_count}")
        print(f"   • Plugins: {plugins_count}")
        
        if services_count > 0 and routes_count > 0:
            print("✅ Kong API Gateway is properly configured!")
        else:
            print("⚠️ Kong configuration may be incomplete")


if __name__ == "__main__":
    asyncio.run(main())
