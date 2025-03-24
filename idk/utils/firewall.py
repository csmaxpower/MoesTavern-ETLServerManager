import subprocess

class FirewallManager:
    def __init__(self, console):
        self.console = console
        self.bash_runner = BashRunner(console)
    
    def configure(self):
        """Configure firewall settings"""
        self.console.clear()
        self.console.print(Panel.fit("[title]Firewall Configuration[/title]", border_style="blue"))
        
        # Check if UFW is installed
        try:
            self.bash_runner.run_command("which ufw")
        except:
            self.console.print("[info]UFW not found. Installing...[/info]")
            self.bash_runner.run_command("apt install -y ufw")
        
        # Get list of installed servers
        from lib.server_manager import ServerManager
        server_manager = ServerManager(self.console)
        installed_servers = server_manager.get_installed_servers()
        
        # Configure common rules
        self.console.print("\n[info]Configuring common firewall rules...[/info]")
        
        # Allow SSH
        self.bash_runner.run_command("ufw allow OpenSSH")
        
        # Configure FTP if needed
        if Confirm.ask("Do you want to configure firewall for FTP access?", default=True):
            self.bash_runner.run_command("ufw allow 20/tcp")
            self.bash_runner.run_command("ufw allow 21/tcp")
            self.bash_runner.run_command("ufw allow 990/tcp")
            self.bash_runner.run_command("ufw allow 40000:50000/tcp")
            self.console.print("[success]FTP firewall rules configured.[/success]")
        
        # Configure server ports
        if installed_servers:
            self.console.print("\n[info]Configuring firewall rules for installed servers...[/info]")
            
            for server in installed_servers:
                if Confirm.ask(f"Allow port {server['port']} for server '{server['name']}'?", default=True):
                    self.configure_for_server(server['port'])
        
        # Configure additional ports
        if Confirm.ask("\nDo you want to configure firewall for additional server ports?", default=False):
            while True:
                port = IntPrompt.ask("Enter port number (or 0 to finish)")
                if port == 0:
                    break
                self.configure_for_server(port)
        
        # Enable firewall if not already enabled
        status = self.bash_runner.run_command("ufw status")
        if "inactive" in status.stdout:
            if Confirm.ask("\nEnable firewall now?", default=True):
                self.bash_runner.run_command("echo y | ufw enable")
                self.console.print("[success]Firewall enabled successfully.[/success]")
        else:
            self.console.print("[info]Firewall is already enabled.[/info]")
        
        self.console.print("\n[success]Firewall configuration complete.[/success]")
        input("Press Enter to continue...")
    
    def configure_for_server(self, port):
        """Configure firewall for a specific server port"""
        try:
            # Allow UDP traffic for ET server port
            self.bash_runner.run_command(f"ufw allow {port}/udp")
            self.console.print(f"[success]Allowed UDP traffic on port {port}.[/success]")
            return True
        except Exception as e:
            self.console.print(f"[danger]Error configuring firewall for port {port}: {e}[/danger]")
            return False