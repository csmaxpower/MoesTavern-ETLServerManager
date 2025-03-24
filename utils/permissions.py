import os
import subprocess
import grp

class PermissionsManager:
    def __init__(self, console):
        self.console = console
    
    def setup_etl_group(self):
        """Create etusers group if it doesn't exist and add current user"""
        try:
            # Check if group exists
            try:
                grp.getgrnam("etusers")
                self.console.print("[info]Group 'etusers' already exists.[/info]")
            except KeyError:
                # Create group
                subprocess.run(["groupadd", "etusers"], check=True)
                self.console.print("[success]Created 'etusers' group.[/success]")
            
            # Add current user to group
            current_user = os.getenv("SUDO_USER", os.getenv("USER"))
            subprocess.run(["usermod", "-aG", "etusers", current_user], check=True)
            self.console.print(f"[success]Added user '{current_user}' to 'etusers' group.[/success]")
            
            # Add root to group
            subprocess.run(["usermod", "-aG", "etusers", "root"], check=True)
            
            return True
        except Exception as e:
            self.console.print(f"[danger]Error setting up etusers group: {e}[/danger]")
            return False
    
    def set_file_permissions(self, install_dir):
        """Set correct permissions for ET Legacy files"""
        try:
            # Set group ownership
            subprocess.run(["chgrp", "-R", "etusers", f"{install_dir}/et"], check=True)
            
            # Set directory permissions
            for root, dirs, files in os.walk(f"{install_dir}/et"):
                # Set directories to 775 (rwxrwxr-x)
                for d in dirs:
                    path = os.path.join(root, d)
                    os.chmod(path, 0o775)
                    # Set setgid bit on directories
                    mode = os.stat(path).st_mode
                    os.chmod(path, mode | 0o2000)  # Set the setgid bit
                
                # Set files to 664 (rw-rw-r--)
                for f in files:
                    path = os.path.join(root, f)
                    os.chmod(path, 0o664)
            
            # Make executable files executable (775)
            for ext in ['.sh', '.x86_64']:
                result = subprocess.run(
                    f"find {install_dir}/et -name '*{ext}' -type f -exec chmod 775 {{}} \\;",
                    shell=True, 
                    check=True
                )
            
            self.console.print("[success]File permissions set successfully.[/success]")
            return True
        except Exception as e:
            self.console.print(f"[danger]Error setting file permissions: {e}[/danger]")
            return False