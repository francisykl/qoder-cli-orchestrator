#!/usr/bin/env python3
"""
LLM client abstraction for CLI-based AI tools.
Supports Qoder CLI, Claude CLI, and other command-line AI assistants.
"""

import json
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    raw_output: str
    success: bool
    error: Optional[str] = None


class CLIBasedLLMClient(ABC):
    """Abstract base class for CLI-based LLM clients."""
    
    def __init__(self, timeout: int = 60):
        """
        Initialize CLI-based LLM client.
        
        Args:
            timeout: Command timeout in seconds
        """
        self.timeout = timeout
        self._verify_installation()
    
    @abstractmethod
    def _verify_installation(self):
        """Verify the CLI tool is installed."""
        pass
    
    @abstractmethod
    def _build_command(self, prompt: str, **kwargs) -> List[str]:
        """Build the CLI command."""
        pass
    
    def execute(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Execute a prompt via the CLI tool.
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments for the CLI
            
        Returns:
            LLMResponse with the result
        """
        try:
            cmd = self._build_command(prompt, **kwargs)
            logger.debug(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                return LLMResponse(
                    content=result.stdout.strip(),
                    raw_output=result.stdout,
                    success=True
                )
            else:
                logger.error(f"CLI command failed: {result.stderr}")
                return LLMResponse(
                    content="",
                    raw_output=result.stderr,
                    success=False,
                    error=result.stderr
                )
                
        except subprocess.TimeoutExpired:
            error_msg = f"CLI command timed out after {self.timeout}s"
            logger.error(error_msg)
            return LLMResponse(
                content="",
                raw_output="",
                success=False,
                error=error_msg
            )
        except Exception as e:
            logger.error(f"CLI execution failed: {e}")
            return LLMResponse(
                content="",
                raw_output="",
                success=False,
                error=str(e)
            )
    
    @abstractmethod
    def split_tasks(self, prompt: str, context: str) -> List[Dict]:
        """Split a high-level prompt into granular tasks."""
        pass
    
    @abstractmethod
    def analyze_codebase(self, project_path: str) -> str:
        """Perform a high-level analysis of the codebase."""
        pass
    
    @abstractmethod
    def analyze_objective(
        self,
        original_prompt: str,
        completed_tasks: List[Dict],
        context: str
    ) -> Dict:
        """Analyze if objectives are met."""
        pass
    
    @abstractmethod
    def suggest_learning(
        self,
        task_description: str,
        task_output: str,
        existing_wiki: str
    ) -> Optional[str]:
        """Suggest wiki/skill updates based on task execution."""
        pass


class QoderCLIClient(CLIBasedLLMClient):
    """Qoder CLI-based LLM client."""
    
    def _verify_installation(self):
        """Verify Qoder CLI is installed."""
        try:
            result = subprocess.run(
                ["qoder", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Qoder CLI verified: {result.stdout.strip()}")
            else:
                raise RuntimeError("Qoder CLI not found or not working")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"Qoder CLI verification failed: {e}")
    
    def _build_command(self, prompt: str, **kwargs) -> List[str]:
        """Build Qoder CLI command."""
        cmd = ["qoder"]
        
        # Use --yolo to avoid interactive permission prompts
        cmd.append("--yolo")
        
        # Use -p (or --print) for non-interactive prompt
        cmd.append("-p")
        cmd.append(prompt)
        
        # Add output format if specified
        if "output_format" in kwargs:
            cmd.extend(["-f", kwargs["output_format"]])
            
        return cmd
    
    def split_tasks(self, prompt: str, context: str) -> List[Dict]:
        """
        Split tasks using Qoder CLI.
        
        Args:
            prompt: High-level objective
            context: Project context (wiki, skills, rules)
            
        Returns:
            List of task dictionaries
        """
        # Build a structured prompt for task splitting
        subagent_list = ", ".join([
            "architect", "backend-dev", "frontend-dev", "database-specialist",
            "testing-specialist", "devops-specialist", "security-specialist",
            "documentation-specialist", "api-designer", "performance-specialist",
            "migration-specialist", "discovery-specialist"
        ])
        
        task_split_prompt = f"""Analyze the provided high-level objective and project context to create a highly specific, granular execution plan.

OBJECTIVE:
{prompt}

PROJECT CONTEXT:
{context}

AVAILABLE SUBAGENTS:
{subagent_list}

### Planning Strategy:
1. **Discovery First**: IF the objective involves setting up new systems, migrating legacy code, or is otherwise broad/ambiguous, the VERY FIRST task(s) MUST be assigned to 'discovery-specialist'. Use them to audit the codebase, identify feature gaps, or research technical feasibility.
2. **Impact Analysis**: Identify exactly which files, components, and modules will be affected.
3. **Atomic Breakdown**: Split large migrations or feature additions into small, verifiable steps. AVOID generic tasks like "Build backend".
4. **Architect vs. Discovery**: Use 'discovery-specialist' to FIND information and gaps (e.g., "Audit backend for missing Supabase integration"). Use 'architect' to DESIGN new structures or define API contracts (e.g., "Design Supabase schema based on audit findings").
5. **Specific Descriptions**: Task descriptions MUST be actionable. **BAD**: "Setup server". **GOOD**: "Create .env file with Supabase credentials" or "Define 'users' table schema in Supabase".

### Requirements for each Task:
- **id**: Unique identifier (e.g., t1, t2).
- **description**: Must be specific. **INCLUDE** file paths when possible.
- **subagent**: One of the available subagents.
- **dependencies**: List of task IDs that MUST be completed before this one.
- **files_scope**: List of EXACT file paths or directory patterns.
- **component**: Categorize as backend, frontend, general, etc.

### Example Plan for "Add Auth":
[
  {{
    "id": "t1",
    "description": "Analyze existing auth flow and identify required Supabase edge functions",
    "subagent": "discovery-specialist",
    "dependencies": [],
    "files_scope": ["lib/auth/**"],
    "component": "backend"
  }},
  {{
    "id": "t2",
    "description": "Design Supabase Auth configuration and session management protocol",
    "subagent": "architect",
    "dependencies": ["t1"],
    "files_scope": ["docs/auth_design.md"],
    "component": "general"
  }}
]

Return a JSON array of tasks:
"""
        
        response = self.execute(task_split_prompt, output_format="json")
        
        if not response.success:
            logger.error("Task splitting failed")
            return []
        
        # Try to parse JSON from response
        try:
            content = response.content.strip()
            
            # 1. Try to extract JSON from markdown code blocks
            json_start = -1
            if "```json" in content:
                json_start = content.find("```json") + 7
            elif "```" in content:
                json_start = content.find("```") + 3
                
            if json_start != -1:
                json_end = content.find("```", json_start)
                if json_end != -1:
                    content = content[json_start:json_end].strip()
            
            # 2. If parsing fails, try to find the first '[' and last ']' 
            # (handles cases with preamble/postamble text)
            try:
                tasks = json.loads(content)
            except json.JSONDecodeError:
                start_idx = content.find("[")
                end_idx = content.rfind("]")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    content = content[start_idx:end_idx+1].strip()
                    tasks = json.loads(content)
                else:
                    raise # Re-raise to be caught by outer block
            
            logger.info(f"Successfully split into {len(tasks)} tasks")
            return tasks
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse task split response as JSON: {e}")
            logger.debug(f"Raw content was: {response.content}")
            return []

    def analyze_codebase(self, project_path: str) -> str:
        """
        Perform a high-level analysis of the codebase using Qoder CLI.
        """
        # We'll use a specific prompt designed to get a structural overview
        analysis_prompt = f"""Perform a high-level structural analysis of the codebase at {project_path}.
        
        Provide a summary including:
        1. Key components and their responsibilities
        2. Main folder structure
        3. Critical entry points (main scripts, apps)
        4. Important dependencies or tech stack used
        
        Keep it concise but informative for a development orchestrator.
        """
        
        response = self.execute(analysis_prompt)
        
        if not response.success:
            logger.error("Codebase analysis failed")
            return "Analysis failed."
            
        return response.content
    
    def analyze_objective(
        self,
        original_prompt: str,
        completed_tasks: List[Dict],
        context: str
    ) -> Dict:
        """
        Analyze if objectives are met using Qoder CLI.
        
        Args:
            original_prompt: Original user objective
            completed_tasks: List of completed tasks
            context: Current project state
            
        Returns:
            Dict with 'met' (bool) and 'reasoning' (str)
        """
        analysis_prompt = f"""Analyze if the original objective has been met based on completed tasks.

ORIGINAL OBJECTIVE:
{original_prompt}

COMPLETED TASKS:
{json.dumps(completed_tasks, indent=2)}

CURRENT PROJECT STATE:
{context}

Return a JSON object with this structure:
{{
  "met": true/false,
  "reasoning": "Explanation of why objectives are/aren't met",
  "missing": ["List of missing items if not met"],
  "next_steps": ["Suggested next steps if not met"]
}}
"""
        
        response = self.execute(analysis_prompt, output_format="json")
        
        if not response.success:
            return {"met": False, "reasoning": "Analysis failed", "missing": [], "next_steps": []}
        
        try:
            content = response.content
            
            # Extract JSON from markdown
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()
            
            result = json.loads(content)
            logger.info(f"Objective analysis: {result.get('met', False)}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse objective analysis: {e}")
            return {"met": False, "reasoning": "Parse error", "missing": [], "next_steps": []}
    
    def suggest_learning(
        self,
        task_description: str,
        task_output: str,
        existing_wiki: str
    ) -> Optional[str]:
        """
        Suggest wiki updates based on task execution.
        
        Args:
            task_description: What the task was supposed to do
            task_output: What actually happened
            existing_wiki: Current wiki content
            
        Returns:
            Suggested wiki update or None
        """
        learning_prompt = f"""Analyze this task execution and suggest wiki updates if the approach differs from documented patterns.

TASK:
{task_description}

EXECUTION OUTPUT:
{task_output}

EXISTING WIKI:
{existing_wiki}

If the execution revealed new patterns, better approaches, or important learnings, suggest a wiki update.
Return JSON:
{{
  "should_update": true/false,
  "suggested_content": "Updated wiki content if should_update is true",
  "reasoning": "Why this update is valuable"
}}
"""
        
        response = self.execute(learning_prompt, output_format="json")
        
        if not response.success:
            return None
        
        try:
            content = response.content
            
            # Extract JSON
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()
            
            result = json.loads(content)
            
            if result.get("should_update", False):
                logger.info(f"Learning suggestion: {result.get('reasoning', '')}")
                return result.get("suggested_content")
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse learning suggestion: {e}")
            return None


class ClaudeCLIClient(CLIBasedLLMClient):
    """Claude CLI-based LLM client."""
    
    def _verify_installation(self):
        """Verify Claude CLI is installed."""
        try:
            # Claude CLI might use 'claude' or 'claude-cli' command
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Claude CLI verified: {result.stdout.strip()}")
                self.cli_command = "claude"
            else:
                raise RuntimeError("Claude CLI not found or not working")
        except FileNotFoundError:
            # Try alternative command name
            try:
                result = subprocess.run(
                    ["claude-cli", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.cli_command = "claude-cli"
                    logger.info(f"Claude CLI verified: {result.stdout.strip()}")
                else:
                    raise RuntimeError("Claude CLI not found")
            except FileNotFoundError:
                raise RuntimeError("Claude CLI not installed. Install from: https://claude.ai/cli")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Claude CLI verification timed out: {e}")
    
    def _build_command(self, prompt: str, **kwargs) -> List[str]:
        """Build Claude CLI command."""
        cmd = [self.cli_command]
        
        # Claude CLI typically uses: claude "prompt"
        # or: claude --file context.txt "prompt"
        
        # Add context file if provided
        if "context_file" in kwargs:
            cmd.extend(["--file", kwargs["context_file"]])
        
        # Add the prompt
        cmd.append(prompt)
        
        return cmd
    
    def split_tasks(self, prompt: str, context: str) -> List[Dict]:
        """Split tasks using Claude CLI."""
        # Similar structure to Qoder but adapted for Claude CLI
        task_split_prompt = f"""Break down this objective into granular tasks.

OBJECTIVE: {prompt}

CONTEXT: {context}

Return JSON array of tasks with: id, description, subagent, dependencies, files_scope, component"""
        
        # Write context to temp file for Claude CLI
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(context)
            context_file = f.name
        
        try:
            response = self.execute(task_split_prompt, context_file=context_file)
            
            if not response.success:
                return []
            
            # Parse JSON from response
            content = response.content
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            
            tasks = json.loads(content)
            return tasks
            
        except Exception as e:
            logger.error(f"Claude task splitting failed: {e}")
            return []
        finally:
            # Clean up temp file
            Path(context_file).unlink(missing_ok=True)
    
    def analyze_objective(
        self,
        original_prompt: str,
        completed_tasks: List[Dict],
        context: str
    ) -> Dict:
        """Analyze objectives using Claude CLI."""
        # Similar to Qoder implementation
        analysis_prompt = f"""Has this objective been met?

OBJECTIVE: {original_prompt}
COMPLETED: {json.dumps(completed_tasks, indent=2)}

Return JSON: {{"met": bool, "reasoning": str, "missing": [], "next_steps": []}}"""
        
        response = self.execute(analysis_prompt)
        
        if not response.success:
            return {"met": False, "reasoning": "Analysis failed", "missing": [], "next_steps": []}
        
        try:
            content = response.content
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            
            return json.loads(content)
        except:
            return {"met": False, "reasoning": "Parse error", "missing": [], "next_steps": []}
    
    def suggest_learning(
        self,
        task_description: str,
        task_output: str,
        existing_wiki: str
    ) -> Optional[str]:
        """Suggest learning using Claude CLI."""
        learning_prompt = f"""Should we update the wiki based on this task?

TASK: {task_description}
OUTPUT: {task_output}
WIKI: {existing_wiki}

Return JSON: {{"should_update": bool, "suggested_content": str, "reasoning": str}}"""
        
        response = self.execute(learning_prompt)
        
        if not response.success:
            return None
        
        try:
            content = response.content
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            
            result = json.loads(content)
            if result.get("should_update"):
                return result.get("suggested_content")
        except:
            pass
        
        return None

    def analyze_codebase(self, project_path: str) -> str:
        """Analyze codebase using Claude CLI."""
        analysis_prompt = f"Analyze the following project structure and provide a high-level summary: {project_path}"
        response = self.execute(analysis_prompt)
        return response.content if response.success else "Analysis failed."


def create_llm_client(provider: str = "qoder", **kwargs) -> CLIBasedLLMClient:
    """
    Factory function to create LLM client.
    
    Args:
        provider: CLI tool to use ('qoder', 'claude')
        **kwargs: Additional arguments for the client
        
    Returns:
        CLIBasedLLMClient instance
    """
    provider = provider.lower()
    
    if provider == "qoder":
        return QoderCLIClient(**kwargs)
    elif provider == "claude":
        return ClaudeCLIClient(**kwargs)
    else:
        raise ValueError(f"Unsupported CLI provider: {provider}. Use 'qoder' or 'claude'")
