# Installation Guide

## Quick Install

Install the package globally so you can use `qoder-orchestrate` from any directory:

```bash
# From the qoder-subagent-architecture directory
pip install -e .
```

The `-e` flag installs in "editable" mode, so any changes you make to the code are immediately available.

## Usage

After installation, you can run the orchestrator from **any directory**:

```bash
# Basic usage
qoder-orchestrate "Create a user authentication system"

# With options
qoder-orchestrate "Build a REST API" --max-parallel 5 --max-iterations 15

# In a specific project
cd /path/to/your/project
qoder-orchestrate "Add payment integration"
```

## Verify Installation

```bash
# Check if installed
qoder-orchestrate --help

# Should output:
# usage: qoder-orchestrate [-h] [--project-dir PROJECT_DIR] ...
```

## Uninstall

```bash
pip uninstall qoder-orchestrator
```

## Development Install

For development, use editable mode:

```bash
# Clone the repo
git clone https://github.com/yourusername/qoder-orchestrator.git
cd qoder-orchestrator

# Install in editable mode
pip install -e .

# Now you can edit the code and changes are immediately available
```

## Building Distribution

To create a distributable package:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# This creates:
# - dist/qoder_orchestrator-0.1.0-py3-none-any.whl
# - dist/qoder-orchestrator-0.1.0.tar.gz
```

## Publishing to PyPI (Optional)

```bash
# Test on TestPyPI first
python -m twine upload --repository testpypi dist/*

# Then publish to PyPI
python -m twine upload dist/*

# Users can then install with:
# pip install qoder-orchestrator
```

## Updating

If you installed in editable mode, just pull the latest changes:

```bash
cd qoder-subagent-architecture
git pull
# Changes are automatically available
```

If you installed normally, reinstall:

```bash
pip install --upgrade qoder-orchestrator
```
