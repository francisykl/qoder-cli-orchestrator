#!/usr/bin/env python3
"""
Error handling and recovery mechanisms for Qoder orchestration.
Includes retry strategies, rollback management, and error classification.
"""

import time
import subprocess
from pathlib import Path
from typing import Optional, Callable, Any, List
from dataclasses import dataclass
import logging
import git

logger = logging.getLogger(__name__)


class TaskError(Exception):
    """Base exception for task errors."""
    def __init__(self, message: str, recoverable: bool = True):
        super().__init__(message)
        self.recoverable = recoverable


class TimeoutError(TaskError):
    """Task execution timeout."""
    def __init__(self, message: str):
        super().__init__(message, recoverable=True)


class NetworkError(TaskError):
    """Network-related error."""
    def __init__(self, message: str):
        super().__init__(message, recoverable=True)


class ValidationError(TaskError):
    """Validation failure."""
    def __init__(self, message: str):
        super().__init__(message, recoverable=False)


class DependencyError(TaskError):
    """Dependency not met."""
    def __init__(self, message: str):
        super().__init__(message, recoverable=False)


@dataclass
class RetryAttempt:
    """Record of a retry attempt."""
    attempt_number: int
    error: Exception
    backoff_seconds: float
    timestamp: float


class RetryStrategy:
    """Implements retry logic with exponential backoff."""
    
    def __init__(self, config: Any):
        """
        Initialize retry strategy.
        
        Args:
            config: RetryConfig instance
        """
        self.max_attempts = config.max_attempts
        self.backoff_factor = config.backoff_factor
        self.max_backoff = config.max_backoff
        self.retry_on_errors = config.retry_on_errors
        self.attempts: List[RetryAttempt] = []
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if we should retry after an error.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number (1-indexed)
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_attempts:
            logger.info(f"Max retry attempts ({self.max_attempts}) reached")
            return False
        
        # Check if error is recoverable
        if isinstance(error, TaskError) and not error.recoverable:
            logger.info(f"Error is not recoverable: {error}")
            return False
        
        # Check error type
        error_type = self._classify_error(error)
        if error_type not in self.retry_on_errors:
            logger.info(f"Error type '{error_type}' not in retry list")
            return False
        
        return True
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type."""
        if isinstance(error, TimeoutError):
            return "timeout"
        elif isinstance(error, NetworkError):
            return "network"
        elif isinstance(error, subprocess.TimeoutExpired):
            return "timeout"
        elif "connection" in str(error).lower():
            return "network"
        else:
            return "temporary"
    
    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate backoff time for retry attempt.
        
        Args:
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Backoff time in seconds
        """
        backoff = min(
            self.backoff_factor ** (attempt - 1),
            self.max_backoff
        )
        return backoff
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func
            
        Raises:
            Last exception if all retries fail
        """
        last_error = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.info(f"Attempt {attempt}/{self.max_attempts}")
                result = func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info(f"✓ Succeeded on attempt {attempt}")
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed: {e}")
                
                if not self.should_retry(e, attempt):
                    raise
                
                backoff = self.calculate_backoff(attempt)
                
                # Record attempt
                self.attempts.append(RetryAttempt(
                    attempt_number=attempt,
                    error=e,
                    backoff_seconds=backoff,
                    timestamp=time.time()
                ))
                
                logger.info(f"Retrying in {backoff:.1f} seconds...")
                time.sleep(backoff)
        
        # All retries failed
        logger.error(f"All {self.max_attempts} attempts failed")
        raise last_error


class RollbackManager:
    """Manages git-based checkpoints and rollbacks."""
    
    def __init__(self, project_dir: Path, config: Any):
        """
        Initialize rollback manager.
        
        Args:
            project_dir: Project directory path
            config: RollbackConfig instance
        """
        self.project_dir = project_dir
        self.enabled = config.enabled
        self.create_checkpoints = config.create_checkpoints
        self.keep_checkpoints = config.keep_checkpoints
        self.auto_rollback = config.auto_rollback_on_failure
        
        self.repo: Optional[git.Repo] = None
        self.checkpoints: List[str] = []
        
        if self.enabled:
            self._init_repo()
    
    def _init_repo(self):
        """Initialize git repository."""
        try:
            self.repo = git.Repo(self.project_dir)
            logger.info("Git repository initialized for rollback")
        except git.InvalidGitRepositoryError:
            logger.warning("Not a git repository - rollback disabled")
            self.enabled = False
    
    def create_checkpoint(self, task_id: str, description: str) -> Optional[str]:
        """
        Create a git checkpoint before task execution.
        
        Args:
            task_id: Task identifier
            description: Checkpoint description
            
        Returns:
            Checkpoint commit SHA or None if failed
        """
        if not self.enabled or not self.create_checkpoints:
            return None
        
        try:
            # Create a tag for the checkpoint
            tag_name = f"qoder-checkpoint-{task_id}"
            
            # Check if there are changes to commit
            if self.repo.is_dirty(untracked_files=True):
                # Stash changes
                logger.info("Stashing uncommitted changes")
                self.repo.git.stash("save", f"Qoder checkpoint: {description}")
            
            # Create tag at current HEAD
            tag = self.repo.create_tag(
                tag_name,
                message=f"Checkpoint before task {task_id}: {description}"
            )
            
            checkpoint_sha = str(tag.commit)
            self.checkpoints.append(checkpoint_sha)
            
            # Clean up old checkpoints
            self._cleanup_old_checkpoints()
            
            logger.info(f"Created checkpoint: {tag_name} ({checkpoint_sha[:8]})")
            return checkpoint_sha
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            return None
    
    def rollback_to_checkpoint(self, checkpoint_sha: str) -> bool:
        """
        Rollback to a specific checkpoint.
        
        Args:
            checkpoint_sha: Checkpoint commit SHA
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.warning("Rollback disabled")
            return False
        
        try:
            logger.warning(f"Rolling back to checkpoint {checkpoint_sha[:8]}")
            
            # Reset to checkpoint
            self.repo.git.reset("--hard", checkpoint_sha)
            
            # Try to pop stash if exists
            try:
                self.repo.git.stash("pop")
            except git.GitCommandError:
                pass  # No stash to pop
            
            logger.info("✓ Rollback successful")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def rollback_last_checkpoint(self) -> bool:
        """Rollback to the most recent checkpoint."""
        if not self.checkpoints:
            logger.warning("No checkpoints available for rollback")
            return False
        
        return self.rollback_to_checkpoint(self.checkpoints[-1])
    
    def _cleanup_old_checkpoints(self):
        """Remove old checkpoints beyond the keep limit."""
        if len(self.checkpoints) <= self.keep_checkpoints:
            return
        
        # Remove oldest checkpoints
        to_remove = self.checkpoints[:-self.keep_checkpoints]
        
        for checkpoint_sha in to_remove:
            try:
                # Find and delete tag
                for tag in self.repo.tags:
                    if str(tag.commit) == checkpoint_sha:
                        self.repo.delete_tag(tag)
                        logger.debug(f"Removed old checkpoint tag: {tag.name}")
                        break
            except Exception as e:
                logger.warning(f"Failed to remove old checkpoint: {e}")
        
        # Update checkpoint list
        self.checkpoints = self.checkpoints[-self.keep_checkpoints:]
    
    def get_checkpoint_info(self, checkpoint_sha: str) -> Optional[dict]:
        """Get information about a checkpoint."""
        if not self.enabled:
            return None
        
        try:
            commit = self.repo.commit(checkpoint_sha)
            return {
                "sha": checkpoint_sha,
                "message": commit.message,
                "author": str(commit.author),
                "timestamp": commit.committed_datetime.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get checkpoint info: {e}")
            return None


class ErrorRecoveryManager:
    """Coordinates retry and rollback strategies."""
    
    def __init__(self, retry_strategy: RetryStrategy, rollback_manager: RollbackManager):
        """
        Initialize error recovery manager.
        
        Args:
            retry_strategy: RetryStrategy instance
            rollback_manager: RollbackManager instance
        """
        self.retry_strategy = retry_strategy
        self.rollback_manager = rollback_manager
    
    def execute_task_with_recovery(
        self,
        task_id: str,
        task_description: str,
        task_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute task with full error recovery.
        
        Args:
            task_id: Task identifier
            task_description: Task description
            task_func: Function to execute
            *args: Positional arguments for task_func
            **kwargs: Keyword arguments for task_func
            
        Returns:
            Result of task_func
            
        Raises:
            Exception if task fails after all recovery attempts
        """
        # Create checkpoint
        checkpoint = self.rollback_manager.create_checkpoint(task_id, task_description)
        
        try:
            # Execute with retry
            result = self.retry_strategy.execute_with_retry(task_func, *args, **kwargs)
            return result
            
        except Exception as e:
            logger.error(f"Task {task_id} failed after all recovery attempts: {e}")
            
            # Auto-rollback if configured
            if self.rollback_manager.auto_rollback and checkpoint:
                logger.warning("Auto-rollback enabled, reverting changes...")
                self.rollback_manager.rollback_to_checkpoint(checkpoint)
            
            raise
