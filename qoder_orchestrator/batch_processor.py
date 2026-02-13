#!/usr/bin/env python3
"""
Batch processing for grouping similar tasks.
"""

import logging
from typing import List, Dict, Set
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TaskBatch:
    """A batch of similar tasks."""
    batch_id: str
    task_ids: List[str]
    common_component: str
    common_subagent: str
    similarity_score: float


class BatchProcessor:
    """Groups similar tasks for efficient batch execution."""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize batch processor.
        
        Args:
            similarity_threshold: Minimum similarity to group tasks (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def compute_task_similarity(self, task1: Dict, task2: Dict) -> float:
        """
        Compute similarity between two tasks.
        
        Args:
            task1: First task
            task2: Second task
            
        Returns:
            Similarity score (0-1)
        """
        score = 0.0
        weights = {
            'component': 0.3,
            'subagent': 0.3,
            'files': 0.2,
            'dependencies': 0.2
        }
        
        # Component similarity
        if task1.get('component') == task2.get('component'):
            score += weights['component']
        
        # Subagent similarity
        if task1.get('subagent') == task2.get('subagent'):
            score += weights['subagent']
        
        # File overlap
        files1 = set(task1.get('files_scope', []))
        files2 = set(task2.get('files_scope', []))
        if files1 and files2:
            overlap = len(files1 & files2) / len(files1 | files2)
            score += weights['files'] * overlap
        
        # Dependency overlap (tasks with shared dependencies are similar)
        deps1 = set(task1.get('dependencies', []))
        deps2 = set(task2.get('dependencies', []))
        if deps1 and deps2:
            overlap = len(deps1 & deps2) / len(deps1 | deps2)
            score += weights['dependencies'] * overlap
        
        return score
    
    def group_tasks(self, tasks: Dict[str, Dict]) -> List[TaskBatch]:
        """
        Group tasks into batches based on similarity.
        
        Args:
            tasks: Dictionary of task_id -> task
            
        Returns:
            List of TaskBatch objects
        """
        batches = []
        processed = set()
        batch_counter = 0
        
        task_list = list(tasks.items())
        
        for i, (task_id, task) in enumerate(task_list):
            if task_id in processed:
                continue
            
            # Start a new batch with this task
            batch_tasks = [task_id]
            processed.add(task_id)
            
            # Find similar tasks
            for j, (other_id, other_task) in enumerate(task_list[i+1:], start=i+1):
                if other_id in processed:
                    continue
                
                similarity = self.compute_task_similarity(task, other_task)
                
                if similarity >= self.similarity_threshold:
                    batch_tasks.append(other_id)
                    processed.add(other_id)
            
            # Create batch if we have multiple tasks
            if len(batch_tasks) > 1:
                batch = TaskBatch(
                    batch_id=f"batch_{batch_counter}",
                    task_ids=batch_tasks,
                    common_component=task.get('component', 'general'),
                    common_subagent=task.get('subagent', 'general'),
                    similarity_score=self.similarity_threshold
                )
                batches.append(batch)
                batch_counter += 1
                
                logger.info(
                    f"Created batch {batch.batch_id} with {len(batch_tasks)} tasks: "
                    f"{', '.join(batch_tasks)}"
                )
        
        return batches
    
    def can_batch_execute(self, batch: TaskBatch, tasks: Dict[str, Dict]) -> bool:
        """
        Check if a batch can be executed together.
        
        Args:
            batch: TaskBatch to check
            tasks: All tasks
            
        Returns:
            True if batch can execute together
        """
        # Check for file conflicts
        all_files = set()
        for task_id in batch.task_ids:
            task = tasks[task_id]
            task_files = set(task.get('files_scope', []))
            
            # If there's overlap, tasks might conflict
            if all_files & task_files:
                logger.warning(
                    f"Batch {batch.batch_id} has file conflicts, "
                    "cannot execute in parallel"
                )
                return False
            
            all_files.update(task_files)
        
        # Check for dependency conflicts
        for task_id in batch.task_ids:
            task = tasks[task_id]
            deps = set(task.get('dependencies', []))
            
            # If any dependency is in the batch, can't execute in parallel
            if deps & set(batch.task_ids):
                logger.warning(
                    f"Batch {batch.batch_id} has internal dependencies, "
                    "cannot execute in parallel"
                )
                return False
        
        return True
    
    def optimize_execution_order(
        self,
        batches: List[TaskBatch],
        tasks: Dict[str, Dict]
    ) -> List[List[str]]:
        """
        Optimize execution order for batches.
        
        Args:
            batches: List of task batches
            tasks: All tasks
            
        Returns:
            List of execution waves (each wave is a list of task IDs)
        """
        waves = []
        
        for batch in batches:
            if self.can_batch_execute(batch, tasks):
                # All tasks in batch can execute together
                waves.append(batch.task_ids)
            else:
                # Execute tasks sequentially
                for task_id in batch.task_ids:
                    waves.append([task_id])
        
        return waves


def create_batch_processor(config: Dict) -> BatchProcessor:
    """
    Create batch processor from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        BatchProcessor instance
    """
    threshold = config.get('batch_similarity_threshold', 0.7)
    return BatchProcessor(similarity_threshold=threshold)
