#!/bin/bash
# Simple script to install Python requirements for HRIM

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== HRIM Requirements Installer =====${NC}"

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed.${NC}"
    exit 1
fi

# Get the Python version
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}Found Python $PY_VERSION${NC}"

# Check if pip is installed
echo -e "${YELLOW}Checking pip...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is not installed.${NC}"
    exit 1
fi

# Install requirements
echo -e "${YELLOW}Installing requirements...${NC}"
pip3 install -r requirements.txt

echo -e "${GREEN}Requirements installed successfully!${NC}"
echo -e "${YELLOW}You can now run individual tests or components.${NC}"
echo -e "${YELLOW}To test the entire workflow: python3 test_hrim.py${NC}"
echo -e "${YELLOW}To test instant delivery: python3 test_instant_delivery.py${NC}"

echo -e "${GREEN}===== Installation completed =====${NC}" 