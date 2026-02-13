---
name: orchestration-context
description: How the orchestrator uses wiki, skills, and rules
---

# Qoder Context Integration

The orchestration script automatically integrates with your project's Qoder context:

## What Gets Loaded

### 1. Wiki (`.qoder/wiki/*.md`)
- All wiki pages are loaded at startup
- Relevant pages are included in task context based on component matching
- Example: A "backend" task gets wiki pages with "backend" in the name

### 2. Skills (`.qoder/skills/*/SKILL.md`)
- All skills are loaded and indexed by name
- When a task uses a subagent, the corresponding skill is included in context
- Example: Task using "backend-dev" subagent gets the backend-dev skill

### 3. Rules (`.qoder/rules.md`)
- Project rules are ALWAYS included in every task
- Rules are never modified by the orchestrator
- Subagents must follow these rules

## How Context Is Used

When executing a task, the orchestrator:

1. Builds a context string containing:
   - Project rules (always)
   - Relevant wiki pages (filtered by component)
   - Relevant skills (matched by subagent name)

2. Passes this context to the Qoder CLI subagent:
```
Task: Implement user authentication

# Context from Project
# Project Rules
- Use TypeScript for all backend code
- Follow REST API conventions
...

# Relevant Wiki Pages
## Wiki: backend-architecture
Our backend uses a layered architecture...

# Skill: backend-dev
You are a backend developer...
```

## Self-Updating Documentation

When a task completes, the orchestrator checks if the approach deviated from documented patterns:

### Detection
- Looks for markers like "different approach", "changed strategy"
- In production, uses LLM to analyze output

### Updates
- **Wiki**: Updated when architectural patterns change
- **Skills**: Updated when best practices evolve
- **Rules**: NEVER updated (requires manual review)

### Example Flow
```
1. Task completes with new pattern
2. Orchestrator detects deviation
3. Calls LLM to analyze change
4. Updates relevant wiki page
5. Future tasks use updated context
```

## Directory Structure

```
.qoder/
├── wiki/
│   ├── backend-architecture.md
│   ├── frontend-patterns.md
│   └── database-schema.md
├── skills/
│   ├── backend-dev/
│   │   └── SKILL.md
│   └── frontend-dev/
│       └── SKILL.md
└── rules.md
```

## Benefits

1. **Consistency**: All tasks follow documented patterns
2. **Learning**: System improves as patterns evolve
3. **Onboarding**: New contributors see current best practices
4. **Traceability**: Changes to approach are documented
