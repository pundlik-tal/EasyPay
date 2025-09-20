#!/usr/bin/env python3
"""
EasyPay Payment Gateway - System Troubleshooting Script

This script provides comprehensive troubleshooting capabilities for the EasyPay system,
including service diagnostics, log analysis, and issue resolution.
"""

import asyncio
import os
import sys
import time
import subprocess
import logging
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemTroubleshooter:
    """Comprehensive system troubleshooting and diagnostics."""
    
    def __init__(self):
        self.project_root = project_root
        self.services = {
            'postgres': {'port': 5432, 'container_name': 'easypay_postgres'},
            'redis': {'port': 6379, 'container_name': 'easypay_redis'},
            'easypay-api': {'port': 8002, 'container_name': 'easypay_easypay-api'},
            'kong': {'port': 8000, 'container_name': 'easypay_kong'},
            'prometheus': {'port': 9090, 'container_name': 'easypay_prometheus'},
            'grafana': {'port': 3000, 'container_name': 'easypay_grafana'},
            'elasticsearch': {'port': 9200, 'container_name': 'easypay_elasticsearch'},
            'kibana': {'port': 5601, 'container_name': 'easypay_kibana'},
            'pgadmin': {'port': 5050, 'container_name': 'easypay_pgadmin'}
        }
    
    async def run_full_diagnostics(self) -> Dict[str, any]:
        """Run comprehensive system diagnostics."""
        logger.info("🔍 Running full system diagnostics...")
        
        diagnostics = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_info': await self._get_system_info(),
            'docker_status': await self._check_docker_status(),
            'service_status': await self._check_all_services(),
            'network_connectivity': await self._check_network_connectivity(),
            'resource_usage': await self._check_resource_usage(),
            'log_analysis': await self._analyze_logs(),
            'database_status': await self._check_database_status(),
            'issues': [],
            'recommendations': []
        }
        
        # Analyze results and generate recommendations
        await self._analyze_diagnostics(diagnostics)
        
        return diagnostics
    
    async def _get_system_info(self) -> Dict[str, any]:
        """Get system information."""
        logger.info("📊 Gathering system information...")
        
        try:
            # Docker version
            docker_version = subprocess.run(
                ['docker', '--version'], 
                capture_output=True, text=True
            ).stdout.strip()
            
            # Docker Compose version
            compose_version = subprocess.run(
                ['docker-compose', '--version'], 
                capture_output=True, text=True
            ).stdout.strip()
            
            # System resources
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'docker_version': docker_version,
                'compose_version': compose_version,
                'cpu_usage': cpu_percent,
                'memory_total': memory.total,
                'memory_available': memory.available,
                'memory_percent': memory.percent,
                'disk_total': disk.total,
                'disk_free': disk.free,
                'disk_percent': disk.percent,
                'python_version': sys.version,
                'platform': os.name
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {'error': str(e)}
    
    async def _check_docker_status(self) -> Dict[str, any]:
        """Check Docker and container status."""
        logger.info("🐳 Checking Docker status...")
        
        try:
            # Docker info
            docker_info = subprocess.run(
                ['docker', 'info'], 
                capture_output=True, text=True
            )
            
            # Container status
            containers = subprocess.run(
                ['docker-compose', 'ps'], 
                cwd=self.project_root,
                capture_output=True, text=True
            )
            
            # Container logs (last 50 lines)
            container_logs = {}
            for service_name, config in self.services.items():
                try:
                    logs = subprocess.run(
                        ['docker-compose', 'logs', '--tail=50', service_name],
                        cwd=self.project_root,
                        capture_output=True, text=True
                    )
                    container_logs[service_name] = logs.stdout
                except Exception as e:
                    container_logs[service_name] = f"Error getting logs: {e}"
            
            return {
                'docker_info': docker_info.stdout,
                'containers': containers.stdout,
                'container_logs': container_logs
            }
        except Exception as e:
            logger.error(f"Failed to check Docker status: {e}")
            return {'error': str(e)}
    
    async def _check_all_services(self) -> Dict[str, any]:
        """Check status of all services."""
        logger.info("🔧 Checking service status...")
        
        service_status = {}
        
        for service_name, config in self.services.items():
            status = await self._check_service_health(service_name, config)
            service_status[service_name] = status
        
        return service_status
    
    async def _check_service_health(self, service_name: str, config: Dict) -> Dict[str, any]:
        """Check health of a specific service."""
        try:
            # Check if container is running
            container_status = subprocess.run(
                ['docker-compose', 'ps', service_name],
                cwd=self.project_root,
                capture_output=True, text=True
            )
            
            # Check port connectivity
            port_open = await self._check_port(config['port'])
            
            # Check HTTP endpoint if applicable
            http_healthy = False
            if service_name in ['easypay-api', 'kong', 'prometheus', 'grafana', 'kibana', 'pgadmin']:
                http_healthy = await self._check_http_endpoint(service_name, config['port'])
            
            return {
                'container_status': container_status.stdout,
                'port_open': port_open,
                'http_healthy': http_healthy,
                'status': 'healthy' if port_open and http_healthy else 'unhealthy'
            }
        except Exception as e:
            return {
                'error': str(e),
                'status': 'error'
            }
    
    async def _check_port(self, port: int) -> bool:
        """Check if a port is open."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    async def _check_http_endpoint(self, service_name: str, port: int) -> bool:
        """Check HTTP endpoint health."""
        endpoints = {
            'easypay-api': '/health',
            'kong': '/status',
            'prometheus': '/-/healthy',
            'grafana': '/api/health',
            'kibana': '/api/status',
            'pgadmin': '/'
        }
        
        endpoint = endpoints.get(service_name, '/')
        url = f'http://localhost:{port}{endpoint}'
        
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def _check_network_connectivity(self) -> Dict[str, any]:
        """Check network connectivity."""
        logger.info("🌐 Checking network connectivity...")
        
        connectivity = {}
        
        # Check external connectivity
        try:
            response = requests.get('https://httpbin.org/get', timeout=10)
            connectivity['external'] = response.status_code == 200
        except Exception as e:
            connectivity['external'] = False
            connectivity['external_error'] = str(e)
        
        # Check internal service connectivity
        internal_checks = {}
        for service_name, config in self.services.items():
            try:
                response = requests.get(f'http://localhost:{config["port"]}', timeout=5)
                internal_checks[service_name] = response.status_code in [200, 404, 405]  # 404/405 are OK for some services
            except Exception as e:
                internal_checks[service_name] = False
        
        connectivity['internal'] = internal_checks
        
        return connectivity
    
    async def _check_resource_usage(self) -> Dict[str, any]:
        """Check system resource usage."""
        logger.info("💾 Checking resource usage...")
        
        try:
            import psutil
            
            # System resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Docker container resource usage
            container_stats = {}
            for service_name in self.services.keys():
                try:
                    stats = subprocess.run(
                        ['docker', 'stats', '--no-stream', '--format', 'json', f'easypay_{service_name}'],
                        capture_output=True, text=True
                    )
                    if stats.returncode == 0:
                        container_stats[service_name] = json.loads(stats.stdout)
                except Exception:
                    container_stats[service_name] = None
            
            return {
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent
                },
                'containers': container_stats
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def _analyze_logs(self) -> Dict[str, any]:
        """Analyze system logs for errors and issues."""
        logger.info("📋 Analyzing logs...")
        
        log_analysis = {}
        
        for service_name in self.services.keys():
            try:
                # Get recent logs
                logs = subprocess.run(
                    ['docker-compose', 'logs', '--tail=100', service_name],
                    cwd=self.project_root,
                    capture_output=True, text=True
                )
                
                log_lines = logs.stdout.split('\n')
                
                # Count error levels
                error_counts = {
                    'ERROR': 0,
                    'WARN': 0,
                    'INFO': 0,
                    'DEBUG': 0
                }
                
                # Find recent errors
                recent_errors = []
                for line in log_lines[-50:]:  # Last 50 lines
                    if any(level in line.upper() for level in error_counts.keys()):
                        for level in error_counts.keys():
                            if level in line.upper():
                                error_counts[level] += 1
                                if level in ['ERROR', 'WARN']:
                                    recent_errors.append(line.strip())
                
                log_analysis[service_name] = {
                    'error_counts': error_counts,
                    'recent_errors': recent_errors[-10:],  # Last 10 errors
                    'total_log_lines': len(log_lines)
                }
                
            except Exception as e:
                log_analysis[service_name] = {'error': str(e)}
        
        return log_analysis
    
    async def _check_database_status(self) -> Dict[str, any]:
        """Check database status and connectivity."""
        logger.info("🗄️  Checking database status...")
        
        try:
            # Check PostgreSQL connection
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='easypay',
                user='easypay',
                password='password'
            )
            
            cursor = conn.cursor()
            
            # Check database size
            cursor.execute("SELECT pg_size_pretty(pg_database_size('easypay'));")
            db_size = cursor.fetchone()[0]
            
            # Check table count
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            table_count = cursor.fetchone()[0]
            
            # Check connection count
            cursor.execute("SELECT COUNT(*) FROM pg_stat_activity;")
            connection_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'status': 'healthy',
                'database_size': db_size,
                'table_count': table_count,
                'connection_count': connection_count
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def _analyze_diagnostics(self, diagnostics: Dict[str, any]):
        """Analyze diagnostics and generate recommendations."""
        logger.info("🧠 Analyzing diagnostics...")
        
        issues = []
        recommendations = []
        
        # Check service health
        for service_name, status in diagnostics['service_status'].items():
            if status.get('status') != 'healthy':
                issues.append(f"Service {service_name} is not healthy")
                recommendations.append(f"Restart service {service_name}: docker-compose restart {service_name}")
        
        # Check resource usage
        if 'resource_usage' in diagnostics and 'system' in diagnostics['resource_usage']:
            system_resources = diagnostics['resource_usage']['system']
            
            if system_resources.get('cpu_percent', 0) > 80:
                issues.append("High CPU usage detected")
                recommendations.append("Consider scaling services or optimizing resource usage")
            
            if system_resources.get('memory_percent', 0) > 90:
                issues.append("High memory usage detected")
                recommendations.append("Consider increasing available memory or optimizing memory usage")
            
            if system_resources.get('disk_percent', 0) > 90:
                issues.append("High disk usage detected")
                recommendations.append("Consider cleaning up logs or increasing disk space")
        
        # Check log errors
        if 'log_analysis' in diagnostics:
            for service_name, analysis in diagnostics['log_analysis'].items():
                if 'error_counts' in analysis:
                    error_count = analysis['error_counts'].get('ERROR', 0)
                    if error_count > 10:
                        issues.append(f"High error count in {service_name} logs")
                        recommendations.append(f"Investigate {service_name} logs for recurring errors")
        
        # Check database status
        if 'database_status' in diagnostics:
            if diagnostics['database_status'].get('status') != 'healthy':
                issues.append("Database connectivity issues")
                recommendations.append("Check PostgreSQL container and connection settings")
        
        diagnostics['issues'] = issues
        diagnostics['recommendations'] = recommendations
    
    async def fix_common_issues(self) -> bool:
        """Attempt to fix common issues automatically."""
        logger.info("🔧 Attempting to fix common issues...")
        
        fixes_applied = []
        
        try:
            # Restart unhealthy services
            for service_name, status in (await self._check_all_services()).items():
                if status.get('status') != 'healthy':
                    logger.info(f"Restarting {service_name}...")
                    subprocess.run(
                        ['docker-compose', 'restart', service_name],
                        cwd=self.project_root
                    )
                    fixes_applied.append(f"Restarted {service_name}")
            
            # Clean up Docker resources
            logger.info("Cleaning up Docker resources...")
            subprocess.run(['docker', 'system', 'prune', '-f'])
            fixes_applied.append("Cleaned up Docker resources")
            
            # Reset Docker networks
            logger.info("Resetting Docker networks...")
            subprocess.run(['docker-compose', 'down'], cwd=self.project_root)
            subprocess.run(['docker-compose', 'up', '-d'], cwd=self.project_root)
            fixes_applied.append("Reset Docker networks")
            
            logger.info(f"✅ Applied {len(fixes_applied)} fixes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply fixes: {e}")
            return False
    
    def generate_report(self, diagnostics: Dict[str, any]) -> str:
        """Generate a comprehensive diagnostic report."""
        report = []
        report.append("=" * 60)
        report.append("EASYPAY PAYMENT GATEWAY - DIAGNOSTIC REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {diagnostics['timestamp']}")
        report.append("")
        
        # System Information
        report.append("SYSTEM INFORMATION:")
        report.append("-" * 20)
        if 'system_info' in diagnostics:
            sys_info = diagnostics['system_info']
            report.append(f"Docker Version: {sys_info.get('docker_version', 'N/A')}")
            report.append(f"Compose Version: {sys_info.get('compose_version', 'N/A')}")
            report.append(f"CPU Usage: {sys_info.get('cpu_usage', 'N/A')}%")
            report.append(f"Memory Usage: {sys_info.get('memory_percent', 'N/A')}%")
            report.append(f"Disk Usage: {sys_info.get('disk_percent', 'N/A')}%")
        report.append("")
        
        # Service Status
        report.append("SERVICE STATUS:")
        report.append("-" * 15)
        for service_name, status in diagnostics.get('service_status', {}).items():
            status_text = status.get('status', 'unknown')
            report.append(f"{service_name:15} : {status_text}")
        report.append("")
        
        # Issues
        if diagnostics.get('issues'):
            report.append("IDENTIFIED ISSUES:")
            report.append("-" * 18)
            for issue in diagnostics['issues']:
                report.append(f"• {issue}")
            report.append("")
        
        # Recommendations
        if diagnostics.get('recommendations'):
            report.append("RECOMMENDATIONS:")
            report.append("-" * 15)
            for rec in diagnostics['recommendations']:
                report.append(f"• {rec}")
            report.append("")
        
        # Database Status
        if 'database_status' in diagnostics:
            report.append("DATABASE STATUS:")
            report.append("-" * 16)
            db_status = diagnostics['database_status']
            report.append(f"Status: {db_status.get('status', 'unknown')}")
            if 'database_size' in db_status:
                report.append(f"Size: {db_status['database_size']}")
            if 'table_count' in db_status:
                report.append(f"Tables: {db_status['table_count']}")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


async def main():
    """Main entry point."""
    troubleshooter = SystemTroubleshooter()
    
    print("🔍 EasyPay Payment Gateway - System Troubleshooter")
    print("=" * 50)
    
    # Run diagnostics
    diagnostics = await troubleshooter.run_full_diagnostics()
    
    # Generate report
    report = troubleshooter.generate_report(diagnostics)
    print(report)
    
    # Save report to file
    report_file = troubleshooter.project_root / 'diagnostic_report.txt'
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Full report saved to: {report_file}")
    
    # Ask if user wants to attempt fixes
    if diagnostics.get('issues'):
        print("\n🔧 Issues detected. Would you like to attempt automatic fixes? (y/n): ", end="")
        try:
            response = input().lower().strip()
            if response in ['y', 'yes']:
                success = await troubleshooter.fix_common_issues()
                if success:
                    print("✅ Automatic fixes applied. Please run diagnostics again to verify.")
                else:
                    print("❌ Automatic fixes failed. Please check the issues manually.")
        except KeyboardInterrupt:
            print("\n👋 Exiting...")


if __name__ == "__main__":
    asyncio.run(main())
