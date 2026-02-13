# Best Practices Guide

This guide provides patterns and best practices for different project types and scenarios.

## General Principles

### 1. Context is King
**Good wiki pages lead to better task execution.**

✅ **Do**:
- Keep wiki pages focused and concise
- Update wiki when patterns change
- Include code examples
- Document integration points

❌ **Don't**:
- Create overly broad wiki pages
- Let wiki become stale
- Duplicate information across pages
- Include sensitive information

### 2. Granular Tasks
**Smaller tasks are easier to execute and debug.**

✅ **Do**:
- Break down complex features
- Create clear task boundaries
- Define explicit dependencies

❌ **Don't**:
- Create monolithic tasks
- Mix concerns (e.g., backend + frontend in one task)
- Skip dependency declaration

### 3. Iterative Development
**Start simple, then enhance.**

✅ **Do**:
- Begin with MVP functionality
- Add features incrementally
- Test after each iteration

❌ **Don't**:
- Try to build everything at once
- Skip validation steps
- Ignore failed tasks

## Project Type Patterns

### Monorepo Projects

**Structure**:
```
project/
├── .qoder/
│   ├── wiki/
│   │   ├── monorepo-structure.md
│   │   ├── shared-packages.md
│   │   └── deployment.md
│   └── rules.md
├── packages/
│   ├── backend/
│   ├── frontend/
│   └── shared/
└── .qoder-orchestrate.yaml
```

**Configuration**:
```yaml
execution:
  max_parallel: 4  # Can run multiple packages in parallel
  enable_batch_processing: true

semantic_search:
  enabled: true  # Important for finding relevant packages
```

**Wiki Example** (`monorepo-structure.md`):
```markdown
# Monorepo Structure

## Packages
- `backend`: FastAPI server
- `frontend`: React app
- `shared`: Common types and utilities

## Dependencies
- Frontend depends on shared types
- Backend uses shared validation

## Build Order
1. shared
2. backend, frontend (parallel)
```

**Best Practices**:
- Use batch processing for similar packages
- Define clear package boundaries
- Track cross-package dependencies
- Use semantic search to find relevant packages

### Microservices Architecture

**Structure**:
```
project/
├── .qoder/
│   ├── wiki/
│   │   ├── service-communication.md
│   │   ├── api-gateway.md
│   │   └── data-flow.md
│   └── rules.md
├── services/
│   ├── auth/
│   ├── users/
│   └── payments/
└── .qoder-orchestrate.yaml
```

**Configuration**:
```yaml
execution:
  max_parallel: 3  # One per service
  enable_speculative: true  # Predict dependent services

enable_contract_verification: true  # Critical for microservices
```

**Wiki Example** (`service-communication.md`):
```markdown
# Service Communication

## Patterns
- Synchronous: REST APIs
- Asynchronous: Message queue (RabbitMQ)

## Service Dependencies
- Auth → None
- Users → Auth
- Payments → Users, Auth

## API Contracts
All services expose OpenAPI specs at `/api/docs`
```

**Best Practices**:
- Enable contract verification
- Document service dependencies
- Use speculative execution for dependent services
- Track API versions in wiki

### Full-Stack Web Application

**Structure**:
```
project/
├── .qoder/
│   ├── wiki/
│   │   ├── tech-stack.md
│   │   ├── api-design.md
│   │   └── state-management.md
│   ├── skills/
│   │   ├── backend-dev/
│   │   └── frontend-dev/
│   └── rules.md
├── backend/
├── frontend/
└── .qoder-orchestrate.yaml
```

**Configuration**:
```yaml
execution:
  max_parallel: 2  # Backend + Frontend
  
enable_contract_verification: true
enable_learning: true

semantic_search:
  enabled: true
  max_results: 3
```

**Best Practices**:
- Always verify API contracts
- Keep frontend/backend tasks separate
- Use integration registry for shared models
- Document state management patterns

### CLI Tool Development

**Structure**:
```
project/
├── .qoder/
│   ├── wiki/
│   │   ├── command-structure.md
│   │   └── testing-strategy.md
│   └── rules.md
├── src/
│   └── commands/
└── .qoder-orchestrate.yaml
```

**Configuration**:
```yaml
execution:
  max_parallel: 1  # Sequential for CLI tools
  
validation:
  check_dependencies: true
  
rollback:
  enabled: true  # Important for CLI tools
```

**Best Practices**:
- Use sequential execution
- Enable rollback for safety
- Document command structure
- Test each command independently

## Task Granularity Guidelines

### Too Coarse ❌
```
"Build a complete e-commerce system"
```
**Problem**: Too broad, unclear scope

### Too Fine ❌
```
"Add import statement for User model"
```
**Problem**: Too granular, overhead outweighs benefit

### Just Right ✅
```
"Implement user authentication with JWT tokens"
```
**Scope**: Clear, achievable, testable

## Wiki Organization Patterns

### By Feature
```
.qoder/wiki/
├── authentication.md
├── user-management.md
├── payment-processing.md
└── notifications.md
```

**When to use**: Feature-focused projects

### By Layer
```
.qoder/wiki/
├── api-layer.md
├── business-logic.md
├── data-access.md
└── frontend-components.md
```

**When to use**: Layered architectures

### By Component
```
.qoder/wiki/
├── auth-service.md
├── user-service.md
├── payment-service.md
└── shared-utilities.md
```

**When to use**: Microservices, modular monoliths

## Skill Definition Patterns

### Specialist Skills
```markdown
---
name: backend-dev
description: Python/FastAPI backend specialist
---

You are a backend developer expert in:
- FastAPI framework
- SQLAlchemy ORM
- Pydantic models
- Async programming
- RESTful API design

Always:
- Use type hints
- Write docstrings
- Handle errors gracefully
- Add logging
```

### Generalist Skills
```markdown
---
name: full-stack-dev
description: Full-stack developer
---

You can work on both frontend and backend.

Backend: Python/FastAPI
Frontend: React/TypeScript

Follow the project's architecture patterns.
```

**When to use**:
- Specialist: Large teams, complex domains
- Generalist: Small teams, simple projects

## Configuration Patterns

### Development Environment
```yaml
execution:
  max_parallel: 3
  max_iterations: 15

llm:
  provider: qoder
  temperature: 0.7

semantic_search:
  enabled: true

cache:
  enabled: true
  max_size_mb: 200

rollback:
  enabled: true
  auto_rollback_on_failure: false  # Manual review
```

### CI/CD Environment
```yaml
execution:
  max_parallel: 1  # Deterministic execution
  max_iterations: 5

validation:
  fail_on_warnings: true  # Strict validation

rollback:
  enabled: true
  auto_rollback_on_failure: true  # Auto-cleanup

cache:
  enabled: false  # Fresh execution each time
```

### Production-Like Testing
```yaml
execution:
  max_parallel: 5
  enable_speculative: true

semantic_search:
  enabled: true
  cache_embeddings: true

cache:
  enabled: true
  max_size_mb: 500

retry:
  max_attempts: 5  # More resilient
```

## Common Scenarios

### Adding a New Feature

**Prompt**:
```bash
qoder-orchestrate "Add user profile page with avatar upload and bio editing"
```

**Expected Tasks**:
1. Create backend endpoint for profile updates
2. Add file upload handling for avatars
3. Create frontend profile page component
4. Integrate frontend with backend API
5. Add tests for profile functionality

**Tips**:
- Let orchestrator handle task breakdown
- Review generated plan before execution
- Check contract verification results

### Refactoring

**Prompt**:
```bash
qoder-orchestrate "Refactor authentication to use repository pattern"
```

**Expected Tasks**:
1. Create repository interface
2. Implement repository
3. Update service to use repository
4. Update tests
5. Remove old code

**Tips**:
- Enable rollback
- Create checkpoint before starting
- Run tests after completion

### Bug Fixing

**Prompt**:
```bash
qoder-orchestrate "Fix race condition in payment processing"
```

**Expected Tasks**:
1. Analyze payment flow
2. Identify race condition
3. Implement locking mechanism
4. Add tests to prevent regression

**Tips**:
- Provide context in wiki about the bug
- Enable learning to document the fix
- Update wiki with the solution

### Database Migration

**Prompt**:
```bash
qoder-orchestrate "Add email verification to user model"
```

**Expected Tasks**:
1. Create migration script
2. Update model definition
3. Update API endpoints
4. Update frontend forms
5. Add tests

**Tips**:
- Document migration strategy in wiki
- Use rollback for safety
- Test migration on staging first

## Performance Optimization

### For Large Projects

```yaml
execution:
  max_parallel: 5

cache:
  enabled: true
  max_size_mb: 500

semantic_search:
  cache_embeddings: true
```

### For Resource-Constrained Environments

```yaml
execution:
  max_parallel: 1

cache:
  max_size_mb: 50

semantic_search:
  enabled: false  # Use keyword fallback
```

### For Fast Iteration

```yaml
execution:
  enable_speculative: true
  enable_batch_processing: true

cache:
  enabled: true
  ttl_seconds: 7200  # 2 hours
```

## Anti-Patterns to Avoid

### 1. Vague Prompts ❌
```bash
qoder-orchestrate "Make it better"
```

**Better** ✅:
```bash
qoder-orchestrate "Improve API response time by adding caching"
```

### 2. Ignoring Validation Errors ❌
```
Validation failed but proceeding anyway...
```

**Better** ✅:
```
Fix validation errors before orchestration
```

### 3. Stale Wiki ❌
```
Wiki last updated 6 months ago
```

**Better** ✅:
```
Enable learning mode to auto-update wiki
```

### 4. No Rollback ❌
```yaml
rollback:
  enabled: false
```

**Better** ✅:
```yaml
rollback:
  enabled: true
  create_checkpoints: true
```

## Summary

**Key Takeaways**:
1. Maintain good context (wiki/skills/rules)
2. Use appropriate task granularity
3. Configure for your environment
4. Enable safety features (validation, rollback)
5. Learn from execution (enable learning mode)

**Project-Specific**:
- Monorepo: Enable batch processing
- Microservices: Enable contract verification
- Full-stack: Verify API contracts
- CLI: Use sequential execution

**Remember**: The orchestrator is only as good as the context you provide!
