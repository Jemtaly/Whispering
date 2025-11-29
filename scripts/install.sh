#!/bin/bash
set -e  # Exit on error

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Whispering Installation Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}Error: Python 3.8+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo

# Check for pip
echo -e "${YELLOW}Checking for pip...${NC}"
if ! python3 -m pip --version &> /dev/null; then
    echo -e "${RED}Error: pip not found. Please install pip first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pip found${NC}"
echo

# Create virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "${BLUE}Virtual environment already exists. Skipping creation.${NC}"
else
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
python -m pip install --upgrade pip --quiet
echo -e "${GREEN}✓ pip upgraded${NC}"
echo

# Install base requirements
echo -e "${YELLOW}Installing base requirements...${NC}"
echo -e "${BLUE}This may take a few minutes...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Base requirements installed${NC}"
echo

# Check for NVIDIA GPU
echo -e "${YELLOW}Checking for NVIDIA GPU...${NC}"
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✓ NVIDIA GPU detected${NC}"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo

    # Ask about CUDA libraries
    echo -e "${YELLOW}Do you want to install CUDA libraries for GPU acceleration? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}Installing CUDA libraries...${NC}"
        pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
        echo -e "${GREEN}✓ CUDA libraries installed${NC}"
    else
        echo -e "${BLUE}Skipping CUDA libraries. You can install them later with:${NC}"
        echo -e "${BLUE}  pip install nvidia-cublas-cu12 nvidia-cudnn-cu12${NC}"
    fi
else
    echo -e "${BLUE}No NVIDIA GPU detected. CPU mode will be used.${NC}"
fi
echo

# Create necessary directories
echo -e "${YELLOW}Creating project directories...${NC}"
mkdir -p log_output
mkdir -p tts_output
echo -e "${GREEN}✓ Directories created${NC}"
echo

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f "config/.env.example" ]; then
        echo -e "${YELLOW}Creating .env file from template...${NC}"
        cp config/.env.example .env
        echo -e "${GREEN}✓ .env file created${NC}"
        echo -e "${BLUE}Note: Edit .env file to add your API keys${NC}"
    else
        echo -e "${BLUE}No .env.example found. Skipping .env creation.${NC}"
    fi
else
    echo -e "${BLUE}.env file already exists. Skipping.${NC}"
fi
echo

# Make scripts executable
echo -e "${YELLOW}Making scripts executable...${NC}"
chmod +x scripts/run.sh
chmod +x scripts/debug_env.sh
echo -e "${GREEN}✓ Scripts are executable${NC}"
echo

# Installation complete
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Run the GUI:     ${GREEN}./scripts/run.sh${NC}"
echo -e "  2. Run the TUI:     ${GREEN}python src/tui.py${NC}"
echo -e "  3. See README.md for usage instructions"
echo
echo -e "${BLUE}Optional setup:${NC}"
echo -e "  - For AI features: Edit .env and set OPENROUTER_API_KEY"
echo -e "  - For TTS: See INSTALL_TTS.md for setup instructions"
echo
echo -e "${YELLOW}Note: Remember to activate the virtual environment before running:${NC}"
echo -e "${GREEN}  source .venv/bin/activate${NC}"
echo
