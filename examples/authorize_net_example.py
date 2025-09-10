#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Authorize.net Integration Example
"""
import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.integrations.authorize_net import (
    AuthorizeNetClient,
    CreditCard,
    BillingAddress,
    AuthorizeNetCredentials
)


async def main():
    """Example usage of Authorize.net integration."""
    
    print("🚀 EasyPay Authorize.net Integration Example")
    print("=" * 50)
    
    # Check if credentials are provided
    api_login_id = os.getenv("AUTHORIZE_NET_API_LOGIN_ID")
    transaction_key = os.getenv("AUTHORIZE_NET_TRANSACTION_KEY")
    
    if not api_login_id or not transaction_key:
        print("⚠️  No Authorize.net credentials found in environment variables.")
        print("   Set AUTHORIZE_NET_API_LOGIN_ID and AUTHORIZE_NET_TRANSACTION_KEY")
        print("   Using demo mode with test credentials...")
        
        # Use test credentials for demonstration
        credentials = AuthorizeNetCredentials(
            api_login_id="demo_login_id",
            transaction_key="demo_transaction_key",
            sandbox=True
        )
    else:
        print("✅ Using provided Authorize.net credentials")
        credentials = AuthorizeNetCredentials(
            api_login_id=api_login_id,
            transaction_key=transaction_key,
            sandbox=True
        )
    
    # Test credit card (Authorize.net test card)
    credit_card = CreditCard(
        card_number="4111111111111111",  # Test Visa card
        expiration_date="1225",  # December 2025
        card_code="123"
    )
    
    # Test billing address
    billing_address = BillingAddress(
        first_name="John",
        last_name="Doe",
        address="123 Main St",
        city="Anytown",
        state="CA",
        zip="12345",
        country="US"
    )
    
    try:
        async with AuthorizeNetClient(credentials) as client:
            print("\n📋 Testing Authorize.net Integration...")
            
            # Test 1: Authentication
            print("\n1️⃣  Testing Authentication...")
            try:
                auth_result = await client.test_authentication()
                print(f"   ✅ Authentication: {'SUCCESS' if auth_result else 'FAILED'}")
            except Exception as e:
                print(f"   ❌ Authentication failed: {e}")
                return
            
            # Test 2: Credit Card Validation
            print("\n2️⃣  Testing Credit Card Validation...")
            try:
                # Test valid card
                valid_card = CreditCard(
                    card_number="4111111111111111",
                    expiration_date="1225",
                    card_code="123"
                )
                print("   ✅ Valid card validation passed")
                
                # Test invalid card (should raise validation error)
                try:
                    invalid_card = CreditCard(
                        card_number="1234567890123456",  # Invalid card number
                        expiration_date="1225",
                        card_code="123"
                    )
                    print("   ❌ Invalid card validation should have failed")
                except ValueError as e:
                    print(f"   ✅ Invalid card validation correctly failed: {e}")
                    
            except Exception as e:
                print(f"   ❌ Card validation test failed: {e}")
            
            # Test 3: Billing Address Validation
            print("\n3️⃣  Testing Billing Address Validation...")
            try:
                valid_address = BillingAddress(
                    first_name="Jane",
                    last_name="Smith",
                    address="456 Oak Ave",
                    city="Springfield",
                    state="IL",
                    zip="62701",
                    country="US"
                )
                print("   ✅ Valid address validation passed")
            except Exception as e:
                print(f"   ❌ Address validation failed: {e}")
            
            # Test 4: Client Configuration
            print("\n4️⃣  Testing Client Configuration...")
            print(f"   📍 API URL: {client.api_url}")
            print(f"   🏪 Sandbox Mode: {client.credentials.sandbox}")
            print(f"   🔑 API Login ID: {client.credentials.api_login_id[:8]}...")
            
            print("\n🎉 All basic tests completed successfully!")
            print("\n💡 To test actual payment processing:")
            print("   1. Set up real Authorize.net sandbox credentials")
            print("   2. Run: python test_authorize_net.py")
            print("   3. Or use the integration test script")
            
    except Exception as e:
        print(f"\n❌ Example failed with error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
