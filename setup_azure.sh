#!/bin/bash

# Azure Secret Manager Setup Script
# This script helps set up the necessary Azure resources for the Secret Manager

set -e

echo "🚀 Azure Secret Manager Setup"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

echo -e "${GREEN}✅ Azure CLI found${NC}"

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not logged in to Azure. Please login first.${NC}"
    echo "Running: az login"
    az login
fi

echo -e "${GREEN}✅ Azure login verified${NC}"

# Get current subscription info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo -e "${GREEN}Current Subscription:${NC} $SUBSCRIPTION_ID"
echo -e "${GREEN}Current Tenant:${NC} $TENANT_ID"

# Prompt for Service Principal name
read -p "Enter a name for your Service Principal (default: secret-manager-sp): " SP_NAME
SP_NAME=${SP_NAME:-secret-manager-sp}

echo -e "${YELLOW}Creating Service Principal: $SP_NAME${NC}"

# Create Service Principal
SP_OUTPUT=$(az ad sp create-for-rbac --name "$SP_NAME" --role "Application Developer" --scopes "/subscriptions/$SUBSCRIPTION_ID")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Service Principal created successfully${NC}"
    
    # Extract values from JSON output
    CLIENT_ID=$(echo $SP_OUTPUT | jq -r '.appId')
    CLIENT_SECRET=$(echo $SP_OUTPUT | jq -r '.password')
    
    echo -e "${GREEN}Service Principal Details:${NC}"
    echo "Client ID: $CLIENT_ID"
    echo "Client Secret: $CLIENT_SECRET"
    echo "Tenant ID: $TENANT_ID"
    
else
    echo -e "${RED}❌ Failed to create Service Principal${NC}"
    exit 1
fi

# Grant Microsoft Graph permissions
echo -e "${YELLOW}Granting Microsoft Graph permissions...${NC}"

# Application.ReadWrite.All permission ID
PERMISSION_ID="1bfefb4e-e0b5-418b-a88f-73c46d2cc8e9"

# Add permission
az ad app permission add --id "$CLIENT_ID" --api "00000003-0000-0000-c000-000000000000" --api-permissions "$PERMISSION_ID=Role"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Permission added${NC}"
else
    echo -e "${YELLOW}⚠️  Permission might already exist${NC}"
fi

# Grant admin consent
echo -e "${YELLOW}Granting admin consent...${NC}"
az ad app permission admin-consent --id "$CLIENT_ID"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Admin consent granted${NC}"
else
    echo -e "${RED}❌ Failed to grant admin consent. You may need to do this manually in Azure Portal.${NC}"
fi

# List available App Registrations
echo -e "${YELLOW}Available App Registrations:${NC}"
az ad app list --query "[].{Name:displayName, ID:id}" -o table

# Prompt for target App Registration
echo ""
read -p "Enter the App Registration ID you want to manage: " TARGET_APP_ID

# Create .env file
echo -e "${YELLOW}Creating .env file...${NC}"

cat > .env << EOF
# Azure Service Principal Authentication (for Secret Manager)
AZURE_CLIENT_ID=$CLIENT_ID
AZURE_CLIENT_SECRET=$CLIENT_SECRET
AZURE_TENANT_ID=$TENANT_ID
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID

# Target App Registration to manage
TARGET_APP_ID=$TARGET_APP_ID

# Application Settings
DEBUG=True
PORT=8000
EOF

echo -e "${GREEN}✅ .env file created${NC}"

# Summary
echo ""
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "=================================="
echo -e "${GREEN}Service Principal:${NC} $SP_NAME"
echo -e "${GREEN}Client ID:${NC} $CLIENT_ID"
echo -e "${GREEN}Tenant ID:${NC} $TENANT_ID"
echo -e "${GREEN}Target App ID:${NC} $TARGET_APP_ID"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Install Python dependencies: pip install -r requirements.txt"
echo "2. Run the application: python simple_secret_manager.py"
echo "3. Click 'Authenticate' in the app to login"
echo ""
echo -e "${YELLOW}Security Notes:${NC}"
echo "- Keep your .env file secure and never commit it to version control"
echo "- The Service Principal has Application Developer role"
echo "- Monitor the application's access in Azure AD audit logs"
echo ""
echo -e "${GREEN}Happy secret managing! 🔐${NC}"
