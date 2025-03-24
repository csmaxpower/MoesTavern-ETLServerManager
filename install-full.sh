#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Repository URL
REPO_URL="https://github.com/csmaxpower/MoesTavern-ETLServerManager.git"
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
        if (( $(echo "$python_version < 3.8" | bc -l 2>/dev/null) )); then
            print_message "Python version $python_version detected. Version 3.8 or higher is required." "$RED"
            missing_deps+=("python3.8+")
        else
            print_message "Python version $python_version detected. This is compatible." "$GREEN"
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
    
    # Check for virtualenv - Install it if missing but Python is available
    if ! python3 -c "import virtualenv" 2>/dev/null; then
        if command_exists pip3; then
            print_message "virtualenv not found. Installing..." "$YELLOW"
            pip3 install virtualenv
            if [ $? -ne 0 ]; then
                missing_deps+=("virtualenv")
            fi
        else
            missing_deps+=("virtualenv")
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
        if [[ "${missing_deps[*]}" =~ "python3" ]]; then
            echo "  sudo apt-get update && sudo apt-get install python3 python3-pip"
        fi
        if [[ "${missing_deps[*]}" =~ "pip3" ]]; then
            echo "  sudo apt-get install python3-pip"
        fi
        if [[ "${missing_deps[*]}" =~ "virtualenv" ]]; then
            echo "  pip3 install virtualenv"
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
            print_message "Failed to create virtual environment with venv. Trying virtualenv..." "$YELLOW"
            python3 -m virtualenv venv
            if [ $? -ne 0 ]; then
                print_message "Failed to create virtual environment." "$RED"
                exit 1
            fi
        fi
    fi
    
    # Activate virtual environment and install dependencies
    print_message "Installing dependencies..." "$BLUE"
    
    # Source might not work in some shells, try different approaches
    if [ -f "$INSTALL_DIR/venv/bin/activate" ]; then
        source "$INSTALL_DIR/venv/bin/activate" || . "$INSTALL_DIR/venv/bin/activate"
    else
        print_message "Could not find activation script for virtual environment." "$RED"
        exit 1
    fi
    
    # Install dependencies
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            print_message "Failed to install dependencies." "$RED"
            exit 1
        fi
    else
        print_message "requirements.txt not found. Creating basic requirements file..." "$YELLOW"
        cat > "$INSTALL_DIR/requirements.txt" << EOF
requests>=2.28.0
python-dotenv>=1.0.0
rich>=13.3.0
beautifulsoup4>=4.12.0
EOF
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            print_message "Failed to install dependencies." "$RED"
            exit 1
        fi
    fi
    
    print_message "Environment setup complete." "$GREEN"
}

# Run the application
run_application() {
    print_message "Starting ET: Legacy Server Manager..." "$BLUE"
    
    cd "$INSTALL_DIR" || exit 1
    source venv/bin/activate || . venv/bin/activate
    
    # Create .env file if it doesn't exist
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        print_message "Creating default .env file..." "$YELLOW"
        cat > "$INSTALL_DIR/.env" << EOF
# ET: Legacy Server Manager Configuration
DOWNLOAD_DIR=$HOME/etlegacy
ETLEGACY_STABLE_URL=https://etlegacy.com/download
ETLEGACY_DEV_URL=https://etlegacy.com/workflow-files
EOF
    fi
    
    # Find the main Python file
    MAIN_FILE=$(find . -maxdepth 1 -name "*.py" | grep -i -E "main|etlegacy|manager" | head -1)
    if [ -z "$MAIN_FILE" ]; then
        MAIN_FILE=$(find . -maxdepth 1 -name "*.py" | head -1)
    fi
    
    if [ -z "$MAIN_FILE" ]; then
        print_message "Could not find a Python file to run. Please check the repository." "$RED"
        exit 1
    else
        # Run the application
        print_message "Running $MAIN_FILE..." "$BLUE"
        python3 "$MAIN_FILE"
    fi
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
    
    print_message "\nInstallation complete!" "$GREEN"
    print_message "You can run the application again later with:" "$BLUE"
    echo "  bash $INSTALL_DIR/run.sh"
    
    # Create a run script for future use
    cat > "$INSTALL_DIR/run.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate || . venv/bin/activate

# Find the main Python file
MAIN_FILE=\$(find . -maxdepth 1 -name "*.py" | grep -i -E "main|etlegacy|manager" | head -1)
if [ -z "\$MAIN_FILE" ]; then
    MAIN_FILE=\$(find . -maxdepth 1 -name "*.py" | head -1)
fi

if [ -z "\$MAIN_FILE" ]; then
    echo "Could not find a Python file to run. Please check the repository."
    exit 1
else
    # Run the application
    echo "Running \$MAIN_FILE..."
    python3 "\$MAIN_FILE"
fi
EOF
    chmod +x "$INSTALL_DIR/run.sh"
    
    # Ask if the user wants to run the application now
    read -p "Do you want to run the application now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_application
    else
        print_message "You can run the application later with: bash $INSTALL_DIR/run.sh" "$BLUE"
    fi
}

# Run the main function
main