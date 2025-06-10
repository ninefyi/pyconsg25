# Azure App Registration Secret Manager

A Terminal User Interface (TUI) application built with Python and Textual to manage CRUD operations for Azure App Registration secret keys.

## Features

- 🔐 **Secure Authentication** - Uses Azure Service Principal authentication
- 📋 **List Secrets** - View all secrets for an App Registration
- ➕ **Create Secrets** - Add new client secrets with custom expiration
- 🗑️ **Delete Secrets** - Remove unused or expired secrets
- 🎨 **Rich TUI** - Beautiful terminal interface with Textual framework
- ⚡ **Real-time Status** - Visual indicators for expired/expiring secrets

## Prerequisites

1. **Azure Account** with appropriate permissions
2. **Service Principal** with Application.ReadWrite.All permissions
3. **Target App Registration** that you want to manage
4. **Python 3.11+** and required packages

## Quick Setup

### 1. Azure Setup

You need to create a Service Principal that can manage App Registration secrets:

```bash
# Login to Azure CLI
az login

# Create a new Service Principal
az ad sp create-for-rbac --name "secret-manager-sp" --role "Application Developer"

# Note down the output:
# - appId (this is your AZURE_CLIENT_ID)
# - password (this is your AZURE_CLIENT_SECRET)
# - tenant (this is your AZURE_TENANT_ID)
```

### 2. Grant Microsoft Graph Permissions

```bash
# Get the Object ID of your Service Principal
az ad sp list --display-name "secret-manager-sp" --query "[0].id" -o tsv

# Grant Application.ReadWrite.All permission
az ad app permission add --id <your-service-principal-app-id> --api 00000003-0000-0000-c000-000000000000 --api-permissions 1bfefb4e-e0b5-418b-a88f-73c46d2cc8e9=Role

# Grant admin consent
az ad app permission admin-consent --id <your-service-principal-app-id>
```

### 3. Environment Setup

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your values
nano .env
```

Required environment variables:
- `AZURE_CLIENT_ID` - Your Service Principal App ID
- `AZURE_CLIENT_SECRET` - Your Service Principal Secret
- `AZURE_TENANT_ID` - Your Azure AD Tenant ID
- `TARGET_APP_ID` - The App Registration ID you want to manage

### 4. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

## Usage

### Simple Secret Manager (Recommended)

```bash
python simple_secret_manager.py
```

**Keyboard Shortcuts:**
- `r` - Refresh secrets list
- `c` - Create new secret
- `d` - Delete selected secret
- `q` - Quit application

**Steps:**
1. Click "Authenticate" to login to Azure
2. Click "Refresh" to load secrets
3. Use arrow keys to navigate the table
4. Use buttons or keyboard shortcuts for actions

### Full-Featured Secret Manager

```bash
python azure_secret_manager.py
```

This version includes:
- Multiple App Registration management
- Interactive browser authentication
- Detailed logging
- Advanced secret management features

## Application Structure

```
├── simple_secret_manager.py    # Simplified TUI app
├── azure_secret_manager.py     # Full-featured TUI app
├── requirements.txt            # Python dependencies
├── .env.template              # Environment variables template
└── README.md                  # This file
```

## Security Notes

- **Never commit** your `.env` file to version control
- **Rotate secrets regularly** - Set expiration dates and monitor them
- **Use least privilege** - Grant only necessary permissions to your Service Principal
- **Monitor access** - Check Azure AD audit logs for secret access

## Troubleshooting

### Authentication Issues

1. **"Missing environment variables"**
   - Ensure all required variables are set in `.env`
   - Check that variable names match exactly

2. **"Authentication failed"**
   - Verify Service Principal credentials
   - Check that admin consent was granted
   - Ensure Service Principal has correct permissions

3. **"No applications found"**
   - Verify TARGET_APP_ID is correct
   - Check that Service Principal has access to the target app

### Permission Issues

1. **"Insufficient privileges"**
   - Ensure Service Principal has `Application.ReadWrite.All` permission
   - Verify admin consent was granted

2. **"Access denied"**
   - Check that you're using the correct tenant ID
   - Verify the target App Registration exists

## Development

To extend or modify the application:

1. **Add new features** to the Textual widgets
2. **Enhance Azure integration** with additional Graph API calls
3. **Improve error handling** with better user feedback
4. **Add configuration options** for different scenarios

## API Reference

The application uses Microsoft Graph API endpoints:
- `GET /applications/{id}` - Get application details and secrets
- `POST /applications/{id}/addPassword` - Create new secret
- `POST /applications/{id}/removePassword` - Delete existing secret

## License

This project is for educational and demonstration purposes. Use at your own risk and ensure compliance with your organization's security policies.
