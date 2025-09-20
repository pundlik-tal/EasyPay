#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Create Simple Test Token

This script creates a simple test JWT token for testing purposes.
"""

import json
from datetime import datetime, timedelta
import os
from jose import jwt

# Test JWT secret (should match the one in the application)
JWT_SECRET = "your-secret-key-change-in-production"  # This should match the JWT_SECRET_KEY in the app
ALGORITHM = "HS256"

def create_test_token():
    """Create a test JWT token."""
    
    # Token payload
    payload = {
        "sub": "test_user",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "jti": "test_token_123",  # JWT ID required by the application
        "key_id": "test_key_123",  # API key ID
        "permissions": [
            "payments:read",
            "payments:write", 
            "payments:delete",
            "webhooks:read",
            "webhooks:write",
            "admin:read",
            "admin:write"
        ],
        "is_admin": True
    }
    
    # Create token
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    
    return token

def main():
    """Main function."""
    print("🔑 Creating test JWT token...")
    
    token = create_test_token()
    
    print("✅ Test token created successfully!")
    print(f"Token: {token}")
    print(f"Authorization Header: Bearer {token}")
    
    # Save to file
    result = {
        "token": token,
        "authorization_header": f"Bearer {token}"
    }
    
    with open("test_token.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print("💾 Token saved to test_token.json")
    
    return result

if __name__ == "__main__":
    main()
