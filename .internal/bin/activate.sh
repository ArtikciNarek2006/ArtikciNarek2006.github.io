#!/bin/bash
# Gallery CLI Activation Script for Unix/Linux/macOS

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INTERNAL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$INTERNAL_DIR/venv"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv "$VENV_DIR"
    
    # Activate and install dependencies
    source "$VENV_DIR/bin/activate"
    pip install -r "$INTERNAL_DIR/requirements.txt"
    echo -e "${GREEN}Virtual environment created successfully!${NC}"
else
    source "$VENV_DIR/bin/activate"
fi

# Create gallery command function
gallery() {
    python3 "$SCRIPT_DIR/cli.py" "$@"
}

# Create deactivate function
deactivate_gallery() {
    deactivate 2>/dev/null || true
    unset -f gallery
    unset -f deactivate_gallery
    echo -e "${GREEN}Gallery CLI deactivated${NC}"
}

# Export functions
export -f gallery
export -f deactivate_gallery

echo -e "${GREEN}Gallery CLI activated!${NC}"
echo "Available commands:"
echo "  gallery create [name]              - Create a new project"
echo "  gallery update [name|all]          - Update project info"
echo "  gallery remove [name]              - Remove a project"
echo "  gallery serve                      - Generate and serve gallery"
echo "  gallery sync                       - Git add, commit, and push"
echo "  gallery migrate [name] [repo_url]  - Migrate project to new repo"
echo "  deactivate_gallery                 - Deactivate and exit"
echo ""
echo "Run 'gallery help' for more information"
