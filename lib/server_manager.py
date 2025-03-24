import os
import glob
import re
import time
import subprocess
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

class ServerManager:
    def __init__(self, console):
        self.console = console
        self.bash_runner = BashRunner(console)
    
    def get_installed_servers(self):
        """Get list of installed servers"""
        servers = []
        
        # Look for systemd service files
        service_files = glob.glob("/etc/systemd/system/etlserver-*.service")
        
        for service_file in service_files:
            try:
                # Extract port from filename
                port_match = re.search(r'etlserver-(\d+)\.service', service_file)
                if port_match:
                    port = int(port_match.group(1))
                    
                    # Read service file to get installation directory
                    with open(service_file, 'r') as f:
                        service_content = f.read()
                    
                    # Extract installation directory
                    dir_match = re.search(r'ExecStart=(.+?)/etl_start\.sh', service_content)
                    if dir_match:
                        server_dir = dir_match.group(1)
                        install_dir = os.path.dirname(os.path.dirname(server_dir))
                        
                        # Extract server name from config
                        server_name = "ET Legacy Server"
                        cfg_file = f"{server_dir}/etmain/etl_server.cfg"
                        if os.path.exists(cfg_file):
                            with open(cfg_file, 'r') as f:
                                cfg_content = f.read()
                            
                            name_match = re.search(r'set sv_hostname\s+"(.+?)"', cfg_content)
                            if name_match:
                                server_name = name_match.group(1)
                        
                        # Try to determine version
                        version = "Unknown"
                        try:
                            result = self.bash_runner.run_command(f"{server_dir}/etlded.x86_64 +set dedicated 1 +set com_quiet 1 +quit")
                            version_match = re.search(r'ET Legacy v(\d+\.\d+\.\d+)', result.stdout)
                            if version_match:
                                version = version_match.group(1)
                        except:
                            pass
                        
                        servers.append({
                            "name": server_name,
                            "port": port,
                            "version": version,
                            "dir": server_dir,
                            "installDir": install_dir
                        })
            except Exception as e:
                self.console.print(f"[warning]Error reading server info from {service_file}: {e}[/warning]")
        
        return servers
    
    def is_server_running(self, port):
        """Check if a server is running"""        
        try:
            result = self.bash_runner.run_command(f"systemctl is-active etlserver-{port}.service")
            return result.stdout.strip() == "active"
        except Exception:
            return False
    
    def start_server(self, port):
        """Start the server"""
        try:
            self.bash_runner.run_command(f"systemctl start etlserver-{port}.service")
            time.sleep(2)  # Give the service a moment to start
            return self.is_server_running(port)
        except Exception as e:
            self.console.print(f"[danger]Error starting server: {e}[/danger]")
            return False
    
    def stop_server(self, port):
        """Stop the server"""
        try:
            self.bash_runner.run_command(f"systemctl stop etlserver-{port}.service")
            time.sleep(2)  # Give the service a moment to stop
            return not self.is_server_running(port)
        except Exception as e:
            self.console.print(f"[danger]Error stopping server: {e}[/danger]")
            return False
    
    def restart_server(self, port):
        """Restart the server"""
        try:
            self.bash_runner.run_command(f"systemctl restart etlserver-{port}.service")
            time.sleep(2)  # Give the service a moment to restart
            return self.is_server_running(port)
        except Exception as e:
            self.console.print(f"[danger]Error restarting server: {e}[/danger]")
            return False
    
    def view_logs(self, port):
        """View server logs"""
        self.console.clear()
        self.console.print(Panel.fit(f"[title]Server Logs (Port {port})[/title]", border_style="blue"))
        
        try:
            # Use journalctl to view logs
            self.console.print("[info]Press 'q' to exit log view[/info]")
            self.console.print("[info]Press Enter to continue...[/info]")
            input()
            
            subprocess.run(["journalctl", "-u", f"etlserver-{port}.service", "-f"])
            return True
        except Exception as e:
            self.console.print(f"[danger]Error viewing logs: {e}[/danger]")
            return False
    
    def edit_config(self, port):
        """Edit server configuration"""
        # Find servers
        servers = self.get_installed_servers()
        server = next((s for s in servers if s['port'] == port), None)
        
        if not server:
            self.console.print(f"[warning]Server on port {port} not found.[/warning]")
            return False
        
        self.console.clear()
        self.console.print(Panel.fit(f"[title]Edit Server Configuration (Port {port})[/title]", border_style="blue"))
        
        # List available configuration files
        self.console.print("\n[title]Available Configuration Files:[/title]")
        self.console.print(f"[1] Main Server Config (etl_server.cfg)")
        self.console.print(f"[2] Legacy Configs (legacy/configs/)")
        
        choice = Prompt.ask("Select file to edit", choices=["1", "2", "b"], default="b")
        
        if choice == "b":
            return False
        
        if choice == "1":
            config_file = f"{server['dir']}/etmain/etl_server.cfg"
            self._edit_file(config_file)
        elif choice == "2":
            # List available legacy configs
            configs_dir = f"{server['dir']}/legacy/configs"
            if not os.path.exists(configs_dir):
                self.console.print(f"[warning]Legacy configs directory not found: {configs_dir}[/warning]")
                return False
            
            configs = [f for f in os.listdir(configs_dir) if f.endswith('.config')]
            
            if not configs:
                self.console.print("[warning]No legacy config files found.[/warning]")
                return False
            
            self.console.clear()
            self.console.print(Panel.fit("[title]Select Legacy Config File[/title]", border_style="blue"))
            
            for i, config in enumerate(configs, 1):
                self.console.print(f"[{i}] {config}")
            
            self.console.print(f"[b] Back")
            
            config_choice = Prompt.ask("Select config file", choices=[str(i) for i in range(1, len(configs) + 1)] + ["b"], default="b")
            
            if config_choice == "b":
                return False
            
            config_file = f"{configs_dir}/{configs[int(config_choice) - 1]}"
            self._edit_file(config_file)
        
        # Ask if user wants to restart server
        if Confirm.ask("Would you like to restart the server to apply changes?", default=True):
            return self.restart_server(port)
        
        return True
    
    def _edit_file(self, file_path):
        """Edit a file using preferred editor"""
        if not os.path.exists(file_path):
            self.console.print(f"[warning]File not found: {file_path}[/warning]")
            return False
        
        # Determine available editors
        editors = ["nano", "vim", "vi"]
        available_editor = None
        
        for editor in editors:
            try:
                result = self.bash_runner.run_command(f"which {editor}")
                if result.returncode == 0:
                    available_editor = editor
                    break
            except:
                pass
        
        if not available_editor:
            self.console.print("[warning]No text editor found. Installing nano...[/warning]")
            self.bash_runner.run_command("apt install -y nano")
            available_editor = "nano"
        
        # Display file content
        with open(file_path, 'r') as f:
            content = f.read()
        
        self.console.print(f"\n[title]Current content of {os.path.basename(file_path)}:[/title]")
        self.console.print(Syntax(content, "ini"))
        
        # Offer to edit
        if Confirm.ask("\nEdit this file?", default=True):
            subprocess.run([available_editor, file_path])
            self.console.print("[success]File saved.[/success]")
            return True
        
        return False
    
    def manage_maps(self, port):
        """Install or update maps"""
        # Find server
        servers = self.get_installed_servers()
        server = next((s for s in servers if s['port'] == port), None)
        
        if not server:
            self.console.print(f"[warning]Server on port {port} not found.[/warning]")
            return False
        
        self.console.clear()
        self.console.print(Panel.fit(f"[title]Map Management (Port {port})[/title]", border_style="blue"))
        
        self.console.print("\n[title]Options:[/title]")
        self.console.print("[1] Install standard map pack")
        self.console.print("[2] Install custom map")
        self.console.print("[3] View installed maps")
        self.console.print("[4] Back")
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4"], default="4")
        
        if choice == "4":
            return False
        
        if choice == "1":
            from lib.installer import Installer
            installer = Installer(None, self.console)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("[green]Installing maps...", total=100)
                installer._install_maps(server['dir'], task, progress)
            
            self.console.print("[success]Standard map pack installed.[/success]")
            
        elif choice == "2":
            # Install custom map
            map_url = Prompt.ask("Enter map download URL")
            map_name = Prompt.ask("Enter map filename (e.g. map_name.pk3)")
            
            try:
                maps_dir = f"{server['dir']}/etmain"
                self.bash_runner.run_command(f"wget -q -O '{maps_dir}/{map_name}' '{map_url}'")
                self.console.print(f"[success]Map {map_name} installed successfully.[/success]")
            except Exception as e:
                self.console.print(f"[danger]Error downloading map: {e}[/danger]")
        
        elif choice == "3":
            # View installed maps
            maps_dir = f"{server['dir']}/etmain"
            maps = [f for f in os.listdir(maps_dir) if f.endswith('.pk3')]
            
            if not maps:
                self.console.print("[warning]No maps found.[/warning]")
                return False
            
            self.console.clear()
            self.console.print(Panel.fit("[title]Installed Maps[/title]", border_style="blue"))
            
            table = Table(title=f"Maps in {maps_dir}")
            table.add_column("Name", style="cyan")
            table.add_column("Size", style="green")
            
            for map_file in sorted(maps):
                size = os.path.getsize(os.path.join(maps_dir, map_file))
                size_str = self._format_size(size)
                table.add_row(map_file, size_str)
            
            self.console.print(table)
            
            self.console.print("\n[info]Press Enter to continue...[/info]")
            input()
        
        return True
    
    def _format_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"