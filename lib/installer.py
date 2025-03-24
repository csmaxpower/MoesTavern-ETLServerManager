import os
import shutil
import subprocess
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel

from utils.permissions import PermissionsManager
from utils.bash_runner import BashRunner
from lib.system_service import SystemServiceManager
from utils.firewall import FirewallManager

class Installer:
    def __init__(self, config_manager, console):
        self.config_manager = config_manager
        self.console = console
        self.bash = BashRunner(console)
        self.permissions = PermissionsManager(console)
        self.services = SystemServiceManager(console)
        self.firewall = FirewallManager(console)
    
    def install_server(self, config):
        """Install a new ET Legacy server"""
        self.console.clear()
        self.console.print(Panel.fit(
            f"[title]Installing ET Legacy Server: {config['servername']}[/title]",
            border_style="blue"
        ))
        
        # Create directory structure
        port = config['port']
        install_dir = config['installDir']
        server_dir = f"{install_dir}/et/{port}"
        
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
            self.permissions.setup_etl_group()
            
            # Create directories
            progress.update(prepare_task, advance=20, description="[green]Creating directories...")
            os.makedirs(server_dir, exist_ok=True)
            os.makedirs(f"{server_dir}/etmain", exist_ok=True)
            os.makedirs(f"{server_dir}/legacy", exist_ok=True)
            
            # Update system packages
            progress.update(prepare_task, advance=40, description="[green]Updating system packages...")
            self.bash.run_command("apt update")
            
            # Install dependencies
            progress.update(prepare_task, advance=30, description="[green]Installing dependencies...")
            self.bash.run_command("apt install -y unzip wget")
            
            progress.update(prepare_task, completed=100)
            
            # Step 2: Download and install ET Legacy
            install_task = progress.add_task("[green]Downloading and installing ET Legacy...", total=100)
            
            # Download installer
            progress.update(install_task, advance=10, description="[green]Downloading installer...")
            from lib.download_manager import DownloadManager
            dm = DownloadManager(self.console)
            installer_path = dm.download_version(config['version'])
            
            # Run installer
            progress.update(install_task, advance=40, description="[green]Running installer...")
            result = self.bash.run_command(f"chmod +x {installer_path} && {installer_path} --target-directory={server_dir}")
            
            if result.returncode != 0:
                self.console.print(f"[danger]Error running installer: {result.stderr}[/danger]")
                return False
            
            # Download configuration files
            progress.update(install_task, advance=30, description="[green]Configuring server...")
            self._configure_server(config, server_dir)
            
            progress.update(install_task, completed=100)
            
            # Step 3: Install maps if requested
            if config.get('install_maps', True):
                maps_task = progress.add_task("[green]Installing maps...", total=100)
                self._install_maps(server_dir, maps_task, progress)
            
            # Step 4: Create start script
            service_task = progress.add_task("[green]Setting up system services...", total=100)
            
            progress.update(service_task, advance=30, description="[green]Creating start script...")
            self._create_start_script(server_dir, port)
            
            # Step 5: Setup system services
            progress.update(service_task, advance=40, description="[green]Creating systemd services...")
            self.services.configure_etl_services(install_dir, port, server_dir)
            
            # Step 6: Setup FTP if needed
            if config.get('ftpuser'):
                progress.update(service_task, advance=20, description="[green]Setting up FTP access...")
                self._setup_ftp
                # Step 6: Setup FTP if needed
            if config.get('ftpuser'):
                progress.update(service_task, advance=20, description="[green]Setting up FTP access...")
                self._setup_ftp(config['ftpuser'], install_dir)
            
            # Step 7: Configure firewall if requested
            if config.get('configure_firewall', True):
                progress.update(service_task, advance=10, description="[green]Configuring firewall...")
                self.firewall.configure_for_server(port)
            
            progress.update(service_task, completed=100)
            
            # Step 8: Set permissions
            perm_task = progress.add_task("[green]Setting permissions...", total=100)
            self.permissions.set_file_permissions(install_dir)
            progress.update(perm_task, completed=100)
            
            # Step 9: Start server
            start_task = progress.add_task("[green]Starting server...", total=100)
            self.services.start_server(port)
            progress.update(start_task, completed=100)
        
        # Display completion message
        self.console.print(Panel.fit(
            f"[success]ET Legacy Server Installation Complete![/success]\n\n"
            f"Server Name: {config['servername']}\n"
            f"Port: {port}\n"
            f"Installation Directory: {server_dir}\n\n"
            f"You can manage this server through this tool or use the following commands:\n"
            f"- Start: sudo systemctl start etlserver-{port}.service\n"
            f"- Stop: sudo systemctl stop etlserver-{port}.service\n"
            f"- Status: sudo systemctl status etlserver-{port}.service",
            title="Installation Complete",
            border_style="green"
        ))
        
        return True
    
    def update_server(self, server_info, version_info):
        """Update an existing ET Legacy server"""
        port = server_info['port']
        install_dir = server_info['installDir']
        server_dir = f"{install_dir}/et/{port}"
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        ) as progress:
            # Step 1: Backup current configuration
            backup_task = progress.add_task("[green]Backing up current configuration...", total=100)
            
            # Create backup directory
            backup_dir = f"{server_dir}_backup_{int(time.time())}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup config files
            progress.update(backup_task, advance=50, description="[green]Copying configuration files...")
            for config_file in ['etl_server.cfg', 'configs', 'mapscripts']:
                src_path = os.path.join(server_dir, 'etmain' if config_file == 'etl_server.cfg' else 'legacy', config_file)
                if os.path.exists(src_path):
                    dst_path = os.path.join(backup_dir, config_file)
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
            
            progress.update(backup_task, completed=100)
            
            # Step 2: Download and install new version
            install_task = progress.add_task("[green]Downloading and installing new version...", total=100)
            
            # Download installer
            progress.update(install_task, advance=20, description="[green]Downloading installer...")
            from lib.download_manager import DownloadManager
            dm = DownloadManager(self.console)
            installer_path = dm.download_version(version_info)
            
            # Rename current directory
            temp_dir = f"{server_dir}_old"
            os.rename(server_dir, temp_dir)
            
            # Run installer for new version
            progress.update(install_task, advance=40, description="[green]Running installer...")
            result = self.bash.run_command(f"chmod +x {installer_path} && {installer_path} --target-directory={server_dir}")
            
            if result.returncode != 0:
                self.console.print(f"[danger]Error running installer: {result.stderr}[/danger]")
                # Restore old directory
                os.rename(temp_dir, server_dir)
                return False
            
            # Restore configs from backup
            progress.update(install_task, advance=40, description="[green]Restoring configuration...")
            for config_file in ['etl_server.cfg', 'configs', 'mapscripts']:
                src_path = os.path.join(backup_dir, config_file)
                if os.path.exists(src_path):
                    dst_path = os.path.join(server_dir, 'etmain' if config_file == 'etl_server.cfg' else 'legacy', config_file)
                    if os.path.isdir(src_path):
                        if os.path.exists(dst_path):
                            shutil.rmtree(dst_path)
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
            
            # Copy any custom maps from old installation
            old_maps_dir = os.path.join(temp_dir, 'etmain')
            new_maps_dir = os.path.join(server_dir, 'etmain')
            if os.path.exists(old_maps_dir):
                for map_file in os.listdir(old_maps_dir):
                    if map_file.endswith('.pk3') and not os.path.exists(os.path.join(new_maps_dir, map_file)):
                        shutil.copy2(os.path.join(old_maps_dir, map_file), os.path.join(new_maps_dir, map_file))
            
            # Update start script
            self._create_start_script(server_dir, port)
            
            # Clean up old directory
            shutil.rmtree(temp_dir)
            
            progress.update(install_task, completed=100)
            
            # Step 3: Set permissions
            perm_task = progress.add_task("[green]Setting permissions...", total=100)
            self.permissions.set_file_permissions(install_dir)
            progress.update(perm_task, completed=100)
        
        # Update server info with new version
        server_info['version'] = version_info['version']
        
        # Display completion message
        self.console.print(Panel.fit(
            f"[success]ET Legacy Server Update Complete![/success]\n\n"
            f"Server Name: {server_info['name']}\n"
            f"Port: {port}\n"
            f"New Version: {version_info['version']}\n\n"
            f"Backup saved to: {backup_dir}",
            title="Update Complete",
            border_style="green"
        ))
        
        return True
    
    def _configure_server(self, config, server_dir):
        """Configure server files with user settings"""
        # Update server config file
        etl_server_cfg = f"{server_dir}/etmain/etl_server.cfg"
        if os.path.exists(etl_server_cfg):
            with open(etl_server_cfg, 'r') as f:
                cfg_content = f.read()
            
            # Replace configuration values
            replacements = {
                'set sv_hostname\\s+".*?"': f'set sv_hostname "{config["servername"]}"',
                'set g_password\\s+".*?"': f'set g_password "{config["g_password"]}"',
                'set sv_maxclients\\s+".*?"': f'set sv_maxclients "{config["sv_maxclients"]}"',
                'set sv_privateclients\\s+".*?"': f'set sv_privateclients "{config["sv_privateclients"]}"',
                'set sv_privatepassword\\s+".*?"': f'set sv_privatepassword "{config.get("sv_privatepassword", "")}"',
                'set rconpassword\\s+".*?"': f'set rconpassword "{config["rconpassword"]}"',
                'set refereePassword\\s+".*?"': f'set refereePassword "{config["refereepassword"]}"',
                'set ShoutcastPassword\\s+".*?"': f'set ShoutcastPassword "{config["ShoutcastPassword"]}"',
                'set sv_wwwBaseURL\\s+".*?"': f'set sv_wwwBaseURL "{config.get("sv_wwwBaseURL", "")}"',
                'set sv_hidden\\s+".*?"': 'set sv_hidden "0"',
                'set net_port\\s+".*?"': f'set net_port "{config["port"]}"'
            }
            
            for pattern, replacement in replacements.items():
                cfg_content = re.sub(pattern, replacement, cfg_content)
            
            with open(etl_server_cfg, 'w') as f:
                f.write(cfg_content)
    
    def _install_maps(self, server_dir, task_id, progress):
        """Install additional maps"""
        maps_url_base = "http://moestavern.site.nfoservers.com/downloads/et/etmain/"
        maps_list = [
            "adlernest.pk3", "etl_adlernest_v4.pk3", "badplace4_rc.pk3", "etl_bergen_v9.pk3",
            "braundorf_b4.pk3", "bremen_b3.pk3", "crevasse_b3.pk3", "ctf_multi.pk3",
            "decay_sw.pk3", "element_b4_1.pk3", "erdenberg_t2.pk3", "et_beach.pk3",
            "et_brewdog_b6.pk3", "et_headshot.pk3", "et_headshot2_b2.pk3", "et_ice.pk3",
            "etl_ice_v12.pk3", "et_ufo_final.pk3", "frostbite.pk3", "etl_frostbite_v17.pk3",
            "karsiah_te2.pk3", "missile_b3.pk3", "mp_sillyctf.pk3", "osiris_final.pk3",
            "reactor_final.pk3", "rifletennis_te.pk3", "rifletennis_te2.pk3", "sos_secret_weapon.pk3",
            "sp_delivery_te.pk3", "etl_sp_delivery_v5.pk3", "supply.pk3", "etl_supply_v14.pk3",
            "sw_battery.pk3", "sw_goldrush_te.pk3", "sw_oasis_b3.pk3", "tc_base.pk3",
            "te_escape2.pk3", "te_escape2_fixed.pk3", "te_valhalla.pk3", "venice_ne4.pk3"
        ]
        
        maps_dir = f"{server_dir}/etmain"
        total_maps = len(maps_list)
        
        progress.update(task_id, total=total_maps)
        
        for i, map_file in enumerate(maps_list):
            map_url = f"{maps_url_base}{map_file}"
            progress.update(task_id, advance=1, description=f"[green]Downloading map {i+1}/{total_maps}: {map_file}")
            
            try:
                # Download the map
                result = self.bash.run_command(f"wget -q -O '{maps_dir}/{map_file}' '{map_url}'")
                
                if result.returncode != 0:
                    self.console.print(f"[warning]Warning: Failed to download {map_file}[/warning]")
            except Exception as e:
                self.console.print(f"[warning]Error downloading {map_file}: {e}[/warning]")
        
        progress.update(task_id, completed=total_maps)
    
    def _create_start_script(self, server_dir, port):
        """Create the server start script"""
        start_script = f"{server_dir}/etl_start.sh"
        
        with open(start_script, 'w') as f:
            f.write(f"""#!/bin/bash

DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" >/dev/null 2>&1 && pwd )"
"${{DIR}}/etlded.x86_64" \\
    +set dedicated 2 \\
    +set vm_game 0 \\
    +set net_port {port} \\
    +set fs_game legacy \\
    +set fs_basepath "${{DIR}}" \\
    +set fs_homepath "${{DIR}}" \\
    +exec etl_server.cfg
""")
        
        os.chmod(start_script, 0o755)
    
    def _setup_ftp(self, username, install_dir):
        """Setup VSFTPD for server access"""
        # Install VSFTPD if not already installed
        self.bash.run_command("apt install -y vsftpd")
        
        # Create FTP configuration
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
            self.bash.run_command(f"id -u {username}")
        except:
            self.bash.run_command(f"useradd -m {username}")
        
        # Set user password
        self.console.print("[info]Set password for FTP user:[/info]")
        self.bash.run_command(f"passwd {username}", interactive=True)
        
        # Add user to etusers group
        self.bash.run_command(f"usermod -aG etusers {username}")
        
        # Disable SSH access for FTP user
        with open('/etc/ssh/sshd_config', 'a') as f:
            f.write(f"\nDenyUsers {username}\n")
        
        self.bash.run_command("systemctl restart sshd")
        self.bash.run_command("systemctl restart vsftpd")