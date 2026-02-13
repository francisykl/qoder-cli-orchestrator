# Tutorial: Getting Started with Qoder Orchestration

Welcome to the Qoder orchestration system! This tutorial will guide you through your first orchestrated development task.

## Prerequisites

Before starting, ensure you have:
- [ ] Python 3.8 or higher
- [ ] Node.js and npm (for Qoder CLI)
- [ ] Git installed
- [ ] A project directory

## Step 1: Installation

### Install Qoder Orchestrator

```bash
cd qoder-subagent-architecture
pip install -e .
```

Verify installation:
```bash
qoder-orchestrate --help
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Configuration management (pyyaml)
- Error handling (gitpython)
- Semantic search (sentence-transformers)
- LLM clients (openai, anthropic)

### Install Qoder CLI

```bash
npm install -g qoder
qoder --version
```

## Step 2: Set Up Your Project

### Initialize Git Repository

```bash
cd your-project
git init
git add .
git commit -m "Initial commit"
```

> **Why?** Rollback features require a git repository.

### Create Qoder Context

Create the `.qoder` directory structure:

```bash
mkdir -p .qoder/wiki .qoder/skills .qoder/rules.md
```

### Add Your First Wiki Page

Create `.qoder/wiki/project-overview.md`:

```markdown
# Project Overview

This is a web application built with:
- Backend: Python/FastAPI
- Frontend: React
- Database: PostgreSQL

## Architecture
We follow a layered architecture with clear separation between API, business logic, and data access.
```

### Add Project Rules

Create `.qoder/rules.md`:

```markdown
# Project Rules

1. All code must pass linting before commit
2. Use TypeScript for frontend code
3. Follow REST API conventions
4. Write tests for all new features
5. Document all public APIs
```

### Create Subagent Definitions

Create `subagents/backend-dev.md`:

```markdown
---
name: backend-dev
description: Backend developer specializing in Python/FastAPI
---

You are a backend developer. Focus on:
- API endpoint implementation
- Database models and migrations
- Business logic
- Error handling
- Testing
```

## Step 3: Configure Orchestration

### Set Up PAT

Create `.env.local`:

```bash
echo "qoder_pat=YOUR_PAT_HERE" > .env.local
```

> **Security**: `.env.local` is gitignored by default.

### Create Configuration File

Create `.qoder-orchestrate.yaml`:

```yaml
# Start with minimal configuration
execution:
  max_parallel: 2
  max_iterations: 5

llm:
  provider: qoder

semantic_search:
  enabled: true

validation:
  enabled: true
```

## Step 4: Your First Orchestrated Task

### Simple Task

Let's start with a simple task:

```bash
qoder-orchestrate "Add a health check endpoint to the API"
```

### What Happens:

1. **Pre-flight validation** checks your environment
2. **Task splitting** breaks down the prompt into subtasks
3. **Context loading** retrieves relevant wiki/skills
4. **Execution** runs tasks via Qoder CLI
5. **Verification** checks if objectives are met

### Expected Output:

```
================================================================================
VALIDATION REPORT
================================================================================
✓ All validation checks passed

Planning Phase: Iteration 0
Original Prompt: Add a health check endpoint to the API

[INFO] Executing 1 tasks in parallel
[INFO] [t1] Starting: Create health check endpoint
[INFO] [t1] Completed successfully

================================================================================
ORCHESTRATION SUMMARY
================================================================================
Total Tasks: 1
Completed: 1
Failed: 0
Iterations: 1
```

## Step 5: More Complex Task

Now try a multi-component task:

```bash
qoder-orchestrate "Create a user registration system with email verification"
```

This will:
1. Create backend API endpoints
2. Add database models
3. Implement email service
4. Create frontend registration form
5. Integrate frontend with backend

### Monitor Progress

Watch the logs:
```bash
tail -f orchestration.log
```

### Check Generated Plan

```bash
cat specs/plan.json
```

This shows the task breakdown and dependencies.

## Step 6: Understanding Task Dependencies

The orchestrator automatically:
- Detects dependencies between tasks
- Runs independent tasks in parallel
- Prevents file conflicts
- Tracks integration points

Example task graph:
```
t1: Create User model (backend)
  ↓
t2: Create registration endpoint (backend)
  ↓
t3: Create registration form (frontend)
  ↓
t4: Integrate frontend with backend
```

## Step 7: Using Advanced Features

### Semantic Search

The orchestrator uses embeddings to find relevant wiki pages:

```bash
# It will automatically find relevant context
qoder-orchestrate "Implement authentication"
# Finds: authentication.md, security.md, user-management.md
```

### Error Recovery

If a task fails, it will:
1. Retry with exponential backoff
2. Create git checkpoint before each task
3. Optionally rollback on failure

### Learning from Execution

After tasks complete, the system can update wiki pages:

```yaml
# Enable in config
enable_learning: true
```

## Step 8: Best Practices

### 1. Start Small
Begin with simple, single-component tasks before complex multi-component workflows.

### 2. Maintain Good Context
Keep your wiki pages updated with:
- Architecture decisions
- Coding patterns
- Integration points
- Common pitfalls

### 3. Review Generated Plans
Before execution, check `specs/plan.json` to ensure task breakdown makes sense.

### 4. Use Checkpoints
Enable rollback for safety:
```yaml
rollback:
  enabled: true
  create_checkpoints: true
```

### 5. Monitor Logs
Watch `orchestration.log` for detailed execution information.

## Step 9: Troubleshooting

### Task Fails Immediately

**Check**: Pre-flight validation
```bash
qoder-orchestrate "test" --project-dir .
```

### Tasks Stuck in Pending

**Cause**: Circular dependencies or missing dependencies

**Fix**: Check `specs/plan.json` for dependency graph

### Slow Performance

**Solution**: Enable caching
```yaml
cache:
  enabled: true
  max_size_mb: 200
```

### Out of Memory

**Solution**: Reduce parallelism
```yaml
execution:
  max_parallel: 1
```

## Step 10: Next Steps

### Explore Configuration

Read the full configuration guide:
```bash
cat .qoder-orchestrate.yaml
```

### Read Architecture Docs

Understand the system:
```bash
cat docs/architecture.md
```

### Check Best Practices

Learn patterns for different project types:
```bash
cat docs/best-practices.md
```

## Common Workflows

### Feature Development
```bash
qoder-orchestrate "Add user profile page with avatar upload"
```

### Bug Fixing
```bash
qoder-orchestrate "Fix authentication timeout issue"
```

### Refactoring
```bash
qoder-orchestrate "Refactor user service to use repository pattern"
```

### Testing
```bash
qoder-orchestrate "Add integration tests for payment flow"
```

## Interactive Mode (Coming Soon)

```bash
qoder-orchestrate --interactive "Build a blog system"
```

This will:
- Show task breakdown
- Ask for approval before each phase
- Allow task injection mid-execution

## Getting Help

### View Logs
```bash
cat orchestration.log
```

### Check Cache Stats
```bash
# Add to your script
from qoder_orchestrator.context_cache import ContextCache
cache = ContextCache(config)
cache.print_stats()
```

### Troubleshooting Guide
```bash
cat docs/troubleshooting.md
```

## Summary

You've learned:
- ✓ How to install and configure the orchestrator
- ✓ How to set up project context
- ✓ How to run your first orchestrated task
- ✓ How to monitor and troubleshoot execution
- ✓ Best practices for effective orchestration

**Next**: Explore [best practices](best-practices.md) for your project type!
