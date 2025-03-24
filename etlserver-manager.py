import os
import sys
import logging
import requests
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from rich.logging import RichHandler
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("etlegacy-manager")

# Initialize Rich console
console = Console()

# Load environment variables
load_dotenv()

# Define constants
DEFAULT_DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", os.path.expanduser("~/etlegacy"))
ETLEGACY_STABLE_URL = os.getenv("ETLEGACY_STABLE_URL", "https://etlegacy.com/download")
ETLEGACY_DEV_URL = os.getenv("ETLEGACY_DEV_URL", "https://etlegacy.com/workflow-files")

class ServerType(Enum):
    COMPETITION = "competition"
    PUBLIC = "public"

class ETLegacyManager:
    """Main class for managing ET: Legacy servers"""
    
    def __init__(self):
        self.console = console
        
    def download_with_progress(self, url: str, destination: Path) -> bool:
        """
        Download a file with progress bar
        
        Args:
            url: URL to download
            destination: Destination path
            
        Returns:
            bool: True if download was successful
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))
            
            # Ensure parent directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Setup progress columns
            progress_columns = [
                TextColumn("[bold blue]{task.description}", justify="right"),
                BarColumn(bar_width=None),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TextColumn("•"),
                TimeElapsedColumn(),
                TextColumn("•"),
                TimeRemainingColumn(),
            ]
            
            # Download with progress bar
            with Progress(*progress_columns) as progress:
                download_task = progress.add_task(f"Downloading {destination.name}", total=total_size)
                
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            progress.update(download_task, advance=len(chunk))
            
            return True
            
        except Exception as e:
            self.console.print(f"[bold red]Error downloading file: {e}[/bold red]")
            log.error(f"Download failed: {e}")
            return False
    
    def get_stable_download_link(self) -> Optional[str]:
        """
        Get the stable download link from the ET: Legacy website
        
        Returns:
            Optional[str]: Download link or None if not found
        """
        try:
            response = requests.get(ETLEGACY_STABLE_URL)
            response.raise_for_status()
            
            # Find the download link for Linux x86_64
            # This is a simplified approach - might need refinement based on the actual website structure
            match = re.search(r'href="(https://etlegacy\.com/download/file/\d+)"', response.text)
            if match:
                return match.group(1)
            return None
            
        except Exception as e:
            self.console.print(f"[bold red]Error retrieving stable download link: {e}[/bold red]")
            log.error(f"Failed to retrieve stable download link: {e}")
            return None
    
    def get_dev_build_links(self) -> List[Dict[str, str]]:
        """
        Get the development build links from the ET: Legacy website
        
        Returns:
            List[Dict[str, str]]: List of build info with version, hash, and download link
        """
        builds = []
        try:
            response = requests.get(ETLEGACY_DEV_URL)
            response.raise_for_status()
            
            # Use BeautifulSoup to parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links to Linux x86_64 builds
            # This pattern might need adjustment based on the actual website structure
            for link in soup.find_all('a', href=re.compile(r'.*lnxx8664/etlegacy-v.*\.sh$')):
                href = link.get('href')
                # Extract version and hash from the URL
                # Example: etlegacy-v2.83.2-74-g6f90ecf-x86_64.sh
                match = re.search(r'etlegacy-v([\d\.\-]+)-(\w+)-x86_64\.sh', href)
                if match:
                    version = match.group(1)
                    commit_hash = match.group(2)
                    builds.append({
                        'version': version,
                        'hash': commit_hash,
                        'url': href,
                    })
            
            return builds[:4]  # Return at most 4 builds
            
        except Exception as e:
            self.console.print(f"[bold red]Error retrieving development build links: {e}[/bold red]")
            log.error(f"Failed to retrieve development build links: {e}")
            return []
    
    def install_server(self, server_type: ServerType) -> bool:
        """
        Install a new ET: Legacy server
        
        Args:
            server_type: Type of server to install
            
        Returns:
            bool: True if installation was successful
        """
        # Clear the screen
        self.console.clear()
        
        self.console.print(Panel(f"[bold yellow]Installing new {server_type.value.title()} Server[/bold yellow]"))
        
        # Get all available versions
        self.console.print("[bold blue]Retrieving available ET: Legacy versions...[/bold blue]")
        
        stable_link = self.get_stable_download_link()
        dev_builds = self.get_dev_build_links()
        
        if not stable_link and not dev_builds:
            self.console.print("[bold red]Failed to retrieve any ET: Legacy versions.[/bold red]")
            return False
        
        # Display available versions
        version_table = Table(title="Available ET: Legacy Versions")
        version_table.add_column("#", style="cyan")
        version_table.add_column("Version", style="green")
        version_table.add_column("Type", style="magenta")
        
        # Add stable version if available
        if stable_link:
            version_table.add_row("1", "Latest Stable Release", "Stable")
        
        # Add development builds
        for i, build in enumerate(dev_builds, start=2 if stable_link else 1):
            version_table.add_row(
                str(i),
                f"v{build['version']} ({build['hash']})",
                "Development"
            )
        
        self.console.print(version_table)
        
        # Get user selection
        version_count = len(dev_builds) + (1 if stable_link else 0)
        version_choice = Prompt.ask(
            "Select version to install",
            choices=[str(i) for i in range(1, version_count + 1)],
            default="1"
        )
        
        # Process the selection
        if version_choice == "1" and stable_link:
            # User selected stable version
            self.console.print("[bold green]You selected the latest stable release.[/bold green]")
            download_url = stable_link
            version_name = "stable"
        else:
            # User selected a development build
            build_index = int(version_choice) - (2 if stable_link else 1)
            selected_build = dev_builds[build_index]
            self.console.print(f"[bold green]You selected version v{selected_build['version']} ({selected_build['hash']}).[/bold green]")
            download_url = selected_build['url']
            version_name = f"v{selected_build['version']}-{selected_build['hash']}"
        
        # Get installation directory
        install_dir = Prompt.ask(
            "Installation directory",
            default=os.path.join(DEFAULT_DOWNLOAD_DIR, f"{server_type.value}-{version_name}")
        )
        
        # Create destination path
        destination = Path(install_dir)
        if destination.exists():
            if not Confirm.ask(f"Directory {install_dir} already exists. Overwrite?"):
                self.console.print("[yellow]Installation aborted.[/yellow]")
                return False
        
        # Download the installer
        installer_filename = download_url.split('/')[-1]
        installer_path = destination / installer_filename
        
        self.console.print(f"[bold blue]Downloading ET: Legacy {version_name}...[/bold blue]")
        if not self.download_with_progress(download_url, installer_path):
            self.console.print("[bold red]Download failed.[/bold red]")
            return False
        
        # Make the installer executable and run it
        self.console.print("[bold blue]Setting up server...[/bold blue]")
        # TODO: Implement server setup based on server_type
        
        self.console.print("[bold green]Server installation complete![/bold green]")
        return True
    
    def manage_existing_server(self) -> bool:
        """
        Manage an existing ET: Legacy server
        
        Returns:
            bool: True if management was successful
        """
        # TODO: Implement server management
        self.console.print("[bold yellow]Server management not yet implemented.[/bold yellow]")
        return False
    
    def main_menu(self) -> None:
        """Display the main menu and handle user selection"""
        while True:
            # Clear the screen
            self.console.clear()
            
            # Display the header
            self.console.print(Panel(
                "[bold yellow]ET: Legacy Server Manager[/bold yellow]\n"
                "[green]A tool for installing and managing ET: Legacy game servers[/green]"
            ))
            
            # Display the menu options
            self.console.print("\n[bold cyan]Main Menu:[/bold cyan]")
            self.console.print("1. Install New Server")
            self.console.print("2. Manage Existing Server")
            self.console.print("3. Exit")
            
            # Get user input
            choice = Prompt.ask(
                "\nSelect an option",
                choices=["1", "2", "3"],
                default="1"
            )
            
            # Process the selection
            if choice == "1":
                # Install new server submenu
                self.console.clear()
                self.console.print(Panel("[bold cyan]Install New Server[/bold cyan]"))
                self.console.print("1. Competition Server")
                self.console.print("2. Public Server")
                self.console.print("3. Back to Main Menu")
                
                server_choice = Prompt.ask(
                    "\nSelect server type",
                    choices=["1", "2", "3"],
                    default="1"
                )
                
                if server_choice == "1":
                    self.install_server(ServerType.COMPETITION)
                elif server_choice == "2":
                    self.install_server(ServerType.PUBLIC)
                # If "3", just go back to main menu
                    
            elif choice == "2":
                self.manage_existing_server()
            elif choice == "3":
                self.console.print("[green]Exiting ET: Legacy Server Manager. Goodbye![/green]")
                break
            
            # Pause before returning to the main menu
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    manager = ETLegacyManager()
    manager.main_menu()