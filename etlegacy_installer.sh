#!/bin/bash
# ET Legacy Server Installer Wrapper
# This script downloads and runs the Python-based ET Legacy Server Installer

# Check if running as root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root (use sudo)"
  exit
fi

echo "ET Legacy Server Installer"
echo "-------------------------"
echo "This script will download and run the Python-based ET Legacy Server Installer."

# Install Python and dependencies
echo "Checking for required packages..."
apt update
apt install -y python3 python3-pip wget unzip

# Create temporary directory
echo "Creating temporary directory..."
TMP_DIR="/tmp/etlegacy-installer"
mkdir -p "$TMP_DIR"
cd "$TMP_DIR" || exit

# Define repository URL
REPO_URL="https://github.com/yourusername/etlegacy-installer/archive/main.zip"

# Download the installer
echo "Downloading installer..."
wget -q "$REPO_URL" -O installer.zip

# Extract the installer
echo "Extracting files..."
unzip -q installer.zip
cd etlegacy-installer-main || exit

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Run the installer
echo "Starting installer..."
python3 etlegacy_installer.py

# Clean up
echo "Cleaning up..."
cd / || exit
rm -rf "$TMP_DIR"

echo "Done!"