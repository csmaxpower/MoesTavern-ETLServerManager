import os

class SystemServiceManager:
    def __init__(self, console):
        self.console = console
        self.bash_runner = BashRunner(console)
    
    def configure_etl_services(self, install_dir, port, server_dir):
        """Configure systemd services for ET Legacy server"""
        try:
            # Create server service file
            server_service = f"""[Unit]
Description=Wolfenstein Enemy Territory Server (Port {port})
After=network.target

[Service]
ExecStart={server_dir}/etl_start.sh
Restart=always
User=root

[Install]
WantedBy=network-up.target
"""
            
            # Create restart service file
            restart_service = f"""[Unit]
Description=Restarts Enemy Territory Legacy server service (Port {port})

[Service]
ExecStart=/bin/systemctl restart etlserver-{port}.service
User=root
"""
            
            # Create monitor timer file
            monitor_timer = f"""[Unit]
Description=This timer restarts the Enemy Territory Legacy server service etlserver-{port}.service every day at 5am
Requires=etlrestart-{port}.service

[Timer]
Unit=etlrestart-{port}.service
OnCalendar=*-*-* 5:00:00

[Install]
WantedBy=timers.target
"""
            
            # Write service files
            with open(f"/etc/systemd/system/etlserver-{port}.service", "w") as f:
                f.write(server_service)
            
            with open(f"/etc/systemd/system/etlrestart-{port}.service", "w") as f:
                f.write(restart_service)
            
            with open(f"/etc/systemd/system/etlmonitor-{port}.timer", "w") as f:
                f.write(monitor_timer)
            
            # Reload systemd
            self.bash_runner.run_command("systemctl daemon-reload")
            
            # Enable services
            self.bash_runner.run_command(f"systemctl enable etlserver-{port}.service")
            self.bash_runner.run_command(f"systemctl enable etlmonitor-{port}.timer")
            
            self.console.print(f"[success]System services configured for port {port}.[/success]")
            return True
        except Exception as e:
            self.console.print(f"[danger]Error configuring system services: {e}[/danger]")
            return False
    
    def start_server(self, port):
        """Start the server"""
        try:
            self.bash_runner.run_command(f"systemctl start etlserver-{port}.service")
            self.bash_runner.run_command(f"systemctl start etlmonitor-{port}.timer")
            
            # Check status
            result = self.bash_runner.run_command(f"systemctl is-active etlserver-{port}.service")
            if result.stdout.strip() == "active":
                self.console.print(f"[success]Server on port {port} started successfully.[/success]")
                return True
            else:
                self.console.print(f"[warning]Server may not have started correctly. Check status with: systemctl status etlserver-{port}.service[/warning]")
                return False
        except Exception as e:
            self.console.print(f"[danger]Error starting server: {e}[/danger]")
            return False
    
    def stop_server(self, port):
        """Stop the server"""
        try:
            self.bash_runner.run_command(f"systemctl stop etlserver-{port}.service")
            
            # Check status
            result = self.bash_runner.run_command(f"systemctl is-active etlserver-{port}.service")
            if result.stdout.strip() != "active":
                self.console.print(f"[success]Server on port {port} stopped successfully.[/success]")
                return True
            else:
                self.console.print(f"[warning]Server may not have stopped correctly. Check status with: systemctl status etlserver-{port}.service[/warning]")
                return False
        except Exception as e:
            self.console.print(f"[danger]Error stopping server: {e}[/danger]")
            return False
    
    def restart_server(self, port):
        """Restart the server"""
        try:
            self.bash_runner.run_command(f"systemctl restart etlserver-{port}.service")
            
            # Check status
            result = self.bash_runner.run_command(f"systemctl is-active etlserver-{port}.service")
            if result.stdout.strip() == "active":
                self.console.print(f"[success]Server on port {port} restarted successfully.[/success]")
                return True
            else:
                self.console.print(f"[warning]Server may not have restarted correctly. Check status with: systemctl status etlserver-{port}.service[/warning]")
                return False
        except Exception as e:
            self.console.print(f"[danger]Error restarting server: {e}[/danger]")
            return False