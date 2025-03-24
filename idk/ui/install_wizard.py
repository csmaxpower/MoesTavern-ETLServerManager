import os
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm

class InstallWizard:
    def __init__(self, console, config_manager, download_manager):
        self.console = console
        self.config_manager = config_manager
        self.download_manager = download_manager
        self.config = {}
    
    def run(self):
        """Run the installation wizard"""
        self.console.clear()
        self.console.print(Panel.fit(
            "[title]ET Legacy Server Installation Wizard[/title]\n"
            "This wizard will guide you through the installation of a new ET Legacy server.",
            border_style="blue"
        ))
        
        # Check if user wants to use an env file
        if Confirm.ask("Do you want to use an environment file for configuration?", default=False):
            env_path = Prompt.ask("Enter the path to your .env file")
            if os.path.exists(env_path):
                self.config = self.config_manager.load_env_file(env_path)
                self.console.print("[success]Configuration loaded from environment file.[/success]")
            else:
                self.console.print("[warning]Environment file not found. Proceeding with manual configuration.[/warning]")
        
        # Step 1: Server Information
        self.console.print("\n[title]Step 1: Server Information[/title]")
        
        # Server name (with default from env if available)
        self.config["servername"] = Prompt.ask(
            "Enter server name (with color codes if desired)",
            default=self.config.get("servername", "^1ET ^2Legacy ^3Server")
        )
        
        # Port number
        self.config["port"] = IntPrompt.ask(
            "Enter server port",
            default=int(self.config.get("port", 27960))
        )
        
        # Max clients
        self.config["sv_maxclients"] = IntPrompt.ask(
            "Enter maximum number of clients",
            default=int(self.config.get("sv_maxclients", 16))
        )
        
        # Game password
        self.config["g_password"] = Prompt.ask(
            "Enter game password (leave empty for no password)",
            default=self.config.get("g_password", ""),
            password=True
        )
        
        # Private slots
        self.config["sv_privateclients"] = IntPrompt.ask(
            "Enter number of private client slots",
            default=int(self.config.get("sv_privateclients", 0))
        )
        
        if int(self.config["sv_privateclients"]) > 0:
            self.config["sv_privatepassword"] = Prompt.ask(
                "Enter private slot password",
                default=self.config.get("sv_privatepassword", ""),
                password=True
            )
        
        # Admin passwords
        self.config["rconpassword"] = Prompt.ask(
            "Enter RCON password",
            default=self.config.get("rconpassword", ""),
            password=True
        )
        
        self.config["refereepassword"] = Prompt.ask(
            "Enter referee password",
            default=self.config.get("refereepassword", ""),
            password=True
        )
        
        self.config["ShoutcastPassword"] = Prompt.ask(
            "Enter shoutcast password",
            default=self.config.get("ShoutcastPassword", ""),
            password=True
        )
        
        # WWW URL
        self.config["sv_wwwBaseURL"] = Prompt.ask(
            "Enter base URL for file downloads (or leave empty)",
            default=self.config.get("sv_wwwBaseURL", "")
        )
        
        # Step 2: Installation Options
        self.console.print("\n[title]Step 2: Installation Options[/title]")
        
        # Installation directory
        self.config["installDir"] = Prompt.ask(
            "Enter installation directory",
            default=self.config.get("installDir", "/home/etlegacy")
        )
        
        # FTP username
        self.config["ftpuser"] = Prompt.ask(
            "Enter FTP username (leave empty to skip FTP setup)",
            default=self.config.get("ftpuser", "")
        )
        
        # Step 3: Version Selection
        self.console.print("\n[title]Step 3: Version Selection[/title]")
        self.console.print("Fetching available versions...")
        
        try:
            versions = self.download_manager.get_available_versions()
            
            if not versions:
                self.console.print("[warning]No versions available. Please check your internet connection.[/warning]")
                return None
            
            self.console.print("\nAvailable versions:")
            for i, version in enumerate(versions, 1):
                self.console.print(f"[{i}] {version['name']} ({version['version']})")
            
            version_choice = IntPrompt.ask(
                "Select version to install",
                default=1,
                choices=[str(i) for i in range(1, len(versions) + 1)]
            )
            
            self.config["version"] = versions[version_choice - 1]
            
        except Exception as e:
            self.console.print(f"[danger]Error fetching versions: {e}[/danger]")
            return None
        
        # Step 4: Additional Options
        self.console.print("\n[title]Step 4: Additional Options[/title]")
        
        # Install maps
        self.config["install_maps"] = Confirm.ask(
            "Do you want to install additional maps?",
            default=True
        )
        
        # Configure firewall
        self.config["configure_firewall"] = Confirm.ask(
            "Do you want to configure the firewall for this server?",
            default=True
        )
        
        # Review configuration
        self.console.clear()
        self.console.print(Panel.fit("[title]Configuration Review[/title]", border_style="blue"))
        
        self.console.print("\n[title]Server Information:[/title]")
        self.console.print(f"Server Name: {self.config['servername']}")
        self.console.print(f"Port: {self.config['port']}")
        self.console.print(f"Max Clients: {self.config['sv_maxclients']}")
        self.console.print(f"Private Slots: {self.config['sv_privateclients']}")
        
        self.console.print("\n[title]Installation Information:[/title]")
        self.console.print(f"Install Directory: {self.config['installDir']}")
        self.console.print(f"Version: {self.config['version']['name']}")
        self.console.print(f"Install Maps: {'Yes' if self.config['install_maps'] else 'No'}")
        self.console.print(f"Configure Firewall: {'Yes' if self.config['configure_firewall'] else 'No'}")
        
        if Confirm.ask("\nProceed with installation?", default=True):
            return self.config
        else:
            self.console.print("[warning]Installation cancelled.[/warning]")
            return None