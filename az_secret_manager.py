#!/usr/bin/env python3
"""
Azure App Registration Client Secret Manager using Textual TUI
A more focused version for easier deployment and testing
"""

import os
import datetime
from typing import List
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import (
    Header, Footer, DataTable, Label, Static
)
from textual import on

from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.applications.item.add_password.add_password_post_request_body import AddPasswordPostRequestBody
from msgraph.generated.applications.item.remove_password.remove_password_post_request_body import RemovePasswordPostRequestBody
from msgraph.generated.models.password_credential import PasswordCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class AppSecret:
    """Simplified data class for application registration client secret"""
    app_id: str
    key_id: str
    app_name: str
    remain_days: int
    exp_date: str
    urgent: str

class AzureManager:
    """Azure app registration client secret manager"""

    def __init__(self):
        self.graph_service_client = None
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')

    async def authenticate(self):
        """Authenticate using service principal"""
        try:
            if not all([self.tenant_id, self.client_id, self.client_secret]):
                return False, "Missing Azure credentials in environment"

            credentials = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            scopes = ['https://graph.microsoft.com/.default']
            self.graph_service_client = GraphServiceClient(credentials=credentials, scopes=scopes)

            return True, "Authentication successful"

        except Exception as e:
            return False, f"Authentication failed: {str(e)}"

    async def list_app_secrets(self) -> List[AppSecret]:
        """Get all application registration client secrets"""
        if not self.graph_service_client:
            return []
        
        try:
            # Get all applications in the tenant
            days_threshold = 30
            secrets = []
            result = await self.graph_service_client.applications.get()
            applications = result.value
            for app in applications:
                # Check passwords (client secrets)
                for password in app.password_credentials:
                    expiry_date = password.end_date_time
                    key_id = password.key_id
                    if expiry_date:
                        time_difference = expiry_date - datetime.datetime.now(datetime.timezone.utc)
                        days_until_expiry = time_difference.days
                        urgent = ""
                        if days_until_expiry <= days_threshold:
                            urgent = "YES"

                        secret = AppSecret(
                            app_id=app.id,
                            key_id=key_id,
                            app_name=app.display_name,
                            remain_days=days_until_expiry,
                            exp_date=expiry_date.strftime("%d-%m-%Y"),
                            urgent=urgent if urgent else "NO"
                        )
                        secrets.append(secret)
        
            # print(f"Found {len(secrets)} application secrets")
            return secrets, f"Found {len(secrets)} application secrets"

        except Exception as e:
            print(f"Error getting secrets: {e}")
            return []
        
    async def create_secret(self, app_id: str, months: int = 24) -> str:
        """Create a new secret"""
        if not app_id:
            return None
        
        name = f"secret-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        description = name
        end_date_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=months * 30)).replace(microsecond=0).isoformat()

        request_body = AddPasswordPostRequestBody(
            password_credential = PasswordCredential(
                display_name = name,
                hint = description,
                end_date_time = end_date_time,
            ),
        )
        
        try:
            response = await self.graph_service_client.applications.by_application_id(app_id).add_password.post(request_body)
            return f"{response.display_name} - {response.secret_text} - {response.end_date_time}"

        except Exception as e:
            print(f"Error creating {e}")
            return f"Error: {str(e)}"

    async def delete_secret(self, app_id: str, key_id: str) -> str:
        """Delete a secret"""

        try:
            request_body = RemovePasswordPostRequestBody(
                key_id = key_id,
            )
            await self.graph_service_client.applications.by_application_id(app_id).remove_password.post(request_body)
            return f"Successfully deleted secret {key_id}"

        except Exception as e:
            return f"Error deleting {key_id}: {e}"

class SecretManagerApp(App):
    """Main Textual application for managing Azure secrets"""
    
    CSS_PATH = "az_secret_manager.tcss"

    BINDINGS = [
        ("a", "authenticate", "Authenticate"),
        ("r", "refresh", "Refresh"),
        ("c", "renew", "Renew"),
        ("d", "delete", "Delete"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.azure_manager = AzureManager()
        self.secrets = []
        self.authenticated = False

    def compose(self) -> ComposeResult:
        """Create app layout"""
        self.title = "Azure App Registration Secret Manager"

        yield Header()

        with Vertical():
            # Status display
            yield Static("Status: Not authenticated", id="status")

            # Add two tables - one for secrets and one for app registrations
            yield Label("App Registrations:", id="apps-label")
            yield DataTable(id="apps-table")

        yield Footer()

    def on_mount(self):
        """Initialize the application"""

        # Check if we have required environment variables
        if not all([
            os.getenv('AZURE_TENANT_ID'),
            os.getenv('AZURE_CLIENT_ID'),
            os.getenv('AZURE_CLIENT_SECRET'),
        ]):
            self.update_status(
                "Missing environment variables. Check .env file")
        else:
            self.update_status("Ready to authenticate")

    def update_status(self, message: str):
        """Update the status display"""
        status_widget = self.query_one("#status", Static)
        status_widget.update(f"Status: {message}")

    async def authenticate(self):
        """Authenticate with Azure"""
        self.update_status("Authenticating...")

        success, message = await self.azure_manager.authenticate()

        if success:
            self.authenticated = True
            self.update_status(f"Authenticated: {message}")
            await self.list_apps()
        else:
            self.update_status(f"{message}")

    async def renew_secret(self):
        """Show create secret dialog"""
        if not self.authenticated:
            self.update_status("Please authenticate first")
            return
        
        table = self.query_one("#apps-table", DataTable)
        
        if table.cursor_row is None or table.cursor_row < 0:
            self.update_status("Please select application for renew")
            return
        
        selected_row = table.get_row_at(table.cursor_row)
        app_id = selected_row[1]  # Assuming app_id is in the second column
        app_name = selected_row[0]
        
        self.update_status(f"Renewing secret: {app_name} - {app_id}")
        
        result = await self.azure_manager.create_secret(app_id, 24)
        
        if result:
            self.update_status(f"{result}")
            self.list_apps()
        else:
            self.update_status(f"Failed to create secret: {app_name}")

    async def delete_secret(self):
        """Delete the selected secret"""
        if not self.authenticated:
            self.update_status("Please authenticate first")
            return

        table = self.query_one("#apps-table", DataTable)

        if table.cursor_row is None or table.cursor_row < 0:
            self.update_status("Please select a secret to delete")
            return

        try:
            # row_key = table.coordinate_to_cell_key(table.cursor_row)       
            self.update_status(f"Deleting secret...{table.cursor_row}")     
            selected_row = table.get_row_at(table.cursor_row)
            app_name = selected_row[0]
            app_id = selected_row[1]
            key_id = selected_row[2]  
            
            self.update_status(f"Deleting secret: {app_name} - {app_id} - {key_id}")

            success = await self.azure_manager.delete_secret(app_id, key_id)

            if success:
                self.update_status(f"{success}")
                await self.list_apps()
            else:
                self.update_status(f"Failed to delete secret: {app_name} - {key_id}")

        except (IndexError, StopIteration):
            self.update_status("Could not find selected secret")

    async def list_apps(self):
        """List all app registrations"""
        if not self.authenticated:
            self.update_status("Please authenticate first")
            return

        self.update_status("Loading app registrations...")

        # Fetch app registrations
        apps, message = await self.azure_manager.list_app_secrets()

        if not apps:
            self.update_status(f"{message}")
            return

        # Setup the apps table
        table = self.query_one("#apps-table", DataTable)
        table.clear()

        # Add column headers if not already added
        if len(table.columns) == 0:
            table.add_columns("Name", "ID", "Key", "Exp", "Days", "Urgent")
        # Add app data
        for app in apps:
            table.add_row(
                app.app_name,
                app.app_id,
                app.key_id,
                app.exp_date if app.exp_date else "N/A",
                str(app.remain_days),
                app.urgent,
                key=app.key_id
            )

        self.update_status(f"Loaded {len(apps)} app registrations")

    # Action methods for keyboard shortcuts
    async def action_refresh(self):
        await self.list_apps()

    async def action_renew(self):
        await self.renew_secret()
        
    async def action_authenticate(self):
        await self.authenticate()

    async def action_delete(self):
        await self.delete_secret()

    def action_quit(self):
        self.exit()


def main():
    """Main entry point"""
    app = SecretManagerApp()
    app.run()
    # a = SimpleAzureManager()
    # asyncio.run(a.authenticate())
    # asyncio.run(a.delete_secret("27ace449-6b88-4b18-a54f-1ae6eee9d427", "1d28f1e4-caab-4881-ad66-900fa4d73e3b"))
if __name__ == "__main__":
    main()
