#!/usr/bin/env python3
"""
Subagent Orchestration Script
Splits high-level prompts into tasks and executes them via Qoder CLI subagents.
"""

import os
import sys
import json
import subprocess
import time
import argparse
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import load_config, OrchestratorConfig
from .llm_client import create_llm_client
from .context_cache import ContextCache

# Initial logging setup (will be reconfigured per orchestrator instance)
logger = logging.getLogger(__name__)

@dataclass
class Task:
    """Represents a single task in the orchestration."""
    id: str
    description: str
    subagent: str
    dependencies: List[str] = field(default_factory=list)
    files_scope: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, hold
    output: Optional[str] = None
    component: str = "general"  # backend, frontend, web, etc.
    error: Optional[str] = None

class QoderContext:
    """Manages Qoder wiki, skills, rules, and subagent metadata for the project."""
    def __init__(self, project_dir: Path, config: Optional[OrchestratorConfig] = None):
        self.project_dir = project_dir
        self.config = config or load_config(project_dir=project_dir)
        self.wiki_dir = project_dir / ".qoder" / "wiki"
        self.skills_dir = project_dir / ".qoder" / "skills"
        self.rules_file = project_dir / ".qoder" / "rules.md"
        self.wiki_content: Dict[str, str] = {}
        self.skills: Dict[str, str] = {}
        self.rules: str = ""
        self.subagents: Dict[str, str] = {}  # Full content including frontmatter
        self.subagent_metadata: Dict[str, Dict[str, Any]] = {}  # Parsed metadata
        
        # Initialize context cache in project directory
        cache_dir = self.project_dir / self.config.cache.cache_dir
        self.cache = ContextCache(self.config.cache, cache_dir=cache_dir)
        
        self._load_all()

    def _load_all(self):
        """Load wiki, skills, and rules from disk."""
        # Load wiki
        if self.wiki_dir.exists():
            for wiki_file in self.wiki_dir.glob("*.md"):
                with open(wiki_file, 'r') as f:
                    self.wiki_content[wiki_file.stem] = f.read()
            logger.info(f"Loaded {len(self.wiki_content)} wiki pages")
        
        # Load skills
        if self.skills_dir.exists():
            for skill_dir in self.skills_dir.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        with open(skill_file, 'r') as f:
                            self.skills[skill_dir.name] = f.read()
            logger.info(f"Loaded {len(self.skills)} skills")
        
        # Load rules
        if self.rules_file.exists():
            with open(self.rules_file, 'r') as f:
                self.rules = f.read()
            logger.info("Loaded project rules")
        
        # Load Subagents from root directory
        subagents_path = self.project_dir / "subagents"
        if subagents_path.exists():
            for subagent_file in subagents_path.glob("*.md"):
                with open(subagent_file, 'r') as f:
                    content = f.read()
                    name = subagent_file.stem
                    self.subagents[name] = content
                    # Parse YAML frontmatter
                    metadata = self._parse_frontmatter(content)
                    if metadata:
                        self.subagent_metadata[name] = metadata
            logger.info(f"Loaded {len(self.subagents)} subagents with metadata")

    def update_wiki(self, page_name: str, content: str, reason: str):
        """Update a wiki page when content strays."""
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        wiki_file = self.wiki_dir / f"{page_name}.md"
        
        with open(wiki_file, 'w') as f:
            f.write(content)
        
        self.wiki_content[page_name] = content
        logger.info(f"Updated wiki page '{page_name}': {reason}")

    def update_skill(self, skill_name: str, content: str, reason: str):
        """Update a skill when approach changes."""
        skill_dir = self.skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        
        with open(skill_file, 'w') as f:
            f.write(content)
        
        self.skills[skill_name] = content
        logger.info(f"Updated skill '{skill_name}': {reason}")

    def _parse_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse YAML frontmatter from markdown content."""
        import yaml
        
        if not content.startswith('---'):
            return None
        
        try:
            # Extract frontmatter between --- markers
            parts = content.split('---', 2)
            if len(parts) < 3:
                return None
            
            frontmatter_text = parts[1].strip()
            metadata = yaml.safe_load(frontmatter_text)
            return metadata
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter: {e}")
            return None
    
    def get_subagent_metadata(self, subagent_name: str) -> Optional[Dict[str, Any]]:
        """Get parsed metadata for a subagent."""
        return self.subagent_metadata.get(subagent_name)
    
    def match_subagent_to_task(self, task_description: str, task_type: Optional[str] = None) -> str:
        """Match a task to the most appropriate subagent based on capabilities."""
        # Simple keyword matching for now
        # In production, this would use LLM-based matching
        
        task_lower = task_description.lower()
        
        # Check for specific keywords
        if any(kw in task_lower for kw in ['discovery', 'analyze', 'analysis', 'research', 'audit', 'gap-analysis', 'investigate', 'find', 'explore']):
            return 'discovery-specialist'
        elif any(kw in task_lower for kw in ['database', 'migration', 'schema', 'query', 'sql']):
            return 'database-specialist'
        elif any(kw in task_lower for kw in ['test', 'testing', 'unit test', 'integration test', 'e2e']):
            return 'testing-specialist'
        elif any(kw in task_lower for kw in ['docker', 'deploy', 'ci/cd', 'kubernetes', 'infrastructure']):
            return 'devops-specialist'
        elif any(kw in task_lower for kw in ['security', 'auth', 'authentication', 'authorization', 'vulnerability']):
            return 'security-specialist'
        elif any(kw in task_lower for kw in ['documentation', 'readme', 'docs', 'api doc']):
            return 'documentation-specialist'
        elif any(kw in task_lower for kw in ['api design', 'rest', 'graphql', 'endpoint']):
            return 'api-designer'
        elif any(kw in task_lower for kw in ['performance', 'optimize', 'slow', 'cache', 'profiling']):
            return 'performance-specialist'
        elif any(kw in task_lower for kw in ['migrate', 'refactor', 'upgrade', 'legacy']):
            return 'migration-specialist'
        elif any(kw in task_lower for kw in ['backend', 'api', 'server', 'service']):
            return 'backend-dev'
        elif any(kw in task_lower for kw in ['frontend', 'ui', 'component', 'react', 'vue', 'flutter']):
            return 'frontend-dev'
        elif any(kw in task_lower for kw in ['architecture', 'design', 'structure', 'system']):
            return 'architect'
        
        # Default to architect for planning tasks
        return 'architect'
    
    def get_codebase_summary(self, llm_client: Any, force: bool = False) -> str:
        """
        Get or generate a high-level codebase summary, using cache if available.
        """
        cache_key = "codebase_summary_v1"
        
        if not force:
            cached_summary = self.cache.get(cache_key)
            if cached_summary:
                logger.info("Using cached codebase summary")
                return cached_summary
        
        logger.info("Generating fresh codebase summary analysis...")
        summary = llm_client.analyze_codebase(str(self.project_dir))
        
        self.cache.put(summary, cache_key)
        return summary
    
    def get_context_for_task(self, task: 'Task') -> str:
        """Build context string for a task including relevant wiki/skills/rules."""
        context_parts = []
        
        # Add rules (always included)
        if self.rules:
            context_parts.append(f"# Project Rules\n{self.rules}")
        
        # Add relevant wiki pages (based on component)
        relevant_wiki = []
        for page_name, content in self.wiki_content.items():
            if task.component.lower() in page_name.lower():
                relevant_wiki.append(f"## Wiki: {page_name}\n{content}")
        if relevant_wiki:
            context_parts.append("# Relevant Wiki Pages\n" + "\n\n".join(relevant_wiki))
        
        # Add relevant skills
        if task.subagent in self.skills:
            context_parts.append(f"# Skill: {task.subagent}\n{self.skills[task.subagent]}")
            
        # Add Subagent Instructions
        if task.subagent in self.subagents:
            context_parts.append(f"# Subagent Instructions: {task.subagent}\n{self.subagents[task.subagent]}")
        
        return "\n\n---\n\n".join(context_parts)

    def get_all_subagents_summary(self) -> str:
        """Get a concise summary of all available subagents and their capabilities."""
        summary_parts = ["# Available Subagents"]
        
        for name, metadata in self.subagent_metadata.items():
            desc = metadata.get('description', 'No description available')
            summary_parts.append(f"## {name}\n**Description**: {desc}")
            
            if 'capabilities' in metadata:
                summary_parts.append("**Capabilities**:")
                for cap in metadata['capabilities']:
                    summary_parts.append(f"- {cap}")
            
            if 'task_types' in metadata:
                summary_parts.append(f"**Best for**: {', '.join(metadata['task_types'])}")
            
            summary_parts.append("")
            
        return "\n".join(summary_parts)
    
    def build_enhanced_prompt(self, task: 'Task', iteration: int = 0, dependency_outputs: Optional[Dict[str, str]] = None) -> str:
        """Build an enhanced, structured prompt with task metadata and context."""
        prompt_parts = []
        
        # Task header
        prompt_parts.append(f"# Task: {task.description}")
        prompt_parts.append(f"**Task ID**: {task.id}")
        prompt_parts.append(f"**Component**: {task.component}")
        prompt_parts.append(f"**Iteration**: {iteration}")
        
        # Dependencies
        if task.dependencies:
            prompt_parts.append(f"**Dependencies**: {', '.join(task.dependencies)} (must be completed first)")
            
            # Add dependency outputs if available
            if dependency_outputs:
                relevant_outputs = {tid: out for tid, out in dependency_outputs.items() if tid in task.dependencies}
                if relevant_outputs:
                    prompt_parts.append("\n### Dependency Outputs")
                    for tid, output in relevant_outputs.items():
                        prompt_parts.append(f"#### Output from {tid}:")
                        # Truncate if too long to avoid exceeding context window
                        if len(output) > 5000:
                            output = output[:5000] + "\n... (further output truncated) ..."
                        prompt_parts.append(output)
        
        # File scope
        if task.files_scope:
            prompt_parts.append(f"**Files in Scope**: {', '.join(task.files_scope)}")
        
        # Subagent metadata
        metadata = self.get_subagent_metadata(task.subagent)
        if metadata:
            prompt_parts.append("\n## Your Role and Capabilities")
            prompt_parts.append(f"You are a **{metadata.get('name', task.subagent)}**: {metadata.get('description', '')}")
            
            if 'capabilities' in metadata:
                prompt_parts.append("\n**Your Capabilities:**")
                for cap in metadata['capabilities']:
                    prompt_parts.append(f"- {cap}")
        
        # Context from wiki/skills/rules
        context = self.get_context_for_task(task)
        if context:
            prompt_parts.append("\n## Project Context")
            prompt_parts.append(context)
        
        # Success criteria
        prompt_parts.append("\n## Success Criteria")
        prompt_parts.append("- Complete the task as described")
        prompt_parts.append("- Follow project rules and best practices")
        prompt_parts.append("- Ensure code is tested and documented")
        prompt_parts.append("- Report any deviations from documented approaches")
        
        return "\n\n".join(prompt_parts)

class IntegrationRegistry:
    """Tracks shared state like models and interfaces between components."""
    def __init__(self):
        self.shared_models: Dict[str, Any] = {}
        self.last_sync_timestamp: float = 0.0
        self.registry_file = "specs/integration_registry.json"
        self._load()

    def _load(self):
        """Load existing registry from disk."""
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
                self.shared_models = data.get('models', {})
                self.last_sync_timestamp = data.get('timestamp', 0.0)

    def _save(self):
        """Save registry to disk."""
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        with open(self.registry_file, 'w') as f:
            json.dump({
                'models': self.shared_models,
                'timestamp': self.last_sync_timestamp
            }, f, indent=2)

    def register_model_update(self, component: str, model_name: str, schema: str):
        """Register a model update from a component."""
        self.shared_models[model_name] = {
            "source": component,
            "schema": schema,
            "updated_at": time.time()
        }
        self.last_sync_timestamp = time.time()
        self._save()
        logger.info(f"[Integration] Model '{model_name}' updated by {component}")

class DecisionMaker:
    """Handles logic for when to continue, hold, or stop the orchestration."""
    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations

    def check_progress(self, iteration: int, tasks: Dict[str, Task], registry: IntegrationRegistry) -> str:
        """
        Returns 'proceed', 'hold', or 'stop'.
        
        Args:
            iteration: Current iteration number
            tasks: Dictionary of all tasks
            registry: Integration registry
            
        Returns:
            Decision string: 'proceed', 'hold', or 'stop'
        """
        if iteration >= self.max_iterations:
            logger.warning(f"Max iterations ({self.max_iterations}) reached")
            return "stop"
        
        # Check for failures
        failed_tasks = [t for t in tasks.values() if t.status == "failed"]
        if failed_tasks:
            logger.error(f"Tasks failed: {[t.id for t in failed_tasks]}")
            return "hold"
            
        # Check if all completed
        if all(t.status == "completed" for t in tasks.values()):
            logger.info("All tasks completed successfully")
            return "stop"
        
        # Check if we're stuck (no pending or running tasks, but not all completed)
        active_tasks = [t for t in tasks.values() if t.status in ["pending", "running"]]
        if not active_tasks:
            logger.warning("No active tasks but not all completed - possible deadlock")
            return "hold"
            
        return "proceed"

class Orchestrator:
    """Main orchestration engine."""
    
    def __init__(self, prompt: str, project_dir: str = "."):
        self.original_prompt = prompt
        self.project_dir = Path(project_dir).resolve()
        self.tasks: Dict[str, Task] = {}
        self.registry = IntegrationRegistry()
        self.config = load_config(project_dir=self.project_dir)
        self.qoder_context = QoderContext(self.project_dir, config=self.config)
        self.decision_maker = DecisionMaker()
        self.current_iteration = 0
        self._setup_logging()
        self._setup_output_dir()
        self.pat = self._get_pat()
        self._ensure_qoder_cli()
        
        # Initialize LLM client
        self.llm_client = create_llm_client(
            provider=self.config.llm.provider,
            timeout=self.config.execution.task_timeout
        )

    def _setup_logging(self):
        """Configure logging to use project directory."""
        log_file = self.project_dir / self.config.log_file
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        # Remove existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Configure new handlers
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file, mode='w'),  # Reset log file on each run
                logging.StreamHandler(sys.stdout)
            ],
            force=True
        )
        
        logger.info(f"Logging configured: {log_file}")
        logger.info(f"Log level: {self.config.log_level}")

    def _setup_output_dir(self):
        """Create output directory for task outputs."""
        self.output_dir = self.project_dir / self.config.execution.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Task outputs will be saved to: {self.output_dir}")

    def _get_pat(self) -> str:
        """Retrieve Qoder PAT from .env.local or prompt user."""
        env_file = self.project_dir / ".env.local"
        pat = None
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        if key in ["QODER_PERSONAL_ACCESS_TOKEN", "qoder_pat"]:
                            pat = val.strip()
                            logger.info(f"PAT loaded from .env.local ({key})")
                            break
        
        if not pat:
            logger.warning("PAT not found in .env.local")
            pat = input("Enter your 'qoder_pat': ").strip()
            
            # Save to .env.local
            with open(env_file, 'a') as f:
                f.write(f"\nQODER_PERSONAL_ACCESS_TOKEN={pat}\n")
            logger.info("PAT saved to .env.local as QODER_PERSONAL_ACCESS_TOKEN")
            
        return pat

    def _ensure_qoder_cli(self):
        """Verify Qoder CLI is installed."""
        try:
            result = subprocess.run(
                ["qoder", "--version"],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Qoder CLI verified: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error("Qoder CLI not found. Please install it first.")
            logger.error("Visit: https://docs.qoder.com for installation instructions")
            sys.exit(1)

    def plan_and_split(self):
        """
        Split the prompt into tasks using LLM.
        """
        logger.info(f"Planning Phase: Iteration {self.current_iteration}")
        logger.info(f"Original Prompt: {self.original_prompt}")
        
        # Get project context
        # 1. Get high-level codebase summary (cached)
        codebase_summary = self.qoder_context.get_codebase_summary(self.llm_client)
        
        # 2. Get specific context for splitting (rules, subagent summaries)
        subagents_summary = self.qoder_context.get_all_subagents_summary()
        dummy_task = Task("split", "Splitting tasks", "architect", component="general")
        context = self.qoder_context.get_context_for_task(dummy_task)
        
        # Combine for splitting
        full_context = f"{codebase_summary}\n\n{subagents_summary}\n\n{context}"
        
        # Call LLM to split tasks
        raw_tasks = self.llm_client.split_tasks(self.original_prompt, full_context)
        
        if not raw_tasks:
            logger.error("Failed to split tasks. Falling back to default tasks.")
            self.tasks = self._mock_task_split()
        else:
            # Convert raw dicts to Task objects
            self.tasks = {}
            for t in raw_tasks:
                task_id = t.get("id", f"t{len(self.tasks) + 1}")
                self.tasks[task_id] = Task(
                    id=task_id,
                    description=t.get("description", ""),
                    subagent=t.get("subagent", "architect"),
                    dependencies=t.get("dependencies", []),
                    files_scope=t.get("files_scope", []),
                    component=t.get("component", "general")
                )
            logger.info(f"Successfully split into {len(self.tasks)} atomic tasks")
        
        # Save the plan
        self._save_plan()

    def _mock_task_split(self) -> Dict[str, Task]:
        """Mock task splitting with discovery-first approach."""
        return {
            "t1": Task(
                "t1",
                "Analyze codebase for existing backend integration and feature gaps",
                "discovery-specialist",
                [],
                ["lib/**", "backend/**"],
                component="general"
            ),
            "t2": Task(
                "t2",
                "Define architectural changes and API contracts based on gap analysis",
                "architect",
                ["t1"],
                ["docs/architecture.md"],
                component="general"
            ),
            "t3": Task(
                "t3",
                "Implement backend services and models",
                "backend-dev",
                ["t2"],
                ["backend/api.py", "backend/models.py"],
                component="backend"
            ),
            "t4": Task(
                "t4",
                "Integrate frontend components with new backend services",
                "frontend-dev",
                ["t3"],
                ["lib/ui/**", "lib/providers/**"],
                component="frontend"
            )
        }

    def _save_plan(self):
        """Save the execution plan to disk."""
        plan_file = self.project_dir / "specs" / "plan.json"
        plan_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(plan_file, 'w') as f:
            json.dump({
                'prompt': self.original_prompt,
                'tasks': {tid: asdict(task) for tid, task in self.tasks.items()},
                'iteration': self.current_iteration
            }, f, indent=2)
        
        logger.info(f"Plan saved to {plan_file}")

    def refine_plan(self):
        """
        Re-evaluate the plan based on new information from completed tasks.
        Preserves completed tasks while potentially splitting remaining objectives.
        """
        logger.info(f"Refining Plan Phase: Iteration {self.current_iteration}")
        
        # 1. Get current project state (latest content, wiki, etc)
        codebase_summary = self.qoder_context.get_codebase_summary(self.llm_client, force=True)
        
        # 2. Get history of what happened so far
        completed_tasks_history = [
            {
                "id": t.id,
                "description": t.description,
                "output": t.output
            }
            for t in self.tasks.values() if t.status == "completed"
        ]
        
        # 3. Build a prompt for refinement
        refine_prompt = f"""Refine the execution plan based on new discovery results.
        
ORIGINAL OBJECTIVE:
{self.original_prompt}

COMPLETED TASKS SO FAR:
{json.dumps(completed_tasks_history, indent=2)}

LATEST CODEBASE CONTEXT:
{codebase_summary}

Based on the completed 'Discovery' or 'Analysis' tasks, split the remaining objectives into highly specific, file-level tasks.
DO NOT include tasks that are already completed.
Ensure dependencies correctly reference existing and new task IDs.
"""
        
        # 4. Call LLM to get refined tasks
        dummy_task = Task("refine", "Refining tasks", "architect", component="general")
        context = self.qoder_context.get_context_for_task(dummy_task)
        full_context = f"{codebase_summary}\n\n{context}"
        
        raw_refined_tasks = self.llm_client.split_tasks(refine_prompt, full_context)
        
        if not raw_refined_tasks:
            logger.warning("Plan refinement returned no new tasks. Keeping existing plan.")
            return

        # 5. Merge new tasks into existing task list
        # We keep "completed" and "running" tasks as they are
        preserved_tasks = {tid: t for tid, t in self.tasks.items() if t.status in ["completed", "running"]}
        
        # Add new refined tasks
        new_tasks = {}
        for t in raw_refined_tasks:
            task_id = t.get("id", f"r{len(new_tasks) + 1}")
            # Ensure we don't overwrite completed IDs unless explicitly desired
            if task_id in preserved_tasks:
                task_id = f"refined_{task_id}"
                
            new_tasks[task_id] = Task(
                id=task_id,
                description=t.get("description", ""),
                subagent=t.get("subagent", "architect"),
                dependencies=t.get("dependencies", []),
                files_scope=t.get("files_scope", []),
                component=t.get("component", "general")
            )
        
        self.tasks = {**preserved_tasks, **new_tasks}
        logger.info(f"Plan refined. Total tasks now: {len(self.tasks)}")
        self._save_plan()

    def _save_task_output(self, task_id: str, stdout: str, stderr: str, success: bool):
        """Save task output to file.
        
        Args:
            task_id: Task identifier
            stdout: Standard output from task
            stderr: Standard error from task
            success: Whether task succeeded
        """
        output_file = self.output_dir / f"{task_id}_output.txt"
        
        try:
            with open(output_file, 'w') as f:
                f.write(f"Task: {task_id}\n")
                f.write(f"Status: {'SUCCESS' if success else 'FAILED'}\n")
                f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                if stdout:
                    f.write("STDOUT:\n")
                    f.write("-" * 80 + "\n")
                    f.write(stdout)
                    f.write("\n" + "-" * 80 + "\n\n")
                
                if stderr:
                    f.write("STDERR:\n")
                    f.write("-" * 80 + "\n")
                    f.write(stderr)
                    f.write("\n" + "-" * 80 + "\n")
            
            logger.debug(f"[{task_id}] Output saved to {output_file}")
        except Exception as e:
            logger.warning(f"[{task_id}] Failed to save output to file: {e}")

    def get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to execute."""
        ready = []
        running_files = set()
        
        # Collect files being worked on
        for t in self.tasks.values():
            if t.status == "running":
                running_files.update(t.files_scope)

        for t in self.tasks.values():
            if t.status == "pending":
                # Check dependencies
                deps_met = all(
                    self.tasks[d].status == "completed"
                    for d in t.dependencies
                )
                
                # Check file conflicts
                conflict = any(f in running_files for f in t.files_scope)
                
                if deps_met and not conflict:
                    ready.append(t)
        
        return ready

    def run_task(self, task: Task) -> Task:
        """Execute a single task via Qoder CLI."""
        logger.info(f"[{task.id}] Starting: {task.description}")
        task.status = "running"
        
        # Retry logic
        max_attempts = self.config.retry.max_attempts
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            logger.info(f"[{task.id}] Attempt {attempt}/{max_attempts}")
            
            try:
                # Prepare dependency outputs
                dependency_outputs = {
                    tid: self.tasks[tid].output 
                    for tid in task.dependencies 
                    if tid in self.tasks and self.tasks[tid].output
                }
                
                # Build enhanced prompt with task metadata and context
                enhanced_description = self.qoder_context.build_enhanced_prompt(
                    task, 
                    iteration=self.current_iteration,
                    dependency_outputs=dependency_outputs
                )
                
                # Prepare environment
                env = os.environ.copy()
                env["QODER_PERSONAL_ACCESS_TOKEN"] = self.pat
                
                # Build command
                cmd = ["qoder", "--yolo", "-p", enhanced_description]
                
                # Add optional Qoder CLI parameters
                if self.config.llm.model:
                    cmd.extend(["--model", self.config.llm.model])
                
                if self.config.llm.max_output_tokens:
                    cmd.extend(["--max-output-tokens", self.config.llm.max_output_tokens])
                
                # Execute
                result = subprocess.run(
                    cmd,
                    cwd=str(self.project_dir),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=self.config.execution.task_timeout
                )
                
                if result.returncode == 0:
                    task.status = "completed"
                    task.output = result.stdout
                    logger.info(f"[{task.id}] Completed successfully")
                    logger.debug(f"[{task.id}] Output:\n{result.stdout}")
                    if result.stderr:
                        logger.debug(f"[{task.id}] Stderr:\n{result.stderr}")
                    
                    # Save output to file
                    self._save_task_output(task.id, result.stdout, result.stderr, success=True)
                    
                    # Check if output indicates deviation from wiki/skills
                    self._check_and_update_context(task, result.stdout)
                    return task
                else:
                    task.status = "failed"
                    task.error = result.stderr
                    logger.error(f"[{task.id}] Failed: {result.stderr[:200]}...")  # Truncate error in main log
                    logger.debug(f"[{task.id}] Full stderr:\n{result.stderr}")
                    if result.stdout:
                        logger.debug(f"[{task.id}] Stdout:\n{result.stdout}")
                    
                    # Save output to file
                    self._save_task_output(task.id, result.stdout, result.stderr, success=False)
                    
            except subprocess.TimeoutExpired:
                task.status = "failed"
                task.error = f"Task timed out after {self.config.execution.task_timeout} seconds"
                logger.error(f"[{task.id}] Timeout")
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                logger.error(f"[{task.id}] Error: {e}")
            
            if attempt < max_attempts:
                wait_time = self.config.retry.backoff_factor ** attempt
                logger.info(f"[{task.id}] Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        return task

    def _check_and_update_context(self, task: Task, output: str):
        """Check if task output indicates deviation and update wiki/skills."""
        # Simple heuristic: look for deviation markers in output
        # In production, this would use LLM to analyze the output
        
        deviation_markers = [
            "different approach",
            "updated approach",
            "changed strategy",
            "new pattern",
            "deviation from"
        ]
        
        output_lower = output.lower()
        if any(marker in output_lower for marker in deviation_markers):
            logger.warning(f"[{task.id}] Detected potential deviation from documented approach")
            
            # TODO: In production, call LLM to:
            # 1. Analyze what changed
            # 2. Determine if wiki/skill should be updated
            # 3. Generate updated content
            # For now, just log it
            logger.info(f"[{task.id}] Consider updating wiki/skills based on this task's output")

    def _log_progress(self):
        """Log current orchestration progress."""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        running = sum(1 for t in self.tasks.values() if t.status == "running")
        failed = sum(1 for t in self.tasks.values() if t.status == "failed")
        pending = sum(1 for t in self.tasks.values() if t.status == "pending")
        
        logger.info("="*60)
        logger.info(f"PROGRESS: {completed}/{total} completed | {running} running | {pending} pending | {failed} failed")
        
        if running > 0:
            running_tasks = [t.id for t in self.tasks.values() if t.status == "running"]
            logger.info(f"Currently running: {', '.join(running_tasks)}")
        
        if completed > 0:
            completed_tasks = [t.id for t in self.tasks.values() if t.status == "completed"]
            logger.info(f"Completed tasks: {', '.join(completed_tasks)}")
        
        if failed > 0:
            failed_tasks = [(t.id, t.error) for t in self.tasks.values() if t.status == "failed"]
            logger.error("Failed tasks:")
            for task_id, error in failed_tasks:
                logger.error(f"  - {task_id}: {error}")
        
        logger.info("="*60)

    def execute_loop(self, max_parallel: int = 3):
        """
        Main execution loop with parallel task execution.
        
        Args:
            max_parallel: Maximum number of tasks to run in parallel
        """
        logger.info("Starting execution loop")
        logger.info(f"Configuration: timeout={self.config.execution.task_timeout}s, max_parallel={max_parallel}, max_iterations={self.config.execution.max_iterations}")
        self._log_progress()
        
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            while True:
                # Check if we should continue
                decision = self.decision_maker.check_progress(
                    self.current_iteration,
                    self.tasks,
                    self.registry
                )
                
                if decision == "stop":
                    logger.info("Orchestration finished")
                    self._log_progress()
                    break
                elif decision == "hold":
                    logger.warning("Orchestration on HOLD - manual intervention needed")
                    self._log_progress()
                    break
                
                # Get ready tasks
                ready_tasks = self.get_ready_tasks()
                
                if not ready_tasks:
                    logger.info("No ready tasks, waiting...")
                    time.sleep(1)
                    continue
                
                logger.info(f"\n--- Iteration {self.current_iteration + 1} ---")
                logger.info(f"Executing {len(ready_tasks)} tasks in parallel: {', '.join([t.id for t in ready_tasks])}")
                
                # Submit tasks
                futures = {
                    executor.submit(self.run_task, task): task
                    for task in ready_tasks
                }
                
                # Wait for completion
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                        self.tasks[result.id] = result
                    except Exception as e:
                        logger.error(f"Task {task.id} raised exception: {e}")
                        task.status = "failed"
                        task.error = str(e)
                
                # Check if any completed tasks provide new discovery info
                # If an 'architect' or 'discovery' task finished, we might want to re-plan
                should_replan = any(
                    t.status == "completed" and (t.subagent == "architect" or "analyze" in t.description.lower())
                    for t in ready_tasks
                )
                
                if should_replan and self.config.execution.enable_speculative: # Using speculative as a proxy for 'smart re-planning'
                    logger.info("Discovery task completed. Triggering plan refinement...")
                    self.refine_plan()
                else:
                    # Refresh codebase analysis cache for the next iteration
                    # This ensures the LLM sees the results of the previous tasks
                    logger.info("Refreshing codebase analysis cache...")
                    self.qoder_context.get_codebase_summary(self.llm_client, force=True)
                
                self.current_iteration += 1
                self._save_plan()
                self._log_progress()

    def print_summary(self):
        """Print execution summary."""
        print("\n" + "="*60)
        print("ORCHESTRATION SUMMARY")
        print("="*60)
        
        completed = [t for t in self.tasks.values() if t.status == "completed"]
        failed = [t for t in self.tasks.values() if t.status == "failed"]
        
        print(f"Total Tasks: {len(self.tasks)}")
        print(f"Completed: {len(completed)}")
        print(f"Failed: {len(failed)}")
        print(f"Iterations: {self.current_iteration}")
        
        if failed:
            print("\nFailed Tasks:")
            for t in failed:
                print(f"  - {t.id}: {t.description}")
                print(f"    Error: {t.error}")
        
        print("="*60 + "\n")

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Orchestrate development tasks using Qoder CLI subagents"
    )
    parser.add_argument(
        "prompt",
        help="High-level development prompt to execute"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory (default: current directory)"
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=3,
        help="Maximum parallel tasks (default: 3)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum iterations (default: 10)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="qoder-orchestrator 1.0.0",
        help="Show version and exit"
    )
    
    args = parser.parse_args()
    
    # Create orchestrator
    orch = Orchestrator(args.prompt, args.project_dir)
    orch.decision_maker.max_iterations = args.max_iterations
    
    # Execute
    orch.plan_and_split()
    orch.execute_loop(max_parallel=args.max_parallel)
    orch.print_summary()

if __name__ == "__main__":
    main()
