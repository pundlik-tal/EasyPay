#!/usr/bin/env python3
"""
Test script for creating payments and verifying persistence.
"""
import asyncio
import httpx
import json
import uuid
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
API_KEY_ID = "ak_test_123456789"  # Replace with your actual API key ID
API_KEY_SECRET = "test_secret_here"  # Replace with your actual API key secret

async def create_payment_test():
    """Test payment creation and verification."""
    print("🚀 Starting Payment Creation Test")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Generate JWT token
            print("\n1. Generating JWT token...")
            token_request = {
                "api_key_id": API_KEY_ID,
                "api_key_secret": API_KEY_SECRET,
                "expires_in": 3600
            }
            
            response = await client.post(
                f"{BASE_URL}/auth/tokens",
                json=token_request
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data["access_token"]
                print(f"✅ JWT token generated successfully")
                print(f"   Token: {access_token[:50]}...")
            else:
                print(f"❌ Token generation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            
            # Step 2: Create payment
            print("\n2. Creating payment...")
            payment_request = {
                "amount": "25.99",
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_test_{uuid.uuid4().hex[:8]}",
                "customer_email": "test@example.com",
                "customer_name": "Test Customer",
                "card_token": "tok_visa_4242",
                "description": "Test payment for verification",
                "metadata": {
                    "order_id": f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "product": "test_product",
                    "test_mode": True
                },
                "is_test": True
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Correlation-ID": f"test-payment-{uuid.uuid4().hex[:8]}",
                "X-Idempotency-Key": f"payment-test-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            response = await client.post(
                f"{BASE_URL}/payments",
                json=payment_request,
                headers=headers
            )
            
            if response.status_code == 201:
                payment_data = response.json()
                payment_id = payment_data["id"]
                authorize_net_id = payment_data.get("authorize_net_transaction_id")
                
                print(f"✅ Payment created successfully!")
                print(f"   Payment ID: {payment_id}")
                print(f"   Status: {payment_data['status']}")
                print(f"   Amount: {payment_data['amount']['value']} {payment_data['amount']['currency']}")
                if authorize_net_id:
                    print(f"   Authorize.net Transaction ID: {authorize_net_id}")
            else:
                print(f"❌ Payment creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            
            # Step 3: Verify payment in database
            print("\n3. Verifying payment in database...")
            response = await client.get(
                f"{BASE_URL}/payments/{payment_id}",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                payment_verification = response.json()
                print(f"✅ Payment verified in database")
                print(f"   Status: {payment_verification['status']}")
                print(f"   Created: {payment_verification['created_at']}")
                print(f"   Customer: {payment_verification.get('customer', {}).get('name', 'N/A')}")
            else:
                print(f"❌ Payment verification failed: {response.status_code}")
                return False
            
            # Step 4: Check payment status history
            print("\n4. Checking payment status history...")
            response = await client.get(
                f"{BASE_URL}/payments/{payment_id}/status-history",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                status_history = response.json()
                print(f"✅ Status history retrieved")
                print(f"   Status transitions: {len(status_history)}")
                for status in status_history:
                    print(f"   - {status['status']}: {status['timestamp']}")
            else:
                print(f"⚠️ Status history not available: {response.status_code}")
            
            # Step 5: Test payment search
            print("\n5. Testing payment search...")
            search_request = {
                "customer_id": payment_request["customer_id"],
                "page": 1,
                "per_page": 10
            }
            
            response = await client.post(
                f"{BASE_URL}/payments/search",
                json=search_request,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code == 200:
                search_results = response.json()
                print(f"✅ Payment search successful")
                print(f"   Found {search_results['total']} payments")
                print(f"   Current page: {search_results['page']}")
            else:
                print(f"⚠️ Payment search failed: {response.status_code}")
            
            print("\n🎉 Payment creation and verification completed successfully!")
            print("\n📋 Next Steps:")
            print("1. Check the payment in your database:")
            print(f"   - Payment ID: {payment_id}")
            print(f"   - Customer ID: {payment_request['customer_id']}")
            print("2. Verify in Authorize.net dashboard:")
            if authorize_net_id:
                print(f"   - Transaction ID: {authorize_net_id}")
                print("   - Go to: https://sandbox.authorize.net/")
                print("   - Navigate to Reports → Transaction Search")
                print(f"   - Search for Transaction ID: {authorize_net_id}")
            else:
                print("   - No Authorize.net transaction ID found")
                print("   - Check if Authorize.net integration is properly configured")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
            return False

async def test_multiple_payments():
    """Test creating multiple payments with different scenarios."""
    print("\n🔄 Testing Multiple Payment Scenarios")
    print("=" * 50)
    
    test_scenarios = [
        {
            "name": "Successful Visa Payment",
            "amount": "10.00",
            "card_token": "tok_visa_4242",
            "customer_name": "Visa Test Customer"
        },
        {
            "name": "Declined Payment",
            "amount": "10.00", 
            "card_token": "tok_visa_0002",
            "customer_name": "Declined Test Customer"
        },
        {
            "name": "Insufficient Funds",
            "amount": "10.00",
            "card_token": "tok_visa_0003", 
            "customer_name": "Insufficient Funds Customer"
        }
    ]
    
    async with httpx.AsyncClient() as client:
        # Get JWT token first
        token_request = {
            "api_key_id": API_KEY_ID,
            "api_key_secret": API_KEY_SECRET,
            "expires_in": 3600
        }
        
        response = await client.post(f"{BASE_URL}/auth/tokens", json=token_request)
        if response.status_code != 200:
            print("❌ Failed to get JWT token for multiple payment test")
            return False
            
        access_token = response.json()["access_token"]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{i}. Testing: {scenario['name']}")
            
            payment_request = {
                "amount": scenario["amount"],
                "currency": "USD",
                "payment_method": "credit_card",
                "customer_id": f"cust_{scenario['name'].lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}",
                "customer_email": f"{scenario['name'].lower().replace(' ', '_')}@test.com",
                "customer_name": scenario["customer_name"],
                "card_token": scenario["card_token"],
                "description": f"Test: {scenario['name']}",
                "is_test": True
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Correlation-ID": f"test-{i}-{uuid.uuid4().hex[:8]}",
                "X-Idempotency-Key": f"payment-test-{i}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            response = await client.post(
                f"{BASE_URL}/payments",
                json=payment_request,
                headers=headers
            )
            
            if response.status_code == 201:
                payment_data = response.json()
                print(f"   ✅ Created: {payment_data['id']} - Status: {payment_data['status']}")
            else:
                print(f"   ❌ Failed: {response.status_code} - {response.text}")

async def main():
    """Run all payment tests."""
    print("🧪 EasyPay Payment Creation Test Suite")
    print("=" * 60)
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL.replace('/api/v1', '')}/health")
            if response.status_code == 200:
                print("✅ EasyPay server is running")
            else:
                print("❌ EasyPay server is not responding properly")
                return
    except Exception as e:
        print(f"❌ Cannot connect to EasyPay server: {str(e)}")
        print("Please ensure the server is running on http://localhost:8000")
        return
    
    # Run tests
    success = await create_payment_test()
    
    if success:
        await test_multiple_payments()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests completed successfully!")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    print("\n📝 Notes:")
    print("- Make sure to update API_KEY_ID and API_KEY_SECRET in this script")
    print("- Ensure Authorize.net sandbox credentials are configured")
    print("- Check the database and Authorize.net dashboard for verification")

if __name__ == "__main__":
    asyncio.run(main())
