# Troubleshooting Guide

Common issues and solutions for the Qoder orchestration system.

## Installation Issues

### `pip install` Fails

**Error**:
```
ERROR: Could not find a version that satisfies the requirement sentence-transformers
```

**Solution**:
```bash
# Upgrade pip
pip install --upgrade pip

# Install with verbose output
pip install -v sentence-transformers
```

### Qoder CLI Not Found

**Error**:
```
qoder: command not found
```

**Solutions**:

1. **Check npm global path**:
```bash
npm config get prefix
# Add to PATH if needed
export PATH="$PATH:$(npm config get prefix)/bin"
```

2. **Reinstall Qoder CLI**:
```bash
npm uninstall -g qoder
npm install -g qoder
```

3. **Use npx**:
```bash
npx qoder --version
```

## Configuration Issues

### Config File Not Found

**Error**:
```
No configuration file found, using defaults
```

**Solution**:
Create `.qoder-orchestrate.yaml` in project root:
```bash
cp .qoder-orchestrate.yaml.example .qoder-orchestrate.yaml
```

### Invalid Configuration

**Error**:
```
Configuration validation failed:
  - execution.max_parallel must be >= 1
```

**Solution**:
Check configuration values:
```yaml
execution:
  max_parallel: 3  # Must be positive integer
  max_iterations: 10  # Must be positive integer
```

### PAT Not Found

**Warning**:
```
Qoder PAT not found in .env.local
```

**Solution**:
```bash
echo "qoder_pat=YOUR_PAT_HERE" > .env.local
```

Get your PAT from: https://qoder.com/settings/tokens

## Validation Errors

### Not a Git Repository

**Error**:
```
Not a git repository (required for rollback feature)
```

**Solutions**:

1. **Initialize git**:
```bash
git init
git add .
git commit -m "Initial commit"
```

2. **Disable rollback**:
```yaml
rollback:
  enabled: false
```

### Missing Dependencies

**Error**:
```
Missing Python packages: gitpython, pyyaml
```

**Solution**:
```bash
pip install -r requirements.txt
```

### Qoder Context Not Found

**Warning**:
```
.qoder directory not found
```

**Solution**:
```bash
mkdir -p .qoder/wiki .qoder/skills
touch .qoder/rules.md
```

## Execution Issues

### Tasks Stuck in Pending

**Symptom**: Tasks never start executing

**Causes & Solutions**:

1. **Circular dependencies**:
```json
{
  "t1": {"dependencies": ["t2"]},
  "t2": {"dependencies": ["t1"]}
}
```
**Fix**: Review `specs/plan.json` and break circular dependencies

2. **Missing dependencies**:
```json
{
  "t2": {"dependencies": ["t99"]}  // t99 doesn't exist
}
```
**Fix**: Ensure all dependencies exist

3. **File conflicts**:
```
Task t2 waiting for t1 to release file.py
```
**Fix**: Reduce parallelism or adjust file scopes

### Task Timeout

**Error**:
```
Task timed out after 300 seconds
```

**Solutions**:

1. **Increase timeout**:
```yaml
execution:
  task_timeout: 600  # 10 minutes
```

2. **Break down task**:
Make the task more granular

3. **Check Qoder CLI**:
```bash
# Test Qoder CLI directly
qoder -p "simple test task" --yolo
```

### All Tasks Fail

**Error**:
```
All 3 attempts failed
```

**Debug Steps**:

1. **Check logs**:
```bash
tail -n 100 orchestration.log
```

2. **Test Qoder CLI**:
```bash
qoder --version
qoder -p "test" --yolo
```

3. **Verify PAT**:
```bash
grep qoder_pat .env.local
```

4. **Disable retry temporarily**:
```yaml
retry:
  max_attempts: 1
```

## Performance Issues

### Slow Execution

**Symptom**: Tasks take much longer than expected

**Solutions**:

1. **Enable caching**:
```yaml
cache:
  enabled: true
  max_size_mb: 200

semantic_search:
  cache_embeddings: true
```

2. **Increase parallelism**:
```yaml
execution:
  max_parallel: 5
```

3. **Reduce context size**:
```yaml
semantic_search:
  max_results: 3  # Fewer wiki pages
```

### High Memory Usage

**Symptom**: System runs out of memory

**Solutions**:

1. **Reduce cache size**:
```yaml
cache:
  max_size_mb: 50
```

2. **Disable semantic search**:
```yaml
semantic_search:
  enabled: false
```

3. **Reduce parallelism**:
```yaml
execution:
  max_parallel: 1
```

### Slow Semantic Search

**Symptom**: First run is very slow

**Cause**: Downloading embedding model (~500MB)

**Solutions**:

1. **Pre-download model**:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

2. **Use smaller model**:
```yaml
semantic_search:
  model_name: all-MiniLM-L6-v2  # Smaller, faster
```

3. **Disable temporarily**:
```yaml
semantic_search:
  enabled: false
```

## LLM Issues

### OpenAI API Errors

**Error**:
```
OpenAI API call failed: Rate limit exceeded
```

**Solutions**:

1. **Add retry delay**:
```yaml
retry:
  backoff_factor: 3.0
  max_backoff: 600
```

2. **Switch to Qoder**:
```yaml
llm:
  provider: qoder
```

3. **Reduce parallelism**:
```yaml
execution:
  max_parallel: 1
```

### Invalid API Key

**Error**:
```
OpenAI API call failed: Invalid API key
```

**Solution**:
```bash
export OPENAI_API_KEY=your-key-here
# Or in config:
```
```yaml
llm:
  api_key: your-key-here
```

### Task Splitting Fails

**Error**:
```
Failed to parse LLM response as JSON
```

**Solutions**:

1. **Check LLM provider**:
```yaml
llm:
  provider: qoder  # uses -p and --yolo
```

2. **Increase temperature**:
```yaml
llm:
  temperature: 0.3  # More deterministic
```

3. **Check logs**:
```bash
grep "LLM response" orchestration.log
```

## Contract Verification Issues

### No Contracts Found

**Warning**:
```
Extracted 0 endpoints from backend code
```

**Causes**:

1. **Wrong directory structure**:
Ensure `backend/` and `frontend/` directories exist

2. **Unsupported framework**:
Contract extraction supports FastAPI, Flask, Express

**Solution**:
Manually create OpenAPI spec

### False Positive Mismatches

**Warning**:
```
Endpoint POST /api/users not used by frontend
```

**Cause**: Contract extractor missed the endpoint

**Solution**:
Add to wiki for manual tracking

## Rollback Issues

### Rollback Fails

**Error**:
```
Rollback failed: Uncommitted changes
```

**Solution**:
```bash
# Commit or stash changes first
git stash
# Or
git commit -am "WIP"
```

### Checkpoint Not Created

**Warning**:
```
Failed to create checkpoint: Not a git repository
```

**Solution**:
```bash
git init
git add .
git commit -m "Initial commit"
```

## Cache Issues

### Cache Not Working

**Symptom**: No performance improvement on second run

**Debug**:
```python
from qoder_orchestrator.context_cache import ContextCache
cache = ContextCache(config)
cache.print_stats()
```

**Solutions**:

1. **Check cache directory**:
```bash
ls -la .qoder-cache/
```

2. **Clear and rebuild**:
```bash
rm -rf .qoder-cache/
```

3. **Increase TTL**:
```yaml
cache:
  ttl_seconds: 7200  # 2 hours
```

### Cache Too Large

**Error**:
```
Cache size exceeds maximum: 150MB > 100MB
```

**Solutions**:

1. **Increase limit**:
```yaml
cache:
  max_size_mb: 200
```

2. **Clear cache**:
```bash
rm -rf .qoder-cache/
```

## Logging Issues

### No Logs Generated

**Symptom**: `orchestration.log` is empty

**Solutions**:

1. **Check log level**:
```yaml
log_level: DEBUG
```

2. **Check permissions**:
```bash
touch orchestration.log
chmod 644 orchestration.log
```

3. **Check log file path**:
```yaml
log_file: /absolute/path/to/orchestration.log
```

### Too Many Logs

**Symptom**: Log file grows too large

**Solutions**:

1. **Reduce log level**:
```yaml
log_level: WARNING
```

2. **Rotate logs**:
```bash
# Add to cron
find . -name "orchestration.log" -size +10M -delete
```

## Common Error Messages

### "Connection refused"

**Cause**: Qoder CLI server not running

**Solution**:
```bash
# Restart Qoder CLI
qoder --version
```

### "Permission denied"

**Cause**: Insufficient file permissions

**Solution**:
```bash
chmod +x qoder-orchestrate
chmod 644 .env.local
```

### "Module not found"

**Cause**: Missing Python package

**Solution**:
```bash
pip install -r requirements.txt
```

### "JSON decode error"

**Cause**: Malformed JSON in config or response

**Solutions**:

1. **Validate config**:
```bash
python -c "import yaml; yaml.safe_load(open('.qoder-orchestrate.yaml'))"
```

2. **Check LLM responses**:
```bash
grep "Failed to parse" orchestration.log
```

## Getting More Help

### Enable Debug Logging

```yaml
log_level: DEBUG
```

### Check System Status

```bash
# Python version
python --version

# Pip packages
pip list | grep -E "pyyaml|gitpython|sentence-transformers"

# Qoder CLI
qoder --version

# Git
git --version

# Disk space
df -h
```

### Collect Diagnostic Info

```bash
# Create diagnostic report
cat > diagnostic.txt << EOF
Python: $(python --version)
Pip: $(pip --version)
Qoder: $(qoder --version 2>&1)
Git: $(git --version)
Config: $(cat .qoder-orchestrate.yaml 2>&1)
Logs: $(tail -n 50 orchestration.log 2>&1)
EOF
```

### Report Issues

When reporting issues, include:
1. Error message
2. Relevant logs from `orchestration.log`
3. Configuration file
4. Python and Qoder CLI versions
5. Steps to reproduce

## FAQ

**Q: Can I use without Qoder CLI?**
A: No, Qoder CLI is required for task execution.

**Q: Can I use without git?**
A: Yes, but rollback features will be disabled.

**Q: Can I use without internet?**
A: Partially. Semantic search works offline after initial model download. LLM calls require internet.

**Q: How do I reset everything?**
A:
```bash
rm -rf .qoder-cache/ specs/ orchestration.log
git clean -fdx
```

**Q: Is it safe to interrupt execution?**
A: Yes, but running tasks may be in inconsistent state. Use rollback to recover.

**Q: Can I run multiple orchestrations in parallel?**
A: Not recommended. Use higher `max_parallel` instead.
