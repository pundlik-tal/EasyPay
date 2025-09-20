#!/usr/bin/env python3
"""
Simple test script to debug API endpoints
"""
import requests
import json
import time

def test_endpoint(url, method="GET", data=None):
    """Test a single endpoint"""
    try:
        print(f"Testing {method} {url}")
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    base_url = "http://localhost:8000"
    
    print("=== Testing EasyPay API Endpoints ===")
    
    # Test health endpoint
    print("\n1. Testing Health Endpoint")
    test_endpoint(f"{base_url}/health")
    
    # Test payment creation
    print("\n2. Testing Payment Creation")
    payment_data = {
        "amount": 10.00,
        "currency": "USD",
        "payment_method": "credit_card",
        "card_token": "test_token_123",
        "customer_email": "test@example.com",
        "customer_name": "Test Customer"
    }
    test_endpoint(f"{base_url}/api/v1/payments/", "POST", payment_data)
    
    # Test payment listing
    print("\n3. Testing Payment Listing")
    test_endpoint(f"{base_url}/api/v1/payments/")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
