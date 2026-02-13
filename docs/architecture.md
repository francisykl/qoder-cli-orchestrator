# System Architecture

This document provides a comprehensive overview of the Qoder orchestration system architecture.

## High-Level Architecture

```mermaid
graph TB
    User[User] -->|Prompt| CLI[CLI Entry Point]
    CLI --> Config[Configuration Manager]
    CLI --> Validator[Pre-Flight Validator]
    
    Validator -->|Validation Report| Orchestrator[Orchestrator]
    Config -->|OrchestratorConfig| Orchestrator
    
    Orchestrator --> LLM[LLM Client]
    Orchestrator --> Context[Qoder Context]
    Orchestrator --> Registry[Integration Registry]
    Orchestrator --> ErrorMgr[Error Recovery Manager]
    
    LLM -->|Task Split| TaskQueue[Task Queue]
    Context --> Embeddings[Embedding Manager]
    Context --> Cache[Context Cache]
    Context --> Versioning[Version Tracker]
    
    ErrorMgr --> Retry[Retry Strategy]
    ErrorMgr --> Rollback[Rollback Manager]
    
    TaskQueue --> Executor[Task Executor]
    Executor --> QoderCLI[Qoder CLI]
    Executor --> Verifier[Contract Verifier]
    
    QoderCLI -->|Results| Orchestrator
    Verifier -->|Mismatches| Orchestrator
    
    Orchestrator -->|Learning Updates| Context
    Orchestrator -->|Summary| User
```

## Component Overview

### 1. Configuration Manager (`config.py`)

**Purpose**: Centralized configuration management with multiple sources

**Key Features**:
- YAML file support (`.qoder-orchestrate.yaml`)
- Environment variable overrides
- CLI argument precedence
- Validation of configuration values

**Configuration Hierarchy** (highest to lowest priority):
1. CLI arguments
2. Environment variables
3. YAML config file
4. Defaults

### 2. Pre-Flight Validator (`validation.py`)

**Purpose**: Validate environment before orchestration begins

**Checks**:
- Git repository status
- Qoder CLI installation and version
- Python dependencies
- Project structure
- Qoder context (wiki/skills/rules)

**Output**: Detailed validation report with errors, warnings, and fix suggestions

### 3. Error Recovery Manager (`error_handling.py`)

**Purpose**: Handle failures gracefully with retry and rollback

**Components**:
- **Retry Strategy**: Exponential backoff with configurable attempts
- **Rollback Manager**: Git-based checkpoints and rollback
- **Error Classification**: Categorize errors as recoverable/non-recoverable

**Recovery Flow**:
```mermaid
graph LR
    Task[Execute Task] -->|Success| Done[Done]
    Task -->|Failure| Classify[Classify Error]
    Classify -->|Recoverable| Retry{Retry?}
    Classify -->|Non-Recoverable| Rollback{Auto-Rollback?}
    Retry -->|Yes| Backoff[Exponential Backoff]
    Backoff --> Task
    Retry -->|No| Rollback
    Rollback -->|Yes| Revert[Revert Changes]
    Rollback -->|No| Fail[Fail]
```

### 4. LLM Client (`llm_client.py`)

**Purpose**: Abstract LLM interactions across providers

**Supported Providers**:
- Qoder CLI (default)
- OpenAI (GPT-4, etc.)
- Anthropic (Claude)

**Operations**:
- **Task Splitting**: Break down high-level prompts into granular tasks
- **Objective Analysis**: Determine if original goals are met
- **Learning Suggestions**: Recommend wiki/skill updates

### 5. Context Management

#### Qoder Context (`cli.py`)
Manages project-specific context (wiki, skills, rules)

#### Embedding Manager (`embeddings.py`)
**Purpose**: Semantic search for relevant context

**Features**:
- Sentence transformer embeddings
- Similarity-based retrieval
- Embedding caching
- Keyword fallback when embeddings unavailable

#### Context Cache (`context_cache.py`)
**Purpose**: Performance optimization through caching

**Features**:
- LRU eviction policy
- Disk persistence
- TTL-based expiration
- Size limits

#### Version Tracker (`versioning.py`)
**Purpose**: Track context versions and detect changes

**Features**:
- Content hashing for wiki/skills/rules
- Dependency fingerprinting
- Incremental update detection
- Task version history

### 6. Contract Verifier (`contract_verifier.py`)

**Purpose**: Ensure frontend/backend API contracts stay in sync

**Features**:
- Extract contracts from code (Python, JavaScript)
- OpenAPI spec support
- Mismatch detection and reporting
- Severity classification (error/warning)

### 7. Integration Registry (`cli.py`)

**Purpose**: Track shared state between components

**Tracks**:
- Shared data models
- API contracts
- Cross-component dependencies
- Last sync timestamps

## Data Flow

### Task Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant LLM
    participant Context
    participant Executor
    participant QoderCLI
    
    User->>Orchestrator: Submit prompt
    Orchestrator->>Context: Load wiki/skills/rules
    Context-->>Orchestrator: Project context
    Orchestrator->>LLM: Split tasks (with context)
    LLM-->>Orchestrator: Task list
    
    loop For each ready task
        Orchestrator->>Context: Get relevant context
        Context->>Embeddings: Find similar wiki pages
        Embeddings-->>Context: Relevant pages
        Context-->>Orchestrator: Task context
        
        Orchestrator->>Executor: Execute task
        Executor->>QoderCLI: Run with context
        QoderCLI-->>Executor: Task output
        Executor-->>Orchestrator: Result
        
        Orchestrator->>LLM: Analyze for learning
        LLM-->>Orchestrator: Update suggestions
        Orchestrator->>Context: Update wiki/skills
    end
    
    Orchestrator->>LLM: Analyze objectives
    LLM-->>Orchestrator: Assessment
    Orchestrator-->>User: Summary
```

### Context Retrieval Flow

```mermaid
graph TB
    Task[Task Description] --> Embed[Embed Query]
    Embed --> Cache{In Cache?}
    Cache -->|Yes| Return1[Return Cached]
    Cache -->|No| Generate[Generate Embedding]
    Generate --> Store[Store in Cache]
    Store --> Search[Similarity Search]
    
    Wiki[Wiki Pages] --> EmbedWiki[Embed Wiki]
    EmbedWiki --> WikiCache{In Cache?}
    WikiCache -->|Yes| UseCache[Use Cached]
    WikiCache -->|No| GenWiki[Generate Embeddings]
    GenWiki --> StoreWiki[Store in Cache]
    
    Search --> Compare[Cosine Similarity]
    UseCache --> Compare
    StoreWiki --> Compare
    Compare --> Filter[Filter by Threshold]
    Filter --> TopK[Select Top K]
    TopK --> Return2[Return Results]
```

## Execution Modes

### Sequential Mode
Tasks execute one at a time, respecting dependencies.

### Parallel Mode (Default)
Independent tasks execute concurrently with:
- Dependency checking
- File conflict detection
- Configurable parallelism limit

### Speculative Mode
Predict and start likely-needed tasks before dependencies complete.

### Batch Mode
Group similar tasks for efficient execution.

## Decision Making

```mermaid
graph TB
    Start[Start Iteration] --> Check{Check Progress}
    Check -->|Max Iterations| Stop[Stop]
    Check -->|Failed Tasks| Hold[Hold for User]
    Check -->|All Complete| Analyze[Analyze Objectives]
    Check -->|Has Ready Tasks| Execute[Execute Tasks]
    
    Analyze -->|Met| Stop
    Analyze -->|Not Met| Generate[Generate More Tasks]
    Generate --> Execute
    
    Execute --> Update[Update State]
    Update --> Start
```

## File Organization

```
qoder_orchestrator/
├── __init__.py
├── cli.py                    # Main orchestrator and CLI entry point
├── config.py                 # Configuration management
├── validation.py             # Pre-flight validation
├── error_handling.py         # Retry and rollback
├── llm_client.py            # LLM abstraction
├── embeddings.py            # Semantic search
├── context_cache.py         # Context caching
├── versioning.py            # Context versioning
└── contract_verifier.py     # API contract verification
```

## Extension Points

### Adding New LLM Providers
1. Extend `LLMClient` abstract class
2. Implement required methods
3. Register in `create_llm_client()` factory

### Custom Validation Rules
1. Extend `PreFlightValidator`
2. Add custom validation methods
3. Call from `validate_all()`

### Custom Error Recovery
1. Extend `RetryStrategy` or `RollbackManager`
2. Override recovery logic
3. Inject into `ErrorRecoveryManager`

## Performance Considerations

### Caching Strategy
- **Embeddings**: Cached indefinitely (invalidated on content change)
- **Context**: TTL-based (default 1 hour)
- **LLM Responses**: Not cached (tasks are unique)

### Parallelization
- Default: 3 parallel tasks
- Increase for I/O-bound workloads
- Decrease for CPU/memory-intensive tasks

### Memory Usage
- Embeddings model: ~100MB
- Context cache: Configurable (default 100MB)
- Per-task overhead: ~1-5MB

## Security

### Secrets Management
- PAT stored in `.env.local` (gitignored)
- API keys via environment variables
- No secrets in configuration files

### Sandboxing
- Tasks execute in project directory
- No system-wide modifications
- Git-based rollback for safety
