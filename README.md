# Subagent Orchestration System

A production-ready orchestration system that splits high-level development prompts into granular tasks and executes them using Qoder CLI subagents.

## Installation

```bash
# Install from source (recommended for development)
cd qoder-subagent-architecture
pip3 install -e .

# Verify installation
qoder-orchestrate --help
```

After installation, you can run `qoder-orchestrate` from **any directory** on your system.

See [INSTALL.md](file:///Users/francis/qoder-subagent-architecture/INSTALL.md) for detailed installation instructions.

## Features

- **Intelligent Task Splitting**: Analyzes prompts and creates a dependency graph of tasks
- **Parallel Execution**: Runs independent tasks concurrently with conflict detection
- **Cross-Component Integration**: Tracks shared models between backend/frontend
- **Qoder Context Integration**: Automatically loads and uses project wiki, skills, and rules
- **Self-Updating Documentation**: Updates wiki/skills when approaches deviate
- **Decision Making**: Automatically determines when to proceed, hold, or stop
- **Security**: Handles Qoder PAT securely via `.env.local`
- **Comprehensive Logging**: Detailed logs saved to `orchestration.log`

## Installation

1. Ensure Qoder CLI is installed:
```bash
npm install -g qoder
```

2. Set up your PAT in `.env.local`:
```bash
echo "qoder_pat=YOUR_PAT_HERE" > .env.local
```

## Usage

### Basic Usage
```bash
./orchestrate.py "Create a user authentication system with login and registration"
```

### Advanced Options
```bash
./orchestrate.py "Build a REST API for blog posts" \
  --project-dir /path/to/project \
  --max-parallel 5 \
  --max-iterations 15
```

### CLI Options

- `prompt`: High-level development task (required)
- `--project-dir`: Project directory (default: current directory)
- `--max-parallel`: Maximum parallel tasks (default: 3)
- `--max-iterations`: Maximum iterations before stopping (default: 10)

## How It Works

1. **Planning Phase**: The orchestrator analyzes your prompt and splits it into tasks
2. **Dependency Resolution**: Creates a DAG of tasks with dependencies
3. **Parallel Execution**: Runs independent tasks concurrently
4. **Conflict Detection**: Prevents multiple tasks from modifying the same files
5. **Integration Tracking**: Maintains a registry of shared models/interfaces
6. **Decision Making**: Evaluates progress and decides when to stop

## Directory Structure

```
qoder-subagent-architecture/
├── orchestrate.py          # Main orchestration script
├── subagents/              # Subagent definitions
│   ├── architect.md
│   ├── backend-dev.md
│   └── frontend-dev.md
├── specs/                  # Generated plans and registry
│   ├── plan.json
│   └── integration_registry.json
└── orchestration.log       # Execution logs
```

## Subagents

The system includes pre-configured subagents:

- **architect**: System design and architecture
- **backend-dev**: Backend implementation (Python, APIs, databases)
- **frontend-dev**: Frontend development (React/Vue, UI/UX)

You can add custom subagents by creating `.md` files in the `subagents/` directory.

## Example Output

```
2026-02-13 22:00:00 [INFO] Planning Phase: Iteration 0
2026-02-13 22:00:01 [INFO] Plan saved to specs/plan.json
2026-02-13 22:00:01 [INFO] Starting execution loop
2026-02-13 22:00:01 [INFO] Executing 2 tasks in parallel
2026-02-13 22:00:01 [INFO] [t1] Starting: Analyze project structure
2026-02-13 22:00:01 [INFO] [t3] Starting: Create frontend components
2026-02-13 22:00:45 [INFO] [t1] Completed successfully
2026-02-13 22:01:12 [INFO] [t3] Completed successfully
...
```

## Considerations

### When to Use
- Complex multi-component development tasks
- Projects requiring backend/frontend coordination
- Tasks that can be parallelized
- Iterative development workflows

### Limitations
- Requires Qoder CLI to be installed
- LLM-based task splitting (currently mocked - needs integration)
- File-based conflict detection (doesn't handle code-level conflicts)
- Maximum iteration limit to prevent infinite loops

## Troubleshooting

**PAT not found**: Ensure `.env.local` contains `qoder_pat=YOUR_PAT`

**Qoder CLI not found**: Install with `npm install -g qoder`

**Tasks stuck in pending**: Check `orchestration.log` for dependency issues

**Timeout errors**: Increase timeout in `run_task()` method (default: 5 minutes)

## Next Steps

To make this production-ready:

1. **Replace mock task splitting** with real LLM call via Qoder CLI
2. **Add retry logic** for failed tasks
3. **Implement rollback** mechanism for failed iterations
4. **Add progress UI** for better visibility
5. **Integrate with CI/CD** for automated workflows
