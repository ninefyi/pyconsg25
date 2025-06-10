#!/usr/bin/env python3
"""
Azure App Registration Secret Manager using Textual TUI
Manages CRUD operations for Azure App Registration secret keys
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    Header, Footer, DataTable, Button, Input, Label, 
    Static, TextLog, Tabs, TabPane, Select, Switch
)
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive
from textual import on
from textual.message import Message

from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
from azure.core.exceptions import AzureError
import requests
from rich.console import Console
from rich.table import Table

console = Console()

@dataclass
class SecretInfo:
    """Data class for App Registration secret information"""
    key_id: str
    display_name: str
    description: str
    expires: datetime
    created: datetime
    hint: str
    is_expired: bool = False

class AzureAppSecretManager:
    """Manager for Azure App Registration secrets using Microsoft Graph API"""
    
    def __init__(self):
        self.credential = None
        self.access_token = None
        self.base_url = "https://graph.microsoft.com/v1.0"
        
    async def authenticate(self, use_browser: bool = False):
        """Authenticate with Azure"""
        try:
            if use_browser:
                self.credential = InteractiveBrowserCredential()
            else:
                self.credential = DefaultAzureCredential()
            
            # Get access token for Microsoft Graph
            token = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.credential.get_token("https://graph.microsoft.com/.default")
            )
            self.access_token = token.token
            return True
        except Exception as e:
            console.print(f"Authentication failed: {e}")
            return False
    
    async def list_applications(self) -> List[Dict]:
        """List all app registrations"""
        if not self.access_token:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(f"{self.base_url}/applications", headers=headers)
            )
            
            if response.status_code == 200:
                return response.json().get("value", [])
            else:
                console.print(f"Failed to list applications: {response.status_code}")
                return []
        except Exception as e:
            console.print(f"Error listing applications: {e}")
            return []
    
    async def get_application_secrets(self, app_id: str) -> List[SecretInfo]:
        """Get secrets for a specific application"""
        if not self.access_token:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(f"{self.base_url}/applications/{app_id}", headers=headers)
            )
            
            if response.status_code == 200:
                app_data = response.json()
                secrets = []
                
                for password_credential in app_data.get("passwordCredentials", []):
                    expires = datetime.fromisoformat(password_credential["endDateTime"].replace("Z", "+00:00"))
                    created = datetime.fromisoformat(password_credential["startDateTime"].replace("Z", "+00:00"))
                    
                    secret = SecretInfo(
                        key_id=password_credential["keyId"],
                        display_name=password_credential.get("displayName", "No name"),
                        description=password_credential.get("hint", ""),
                        expires=expires,
                        created=created,
                        hint=password_credential.get("hint", ""),
                        is_expired=expires < datetime.now(expires.tzinfo)
                    )
                    secrets.append(secret)
                
                return secrets
            else:
                console.print(f"Failed to get application secrets: {response.status_code}")
                return []
        except Exception as e:
            console.print(f"Error getting application secrets: {e}")
            return []
    
    async def create_secret(self, app_id: str, display_name: str, description: str, months_valid: int = 24) -> Optional[Dict]:
        """Create a new secret for the application"""
        if not self.access_token:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        end_date = datetime.utcnow() + timedelta(days=months_valid * 30)
        
        payload = {
            "passwordCredential": {
                "displayName": display_name,
                "hint": description,
                "endDateTime": end_date.isoformat() + "Z"
            }
        }
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(f"{self.base_url}/applications/{app_id}/addPassword", 
                                    headers=headers, json=payload)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                console.print(f"Failed to create secret: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            console.print(f"Error creating secret: {e}")
            return None
    
    async def delete_secret(self, app_id: str, key_id: str) -> bool:
        """Delete a secret from the application"""
        if not self.access_token:
            return False
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "keyId": key_id
        }
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(f"{self.base_url}/applications/{app_id}/removePassword", 
                                    headers=headers, json=payload)
            )
            
            return response.status_code == 204
        except Exception as e:
            console.print(f"Error deleting secret: {e}")
            return False

class CreateSecretScreen(ModalScreen):
    """Modal screen for creating a new secret"""
    
    def __init__(self, app_id: str, azure_manager: AzureAppSecretManager):
        super().__init__()
        self.app_id = app_id
        self.azure_manager = azure_manager
    
    def compose(self) -> ComposeResult:
        with Container(id="create-secret-dialog"):
            yield Label("Create New Secret", id="create-secret-title")
            yield Label("Display Name:")
            yield Input(placeholder="Enter secret display name", id="secret-name")
            yield Label("Description:")
            yield Input(placeholder="Enter secret description", id="secret-description")
            yield Label("Valid for (months):")
            yield Select([
                ("6 months", 6),
                ("12 months", 12),
                ("24 months", 24),
                ("36 months", 36)
            ], value=24, id="secret-validity")
            with Horizontal():
                yield Button("Create", variant="primary", id="create-button")
                yield Button("Cancel", variant="default", id="cancel-button")
    
    @on(Button.Pressed, "#create-button")
    async def create_secret(self):
        name = self.query_one("#secret-name", Input).value
        description = self.query_one("#secret-description", Input).value
        validity = self.query_one("#secret-validity", Select).value
        
        if not name:
            return
        
        result = await self.azure_manager.create_secret(
            self.app_id, name, description, validity
        )
        
        if result:
            self.app.bell()
            self.dismiss(result)
        else:
            self.app.bell()
    
    @on(Button.Pressed, "#cancel-button")
    def cancel_create(self):
        self.dismiss(None)

class AzureSecretManagerApp(App):
    """Main Textual application for Azure Secret Manager"""
    
    CSS = """
    #create-secret-dialog {
        dock: center;
        width: 60;
        height: 20;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    
    #create-secret-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .expired {
        color: $error;
    }
    
    .expiring-soon {
        color: $warning;
    }
    
    DataTable > .datatable--header {
        background: $primary;
        color: $text;
    }
    
    #logs {
        height: 10;
        border: solid $primary;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("c", "create_secret", "Create Secret"),
        ("d", "delete_secret", "Delete Secret"),
    ]
    
    current_app_id = reactive("")
    authenticated = reactive(False)
    
    def __init__(self):
        super().__init__()
        self.azure_manager = AzureAppSecretManager()
        self.applications = []
        self.current_secrets = []
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Tabs("Applications", "Secrets", "Logs"):
            with TabPane("Applications", id="apps-tab"):
                yield Select([], id="app-select", allow_blank=False)
                yield Button("Authenticate", variant="primary", id="auth-button")
                yield Button("Load Applications", variant="default", id="load-apps-button")
            
            with TabPane("Secrets", id="secrets-tab"):
                yield DataTable(id="secrets-table")
                with Horizontal():
                    yield Button("Create Secret", variant="success", id="create-secret-button")
                    yield Button("Delete Secret", variant="error", id="delete-secret-button")
                    yield Button("Refresh", variant="default", id="refresh-secrets-button")
            
            with TabPane("Logs", id="logs-tab"):
                yield TextLog(id="logs", highlight=True, markup=True)
        
        yield Footer()
    
    def on_mount(self):
        """Initialize the application"""
        self.log("Azure App Registration Secret Manager started")
        self.log("Please authenticate first to access Azure resources")
    
    def log(self, message: str):
        """Add a log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_widget = self.query_one("#logs", TextLog)
        log_widget.write(f"[dim]{timestamp}[/dim] {message}")
    
    @on(Button.Pressed, "#auth-button")
    async def authenticate(self):
        """Authenticate with Azure"""
        self.log("Starting authentication...")
        auth_button = self.query_one("#auth-button", Button)
        auth_button.disabled = True
        auth_button.label = "Authenticating..."
        
        success = await self.azure_manager.authenticate(use_browser=True)
        
        if success:
            self.authenticated = True
            self.log("✅ Authentication successful")
            auth_button.label = "Authenticated"
            auth_button.variant = "success"
        else:
            self.log("❌ Authentication failed")
            auth_button.disabled = False
            auth_button.label = "Authenticate"
    
    @on(Button.Pressed, "#load-apps-button")
    async def load_applications(self):
        """Load Azure applications"""
        if not self.authenticated:
            self.log("❌ Please authenticate first")
            return
        
        self.log("Loading applications...")
        load_button = self.query_one("#load-apps-button", Button)
        load_button.disabled = True
        load_button.label = "Loading..."
        
        self.applications = await self.azure_manager.list_applications()
        
        app_select = self.query_one("#app-select", Select)
        if self.applications:
            options = [(app["displayName"], app["id"]) for app in self.applications]
            app_select.set_options(options)
            self.log(f"✅ Loaded {len(self.applications)} applications")
        else:
            self.log("❌ No applications found")
        
        load_button.disabled = False
        load_button.label = "Load Applications"
    
    @on(Select.Changed, "#app-select")
    async def on_app_selected(self, event: Select.Changed):
        """Handle application selection"""
        if event.value:
            self.current_app_id = event.value
            selected_app = next((app for app in self.applications if app["id"] == event.value), None)
            if selected_app:
                self.log(f"Selected application: {selected_app['displayName']}")
                await self.load_secrets()
    
    async def load_secrets(self):
        """Load secrets for the current application"""
        if not self.current_app_id:
            return
        
        self.log("Loading secrets...")
        secrets_table = self.query_one("#secrets-table", DataTable)
        secrets_table.clear(columns=True)
        
        # Setup table columns
        secrets_table.add_columns("Display Name", "Description", "Created", "Expires", "Status")
        
        self.current_secrets = await self.azure_manager.get_application_secrets(self.current_app_id)
        
        for secret in self.current_secrets:
            status = "🔴 Expired" if secret.is_expired else "🟢 Active"
            if not secret.is_expired:
                days_to_expire = (secret.expires - datetime.now(secret.expires.tzinfo)).days
                if days_to_expire < 30:
                    status = "🟡 Expiring Soon"
            
            secrets_table.add_row(
                secret.display_name,
                secret.description,
                secret.created.strftime("%Y-%m-%d"),
                secret.expires.strftime("%Y-%m-%d"),
                status,
                key=secret.key_id
            )
        
        self.log(f"✅ Loaded {len(self.current_secrets)} secrets")
    
    @on(Button.Pressed, "#create-secret-button")
    async def create_secret(self):
        """Show create secret dialog"""
        if not self.current_app_id:
            self.log("❌ Please select an application first")
            return
        
        def handle_result(result):
            if result:
                self.log(f"✅ Secret created: {result['displayName']}")
                self.call_after_refresh(self.load_secrets)
            else:
                self.log("❌ Failed to create secret")
        
        screen = CreateSecretScreen(self.current_app_id, self.azure_manager)
        self.push_screen(screen, handle_result)
    
    @on(Button.Pressed, "#delete-secret-button")
    async def delete_secret(self):
        """Delete the selected secret"""
        secrets_table = self.query_one("#secrets-table", DataTable)
        
        if not secrets_table.cursor_row or secrets_table.cursor_row < 0:
            self.log("❌ Please select a secret to delete")
            return
        
        row_key = secrets_table.get_row_at(secrets_table.cursor_row)
        if not row_key:
            return
        
        # Find the secret by matching the row data
        selected_secret = None
        for secret in self.current_secrets:
            if secret.key_id == secrets_table.get_row_key(secrets_table.cursor_row):
                selected_secret = secret
                break
        
        if not selected_secret:
            self.log("❌ Could not find selected secret")
            return
        
        self.log(f"Deleting secret: {selected_secret.display_name}")
        success = await self.azure_manager.delete_secret(self.current_app_id, selected_secret.key_id)
        
        if success:
            self.log(f"✅ Secret deleted: {selected_secret.display_name}")
            await self.load_secrets()
        else:
            self.log(f"❌ Failed to delete secret: {selected_secret.display_name}")
    
    @on(Button.Pressed, "#refresh-secrets-button")
    async def refresh_secrets(self):
        """Refresh the secrets list"""
        await self.load_secrets()
    
    def action_quit(self):
        """Quit the application"""
        self.exit()
    
    def action_refresh(self):
        """Refresh current view"""
        if self.current_app_id:
            self.call_after_refresh(self.load_secrets)
    
    def action_create_secret(self):
        """Create a new secret"""
        if self.current_app_id:
            self.call_after_refresh(self.create_secret)
    
    def action_delete_secret(self):
        """Delete selected secret"""
        if self.current_app_id:
            self.call_after_refresh(self.delete_secret)

def main():
    """Main entry point"""
    app = AzureSecretManagerApp()
    app.run()

if __name__ == "__main__":
    main()
