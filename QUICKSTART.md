# Quick Setup Guide

## 1. Install Globally

```bash
cd qoder-subagent-architecture
pip3 install -e .
```

## 2. Add to PATH

The installer puts `qoder-orchestrate` in your Python user bin directory. Add it to your PATH:

```bash
# Add to ~/.zshrc (or ~/.bashrc for bash)
echo 'export PATH="$PATH:$HOME/Library/Python/3.9/bin"' >> ~/.zshrc

# Reload shell
source ~/.zshrc
```

**Note**: Replace `3.9` with your Python version if different. Check with:
```bash
python3 --version
```

## 3. Verify Installation

```bash
qoder-orchestrate --help
```

You should see the help message.

## 4. Use from Any Project

```bash
# Navigate to your project
cd ~/my-project

# Create .env.local with your PAT
echo "qoder_pat=YOUR_PAT_HERE" > .env.local

# Run orchestration
qoder-orchestrate "Add user authentication"
```

## Alternative: Use Without Adding to PATH

If you don't want to modify PATH, use the full path:

```bash
/Users/francis/Library/Python/3.9/bin/qoder-orchestrate "Your objective"
```

Or create an alias in ~/.zshrc:

```bash
alias qoder-orchestrate='/Users/francis/Library/Python/3.9/bin/qoder-orchestrate'
```

## Troubleshooting

### Command Not Found After Installation

1. Find your Python user base:
   ```bash
   python3 -m site --user-base
   ```

2. Add the bin directory to PATH:
   ```bash
   export PATH="$PATH:$(python3 -m site --user-base)/bin"
   ```

3. Make it permanent by adding to ~/.zshrc or ~/.bashrc

### Permission Issues

Use `--user` flag:
```bash
pip3 install --user -e .
```

## Next Steps

See [INSTALL.md](INSTALL.md) for detailed documentation.
