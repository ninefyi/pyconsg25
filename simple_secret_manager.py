#!/usr/bin/env python3
"""
Simplified Azure App Registration Secret Manager using Textual TUI
A more focused version for easier deployment and testing
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Header, Footer, DataTable, Button, Input, Label, 
    Static, TextLog, Select
)
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual import on

from azure.identity import DefaultAzureCredential, ClientSecretCredential
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class AppSecret:
    """Simplified data class for App Registration secret"""
    key_id: str
    display_name: str
    description: str
    expires: str
    status: str

class SimpleAzureManager:
    """Simplified Azure manager using environment variables"""
    
    def __init__(self):
        self.access_token = None
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.target_app_id = os.getenv('TARGET_APP_ID')  # The app we want to manage
        
    async def authenticate(self):
        """Authenticate using service principal"""
        try:
            if not all([self.tenant_id, self.client_id, self.client_secret]):
                return False, "Missing Azure credentials in environment"
            
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            token = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: credential.get_token("https://graph.microsoft.com/.default")
            )
            
            self.access_token = token.token
            return True, "Authentication successful"
            
        except Exception as e:
            return False, f"Authentication failed: {str(e)}"
    
    async def get_secrets(self) -> List[AppSecret]:
        """Get secrets for the target application"""
        if not self.access_token or not self.target_app_id:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(
                    f"https://graph.microsoft.com/v1.0/applications/{self.target_app_id}",
                    headers=headers
                )
            )
            
            if response.status_code != 200:
                return []
            
            app_data = response.json()
            secrets = []
            
            for cred in app_data.get("passwordCredentials", []):
                expires = datetime.fromisoformat(cred["endDateTime"].replace("Z", "+00:00"))
                now = datetime.now(expires.tzinfo)
                
                if expires < now:
                    status = "🔴 Expired"
                elif (expires - now).days < 30:
                    status = "🟡 Expiring Soon"
                else:
                    status = "🟢 Active"
                
                secret = AppSecret(
                    key_id=cred["keyId"],
                    display_name=cred.get("displayName", "Unnamed"),
                    description=cred.get("hint", "No description"),
                    expires=expires.strftime("%Y-%m-%d"),
                    status=status
                )
                secrets.append(secret)
            
            return secrets
            
        except Exception as e:
            print(f"Error getting secrets: {e}")
            return []
    
    async def create_secret(self, name: str, description: str, months: int = 24) -> Optional[Dict]:
        """Create a new secret"""
        if not self.access_token or not self.target_app_id:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        end_date = datetime.utcnow() + timedelta(days=months * 30)
        
        payload = {
            "passwordCredential": {
                "displayName": name,
                "hint": description,
                "endDateTime": end_date.isoformat() + "Z"
            }
        }
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    f"https://graph.microsoft.com/v1.0/applications/{self.target_app_id}/addPassword",
                    headers=headers,
                    json=payload
                )
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            print(f"Error creating secret: {e}")
            return None
    
    async def delete_secret(self, key_id: str) -> bool:
        """Delete a secret"""
        if not self.access_token or not self.target_app_id:
            return False
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {"keyId": key_id}
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    f"https://graph.microsoft.com/v1.0/applications/{self.target_app_id}/removePassword",
                    headers=headers,
                    json=payload
                )
            )
            
            return response.status_code == 204
            
        except Exception as e:
            print(f"Error deleting secret: {e}")
            return False

class CreateSecretDialog(ModalScreen):
    """Dialog for creating new secrets"""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Create New Secret", id="title")
            yield Label("Name:")
            yield Input(placeholder="Secret name", id="name-input")
            yield Label("Description:")
            yield Input(placeholder="Secret description", id="desc-input")
            yield Label("Valid for:")
            yield Select([
                ("6 months", 6),
                ("12 months", 12),
                ("24 months", 24)
            ], value=24, id="months-select")
            with Horizontal():
                yield Button("Create", variant="primary", id="create-btn")
                yield Button("Cancel", id="cancel-btn")
    
    @on(Button.Pressed, "#create-btn")
    def create_secret(self):
        name = self.query_one("#name-input", Input).value
        desc = self.query_one("#desc-input", Input).value
        months = self.query_one("#months-select", Select).value
        
        if name.strip():
            self.dismiss((name, desc, months))
    
    @on(Button.Pressed, "#cancel-btn")
    def cancel(self):
        self.dismiss(None)

class SecretManagerApp(App):
    """Main Textual application for managing Azure secrets"""
    
    CSS = """
    #dialog {
        dock: center;
        width: 50;
        height: 15;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    
    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #status {
        height: 3;
        border: solid $primary;
        margin: 1 0;
    }
    
    #secrets-table {
        height: 15;
    }
    """
    
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("c", "create", "Create"),
        ("d", "delete", "Delete"),
        ("q", "quit", "Quit"),
    ]
    
    def __init__(self):
        super().__init__()
        self.azure_manager = SimpleAzureManager()
        self.secrets = []
        self.authenticated = False
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Azure App Registration Secret Manager", id="title")
        yield Static("Status: Not authenticated", id="status")
        
        with Horizontal():
            yield Button("Authenticate", variant="primary", id="auth-btn")
            yield Button("Refresh", id="refresh-btn")
            yield Button("Create Secret", variant="success", id="create-btn")
            yield Button("Delete Secret", variant="error", id="delete-btn")
        
        yield DataTable(id="secrets-table")
        yield Footer()
    
    def on_mount(self):
        """Initialize the application"""
        table = self.query_one("#secrets-table", DataTable)
        table.add_columns("Name", "Description", "Expires", "Status")
        
        # Check if we have required environment variables
        if not all([
            os.getenv('AZURE_TENANT_ID'),
            os.getenv('AZURE_CLIENT_ID'),
            os.getenv('AZURE_CLIENT_SECRET'),
            os.getenv('TARGET_APP_ID')
        ]):
            self.update_status("❌ Missing environment variables. Check .env file")
        else:
            self.update_status("Ready to authenticate")
    
    def update_status(self, message: str):
        """Update the status display"""
        status_widget = self.query_one("#status", Static)
        status_widget.update(f"Status: {message}")
    
    @on(Button.Pressed, "#auth-btn")
    async def authenticate(self):
        """Authenticate with Azure"""
        self.update_status("Authenticating...")
        auth_btn = self.query_one("#auth-btn", Button)
        auth_btn.disabled = True
        
        success, message = await self.azure_manager.authenticate()
        
        if success:
            self.authenticated = True
            self.update_status("✅ Authenticated")
            auth_btn.label = "Authenticated"
            auth_btn.variant = "success"
            await self.refresh_secrets()
        else:
            self.update_status(f"❌ {message}")
            auth_btn.disabled = False
    
    @on(Button.Pressed, "#refresh-btn")
    async def refresh_secrets(self):
        """Refresh the secrets list"""
        if not self.authenticated:
            self.update_status("❌ Please authenticate first")
            return
        
        self.update_status("Loading secrets...")
        self.secrets = await self.azure_manager.get_secrets()
        
        table = self.query_one("#secrets-table", DataTable)
        table.clear()
        
        for secret in self.secrets:
            table.add_row(
                secret.display_name,
                secret.description,
                secret.expires,
                secret.status,
                key=secret.key_id
            )
        
        self.update_status(f"✅ Loaded {len(self.secrets)} secrets")
    
    @on(Button.Pressed, "#create-btn")
    async def create_secret(self):
        """Show create secret dialog"""
        if not self.authenticated:
            self.update_status("❌ Please authenticate first")
            return
        
        def handle_result(result):
            if result:
                name, desc, months = result
                self.call_after_refresh(self._create_secret, name, desc, months)
        
        self.push_screen(CreateSecretDialog(), handle_result)
    
    async def _create_secret(self, name: str, desc: str, months: int):
        """Actually create the secret"""
        self.update_status(f"Creating secret: {name}")
        
        result = await self.azure_manager.create_secret(name, desc, months)
        
        if result:
            self.update_status(f"✅ Created secret: {name}")
            await self.refresh_secrets()
        else:
            self.update_status(f"❌ Failed to create secret: {name}")
    
    @on(Button.Pressed, "#delete-btn")
    async def delete_secret(self):
        """Delete the selected secret"""
        if not self.authenticated:
            self.update_status("❌ Please authenticate first")
            return
        
        table = self.query_one("#secrets-table", DataTable)
        
        if table.cursor_row is None or table.cursor_row < 0:
            self.update_status("❌ Please select a secret to delete")
            return
        
        try:
            row_key = table.get_row_key(table.cursor_row)
            selected_secret = next(s for s in self.secrets if s.key_id == row_key)
            
            self.update_status(f"Deleting secret: {selected_secret.display_name}")
            
            success = await self.azure_manager.delete_secret(selected_secret.key_id)
            
            if success:
                self.update_status(f"✅ Deleted secret: {selected_secret.display_name}")
                await self.refresh_secrets()
            else:
                self.update_status(f"❌ Failed to delete secret: {selected_secret.display_name}")
                
        except (IndexError, StopIteration):
            self.update_status("❌ Could not find selected secret")
    
    # Action methods for keyboard shortcuts
    async def action_refresh(self):
        await self.refresh_secrets()
    
    async def action_create(self):
        await self.create_secret()
    
    async def action_delete(self):
        await self.delete_secret()
    
    def action_quit(self):
        self.exit()

def main():
    """Main entry point"""
    app = SecretManagerApp()
    app.run()

if __name__ == "__main__":
    main()
