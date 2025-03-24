etlegacy-installer/
├── etlegacy_installer.py      # Main application entry point
├── lib/
│   ├── __init__.py
│   ├── installer.py           # Core installation logic
│   ├── config_manager.py      # Handles .env files and configuration
│   ├── server_manager.py      # Manages running servers
│   ├── download_manager.py    # Handles downloads and version checking
│   └── system_service.py      # Creates and manages systemd services
├── ui/
│   ├── __init__.py
│   ├── main_menu.py           # Main menu interface
│   ├── install_wizard.py      # Installation wizard interface
│   └── progress.py            # Progress bars and status displays
└── utils/
    ├── __init__.py
    ├── bash_runner.py         # Interface for running bash commands/scripts
    ├── permissions.py         # Handles group/user permissions
    └── firewall.py            # Manages firewall configurations