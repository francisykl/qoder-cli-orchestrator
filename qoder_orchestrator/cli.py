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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('orchestration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
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
    """Manages Qoder wiki, skills, and rules for the project."""
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.wiki_dir = project_dir / ".qoder" / "wiki"
        self.skills_dir = project_dir / ".qoder" / "skills"
        self.rules_file = project_dir / ".qoder" / "rules.md"
        self.wiki_content: Dict[str, str] = {}
        self.skills: Dict[str, str] = {}
        self.rules: str = ""
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
        
        return "\n\n---\n\n".join(context_parts)

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
        self.qoder_context = QoderContext(self.project_dir)
        self.decision_maker = DecisionMaker()
        self.current_iteration = 0
        self.pat = self._get_pat()
        self._ensure_qoder_cli()

    def _get_pat(self) -> str:
        """Retrieve Qoder PAT from .env.local or prompt user."""
        env_file = self.project_dir / ".env.local"
        pat = None
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip().startswith("qoder_pat="):
                        pat = line.split("=", 1)[1].strip()
                        logger.info("PAT loaded from .env.local")
                        break
        
        if not pat:
            logger.warning("PAT not found in .env.local")
            pat = input("Enter your 'qoder_pat': ").strip()
            
            # Save to .env.local
            with open(env_file, 'a') as f:
                f.write(f"\nqoder_pat={pat}\n")
            logger.info("PAT saved to .env.local")
            
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
        In production, this would call Qoder CLI to analyze the prompt.
        """
        logger.info(f"Planning Phase: Iteration {self.current_iteration}")
        logger.info(f"Original Prompt: {self.original_prompt}")
        
        # TODO: Replace with actual LLM call via Qoder CLI
        # For now, using a mock implementation
        self.tasks = self._mock_task_split()
        
        # Save the plan
        self._save_plan()

    def _mock_task_split(self) -> Dict[str, Task]:
        """Mock task splitting - replace with real LLM call."""
        return {
            "t1": Task(
                "t1",
                "Analyze project structure and define architecture",
                "architect",
                [],
                ["docs/architecture.md"],
                component="general"
            ),
            "t2": Task(
                "t2",
                "Implement backend API endpoints",
                "backend-dev",
                ["t1"],
                ["backend/api.py", "backend/models.py"],
                component="backend"
            ),
            "t3": Task(
                "t3",
                "Create frontend components",
                "frontend-dev",
                ["t1"],
                ["app/frontend/components/*.js"],
                component="frontend"
            ),
            "t4": Task(
                "t4",
                "Integrate frontend with backend API",
                "frontend-dev",
                ["t2", "t3"],
                ["app/frontend/api.js"],
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
        
        try:
            # Get context from wiki/skills/rules
            context = self.qoder_context.get_context_for_task(task)
            
            # Build enhanced description with context
            enhanced_description = f"""{task.description}

# Context from Project
{context}

IMPORTANT: Follow the project rules. If your approach differs from documented wiki/skills, note this in your output.
"""
            
            # Prepare environment
            env = os.environ.copy()
            env["QODER_PAT"] = self.pat
            
            # Build command
            cmd = ["qoder", "/agent", task.subagent, enhanced_description]
            
            # Execute
            result = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                task.status = "completed"
                task.output = result.stdout
                logger.info(f"[{task.id}] Completed successfully")
                
                # Check if output indicates deviation from wiki/skills
                self._check_and_update_context(task, result.stdout)
            else:
                task.status = "failed"
                task.error = result.stderr
                logger.error(f"[{task.id}] Failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            task.status = "failed"
            task.error = "Task timed out after 5 minutes"
            logger.error(f"[{task.id}] Timeout")
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            logger.error(f"[{task.id}] Error: {e}")
        
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

    def execute_loop(self, max_parallel: int = 3):
        """
        Main execution loop with parallel task execution.
        
        Args:
            max_parallel: Maximum number of tasks to run in parallel
        """
        logger.info("Starting execution loop")
        
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
                    break
                elif decision == "hold":
                    logger.warning("Orchestration on HOLD - manual intervention needed")
                    break
                
                # Get ready tasks
                ready_tasks = self.get_ready_tasks()
                
                if not ready_tasks:
                    logger.info("No ready tasks, waiting...")
                    time.sleep(1)
                    continue
                
                logger.info(f"Executing {len(ready_tasks)} tasks in parallel")
                
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
                
                self.current_iteration += 1
                self._save_plan()

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
