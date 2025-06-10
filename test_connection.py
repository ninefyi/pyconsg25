#!/usr/bin/env python3
"""
Test script to verify Azure authentication and basic functionality
"""

import os
import asyncio
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
import requests

# Load environment variables
load_dotenv()

async def test_authentication():
    """Test Azure authentication"""
    print("🔐 Testing Azure Authentication")
    print("=" * 40)
    
    # Check environment variables
    tenant_id = os.getenv('AZURE_TENANT_ID')
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    target_app_id = os.getenv('TARGET_APP_ID')
    
    if not all([tenant_id, client_id, client_secret, target_app_id]):
        print("❌ Missing required environment variables")
        print("Required: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, TARGET_APP_ID")
        return False
    
    print(f"✅ Environment variables loaded")
    print(f"   Tenant ID: {tenant_id}")
    print(f"   Client ID: {client_id}")
    print(f"   Target App ID: {target_app_id}")
    
    try:
        # Authenticate
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        print("\n🔄 Getting access token...")
        token = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: credential.get_token("https://graph.microsoft.com/.default")
        )
        
        print("✅ Authentication successful")
        
        # Test Graph API access
        print("\n🔄 Testing Microsoft Graph API access...")
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: requests.get(
                f"https://graph.microsoft.com/v1.0/applications/{target_app_id}",
                headers=headers
            )
        )
        
        if response.status_code == 200:
            app_data = response.json()
            print("✅ Microsoft Graph API access successful")
            print(f"   App Name: {app_data.get('displayName', 'Unknown')}")
            
            # Count existing secrets
            secret_count = len(app_data.get('passwordCredentials', []))
            print(f"   Current Secrets: {secret_count}")
            
            return True
        else:
            print(f"❌ Microsoft Graph API access failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("🧪 Azure Secret Manager - Connection Test")
    print("=" * 50)
    
    success = await test_authentication()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! You're ready to use the Secret Manager.")
        print("\nTo start the application:")
        print("   python simple_secret_manager.py")
    else:
        print("❌ Tests failed. Please check your configuration.")
        print("\nTroubleshooting:")
        print("1. Verify your .env file has the correct values")
        print("2. Check that your Service Principal has the right permissions")
        print("3. Ensure the target App Registration ID is correct")
        print("4. Run the setup script: ./setup_azure.sh")

if __name__ == "__main__":
    asyncio.run(main())
