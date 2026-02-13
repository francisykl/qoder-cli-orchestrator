#!/bin/bash
# Quick installation script for Qoder Orchestrator

set -e

echo "🚀 Installing Qoder Orchestrator..."
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"
echo ""

# Check if in correct directory
if [ ! -f "setup.py" ]; then
    echo "❌ Error: setup.py not found"
    echo "Please run this script from the qoder-subagent-architecture directory"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -e .
echo ""

# Verify installation
echo "Verifying installation..."
if command -v qoder-orchestrate &> /dev/null; then
    echo "✓ qoder-orchestrate command is available"
    qoder-orchestrate --version
else
    echo "⚠️  qoder-orchestrate not found in PATH"
    echo ""
    echo "Add this to your ~/.zshrc or ~/.bashrc:"
    echo "export PATH=\"\$PATH:$(python3 -m site --user-base)/bin\""
    echo ""
    echo "Then run: source ~/.zshrc"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Navigate to your project directory"
echo "2. Create .env.local with your Qoder PAT:"
echo "   echo \"QODER_PERSONAL_ACCESS_TOKEN=YOUR_PAT_HERE\" > .env.local"
echo "3. Run: qoder-orchestrate \"Your objective here\""
echo ""
echo "For more information, see INSTALL.md"
