from rich.console import Console
from rich.menu import Menu
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from lib.download_manager import DownloadManager
from lib.installer import Installer
from lib.server_manager import ServerManager
from ui.install_wizard import InstallWizard

class MainMenu:
    def __init__(self, console, config_manager):
        self.console = console
        self.config_manager = config_manager
        self.download_manager = DownloadManager(console)
        self.server_manager = ServerManager(console)
    
    def show(self):
        """Display the main menu"""
        while True:
            self.console.clear()
            self.console.print(Panel.fit(
                "[title]ET Legacy Server Manager[/title]",
                border_style="blue"
            ))
            
            # Show installed servers if any
            installed_servers = self.server_manager.get_installed_servers()
            if installed_servers:
                table = Table(title="Installed Servers")
                table.add_column("Name", style="cyan")
                table.add_column("Port", style="green")
                table.add_column("Status", style="yellow")
                table.add_column("Version", style="magenta")
                
                for server in installed_servers:
                    table.add_row(
                        server["name"],
                        str(server["port"]),
                        "Running" if self.server_manager.is_server_running(server["port"]) else "Stopped",
                        server["version"]
                    )
                
                self.console.print(table)
            
            # Main menu options
            self.console.print("\n[title]Menu Options:[/title]")
            self.console.print("[1] Install a new server")
            self.console.print("[2] Manage existing servers")
            self.console.print("[3] Update a server")
            self.console.print("[4] Configure firewall")
            self.console.print("[5] Exit")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"], default="1")
            
            if choice == "1":
                self._install_new_server()
            elif choice == "2":
                self._manage_servers(installed_servers)
            elif choice == "3":
                self._update_server(installed_servers)
            elif choice == "4":
                self._configure_firewall()
            elif choice == "5":
                break
    
    def _install_new_server(self):
        """Handle new server installation"""
        wizard = InstallWizard(self.console, self.config_manager, self.download_manager)
        server_config = wizard.run()
        
        if server_config:
            installer = Installer(self.config_manager, self.console)
            installer.install_server(server_config)
    
    def _manage_servers(self, installed_servers):
        """Manage existing servers"""
        if not installed_servers:
            self.console.print("[warning]No servers installed yet.[/warning]")
            input("Press Enter to continue...")
            return
        
        # Server management menu
        while True:
            self.console.clear()
            self.console.print(Panel.fit("[title]Server Management[/title]", border_style="blue"))
            
            table = Table(title="Installed Servers")
            table.add_column("#", style="cyan")
            table.add_column("Name", style="cyan")
            table.add_column("Port", style="green")
            table.add_column("Status", style="yellow")
            
            for i, server in enumerate(installed_servers, 1):
                status = "Running" if self.server_manager.is_server_running(server["port"]) else "Stopped"
                table.add_row(str(i), server["name"], str(server["port"]), status)
            
            self.console.print(table)
            self.console.print("\n[title]Actions:[/title]")
            self.console.print("[#] Select server by number")
            self.console.print("[b] Back to main menu")
            
            choice = Prompt.ask("Select an option", default="b")
            
            if choice.lower() == "b":
                break
            
            try:
                server_idx = int(choice) - 1
                if 0 <= server_idx < len(installed_servers):
                    self._server_actions(installed_servers[server_idx])
                else:
                    self.console.print("[warning]Invalid server number.[/warning]")
                    input("Press Enter to continue...")
            except ValueError:
                self.console.print("[warning]Invalid input.[/warning]")
                input("Press Enter to continue...")
    
    def _server_actions(self, server):
        """Actions for a specific server"""
        while True:
            self.console.clear()
            is_running = self.server_manager.is_server_running(server["port"])
            status = "Running" if is_running else "Stopped"
            
            self.console.print(Panel.fit(
                f"[title]Server: {server['name']}[/title]\n"
                f"Port: {server['port']}\n"
                f"Status: {status}\n"
                f"Version: {server['version']}",
                border_style="blue"
            ))
            
            self.console.print("\n[title]Actions:[/title]")
            if is_running:
                self.console.print("[1] Stop server")
                self.console.print("[2] Restart server")
            else:
                self.console.print("[1] Start server")
            
            self.console.print("[3] View server logs")
            self.console.print("[4] Edit configuration")
            self.console.print("[5] Install/update maps")
            self.console.print("[6] Back")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6"], default="6")
            
            if choice == "1":
                if is_running:
                    if self.server_manager.stop_server(server["port"]):
                        self.console.print("[success]Server stopped successfully.[/success]")
                else:
                    if self.server_manager.start_server(server["port"]):
                        self.console.print("[success]Server started successfully.[/success]")
                input("Press Enter to continue...")
            
            elif choice == "2" and is_running:
                if self.server_manager.restart_server(server["port"]):
                    self.console.print("[success]Server restarted successfully.[/success]")
                input("Press Enter to continue...")
            
            elif choice == "3":
                self.server_manager.view_logs(server["port"])
            
            elif choice == "4":
                self.server_manager.edit_config(server["port"])
            
            elif choice == "5":
                self.server_manager.manage_maps(server["port"])
            
            elif choice == "6":
                break
    
    def _update_server(self, installed_servers):
        """Update an existing server"""
        if not installed_servers:
            self.console.print("[warning]No servers installed yet.[/warning]")
            input("Press Enter to continue...")
            return
        
        self.console.clear()
        self.console.print(Panel.fit("[title]Update Server[/title]", border_style="blue"))
        
        table = Table(title="Installed Servers")
        table.add_column("#", style="cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Port", style="green")
        table.add_column("Version", style="magenta")
        
        for i, server in enumerate(installed_servers, 1):
            table.add_row(str(i), server["name"], str(server["port"]), server["version"])
        
        self.console.print(table)
        server_idx = Prompt.ask("Select server to update (or 'b' to go back)", default="b")
        
        if server_idx.lower() == "b":
            return
        
        try:
            server_idx = int(server_idx) - 1
            if 0 <= server_idx < len(installed_servers):
                self._perform_server_update(installed_servers[server_idx])
            else:
                self.console.print("[warning]Invalid server number.[/warning]")
                input("Press Enter to continue...")
        except ValueError:
            self.console.print("[warning]Invalid input.[/warning]")
            input("Press Enter to continue...")
    
    def _perform_server_update(self, server):
        """Perform the server update"""
        self.console.print(f"\nFetching available versions for updating {server['name']}...")
        
        available_versions = self.download_manager.get_available_versions()
        
        if not available_versions:
            self.console.print("[warning]No versions available for update.[/warning]")
            input("Press Enter to continue...")
            return
        
        table = Table(title="Available Versions")
        table.add_column("#", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Type", style="yellow")
        
        for i, version in enumerate(available_versions, 1):
            table.add_row(
                str(i),
                version["version"],
                "Stable" if version["is_stable"] else "Development"
            )
        
        self.console.print(table)
        version_idx = Prompt.ask("Select version to update to (or 'b' to go back)", default="b")
        
        if version_idx.lower() == "b":
            return
        
        try:
            version_idx = int(version_idx) - 1
            if 0 <= version_idx < len(available_versions):
                version = available_versions[version_idx]
                
                self.console.print(f"Updating {server['name']} to {version['name']}...")
                
                # Check if server is running
                is_running = self.server_manager.is_server_running(server["port"])
                if is_running:
                    if Confirm.ask("Server is currently running. Stop it for update?", default=True):
                        self.server_manager.stop_server(server["port"])
                    else:
                        self.console.print("[warning]Update canceled.[/warning]")
                        input("Press Enter to continue...")
                        return
                
                # Perform update
                installer = Installer(self.config_manager, self.console)
                if installer.update_server(server, version):
                    self.console.print("[success]Server updated successfully.[/success]")
                    
                    # Ask to restart server if it was running
                    if is_running and Confirm.ask("Would you like to start the server now?", default=True):
                        self.server_manager.start_server(server["port"])
                
                input("Press Enter to continue...")
            else:
                self.console.print("[warning]Invalid version number.[/warning]")
                input("Press Enter to continue...")
        except ValueError:
            self.console.print("[warning]Invalid input.[/warning]")
            input("Press Enter to continue...")
    
    def _configure_firewall(self):
        """Configure firewall settings"""
        from utils.firewall import FirewallManager
        
        firewall = FirewallManager(self.console)
        firewall.configure()