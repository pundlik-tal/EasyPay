#!/usr/bin/env python3
"""
EasyPay Payment Gateway - Environment Fix Script

This script helps fix the environment configuration issues by:
1. Creating a proper .env file from env.development
2. Setting up all required environment variables
3. Validating the configuration

Usage:
    python scripts/fix_environment.py
"""

import os
import sys
from pathlib import Path


def create_env_file():
    """Create .env file from env.development."""
    project_root = Path(__file__).parent.parent
    
    # Read env.development
    env_dev_path = project_root / "env.development"
    if not env_dev_path.exists():
        print("❌ env.development file not found")
        return False
    
    # Read the content
    with open(env_dev_path, 'r') as f:
        content = f.read()
    
    # Create .env file (if not blocked)
    env_path = project_root / ".env"
    try:
        with open(env_path, 'w') as f:
            f.write(content)
        print(f"✅ Created .env file from env.development")
        return True
    except Exception as e:
        print(f"⚠️  Could not create .env file: {e}")
        print("   This is normal if .env files are gitignored")
        return False


def load_and_validate_env():
    """Load and validate environment variables."""
    project_root = Path(__file__).parent.parent
    
    # Try to load from env.development
    env_dev_path = project_root / "env.development"
    if env_dev_path.exists():
        print("📄 Loading environment variables from env.development...")
        
        with open(env_dev_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('"\'')
                    os.environ[key.strip()] = value
                    print(f"✅ Loaded: {key.strip()}")
    
    # Check required variables
    required_vars = [
        "AUTHORIZE_NET_API_LOGIN_ID",
        "AUTHORIZE_NET_TRANSACTION_KEY", 
        "AUTHORIZE_NET_SANDBOX",
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
        "JWT_SECRET_KEY"
    ]
    
    print("\n🔐 Checking required environment variables...")
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            print(f"❌ {var} - Missing")
        else:
            # Mask sensitive values
            value = os.getenv(var)
            if "KEY" in var or "SECRET" in var:
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                print(f"✅ {var} - {masked_value}")
            else:
                print(f"✅ {var} - {value}")
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("\n✅ All required environment variables are set!")
    return True


def main():
    """Main function."""
    print("🔧 EasyPay Payment Gateway - Environment Fix")
    print("=" * 50)
    
    # Create .env file
    create_env_file()
    
    # Load and validate environment
    success = load_and_validate_env()
    
    if success:
        print("\n🎉 Environment configuration is now ready!")
        print("\n🚀 Next steps:")
        print("   1. Run setup: python scripts/setup_testing_environment.py --start-services")
        print("   2. Run tests: python scripts/run_all_tests.py")
    else:
        print("\n❌ Please fix the missing environment variables in env.development")
        print("   Then run this script again")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Fix interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
