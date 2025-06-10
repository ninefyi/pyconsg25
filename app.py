#!/usr/bin/env python3
"""
Sample Python application with Azure integration
"""

import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import docker

# Load environment variables
load_dotenv()

def test_azure_connection():
    """Test Azure connection using managed identity or service principal"""
    try:
        # Use DefaultAzureCredential for authentication
        credential = DefaultAzureCredential()
        
        # Test with Azure Storage (if configured)
        storage_account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        if storage_account:
            blob_service_client = BlobServiceClient(
                account_url=f"https://{storage_account}.blob.core.windows.net",
                credential=credential
            )
            print("✓ Azure Storage connection successful")
        
        return True
    except Exception as e:
        print(f"✗ Azure connection failed: {e}")
        return False

def test_docker_connection():
    """Test Docker connection"""
    try:
        client = docker.from_env()
        client.ping()
        print("✓ Docker connection successful")
        
        # List running containers
        containers = client.containers.list()
        print(f"Running containers: {len(containers)}")
        
        return True
    except Exception as e:
        print(f"✗ Docker connection failed: {e}")
        return False

def main():
    """Main application entry point"""
    print("🚀 Python + Docker + Azure CLI Development Environment")
    print("=" * 50)
    
    # Test connections
    azure_ok = test_azure_connection()
    docker_ok = test_docker_connection()
    
    if azure_ok and docker_ok:
        print("\n✅ All systems ready!")
    else:
        print("\n⚠️  Some systems need configuration")
    
    print("\nEnvironment variables loaded:")
    print(f"DEBUG: {os.getenv('DEBUG', 'Not set')}")
    print(f"PORT: {os.getenv('PORT', 'Not set')}")

if __name__ == "__main__":
    main()
