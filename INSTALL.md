# Installation Guide

## Quick Install (Recommended)

Install globally from the repository:

```bash
# Clone or navigate to the repository
cd qoder-subagent-architecture

# Install in editable mode (allows updates without reinstalling)
pip install -e .

# Verify installation
qoder-orchestrate --version
```

Now you can use `qoder-orchestrate` from **any directory** on your system!

## How It Works

When you run `qoder-orchestrate` from any directory:

1. **Current Working Directory**: The orchestrator uses your current directory as the project directory
2. **PAT Token**: Looks for `.env.local` in the current directory
3. **Context**: Loads `.qoder/` context from the current directory
4. **Configuration**: Reads `.qoder-orchestrate.yaml` from the current directory

## Example Usage

```bash
# Navigate to your project
cd ~/my-awesome-project

# Create .env.local with your PAT
echo "qoder_pat=YOUR_PAT_HERE" > .env.local

# Run orchestration
qoder-orchestrate "Add user authentication"
```

The orchestrator will:
- Use `~/my-awesome-project` as the project directory
- Read PAT from `~/my-awesome-project/.env.local`
- Load context from `~/my-awesome-project/.qoder/`
- Save outputs to `~/my-awesome-project/specs/`

## Installation Options

### Option 1: Editable Install (Development)

Best for development or if you want to modify the orchestrator:

```bash
cd qoder-subagent-architecture
pip install -e .
```

Changes to the code take effect immediately without reinstalling.

### Option 2: Regular Install

Install as a regular package:

```bash
cd qoder-subagent-architecture
pip install .
```

### Option 3: Install from Git (Future)

Once published, you can install directly from Git:

```bash
pip install git+https://github.com/qoder/qoder-orchestrator.git
```

## Uninstall

```bash
pip uninstall qoder-orchestrator
```

## Updating

### For Editable Install

Just pull the latest changes:

```bash
cd qoder-subagent-architecture
git pull
```

Changes are immediately available.

### For Regular Install

Reinstall:

```bash
cd qoder-subagent-architecture
git pull
pip install --upgrade .
```

## Verifying Installation

```bash
# Check version
qoder-orchestrate --version

# Check help
qoder-orchestrate --help

# Check where it's installed
which qoder-orchestrate

# Check Python package
pip show qoder-orchestrator
```

## Setting Up a New Project

```bash
# Navigate to your project
cd ~/my-project

# Create .env.local with PAT
echo "qoder_pat=YOUR_PAT_HERE" > .env.local

# Create Qoder context structure
mkdir -p .qoder/wiki .qoder/skills
touch .qoder/rules.md

# Create configuration (optional)
cp /path/to/qoder-subagent-architecture/.qoder-orchestrate.yaml .

# Run orchestration
qoder-orchestrate "Your objective here"
```

## Troubleshooting

### Command Not Found

If `qoder-orchestrate` is not found after installation:

```bash
# Check if pip bin directory is in PATH
python -m site --user-base

# Add to PATH (add to ~/.zshrc or ~/.bashrc)
export PATH="$PATH:$(python -m site --user-base)/bin"

# Reload shell
source ~/.zshrc  # or source ~/.bashrc
```

### Permission Denied

```bash
# Use --user flag
pip install --user -e .
```

### Wrong Python Version

```bash
# Use specific Python version
python3.10 -m pip install -e .
```

## Multiple Projects

You can use the same global installation for multiple projects:

```bash
# Project 1
cd ~/project-1
echo "qoder_pat=PAT_1" > .env.local
qoder-orchestrate "Build feature A"

# Project 2
cd ~/project-2
echo "qoder_pat=PAT_2" > .env.local
qoder-orchestrate "Build feature B"
```

Each project maintains its own:
- PAT token (`.env.local`)
- Context (`.qoder/`)
- Configuration (`.qoder-orchestrate.yaml`)
- Outputs (`specs/`, `orchestration.log`)

## Advanced: Custom Installation Location

```bash
# Install to specific location
pip install --target=/custom/path .

# Add to PATH
export PATH="$PATH:/custom/path/bin"
```

## Dependencies

The installer will automatically install:
- `pyyaml` - Configuration management
- `gitpython` - Rollback functionality
- `sentence-transformers` - Semantic search
- `numpy` - Numerical operations
- `scikit-learn` - Similarity calculations

Optional dependencies:
- `torch` - GPU acceleration for embeddings (large download)

## Development Setup

For contributing or development:

```bash
# Clone repository
git clone https://github.com/qoder/qoder-orchestrator.git
cd qoder-orchestrator

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black qoder_orchestrator/

# Type checking
mypy qoder_orchestrator/
```

## System Requirements

- **Python**: 3.8 or higher
- **Git**: Required for rollback features
- **Qoder CLI**: `npm install -g qoder`
- **Disk Space**: ~500MB for embedding models (first run)
- **Memory**: 2GB+ recommended

## Platform Support

- ✅ macOS
- ✅ Linux
- ✅ Windows (with WSL recommended)

## Next Steps

After installation:
1. Read the [Tutorial](docs/tutorial.md)
2. Check [Best Practices](docs/best-practices.md)
3. Review [Architecture](docs/architecture.md)
4. Try the examples in [README](README.md)
