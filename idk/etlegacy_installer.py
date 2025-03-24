#!/usr/bin/env python3
import os
import sys
import argparse
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel

# Import local modules
from ui.main_menu import MainMenu
from lib.config_manager import ConfigManager

# Custom theme for rich
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "danger": "bold red",
    "success": "green",
    "title": "bold blue",
})

console = Console(theme=custom_theme)

def check_prerequisites():
    """Check if the script is run with necessary permissions"""
    if os.geteuid() != 0:
        console.print(Panel("[danger]This script must be run with sudo or as root.[/danger]"))
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="ET Legacy Server Installer")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--non-interactive", action="store_true", help="Run in non-interactive mode using config file")
    args = parser.parse_args()
    
    if not check_prerequisites():
        sys.exit(1)
    
    # Welcome banner
    console.print(Panel.fit(
        "[title]ET Legacy Server Installer[/title]\n"
        "A tool for installing and managing Enemy Territory Legacy servers",
        title="Welcome",
        border_style="blue"
    ))
    
    # Initialize configuration
    config = ConfigManager(args.config if args.config else None)
    
    # Start main menu
    if args.non_interactive and args.config:
        # Run in non-interactive mode with provided config
        from lib.installer import Installer
        installer = Installer(config, console)
        installer.install_server()
    else:
        # Start interactive menu
        menu = MainMenu(console, config)
        menu.show()

if __name__ == "__main__":
    main()