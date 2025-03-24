#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# GitHub repository information
REPO_OWNER="csmaxpower"
REPO_NAME="MoesTavern-ETLServerManager"
REPO_BRANCH="main"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"

# Installation directory
INSTALL_DIR="$HOME/etlegacy-server-manager"

# Print a message with color
print_message() {
    echo -e "${2}${1}${NC}"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required dependencies
check_dependencies() {
    print_message "Checking dependencies..." "$BLUE"
    
    local missing_deps=()
    
    # Check for Python 3.8+
    if ! command_exists python3; then
        missing_deps+=("python3")
    else
        python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        print_message "Python version $python_version detected." "$GREEN"
        
        # Proper numeric comparison for Python version
        major=$(echo "$python_version" | cut -d. -f1)
        minor=$(echo "$python_version" | cut -d. -f2)
        
        if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
            print_message "Python 3.8 or higher is required." "$RED"
            missing_deps+=("python3.8+")
        fi
    fi
    
    # Check for pip
    if ! command_exists pip3; then
        missing_deps+=("pip3")
    fi
    
    # Check for git
    if ! command_exists git; then
        missing_deps+=("git")
    fi
    
    # Check for python3-venv on Debian-based systems
    if [ -f /etc/debian_version ]; then
        if ! dpkg -l | grep -q python3-venv; then
            missing_deps+=("python3-venv")
        fi
    fi
    
    # If there are missing dependencies, print them and exit
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_message "The following dependencies are missing:" "$RED"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        
        # Suggest installation commands
        print_message "\nPlease install the missing dependencies. For example:" "$YELLOW"
        if [[ "${missing_deps[*]}" =~ "python3" ]] || [[ "${missing_deps[*]}" =~ "pip3" ]] || [[ "${missing_deps[*]}" =~ "python3-venv" ]]; then
            echo "  sudo apt-get update && sudo apt-get install python3 python3-pip python3-venv python3-full"
        fi
        if [[ "${missing_deps[*]}" =~ "git" ]]; then
            echo "  sudo apt-get install git"
        fi
        exit 1
    fi
    
    print_message "All dependencies are installed." "$GREEN"
}

# Clone or update the repository
setup_repository() {
    print_message "Setting up repository..." "$BLUE"
    
    if [ -d "$INSTALL_DIR" ]; then
        # Directory exists, check if it's a git repository
        if [ -d "$INSTALL_DIR/.git" ]; then
            print_message "Repository already exists. Updating..." "$YELLOW"
            cd "$INSTALL_DIR" || exit 1
            git pull
            if [ $? -ne 0 ]; then
                print_message "Failed to update repository." "$RED"
                exit 1
            fi
        else
            print_message "Directory $INSTALL_DIR exists but is not a git repository." "$RED"
            read -p "Do you want to delete it and clone a fresh copy? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$INSTALL_DIR"
                git clone "$REPO_URL" "$INSTALL_DIR"
                if [ $? -ne 0 ]; then
                    print_message "Failed to clone repository." "$RED"
                    exit 1
                fi
            else
                print_message "Aborting installation." "$RED"
                exit 1
            fi
        fi
    else
        # Directory doesn't exist, clone the repository
        print_message "Cloning repository..." "$BLUE"
        git clone "$REPO_URL" "$INSTALL_DIR"
        if [ $? -ne 0 ]; then
            print_message "Failed to clone repository." "$RED"
            exit 1
        fi
    fi
    
    print_message "Repository setup complete." "$GREEN"
}

# Setup virtual environment and install dependencies
setup_environment() {
    print_message "Setting up virtual environment..." "$BLUE"
    
    cd "$INSTALL_DIR" || exit 1
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$INSTALL_DIR/venv" ]; then
        python3 -m venv venv
        if [ $? -ne 0 ]; then
            print_message "Failed to create virtual environment. Make sure python3-venv is installed." "$RED"
            exit 1
        fi
    fi
    
    # Activate virtual environment and install dependencies
    print_message "Installing dependencies..." "$BLUE"
    
    # Source activation script - handle potential errors
    if [ -f "$INSTALL_DIR/venv/bin/activate" ]; then
        # Try both ways to source the file
        source "$INSTALL_DIR/venv/bin/activate" 2>/dev/null || . "$INSTALL_DIR/venv/bin/activate"
    else
        print_message "Could not find activation script for virtual environment." "$RED"
        exit 1
    fi
    
    # Install dependencies
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        "$INSTALL_DIR/venv/bin/pip" install -r requirements.txt
        if [ $? -ne 0 ]; then
            print_message "Failed to install dependencies." "$RED"
            exit 1
        fi
    else
        print_message "requirements.txt not found in the repository." "$RED"
        exit 1
    fi
    
    print_message "Environment setup complete." "$GREEN"
}

# Create .env file if it doesn't exist
setup_env_file() {
    print_message "Setting up environment configuration..." "$BLUE"
    
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        print_message "Creating default .env file..." "$YELLOW"
        cat > "$INSTALL_DIR/.env" << EOF
# ET: Legacy Server Manager Configuration
DOWNLOAD_DIR=$HOME/etlegacy
ETLEGACY_STABLE_URL=https://etlegacy.com/download
ETLEGACY_DEV_URL=https://etlegacy.com/workflow-files
EOF
    else
        print_message ".env file already exists." "$GREEN"
    fi
}

# Create run script
create_run_script() {
    print_message "Creating run script..." "$BLUE"
    
    # Find main Python file
    MAIN_FILE=""
    if [ -f "$INSTALL_DIR/etlegacy_manager.py" ]; then
        MAIN_FILE="etlegacy_manager.py"
    elif [ -f "$INSTALL_DIR/main.py" ]; then
        MAIN_FILE="main.py"
    else
        MAIN_FILE=$(find "$INSTALL_DIR" -maxdepth 1 -name "*.py" | head -1)
        if [ -z "$MAIN_FILE" ]; then
            print_message "Could not find a Python file to run." "$RED"
            exit 1
        fi
        MAIN_FILE=$(basename "$MAIN_FILE")
    fi
    
    cat > "$INSTALL_DIR/run.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate || . venv/bin/activate
python3 $MAIN_FILE
EOF
    chmod +x "$INSTALL_DIR/run.sh"
    print_message "Run script created successfully." "$GREEN"
}

# Run the application
run_application() {
    print_message "Starting ET: Legacy Server Manager..." "$BLUE"
    
    cd "$INSTALL_DIR" || exit 1
    source venv/bin/activate 2>/dev/null || . venv/bin/activate
    
    # Find main Python file
    MAIN_FILE=""
    if [ -f "$INSTALL_DIR/etlegacy_manager.py" ]; then
        MAIN_FILE="etlegacy_manager.py"
    elif [ -f "$INSTALL_DIR/main.py" ]; then
        MAIN_FILE="main.py"
    else
        MAIN_FILE=$(find "$INSTALL_DIR" -maxdepth 1 -name "*.py" | head -1)
        if [ -z "$MAIN_FILE" ]; then
            print_message "Could not find a Python file to run." "$RED"
            exit 1
        fi
        MAIN_FILE=$(basename "$MAIN_FILE")
    fi
    
    # Run the application
    python3 "$MAIN_FILE"
}

# Main execution
main() {
    print_message "=======================================" "$GREEN"
    print_message "  ET: Legacy Server Manager Installer  " "$GREEN"
    print_message "=======================================" "$GREEN"
    echo
    
    check_dependencies
    setup_repository
    setup_environment
    setup_env_file
    create_run_script
    
    print_message "\nInstallation complete!" "$GREEN"
    print_message "You can run the application at any time with:" "$BLUE"
    echo "  bash $INSTALL_DIR/run.sh"
    
    # Ask if the user wants to run the application now
    read -p "Do you want to run the application now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_application
    fi
}

# Run the main function
main