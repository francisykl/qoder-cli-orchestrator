import os
import json
import subprocess
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class Task:
    id: str
    description: str
    subagent: str
    dependencies: List[str] = field(default_factory=list)
    files_scope: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, hold
    output: Optional[str] = None
    component: str = "general" # backend, frontend, web, etc.

class IntegrationRegistry:
    """Tracks shared state like models and interfaces between components."""
    def __init__(self):
        self.shared_models: Dict[str, Any] = {}
        self.last_sync_timestamp: float = 0.0

    def register_model_update(self, component: str, model_name: str, schema: str):
        self.shared_models[model_name] = {"source": component, "schema": schema}
        self.last_sync_timestamp = time.time()
        print(f"--- [Integration] Model '{model_name}' updated by {component} ---")

class DecisionMaker:
    """Handles logic for when to continue, hold, or stop the orchestration."""
    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations

    def check_progress(self, iteration: int, tasks: Dict[str, Task], registry: IntegrationRegistry) -> str:
        """Returns 'proceed', 'hold', 'stop'."""
        if iteration >= self.max_iterations:
            return "stop"
        
        # Logic to check for integration issues (e.g., dead code, out-of-sync models)
        # In a real scenario, this would involve an LLM call.
        
        if any(t.status == "failed" for t in tasks.values()):
            return "hold" # Pause for user intervention on failure
            
        # Example condition: If backend updated a model but frontend tasks aren't aware
        # we might need to inject a 'sync' task and 'proceed'.
        
        if all(t.status == "completed" for t in tasks.values()):
            return "stop"
            
        return "proceed"

class Orchestrator:
    def __init__(self, prompt: str):
        self.original_prompt = prompt
        self.tasks: Dict[str, Task] = {}
        self.registry = IntegrationRegistry()
        self.decision_maker = DecisionMaker()
        self.current_iteration = 0
        self.pat = self._get_pat()
        self._ensure_qoder_cli()

    def _get_pat(self) -> str:
        """Retrieve Qoder PAT from .env.local or prompt user."""
        pat = None
        if os.path.exists(".env.local"):
            with open(".env.local", "r") as f:
                for line in f:
                    if line.startswith("qoder_pat="):
                        pat = line.split("=")[1].strip()
                        break
        
        if not pat:
            pat = input("Enter your 'qoder_pat': ")
            # Optionally save to .env.local
            with open(".env.local", "a") as f:
                f.write(f"\nqoder_pat={pat}\n")
        return pat

    def _ensure_qoder_cli(self):
        """Install or verify Qoder CLI."""
        try:
            subprocess.run(["qoder", "--version"], check=True, capture_output=True)
            print("--- Qoder CLI verified ---")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("--- Qoder CLI not found. Installing... ---")
            # In real environment, might run: npm install -g qoder
            # subprocess.run(["npm", "install", "-g", "qoder"], check=True)
            print("--- Simulated: Qoder CLI Installed ---")

    def plan_and_split(self):
        print(f"--- Planning Phase: Iteration {self.current_iteration} ---")
        # Logic to split including cross-component awareness
        self.tasks = {
            "t1": Task("t1", "Define User model and migration (Backend)", "backend-dev", [], ["backend/models.py"], component="backend"),
            "t2": Task("t2", "Update User Profile UI to use User model (Frontend)", "frontend-dev", ["t1"], ["app/frontend/user_profile.js"], component="frontend"),
            "t3": Task("t3", "Audit and remove dead code in user management", "architect", ["t2"], ["app/shared/utils.js"], component="general")
        }

    def run_task(self, task: Task):
        print(f"--- [Subagent: {task.subagent}] Executing: {task.description} ---")
        task.status = "running"
        
        # Integration logic: Mocking model update
        if task.component == "backend" and "model" in task.description.lower():
            self.registry.register_model_update(task.component, "User", "{id: int, name: string}")

        # Invoke Qoder:
        # env = os.environ.copy()
        # env["QODER_PAT"] = self.pat
        # subprocess.run(["qoder", "/agent", task.subagent, task.description], env=env)
        
        time.sleep(1)
        task.status = "completed"

    def execute_loop(self):
        while True:
            decision = self.decision_maker.check_progress(self.current_iteration, self.tasks, self.registry)
            
            if decision == "stop":
                print("--- Orchestration Finished ---")
                break
            elif decision == "hold":
                print("--- Orchestration on HOLD. Waiting for user input or fix. ---")
                # User could provide feedback here
                break
            
            ready_tasks = [t for t in self.tasks.values() if t.status == "pending" and all(self.tasks[d].status == "completed" for d in t.dependencies)]
            
            for task in ready_tasks:
                self.run_task(task)
            
            self.current_iteration += 1

if __name__ == "__main__":
    orch = Orchestrator("Modernize the user profile system with cross-component sync.")
    orch.plan_and_split()
    orch.execute_loop()
