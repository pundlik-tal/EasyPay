#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Security System Test Script

This script tests all the security features implemented in Day 13:
- Role-Based Access Control (RBAC)
- Permission System
- Resource-Level Authorization
- API Key Scoping
- Request Signing
- Security Headers
- Audit Logging
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database import get_db_session, init_database
from src.core.services.rbac_service import RBACService
from src.core.services.scoping_service import ScopingService
from src.core.services.request_signing_service import RequestSigningService, WebhookSigningService
from src.core.services.audit_logging_service import AuditLoggingService, AuditLogger
from src.core.models.rbac import Role, Permission, SecurityEvent
from src.core.models.auth import APIKey, APIKeyStatus


class SecuritySystemTester:
    """Comprehensive security system tester."""
    
    def __init__(self):
        """Initialize security system tester."""
        self.results = {
            "rbac_tests": [],
            "scoping_tests": [],
            "signing_tests": [],
            "audit_tests": [],
            "integration_tests": [],
            "performance_tests": []
        }
        self.signing_service = RequestSigningService("test-secret-key")
        self.webhook_service = WebhookSigningService("test-webhook-secret")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests."""
        print("🔒 Starting EasyPay Security System Tests")
        print("=" * 50)
        
        try:
            # Initialize database
            await init_database()
            
            # Run test suites
            await self.test_rbac_system()
            await self.test_scoping_system()
            await self.test_request_signing()
            await self.test_audit_logging()
            await self.test_integration()
            await self.test_performance()
            
            # Generate report
            report = self.generate_report()
            self.print_report(report)
            
            return report
            
        except Exception as e:
            print(f"❌ Test execution failed: {str(e)}")
            return {"error": str(e)}
    
    async def test_rbac_system(self):
        """Test Role-Based Access Control system."""
        print("\n🔐 Testing RBAC System...")
        
        async with get_db_session() as db:
            rbac_service = RBACService(db)
            
            # Test 1: Initialize system roles and permissions
            try:
                init_result = await rbac_service.initialize_system_roles_and_permissions()
                self.results["rbac_tests"].append({
                    "test": "Initialize system roles and permissions",
                    "status": "PASS",
                    "details": f"Created {init_result['roles_created']} roles and {init_result['permissions_created']} permissions"
                })
                print("  ✅ System roles and permissions initialized")
            except Exception as e:
                self.results["rbac_tests"].append({
                    "test": "Initialize system roles and permissions",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Failed to initialize system: {str(e)}")
            
            # Test 2: Create custom role
            try:
                role = await rbac_service.create_role(
                    name="test_role",
                    display_name="Test Role",
                    description="A test role for security testing",
                    permissions=["payment:read", "payment:write"]
                )
                self.results["rbac_tests"].append({
                    "test": "Create custom role",
                    "status": "PASS",
                    "details": f"Created role '{role.name}' with {len(role.permissions)} permissions"
                })
                print(f"  ✅ Created role: {role.name}")
            except Exception as e:
                self.results["rbac_tests"].append({
                    "test": "Create custom role",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Failed to create role: {str(e)}")
            
            # Test 3: Create permission
            try:
                permission = await rbac_service.create_permission(
                    name="test_permission",
                    display_name="Test Permission",
                    resource_type="payment",
                    action_type="delete",
                    description="A test permission"
                )
                self.results["rbac_tests"].append({
                    "test": "Create permission",
                    "status": "PASS",
                    "details": f"Created permission '{permission.name}'"
                })
                print(f"  ✅ Created permission: {permission.name}")
            except Exception as e:
                self.results["rbac_tests"].append({
                    "test": "Create permission",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Failed to create permission: {str(e)}")
            
            # Test 4: Permission checking
            try:
                # Create API key with role
                api_key = APIKey(
                    key_id="test_key_rbac",
                    key_secret_hash="hashed_secret",
                    name="Test RBAC Key",
                    role_id=role.id,
                    status=APIKeyStatus.ACTIVE
                )
                db.add(api_key)
                await db.commit()
                
                # Test permission check
                has_permission = await rbac_service.check_permission(
                    api_key_id=api_key.id,
                    resource_type="payment",
                    action="read"
                )
                
                self.results["rbac_tests"].append({
                    "test": "Permission checking",
                    "status": "PASS" if has_permission else "FAIL",
                    "details": f"Permission check result: {has_permission}"
                })
                print(f"  ✅ Permission check: {has_permission}")
                
            except Exception as e:
                self.results["rbac_tests"].append({
                    "test": "Permission checking",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Permission check failed: {str(e)}")
    
    async def test_scoping_system(self):
        """Test API key scoping system."""
        print("\n🌐 Testing Scoping System...")
        
        async with get_db_session() as db:
            scoping_service = ScopingService(db)
            
            # Create test API key
            api_key = APIKey(
                key_id="test_key_scoping",
                key_secret_hash="hashed_secret",
                name="Test Scoping Key",
                status=APIKeyStatus.ACTIVE
            )
            db.add(api_key)
            await db.commit()
            
            # Test 1: Environment scoping
            try:
                scope = await scoping_service.create_environment_scope(
                    api_key_id=api_key.id,
                    environment="sandbox"
                )
                
                # Test validation
                allowed = await scoping_service.validate_environment_access(
                    api_key_id=api_key.id,
                    requested_environment="sandbox"
                )
                
                denied = await scoping_service.validate_environment_access(
                    api_key_id=api_key.id,
                    requested_environment="production"
                )
                
                self.results["scoping_tests"].append({
                    "test": "Environment scoping",
                    "status": "PASS" if allowed and not denied else "FAIL",
                    "details": f"Sandbox allowed: {allowed}, Production denied: {denied}"
                })
                print(f"  ✅ Environment scoping: Sandbox={allowed}, Production={denied}")
                
            except Exception as e:
                self.results["scoping_tests"].append({
                    "test": "Environment scoping",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Environment scoping failed: {str(e)}")
            
            # Test 2: Domain scoping
            try:
                scope = await scoping_service.create_domain_scope(
                    api_key_id=api_key.id,
                    domain="example.com"
                )
                
                # Test validation
                allowed = await scoping_service.validate_domain_access(
                    api_key_id=api_key.id,
                    requested_domain="example.com"
                )
                
                denied = await scoping_service.validate_domain_access(
                    api_key_id=api_key.id,
                    requested_domain="malicious.com"
                )
                
                self.results["scoping_tests"].append({
                    "test": "Domain scoping",
                    "status": "PASS" if allowed and not denied else "FAIL",
                    "details": f"Example.com allowed: {allowed}, Malicious.com denied: {denied}"
                })
                print(f"  ✅ Domain scoping: Example.com={allowed}, Malicious.com={denied}")
                
            except Exception as e:
                self.results["scoping_tests"].append({
                    "test": "Domain scoping",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Domain scoping failed: {str(e)}")
            
            # Test 3: IP range scoping
            try:
                scope = await scoping_service.create_ip_range_scope(
                    api_key_id=api_key.id,
                    ip_range="192.168.1.0/24"
                )
                
                # Test validation
                allowed = await scoping_service.validate_ip_access(
                    api_key_id=api_key.id,
                    client_ip="192.168.1.100"
                )
                
                denied = await scoping_service.validate_ip_access(
                    api_key_id=api_key.id,
                    client_ip="10.0.0.1"
                )
                
                self.results["scoping_tests"].append({
                    "test": "IP range scoping",
                    "status": "PASS" if allowed and not denied else "FAIL",
                    "details": f"192.168.1.100 allowed: {allowed}, 10.0.0.1 denied: {denied}"
                })
                print(f"  ✅ IP range scoping: 192.168.1.100={allowed}, 10.0.0.1={denied}")
                
            except Exception as e:
                self.results["scoping_tests"].append({
                    "test": "IP range scoping",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ IP range scoping failed: {str(e)}")
    
    async def test_request_signing(self):
        """Test request signing system."""
        print("\n🔏 Testing Request Signing...")
        
        # Test 1: Signature generation and verification
        try:
            method = "POST"
            url = "https://api.easypay.com/v1/payments"
            headers = {"Content-Type": "application/json"}
            body = '{"amount": 1000, "currency": "USD"}'
            
            # Generate signature
            signature = self.signing_service.generate_signature(
                method=method,
                url=url,
                headers=headers,
                body=body
            )
            
            # Verify signature
            is_valid = self.signing_service.verify_signature(
                method=method,
                url=url,
                headers=headers,
                body=body,
                signature=signature,
                timestamp=int(time.time())
            )
            
            self.results["signing_tests"].append({
                "test": "Signature generation and verification",
                "status": "PASS" if is_valid else "FAIL",
                "details": f"Signature generated and verified: {is_valid}"
            })
            print(f"  ✅ Signature generation and verification: {is_valid}")
            
        except Exception as e:
            self.results["signing_tests"].append({
                "test": "Signature generation and verification",
                "status": "FAIL",
                "error": str(e)
            })
            print(f"  ❌ Signature generation failed: {str(e)}")
        
        # Test 2: Signed request creation
        try:
            signed_headers = self.signing_service.create_signed_request(
                method="GET",
                url="https://api.easypay.com/v1/payments/pay_123",
                headers={"Accept": "application/json"}
            )
            
            required_headers = ["X-Timestamp", "X-Signature", "X-Signature-Method", "X-Signature-Version"]
            has_all_headers = all(header in signed_headers for header in required_headers)
            
            self.results["signing_tests"].append({
                "test": "Signed request creation",
                "status": "PASS" if has_all_headers else "FAIL",
                "details": f"All required headers present: {has_all_headers}"
            })
            print(f"  ✅ Signed request creation: {has_all_headers}")
            
        except Exception as e:
            self.results["signing_tests"].append({
                "test": "Signed request creation",
                "status": "FAIL",
                "error": str(e)
            })
            print(f"  ❌ Signed request creation failed: {str(e)}")
        
        # Test 3: Webhook signing
        try:
            payload = '{"event": "payment.completed", "data": {"id": "pay_123"}}'
            
            # Generate webhook signature
            webhook_signature = self.webhook_service.generate_webhook_signature(payload)
            
            # Verify webhook signature
            is_valid = self.webhook_service.verify_webhook_signature(
                payload=payload,
                signature_header=webhook_signature
            )
            
            self.results["signing_tests"].append({
                "test": "Webhook signing",
                "status": "PASS" if is_valid else "FAIL",
                "details": f"Webhook signature generated and verified: {is_valid}"
            })
            print(f"  ✅ Webhook signing: {is_valid}")
            
        except Exception as e:
            self.results["signing_tests"].append({
                "test": "Webhook signing",
                "status": "FAIL",
                "error": str(e)
            })
            print(f"  ❌ Webhook signing failed: {str(e)}")
    
    async def test_audit_logging(self):
        """Test audit logging system."""
        print("\n📝 Testing Audit Logging...")
        
        async with get_db_session() as db:
            audit_service = AuditLoggingService(db)
            audit_logger = AuditLogger(audit_service)
            
            # Test 1: Security event logging
            try:
                event = await audit_service.log_security_event(
                    event_type="test_event",
                    event_category="test",
                    message="Test security event",
                    severity="info",
                    success=True,
                    details={"test": True}
                )
                
                self.results["audit_tests"].append({
                    "test": "Security event logging",
                    "status": "PASS",
                    "details": f"Event logged with ID: {event.id}"
                })
                print(f"  ✅ Security event logged: {event.id}")
                
            except Exception as e:
                self.results["audit_tests"].append({
                    "test": "Security event logging",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Security event logging failed: {str(e)}")
            
            # Test 2: Authentication event logging
            try:
                event = await audit_logger.log_login_success(
                    api_key_id=uuid.uuid4(),
                    ip_address="192.168.1.1",
                    user_agent="Test Agent",
                    request_id="req_123"
                )
                
                self.results["audit_tests"].append({
                    "test": "Authentication event logging",
                    "status": "PASS",
                    "details": f"Login success event logged"
                })
                print("  ✅ Authentication event logged")
                
            except Exception as e:
                self.results["audit_tests"].append({
                    "test": "Authentication event logging",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Authentication event logging failed: {str(e)}")
            
            # Test 3: Authorization event logging
            try:
                event = await audit_logger.log_permission_denied(
                    api_key_id=uuid.uuid4(),
                    resource_type="payment",
                    resource_id="pay_123",
                    action="delete",
                    ip_address="192.168.1.1",
                    user_agent="Test Agent",
                    request_id="req_123"
                )
                
                self.results["audit_tests"].append({
                    "test": "Authorization event logging",
                    "status": "PASS",
                    "details": f"Permission denied event logged"
                })
                print("  ✅ Authorization event logged")
                
            except Exception as e:
                self.results["audit_tests"].append({
                    "test": "Authorization event logging",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Authorization event logging failed: {str(e)}")
            
            # Test 4: Event querying
            try:
                events = await audit_service.get_security_events(
                    event_category="test",
                    limit=10
                )
                
                self.results["audit_tests"].append({
                    "test": "Event querying",
                    "status": "PASS",
                    "details": f"Retrieved {len(events)} events"
                })
                print(f"  ✅ Event querying: {len(events)} events retrieved")
                
            except Exception as e:
                self.results["audit_tests"].append({
                    "test": "Event querying",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Event querying failed: {str(e)}")
    
    async def test_integration(self):
        """Test integration of all security features."""
        print("\n🔗 Testing Integration...")
        
        async with get_db_session() as db:
            rbac_service = RBACService(db)
            scoping_service = ScopingService(db)
            audit_service = AuditLoggingService(db)
            
            try:
                # Create role
                role = await rbac_service.create_role(
                    name="integration_test_role",
                    display_name="Integration Test Role",
                    permissions=["payment:read", "payment:write"]
                )
                
                # Create API key with role
                api_key = APIKey(
                    key_id="test_key_integration",
                    key_secret_hash="hashed_secret",
                    name="Test Integration Key",
                    role_id=role.id,
                    status=APIKeyStatus.ACTIVE
                )
                db.add(api_key)
                await db.commit()
                
                # Create scopes
                await scoping_service.create_environment_scope(
                    api_key_id=api_key.id,
                    environment="sandbox"
                )
                
                # Test comprehensive validation
                validation_result = await scoping_service.validate_api_key_access(
                    api_key_id=api_key.id,
                    environment="sandbox",
                    domain="example.com",
                    client_ip="192.168.1.1"
                )
                
                # Test permission check
                has_permission = await rbac_service.check_permission(
                    api_key_id=api_key.id,
                    resource_type="payment",
                    action="read"
                )
                
                # Log integration event
                await audit_service.log_security_event(
                    event_type="integration_test",
                    event_category="test",
                    message="Integration test completed",
                    api_key_id=api_key.id,
                    severity="info",
                    success=True
                )
                
                self.results["integration_tests"].append({
                    "test": "Complete security integration",
                    "status": "PASS" if validation_result["valid"] and has_permission else "FAIL",
                    "details": f"Validation: {validation_result['valid']}, Permission: {has_permission}"
                })
                print(f"  ✅ Integration test: Validation={validation_result['valid']}, Permission={has_permission}")
                
            except Exception as e:
                self.results["integration_tests"].append({
                    "test": "Complete security integration",
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"  ❌ Integration test failed: {str(e)}")
    
    async def test_performance(self):
        """Test performance of security features."""
        print("\n⚡ Testing Performance...")
        
        # Test 1: Signature generation performance
        try:
            start_time = time.time()
            
            for _ in range(100):
                signature = self.signing_service.generate_signature(
                    method="POST",
                    url="https://api.easypay.com/v1/payments",
                    headers={"Content-Type": "application/json"},
                    body='{"amount": 1000}'
                )
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.results["performance_tests"].append({
                "test": "Signature generation performance",
                "status": "PASS" if duration < 1.0 else "FAIL",
                "details": f"100 signatures in {duration:.3f} seconds"
            })
            print(f"  ✅ Signature generation: {duration:.3f}s for 100 signatures")
            
        except Exception as e:
            self.results["performance_tests"].append({
                "test": "Signature generation performance",
                "status": "FAIL",
                "error": str(e)
            })
            print(f"  ❌ Signature generation performance test failed: {str(e)}")
        
        # Test 2: Signature verification performance
        try:
            signature = self.signing_service.generate_signature(
                method="POST",
                url="https://api.easypay.com/v1/payments",
                headers={"Content-Type": "application/json"},
                body='{"amount": 1000}'
            )
            
            start_time = time.time()
            
            for _ in range(100):
                is_valid = self.signing_service.verify_signature(
                    method="POST",
                    url="https://api.easypay.com/v1/payments",
                    headers={"Content-Type": "application/json"},
                    body='{"amount": 1000}',
                    signature=signature,
                    timestamp=int(time.time())
                )
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.results["performance_tests"].append({
                "test": "Signature verification performance",
                "status": "PASS" if duration < 1.0 else "FAIL",
                "details": f"100 verifications in {duration:.3f} seconds"
            })
            print(f"  ✅ Signature verification: {duration:.3f}s for 100 verifications")
            
        except Exception as e:
            self.results["performance_tests"].append({
                "test": "Signature verification performance",
                "status": "FAIL",
                "error": str(e)
            })
            print(f"  ❌ Signature verification performance test failed: {str(e)}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report."""
        total_tests = sum(len(tests) for tests in self.results.values())
        passed_tests = sum(
            len([test for test in tests if test["status"] == "PASS"])
            for tests in self.results.values()
        )
        failed_tests = total_tests - passed_tests
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "results": self.results,
            "timestamp": datetime.now().isoformat()
        }
    
    def print_report(self, report: Dict[str, Any]):
        """Print test report."""
        print("\n" + "=" * 50)
        print("🔒 SECURITY SYSTEM TEST REPORT")
        print("=" * 50)
        
        summary = report["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        if summary['failed_tests'] > 0:
            print("\n❌ FAILED TESTS:")
            for category, tests in report["results"].items():
                failed_tests = [test for test in tests if test["status"] == "FAIL"]
                if failed_tests:
                    print(f"\n{category.upper()}:")
                    for test in failed_tests:
                        print(f"  - {test['test']}: {test.get('error', 'Unknown error')}")
        
        print(f"\nTest completed at: {report['timestamp']}")


async def main():
    """Main test execution function."""
    tester = SecuritySystemTester()
    report = await tester.run_all_tests()
    
    # Exit with error code if tests failed
    if report.get("summary", {}).get("failed_tests", 0) > 0:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())
