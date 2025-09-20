#!/usr/bin/env python3
"""
Setup script for payment testing - creates API keys and provides ready-to-use examples.
"""
import asyncio
import httpx
import json
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

async def create_test_api_key():
    """Create a test API key for payment testing."""
    print("🔑 Creating test API key...")
    
    async with httpx.AsyncClient() as client:
        # First, we need admin access to create API keys
        # For testing, we'll use a simple approach
        
        api_key_request = {
            "name": "Payment Testing API Key",
            "description": "API key for testing payment creation and verification",
            "permissions": [
                "payments:read",
                "payments:write", 
                "payments:delete",
                "webhooks:read",
                "webhooks:write"
            ],
            "rate_limit_per_minute": 100,
            "rate_limit_per_hour": 1000,
            "rate_limit_per_day": 10000,
            "expires_at": None
        }
        
        # Note: This requires admin authentication
        # You may need to modify this based on your authentication setup
        response = await client.post(
            f"{BASE_URL}/auth/api-keys",
            json=api_key_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            api_key_data = response.json()
            print("✅ API key created successfully!")
            print(f"   Key ID: {api_key_data['key_id']}")
            print(f"   Key Secret: {api_key_data['key_secret']}")
            return api_key_data
        else:
            print(f"❌ Failed to create API key: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

async def generate_test_token(api_key_id, api_key_secret):
    """Generate JWT token for testing."""
    print("\n🎫 Generating JWT token...")
    
    async with httpx.AsyncClient() as client:
        token_request = {
            "api_key_id": api_key_id,
            "api_key_secret": api_key_secret,
            "expires_in": 3600
        }
        
        response = await client.post(
            f"{BASE_URL}/auth/tokens",
            json=token_request
        )
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ JWT token generated successfully!")
            print(f"   Access Token: {token_data['access_token'][:50]}...")
            print(f"   Expires At: {token_data['expires_at']}")
            return token_data
        else:
            print(f"❌ Failed to generate token: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

async def test_payment_creation(access_token):
    """Test creating a payment."""
    print("\n💳 Creating test payment...")
    
    async with httpx.AsyncClient() as client:
        payment_request = {
            "amount": "15.99",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": f"cust_setup_test_{uuid.uuid4().hex[:8]}",
            "customer_email": "setup.test@example.com",
            "customer_name": "Setup Test Customer",
            "card_token": "tok_visa_4242",
            "description": "Setup test payment",
            "metadata": {
                "test_type": "setup_verification",
                "created_by": "setup_script"
            },
            "is_test": True
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Correlation-ID": f"setup-test-{uuid.uuid4().hex[:8]}",
            "X-Idempotency-Key": f"setup-payment-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        response = await client.post(
            f"{BASE_URL}/payments",
            json=payment_request,
            headers=headers
        )
        
        if response.status_code == 201:
            payment_data = response.json()
            print("✅ Test payment created successfully!")
            print(f"   Payment ID: {payment_data['id']}")
            print(f"   Status: {payment_data['status']}")
            print(f"   Amount: {payment_data['amount']['value']} {payment_data['amount']['currency']}")
            print(f"   Authorize.net ID: {payment_data.get('authorize_net_transaction_id', 'N/A')}")
            return payment_data
        else:
            print(f"❌ Failed to create payment: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

def create_test_scripts(api_key_id, api_key_secret, access_token):
    """Create ready-to-use test scripts."""
    print("\n📝 Creating test scripts...")
    
    # Create curl test script
    curl_script = f"""#!/bin/bash
# EasyPay Payment Test Script
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

API_BASE_URL="http://localhost:8000/api/v1"
API_KEY_ID="{api_key_id}"
API_KEY_SECRET="{api_key_secret}"
JWT_TOKEN="{access_token}"

echo "🚀 EasyPay Payment Test"
echo "======================"

# Test 1: Create a successful payment
echo "\\n1. Creating successful payment..."
PAYMENT_RESPONSE=$(curl -s -X POST "$API_BASE_URL/payments" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $JWT_TOKEN" \\
  -H "X-Correlation-ID: curl-test-$(date +%s)" \\
  -H "X-Idempotency-Key: curl-payment-$(date +%s)" \\
  -d '{{
    "amount": "25.99",
    "currency": "USD",
    "payment_method": "credit_card",
    "customer_id": "cust_curl_test_$(date +%s)",
    "customer_email": "curl.test@example.com",
    "customer_name": "Curl Test Customer",
    "card_token": "tok_visa_4242",
    "description": "Curl test payment",
    "is_test": true
  }}')

echo "Payment Response:"
echo "$PAYMENT_RESPONSE" | jq '.'

# Extract payment ID
PAYMENT_ID=$(echo "$PAYMENT_RESPONSE" | jq -r '.id')
echo "\\nPayment ID: $PAYMENT_ID"

# Test 2: Verify payment
echo "\\n2. Verifying payment..."
curl -s -X GET "$API_BASE_URL/payments/$PAYMENT_ID" \\
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.'

echo "\\n✅ Test completed!"
"""
    
    with open("test_payment_curl.sh", "w") as f:
        f.write(curl_script)
    
    # Create Python test script
    python_script = f"""#!/usr/bin/env python3
\"\"\"
EasyPay Payment Test Script
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
\"\"\"
import asyncio
import httpx
import json
import uuid
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
API_KEY_ID = "{api_key_id}"
API_KEY_SECRET = "{api_key_secret}"
JWT_TOKEN = "{access_token}"

async def test_payment():
    \"\"\"Test payment creation and verification.\"\"\"
    print("🚀 EasyPay Payment Test")
    print("======================")
    
    async with httpx.AsyncClient() as client:
        # Create payment
        payment_request = {{
            "amount": "25.99",
            "currency": "USD",
            "payment_method": "credit_card",
            "customer_id": f"cust_python_test_{{uuid.uuid4().hex[:8]}}",
            "customer_email": "python.test@example.com",
            "customer_name": "Python Test Customer",
            "card_token": "tok_visa_4242",
            "description": "Python test payment",
            "metadata": {{
                "test_type": "python_script",
                "timestamp": datetime.now().isoformat()
            }},
            "is_test": True
        }}
        
        headers = {{
            "Authorization": f"Bearer {{JWT_TOKEN}}",
            "Content-Type": "application/json",
            "X-Correlation-ID": f"python-test-{{uuid.uuid4().hex[:8]}}",
            "X-Idempotency-Key": f"python-payment-{{datetime.now().strftime('%Y%m%d_%H%M%S')}}"
        }}
        
        print("\\n1. Creating payment...")
        response = await client.post(
            f"{{BASE_URL}}/payments",
            json=payment_request,
            headers=headers
        )
        
        if response.status_code == 201:
            payment_data = response.json()
            print("✅ Payment created successfully!")
            print(f"   Payment ID: {{payment_data['id']}}")
            print(f"   Status: {{payment_data['status']}}")
            print(f"   Amount: {{payment_data['amount']['value']}} {{payment_data['amount']['currency']}}")
            
            # Verify payment
            print("\\n2. Verifying payment...")
            verify_response = await client.get(
                f"{{BASE_URL}}/payments/{{payment_data['id']}}",
                headers={{"Authorization": f"Bearer {{JWT_TOKEN}}"}}
            )
            
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                print("✅ Payment verified!")
                print(f"   Status: {{verify_data['status']}}")
                print(f"   Created: {{verify_data['created_at']}}")
            else:
                print(f"❌ Verification failed: {{verify_response.status_code}}")
        else:
            print(f"❌ Payment creation failed: {{response.status_code}}")
            print(f"   Response: {{response.text}}")

if __name__ == "__main__":
    asyncio.run(test_payment())
"""
    
    with open("test_payment_python.py", "w") as f:
        f.write(python_script)
    
    print("✅ Test scripts created:")
    print("   - test_payment_curl.sh (Bash script)")
    print("   - test_payment_python.py (Python script)")

def print_verification_instructions():
    """Print instructions for verifying payments."""
    print("\n🔍 Verification Instructions")
    print("=" * 50)
    print("1. Database Verification:")
    print("   - Go to: http://localhost:8000/api/v1/admin/database")
    print("   - Run query: SELECT * FROM payments ORDER BY created_at DESC LIMIT 10;")
    print()
    print("2. Authorize.net Dashboard:")
    print("   - Go to: https://sandbox.authorize.net/")
    print("   - Login with your sandbox credentials")
    print("   - Navigate to Reports → Transaction Search")
    print("   - Search for transactions created today")
    print()
    print("3. API Verification:")
    print("   - Use the payment ID from the response")
    print("   - GET /api/v1/payments/{payment_id}")
    print("   - Check status history: GET /api/v1/payments/{payment_id}/status-history")

async def main():
    """Main setup function."""
    print("🛠️ EasyPay Payment Testing Setup")
    print("=" * 50)
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ EasyPay server is running")
            else:
                print("❌ EasyPay server is not responding properly")
                return
    except Exception as e:
        print(f"❌ Cannot connect to EasyPay server: {str(e)}")
        print("Please ensure the server is running on http://localhost:8000")
        return
    
    # Create API key
    api_key_data = await create_test_api_key()
    if not api_key_data:
        print("❌ Setup failed: Could not create API key")
        print("You may need to create an API key manually or check authentication setup")
        return
    
    # Generate JWT token
    token_data = await generate_test_token(
        api_key_data['key_id'], 
        api_key_data['key_secret']
    )
    if not token_data:
        print("❌ Setup failed: Could not generate JWT token")
        return
    
    # Test payment creation
    payment_data = await test_payment_creation(token_data['access_token'])
    if not payment_data:
        print("❌ Setup failed: Could not create test payment")
        return
    
    # Create test scripts
    create_test_scripts(
        api_key_data['key_id'],
        api_key_data['key_secret'], 
        token_data['access_token']
    )
    
    # Print verification instructions
    print_verification_instructions()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Summary:")
    print(f"   API Key ID: {api_key_data['key_id']}")
    print(f"   API Key Secret: {api_key_data['key_secret']}")
    print(f"   JWT Token: {token_data['access_token'][:50]}...")
    print(f"   Test Payment ID: {payment_data['id']}")
    
    print("\n🚀 Next Steps:")
    print("1. Run the generated test scripts:")
    print("   - bash test_payment_curl.sh")
    print("   - python test_payment_python.py")
    print("2. Check the database and Authorize.net dashboard")
    print("3. Use the API key and JWT token for your own tests")

if __name__ == "__main__":
    asyncio.run(main())
