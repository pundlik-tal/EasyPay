"""
EasyPay Payment Gateway - Authorize.net Integration Test Script
"""
import asyncio
import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .client import AuthorizeNetClient
from .models import CreditCard, BillingAddress, AuthorizeNetCredentials
from .exceptions import AuthorizeNetError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_authorize_net_integration():
    """Test Authorize.net integration with sandbox credentials."""
    
    # Get credentials from environment or use defaults
    api_login_id = os.getenv("AUTHORIZE_NET_API_LOGIN_ID", "")
    transaction_key = os.getenv("AUTHORIZE_NET_TRANSACTION_KEY", "")
    
    if not api_login_id or not transaction_key:
        logger.warning("Authorize.net credentials not found in environment variables.")
        logger.warning("Please set AUTHORIZE_NET_API_LOGIN_ID and AUTHORIZE_NET_TRANSACTION_KEY")
        logger.warning("Using test credentials for demonstration...")
        
        # Use test credentials for demonstration
        credentials = AuthorizeNetCredentials(
            api_login_id="test_login",
            transaction_key="test_key",
            sandbox=True
        )
    else:
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
            logger.info("Testing Authorize.net integration...")
            
            # Test 1: Authentication
            logger.info("1. Testing authentication...")
            try:
                auth_result = await client.test_authentication()
                logger.info(f"✓ Authentication test: {'PASSED' if auth_result else 'FAILED'}")
            except AuthorizeNetError as e:
                logger.error(f"✗ Authentication test failed: {e}")
                return False
            
            # Test 2: Charge Credit Card
            logger.info("2. Testing credit card charge...")
            try:
                charge_result = await client.charge_credit_card(
                    amount="10.00",
                    credit_card=credit_card,
                    billing_address=billing_address,
                    order_info={"invoiceNumber": "TEST-001", "description": "Test transaction"},
                    ref_id="test_charge_001"
                )
                logger.info(f"✓ Charge test: {charge_result.status.value}")
                logger.info(f"  Transaction ID: {charge_result.transaction_id}")
                logger.info(f"  Response: {charge_result.response_text}")
                
                transaction_id = charge_result.transaction_id
                
            except AuthorizeNetError as e:
                logger.error(f"✗ Charge test failed: {e}")
                return False
            
            # Test 3: Authorize Only
            logger.info("3. Testing authorization only...")
            try:
                auth_only_result = await client.authorize_only(
                    amount="5.00",
                    credit_card=credit_card,
                    billing_address=billing_address,
                    ref_id="test_auth_001"
                )
                logger.info(f"✓ Authorization test: {auth_only_result.status.value}")
                logger.info(f"  Transaction ID: {auth_only_result.transaction_id}")
                
                auth_transaction_id = auth_only_result.transaction_id
                
            except AuthorizeNetError as e:
                logger.error(f"✗ Authorization test failed: {e}")
                return False
            
            # Test 4: Capture (if we have an authorization)
            if auth_transaction_id:
                logger.info("4. Testing capture...")
                try:
                    capture_result = await client.capture(
                        transaction_id=auth_transaction_id,
                        amount="5.00",
                        ref_id="test_capture_001"
                    )
                    logger.info(f"✓ Capture test: {capture_result.status.value}")
                    logger.info(f"  Transaction ID: {capture_result.transaction_id}")
                    
                except AuthorizeNetError as e:
                    logger.error(f"✗ Capture test failed: {e}")
                    return False
            
            # Test 5: Refund (if we have a successful transaction)
            if transaction_id:
                logger.info("5. Testing refund...")
                try:
                    refund_result = await client.refund(
                        transaction_id=transaction_id,
                        amount="5.00",
                        credit_card=credit_card,
                        ref_id="test_refund_001"
                    )
                    logger.info(f"✓ Refund test: {refund_result.status.value}")
                    logger.info(f"  Transaction ID: {refund_result.transaction_id}")
                    
                except AuthorizeNetError as e:
                    logger.error(f"✗ Refund test failed: {e}")
                    return False
            
            # Test 6: Void (test with a new authorization)
            logger.info("6. Testing void transaction...")
            try:
                # Create a new authorization to void
                void_auth_result = await client.authorize_only(
                    amount="3.00",
                    credit_card=credit_card,
                    billing_address=billing_address,
                    ref_id="test_void_auth_001"
                )
                
                if void_auth_result.transaction_id:
                    void_result = await client.void_transaction(
                        transaction_id=void_auth_result.transaction_id,
                        ref_id="test_void_001"
                    )
                    logger.info(f"✓ Void test: {void_result.status.value}")
                    logger.info(f"  Transaction ID: {void_result.transaction_id}")
                
            except AuthorizeNetError as e:
                logger.error(f"✗ Void test failed: {e}")
                return False
            
            logger.info("🎉 All Authorize.net integration tests completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"Integration test failed with unexpected error: {e}")
        return False


async def main():
    """Main function to run integration tests."""
    logger.info("Starting Authorize.net Integration Tests...")
    logger.info("=" * 50)
    
    success = await test_authorize_net_integration()
    
    logger.info("=" * 50)
    if success:
        logger.info("✅ Integration tests PASSED")
    else:
        logger.info("❌ Integration tests FAILED")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
