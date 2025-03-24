#!/bin/bash
# ET Legacy Server Installer (Self-contained)

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "ET Legacy Server Installer"
echo "-------------------------"

# Install required packages
echo "Installing required packages..."
apt update
apt install -y python3 python3-venv python3-pip wget unzip vsftpd

# Create a virtual environment
echo "Setting up Python virtual environment..."
VENV_DIR="/tmp/etlegacy-venv"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Install Python dependencies in the virtual environment
echo "Installing Python dependencies..."
pip install rich requests beautifulsoup4

# Create a Python script
echo "Creating installer script..."
SCRIPT_PATH="/tmp/etlegacy_installer.py"

cat > "$SCRIPT_PATH" << 'PYTHONEOF'
#!/usr/bin/env python3

import os
import sys
import re
import subprocess
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, IntPrompt, Confirm

console = Console()

class DownloadManager:
    def __init__(self):
        self.workflow_files_url = "https://etlegacy.com/workflow-files"
        self.download_base_url = "https://etlegacy.com/download"
        self.temp_dir = "/tmp/etlegacy-installer"
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def get_available_versions(self):
        """Get list of available ET Legacy versions"""
        versions = []
        
        # Get development versions
        try:
            dev_versions = self._get_dev_versions()
            versions.extend(dev_versions)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch development versions: {e}[/yellow]")
        
        # Add fallback version if no versions found
        if not versions:
            versions.append({
                "name": "Fallback Dev Version 2.83.2",
                "url": "https://www.etlegacy.com/workflow-files/dl/6f90ecff1ed0e041ddc1f2148d30752f314209a3/lnxx8664/etlegacy-v2.83.2-74-g6f90ecf-x86_64.sh",
                "version": "2.83.2",
                "is_stable": False
            })
        
        return versions
    
    def _get_dev_versions(self):
        """Get development versions from workflow files page"""
        try:
            response = requests.get(self.workflow_files_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            versions = []
            # Look for Linux x86_64 .sh files
            download_links = soup.find_all("a", href=re.compile(r"/workflow-files/dl/.*?/lnxx8664/.*?\.sh"))
            
            for link in download_links:
                url = f"https://etlegacy.com{link['href']}"
                version_match = re.search(r"etlegacy-v(\d+\.\d+\.\d+(?:-\d+-g[a-f0-9]+)?)", link.text)
                if version_match:
                    version_str = version_match.group(1)
                    versions.append({
                        "name": f"Development {version_str}",
                        "url": url,
                        "version": version_str,
                        "is_stable": False
                    })
            
            return versions
        except Exception as e:
            raise Exception(f"Error fetching development versions: {e}")
    
    def download_version(self, version_info):
        """Download the specified version"""
        filename = os.path.join(self.temp_dir, f"etlegacy-{version_info['version']}.sh")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task(f"Downloading {version_info['name']}", total=100)
            
            try:
                response = requests.get(version_info['url'], stream=True)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size:
                    progress.update(task, total=total_size)
                    
                downloaded = 0
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress.update(task, completed=downloaded)
                
                # Make the file executable
                os.chmod(filename, 0o755)
                progress.update(task, completed=100)
                return filename
            except Exception as e:
                console.print(f"[bold red]Error downloading: {e}[/bold red]")
                return None

class ETLegacyInstaller:
    def __init__(self):
        self.download_manager = DownloadManager()
        self.config = {
            'port': 27960,
            'servername': '^1ET ^2Legacy ^3Server',
            'installDir': '/root',
            'g_password': '',
            'sv_maxclients': 16,
            'sv_privateclients': 0,
            'sv_privatepassword': '',
            'rconpassword': 'admin',
            'refereepassword': 'referee',
            'ShoutcastPassword': 'shoutcast',
            'sv_wwwBaseURL': '',
            'ftpuser': ''
        }
    
    def run(self):
        """Main entry point for the installer"""
        console.clear()
        self.show_welcome()
        self.get_server_config()
        self.select_version()
        if self.confirm_installation():
            self.install_server()
    
    def show_welcome(self):
        """Show welcome message"""
        console.print(Panel.fit(
            "[bold blue]ET Legacy Server Installer[/bold blue]\n"
            "This will install an Enemy Territory Legacy server on your system.",
            border_style="blue"
        ))
    
    def get_server_config(self):
        """Get user input for server configuration"""
        console.print("\n[bold]Server Configuration[/bold]")
        
        # Ask if user wants to use an env file
        if Confirm.ask("Do you want to use an environment file for configuration?", default=False):
            env_path = Prompt.ask("Enter the path to your .env file")
            if os.path.exists(env_path):
                self.load_env_file(env_path)
                console.print("[green]Configuration loaded from environment file.[/green]")
            else:
                console.print("[yellow]Environment file not found. Proceeding with manual configuration.[/yellow]")
        
        # Server name
        self.config['servername'] = Prompt.ask(
            "Enter server name (with color codes if desired)",
            default=self.config['servername']
        )
        
        # Port number
        self.config['port'] = IntPrompt.ask(
            "Enter server port",
            default=self.config['port']
        )
        
        # Installation directory
        self.config['installDir'] = Prompt.ask(
            "Enter installation base directory",
            default=self.config['installDir']
        )
        
        # Max clients
        self.config['sv_maxclients'] = IntPrompt.ask(
            "Enter maximum number of clients",
            default=self.config['sv_maxclients']
        )
        
        # Game password
        self.config['g_password'] = Prompt.ask(
            "Enter game password (leave empty for no password)",
            default=self.config['g_password'],
            password=not self.config['g_password'] == ''
        )
        
        # RCON password
        self.config['rconpassword'] = Prompt.ask(
            "Enter RCON password",
            default=self.config['rconpassword'],
            password=not self.config['rconpassword'] == ''
        )
        
        # FTP user
        if Confirm.ask("Do you want to set up an FTP user for server management?", default=False):
            self.config['ftpuser'] = Prompt.ask("Enter FTP username")
        
        # Convert paths for consistent structure
        self.config['installDir'] = os.path.expanduser(self.config['installDir'])
        self.config['server_dir'] = f"{self.config['installDir']}/et/{self.config['port']}"
    
    def load_env_file(self, env_file):
        """Load configuration from environment file"""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        self.config[key] = value
        except Exception as e:
            console.print(f"[bold red]Error loading environment file: {e}[/bold red]")
    
    def select_version(self):
        """Select ET Legacy version to install"""
        console.print("\n[bold]Version Selection[/bold]")
        console.print("Fetching available versions...")
        
        versions = self.download_manager.get_available_versions()
        
        table = Table(title="Available Versions")
        table.add_column("#", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Type", style="yellow")
        
        for i, version in enumerate(versions, 1):
            table.add_row(
                str(i),
                version["version"],
                "Stable" if version["is_stable"] else "Development"
            )
        
        console.print(table)
        
        version_idx = IntPrompt.ask(
            "Select version to install",
            default=1,
            choices=[str(i) for i in range(1, len(versions) + 1)]
        )
        
        self.config['version'] = versions[version_idx - 1]
    
    def confirm_installation(self):
        """Confirm installation details"""
        console.clear()
        console.print(Panel.fit("[bold]Installation Review[/bold]", border_style="blue"))
        
        console.print("\n[bold]Server Information:[/bold]")
        console.print(f"Server Name: {self.config['servername']}")
        console.print(f"Port: {self.config['port']}")
        console.print(f"Max Clients: {self.config['sv_maxclients']}")
        
        console.print("\n[bold]Installation Information:[/bold]")
        console.print(f"Installation Directory: {self.config['server_dir']}")
        console.print(f"Version: {self.config['version']['name']}")
        console.print(f"FTP User: {self.config['ftpuser'] if self.config['ftpuser'] else 'None'}")
        
        return Confirm.ask("\nProceed with installation?", default=True)
    
    def run_command(self, command, capture_output=True, check=True, interactive=False):
        """Run a shell command and return the result"""
        try:
            if interactive:
                result = subprocess.run(command, shell=True)
                return result
            elif capture_output:
                result = subprocess.run(command, shell=True, check=check, 
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                       text=True)
                return result
            else:
                result = subprocess.run(command, shell=True, check=check)
                return result
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Command failed: {e}[/bold red]")
            console.print(f"[bold red]Error output: {e.stderr}[/bold red]")
            raise e
    
    def install_server(self):
        """Install ET Legacy server"""
        console.clear()
        console.print(Panel.fit(
            f"[bold blue]Installing ET Legacy Server on port {self.config['port']}[/bold blue]",
            border_style="blue"
        ))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        ) as progress:
            # Step 1: Prepare system
            prepare_task = progress.add_task("[green]Preparing system...", total=100)
            
            # Create etusers group
            progress.update(prepare_task, advance=10, description="[green]Creating etusers group...")
            try:
                # Check if group exists
                self.run_command("getent group etusers", check=False)
                console.print("[green]Group 'etusers' already exists.[/green]")
            except:
                self.run_command("groupadd etusers")
                console.print("[green]Created 'etusers' group.[/green]")
            
            # Add current user to group
            progress.update(prepare_task, advance=10, description="[green]Adding users to group...")
            self.run_command("usermod -aG etusers root")
            
            # Create directories
            progress.update(prepare_task, advance=20, description="[green]Creating directories...")
            os.makedirs(self.config['server_dir'], exist_ok=True)
            os.makedirs(f"{self.config['server_dir']}/etmain", exist_ok=True)
            os.makedirs(f"{self.config['server_dir']}/legacy", exist_ok=True)
            
            # Install dependencies
            progress.update(prepare_task, advance=60, description="[green]Installing dependencies...")
            self.run_command("apt install -y unzip wget vsftpd")
            progress.update(prepare_task, completed=100)
            
            # Step 2: Download and install ET Legacy
            install_task = progress.add_task("[green]Downloading and installing ET Legacy...", total=100)
            
            # Download installer
            progress.update(install_task, advance=10, description="[green]Downloading installer...")
            installer_path = self.download_manager.download_version(self.config['version'])
            
            if not installer_path:
                console.print("[bold red]Failed to download installer. Aborting.[/bold red]")
                return
            
            # Run installer
            progress.update(install_task, advance=40, description="[green]Running installer...")
            try:
                self.run_command(f"{installer_path} --target-directory={self.config['server_dir']}", capture_output=False)
            except Exception as e:
                console.print(f"[bold red]Error running installer: {e}[/bold red]")
                return
            
            # Configure server
            progress.update(install_task, advance=30, description="[green]Configuring server...")
            self.configure_server()
            
            # Download maps
            progress.update(install_task, advance=20, description="[green]Downloading maps...")
            self.install_maps()
            
            progress.update(install_task, completed=100)
            
            # Step 3: Create start script
            service_task = progress.add_task("[green]Setting up system services...", total=100)
            
            progress.update(service_task, advance=10, description="[green]Creating start script...")
            self.create_start_script()
            
            # Setup system services
            progress.update(service_task, advance=30, description="[green]Creating systemd services...")
            self.configure_system_services()
            
            # Setup FTP if needed
            if self.config['ftpuser']:
                progress.update(service_task, advance=30, description="[green]Setting up FTP access...")
                self.setup_ftp()
            else:
                progress.update(service_task, advance=30)
            
            # Configure firewall
            progress.update(service_task, advance=30, description="[green]Configuring firewall...")
            self.configure_firewall()
            
            progress.update(service_task, completed=100)
            
            # Set permissions
            perm_task = progress.add_task("[green]Setting permissions...", total=100)
            self.set_permissions()
            progress.update(perm_task, completed=100)
            
            # Start server
            start_task = progress.add_task("[green]Starting server...", total=100)
            self.start_server()
            progress.update(start_task, completed=100)
        
        # Display completion message
        console.print(Panel.fit(
            f"[bold green]ET Legacy Server Installation Complete![/bold green]\n\n"
            f"Server Name: {self.config['servername']}\n"
            f"Port: {self.config['port']}\n"
            f"Installation Directory: {self.config['server_dir']}\n\n"
            f"You can manage this server with the following commands:\n"
            f"- Start: sudo systemctl start etlserver-{self.config['port']}.service\n"
            f"- Stop: sudo systemctl stop etlserver-{self.config['port']}.service\n"
            f"- Status: sudo systemctl status etlserver-{self.config['port']}.service",
            title="Installation Complete",
            border_style="green"
        ))
    
    def configure_server(self):
        """Configure server files with user settings"""
        etl_server_cfg = f"{self.config['server_dir']}/etmain/etl_server.cfg"
        
        # Download a sample config if it doesn't exist
        if not os.path.exists(etl_server_cfg):
            self.run_command(f"wget -q https://raw.githubusercontent.com/etlegacy/etlegacy/master/misc/etmain/etl_server.cfg -O {etl_server_cfg}")
        
        with open(etl_server_cfg, 'r') as f:
            cfg_content = f.read()
        
        # Replace configuration values
        replacements = {
            'set sv_hostname\\s+".*?"': f'set sv_hostname "{self.config["servername"]}"',
            'set g_password\\s+".*?"': f'set g_password "{self.config["g_password"]}"',
            'set sv_maxclients\\s+".*?"': f'set sv_maxclients "{self.config["sv_maxclients"]}"',
            'set sv_privateclients\\s+".*?"': f'set sv_privateclients "{self.config["sv_privateclients"]}"',
            'set sv_privatepassword\\s+".*?"': f'set sv_privatepassword "{self.config.get("sv_privatepassword", "")}"',
            'set rconpassword\\s+".*?"': f'set rconpassword "{self.config["rconpassword"]}"',
            'set refereePassword\\s+".*?"': f'set refereePassword "{self.config["refereepassword"]}"',
            'set ShoutcastPassword\\s+".*?"': f'set ShoutcastPassword "{self.config["ShoutcastPassword"]}"',
            'set sv_wwwBaseURL\\s+".*?"': f'set sv_wwwBaseURL "{self.config.get("sv_wwwBaseURL", "")}"',
            'set sv_hidden\\s+".*?"': 'set sv_hidden "0"',
            'set net_port\\s+".*?"': f'set net_port "{self.config["port"]}"'
        }
        
        for pattern, replacement in replacements.items():
            cfg_content = re.sub(pattern, replacement, cfg_content)
        
        with open(etl_server_cfg, 'w') as f:
            f.write(cfg_content)
    
    def install_maps(self):
        """Install additional maps"""
        maps_url_base = "http://moestavern.site.nfoservers.com/downloads/et/etmain/"
        maps_list = [
            "adlernest.pk3", "badplace4_rc.pk3", "braundorf_b4.pk3", 
            "bremen_b3.pk3", "et_beach.pk3", "et_ice.pk3", "frostbite.pk3"
        ]
        
        maps_dir = f"{self.config['server_dir']}/etmain"
        
        for map_file in maps_list:
            map_url = f"{maps_url_base}{map_file}"
            try:
                self.run_command(f"wget -q -O '{maps_dir}/{map_file}' '{map_url}'")
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to download {map_file}: {e}[/yellow]")
    
    def create_start_script(self):
        """Create the server start script"""
        start_script = f"{self.config['server_dir']}/etl_start.sh"
        
        with open(start_script, 'w') as f:
            f.write(f"""#!/bin/bash

DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" >/dev/null 2>&1 && pwd )"
"${{DIR}}/etlded.x86_64" \\
    +set dedicated 2 \\
    +set vm_game 0 \\
    +set net_port {self.config['port']} \\
    +set fs_game legacy \\
    +set fs_basepath "${{DIR}}" \\
    +set fs_homepath "${{DIR}}" \\
    +exec etl_server.cfg
""")
        
        os.chmod(start_script, 0o755)
    
    def configure_system_services(self):
        """Configure systemd services for the server"""
        # Create server service file
        server_service = f"""[Unit]
Description=Wolfenstein Enemy Territory Server (Port {self.config['port']})
After=network.target

[Service]
ExecStart={self.config['server_dir']}/etl_start.sh
Restart=always
User=root

[Install]
WantedBy=network-up.target
"""
        
        # Create restart service file
        restart_service = f"""[Unit]
Description=Restarts Enemy Territory Legacy server service (Port {self.config['port']})

[Service]
ExecStart=/bin/systemctl restart etlserver-{self.config['port']}.service
User=root
"""
        
        # Create monitor timer file
        monitor_timer = f"""[Unit]
Description=This timer restarts the Enemy Territory Legacy server service etlserver-{self.config['port']}.service every day at 5am
Requires=etlrestart-{self.config['port']}.service

[Timer]
Unit=etlrestart-{self.config['port']}.service
OnCalendar=*-*-* 5:00:00

[Install]
WantedBy=timers.target
"""
        
        # Write service files
        with open(f"/etc/systemd/system/etlserver-{self.config['port']}.service", "w") as f:
            f.write(server_service)
        
        with open(f"/etc/systemd/system/etlrestart-{self.config['port']}.service", "w") as f:
            f.write(restart_service)
        
        with open(f"/etc/systemd/system/etlmonitor-{self.config['port']}.timer", "w") as f:
            f.write(monitor_timer)
        
        # Reload systemd
        self.run_command("systemctl daemon-reload")
        
        # Enable services
        self.run_command(f"systemctl enable etlserver-{self.config['port']}.service")
        self.run_command(f"systemctl enable etlmonitor-{self.config['port']}.timer")
    
    def setup_ftp(self):
        """Setup VSFTPD for server access"""
        if not self.config['ftpuser']:
            return
        
        # Configure VSFTPD
        vsftpd_conf = """# ET Legacy Server FTP Configuration
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=NO
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000
allow_writeable_chroot=YES
"""
        
        with open('/etc/vsftpd.conf', 'w') as f:
            f.write(vsftpd_conf)
        
        # Add user if it doesn't exist
        try:
            self.run_command(f"id -u {self.config['ftpuser']}", check=False)
        except:
            self.run_command(f"useradd -m {self.config['ftpuser']}")
        
        # Set user password
        console.print("[info]Set password for FTP user:[/info]")
        self.run_command(f"passwd {self.config['ftpuser']}", interactive=True)
        
        # Add user to etusers group
        self.run_command(f"usermod -aG etusers {self.config['ftpuser']}")
        
        # Disable SSH access for FTP user
        with open('/etc/ssh/sshd_config', 'a') as f:
            f.write(f"\nDenyUsers {self.config['ftpuser']}\n")
        
        self.run_command("systemctl restart sshd")
        self.run_command("systemctl restart vsftpd")
    
    def configure_firewall(self):
        """Configure firewall for server port"""
        try:
            # Check if ufw is installed
            self.run_command("which ufw", check=False)
            
            # Configure UFW
            self.run_command(f"ufw allow {self.config['port']}/udp")
            self.run_command("ufw allow OpenSSH")
            
            if self.config['ftpuser']:
                self.run_command("ufw allow 20/tcp")
                self.run_command("ufw allow 21/tcp")
                self.run_command("ufw allow 990/tcp")
                self.run_command("ufw allow 40000:50000/tcp")
            
            # Enable UFW if it's not already enabled
            status = self.run_command("ufw status")
            if "inactive" in status.stdout:
                self.run_command("echo y | ufw enable")
        except:
            console.print("[yellow]UFW firewall not installed. Skipping firewall configuration.[/yellow]")
    
    def set_permissions(self):
        """Set correct permissions for ET Legacy files"""
        try:
            # Set group ownership
            self.run_command(f"chgrp -R etusers {self.config['installDir']}/et")
            
            # Set directory permissions with find
            self.run_command(f"find {self.config['installDir']}/et -type d -exec chmod 775 {{}} \\;")
            self.run_command(f"find {self.config['installDir']}/et -type d -exec chmod g+s {{}} \\;")
            
            # Set file permissions with find
            self.run_command(f"find {self.config['installDir']}/et -type f -exec chmod 664 {{}} \\;")
            
            # Make executable files executable
            self.run_command(f"find {self.config['installDir']}/et -name '*.sh' -type f -exec chmod 775 {{}} \\;")
            self.run_command(f"find {self.config['installDir']}/et -name '*.x86_64' -type f -exec chmod 775 {{}} \\;")
        except Exception as e:
            console.print(f"[yellow]Warning: Error setting permissions: {e}[/yellow]")
    
    def start_server(self):
        """Start the server"""
        try:
            self.run_command(f"systemctl start etlserver-{self.config['port']}.service")
            self.run_command(f"systemctl start etlmonitor-{self.config['port']}.timer")
            
            # Check status
            time.sleep(2)  # Give the service a moment to start
            result = self.run_command(f"systemctl is-active etlserver-{self.config['port']}.service")
            if result.stdout.strip() == "active":
                console.print(f"[green]Server on port {self.config['port']} started successfully.[/green]")
                return True
            else:
                console.print(f"[yellow]Server may not have started correctly. Check status with: systemctl status etlserver-{self.config['port']}.service[/yellow]")
                return False
        except Exception as e:
            console.print(f"[red]Error starting server: {e}[/red]")
            return False

if __name__ == "__main__":
    installer = ETLegacyInstaller()
    installer.run()
    
PYTHONEOF

chmod +x "$SCRIPT_PATH"

# Run the installer with the virtual environment's Python
echo "Starting installer..."
"$VENV_DIR/bin/python" "$SCRIPT_PATH"

# Clean up
echo "Cleaning up..."
rm -rf "$VENV_DIR"

echo "Installation script completed."