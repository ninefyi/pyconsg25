#!/usr/bin/env python3
"""
Demo script showing the Azure Secret Manager capabilities
"""

import asyncio
from datetime import datetime
from simple_secret_manager import SimpleAzureManager
from dotenv import load_dotenv

load_dotenv()

async def demo():
    """Demonstrate the Secret Manager functionality"""
    print("🎭 Azure Secret Manager Demo")
    print("=" * 40)
    
    # Initialize manager
    manager = SimpleAzureManager()
    
    # Authenticate
    print("🔐 Authenticating...")
    success, message = await manager.authenticate()
    
    if not success:
        print(f"❌ Authentication failed: {message}")
        return
    
    print(f"✅ {message}")
    
    # List existing secrets
    print("\n📋 Current secrets:")
    secrets = await manager.get_secrets()
    
    if not secrets:
        print("   No secrets found")
    else:
        for i, secret in enumerate(secrets, 1):
            print(f"   {i}. {secret.display_name}")
            print(f"      Description: {secret.description}")
            print(f"      Expires: {secret.expires}")
            print(f"      Status: {secret.status}")
            print()
    
    # Demo create secret (commented out to avoid creating actual secrets)
    print("🔧 Demo Operations Available:")
    print("   ➕ Create Secret: manager.create_secret(name, description, months)")
    print("   🗑️  Delete Secret: manager.delete_secret(key_id)")
    print("   🔄 Refresh List: manager.get_secrets()")
    
    print("\n🎨 To use the interactive TUI:")
    print("   python simple_secret_manager.py")
    
    print("\n🛡️  Security Features:")
    print("   • Visual status indicators for expired/expiring secrets")
    print("   • Secure authentication with Service Principal")
    print("   • Real-time secret management")
    print("   • Keyboard shortcuts for efficiency")

if __name__ == "__main__":
    asyncio.run(demo())
