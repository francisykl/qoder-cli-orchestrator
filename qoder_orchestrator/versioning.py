#!/usr/bin/env python3
"""
Context versioning and dependency fingerprinting.
Tracks which versions of wiki/skills were used for each task.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Set
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ContextVersion:
    """Version information for context."""
    wiki_hashes: Dict[str, str] = field(default_factory=dict)
    skill_hashes: Dict[str, str] = field(default_factory=dict)
    rules_hash: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class TaskVersionRecord:
    """Record of context versions used for a task."""
    task_id: str
    context_version: ContextVersion
    dependencies_hash: str
    files_hash: str


class VersionTracker:
    """Tracks context versions and detects changes."""
    
    def __init__(self, project_dir: Path):
        """
        Initialize version tracker.
        
        Args:
            project_dir: Project directory path
        """
        self.project_dir = project_dir
        self.version_file = project_dir / "specs" / "context_versions.json"
        self.task_versions: Dict[str, TaskVersionRecord] = {}
        self._load()
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _compute_file_hash(self, file_path: Path) -> Optional[str]:
        """Compute hash of file content."""
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash file {file_path}: {e}")
            return None
    
    def capture_context_version(
        self,
        wiki_content: Dict[str, str],
        skills: Dict[str, str],
        rules: str
    ) -> ContextVersion:
        """
        Capture current version of context.
        
        Args:
            wiki_content: Dictionary of wiki pages
            skills: Dictionary of skills
            rules: Rules content
            
        Returns:
            ContextVersion with hashes
        """
        import time
        
        version = ContextVersion(timestamp=time.time())
        
        # Hash wiki pages
        for name, content in wiki_content.items():
            version.wiki_hashes[name] = self._compute_hash(content)
        
        # Hash skills
        for name, content in skills.items():
            version.skill_hashes[name] = self._compute_hash(content)
        
        # Hash rules
        if rules:
            version.rules_hash = self._compute_hash(rules)
        
        return version
    
    def record_task_version(
        self,
        task_id: str,
        context_version: ContextVersion,
        dependencies: list,
        files_scope: list
    ):
        """
        Record context version used for a task.
        
        Args:
            task_id: Task identifier
            context_version: Context version used
            dependencies: Task dependencies
            files_scope: Files in task scope
        """
        # Hash dependencies and files
        deps_hash = self._compute_hash(json.dumps(sorted(dependencies)))
        files_hash = self._compute_hash(json.dumps(sorted(files_scope)))
        
        record = TaskVersionRecord(
            task_id=task_id,
            context_version=context_version,
            dependencies_hash=deps_hash,
            files_hash=files_hash
        )
        
        self.task_versions[task_id] = record
        self._save()
        
        logger.debug(f"Recorded context version for task {task_id}")
    
    def has_context_changed(
        self,
        task_id: str,
        current_version: ContextVersion
    ) -> bool:
        """
        Check if context has changed since task was executed.
        
        Args:
            task_id: Task identifier
            current_version: Current context version
            
        Returns:
            True if context changed, False otherwise
        """
        if task_id not in self.task_versions:
            return True
        
        old_version = self.task_versions[task_id].context_version
        
        # Check wiki changes
        if old_version.wiki_hashes != current_version.wiki_hashes:
            return True
        
        # Check skill changes
        if old_version.skill_hashes != current_version.skill_hashes:
            return True
        
        # Check rules changes
        if old_version.rules_hash != current_version.rules_hash:
            return True
        
        return False
    
    def get_affected_tasks(
        self,
        changed_wiki: Set[str],
        changed_skills: Set[str],
        rules_changed: bool
    ) -> Set[str]:
        """
        Get tasks affected by context changes.
        
        Args:
            changed_wiki: Set of changed wiki page names
            changed_skills: Set of changed skill names
            rules_changed: Whether rules changed
            
        Returns:
            Set of affected task IDs
        """
        affected = set()
        
        for task_id, record in self.task_versions.items():
            version = record.context_version
            
            # Check if task used changed wiki pages
            if any(wiki in version.wiki_hashes for wiki in changed_wiki):
                affected.add(task_id)
                continue
            
            # Check if task used changed skills
            if any(skill in version.skill_hashes for skill in changed_skills):
                affected.add(task_id)
                continue
            
            # Check if rules changed (affects all tasks)
            if rules_changed and version.rules_hash:
                affected.add(task_id)
        
        return affected
    
    def compute_file_fingerprint(self, file_paths: list) -> str:
        """
        Compute fingerprint for a set of files.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Combined hash of all files
        """
        hashes = []
        
        for file_path in sorted(file_paths):
            path = self.project_dir / file_path
            file_hash = self._compute_file_hash(path)
            if file_hash:
                hashes.append(file_hash)
        
        combined = "|".join(hashes)
        return self._compute_hash(combined)
    
    def should_reexecute_task(
        self,
        task_id: str,
        current_context: ContextVersion,
        current_files: list
    ) -> bool:
        """
        Determine if task should be re-executed based on changes.
        
        Args:
            task_id: Task identifier
            current_context: Current context version
            current_files: Current file list
            
        Returns:
            True if task should be re-executed
        """
        if task_id not in self.task_versions:
            return True
        
        record = self.task_versions[task_id]
        
        # Check context changes
        if self.has_context_changed(task_id, current_context):
            logger.info(f"Task {task_id} needs re-execution: context changed")
            return True
        
        # Check file changes
        current_files_hash = self.compute_file_fingerprint(current_files)
        if record.files_hash != current_files_hash:
            logger.info(f"Task {task_id} needs re-execution: files changed")
            return True
        
        return False
    
    def _load(self):
        """Load version records from disk."""
        if not self.version_file.exists():
            return
        
        try:
            with open(self.version_file, 'r') as f:
                data = json.load(f)
            
            for task_id, record_data in data.items():
                context_data = record_data['context_version']
                context = ContextVersion(
                    wiki_hashes=context_data.get('wiki_hashes', {}),
                    skill_hashes=context_data.get('skill_hashes', {}),
                    rules_hash=context_data.get('rules_hash'),
                    timestamp=context_data.get('timestamp', 0.0)
                )
                
                self.task_versions[task_id] = TaskVersionRecord(
                    task_id=task_id,
                    context_version=context,
                    dependencies_hash=record_data['dependencies_hash'],
                    files_hash=record_data['files_hash']
                )
            
            logger.info(f"Loaded version records for {len(self.task_versions)} tasks")
            
        except Exception as e:
            logger.warning(f"Failed to load version records: {e}")
    
    def _save(self):
        """Save version records to disk."""
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {}
            for task_id, record in self.task_versions.items():
                data[task_id] = {
                    'task_id': task_id,
                    'context_version': asdict(record.context_version),
                    'dependencies_hash': record.dependencies_hash,
                    'files_hash': record.files_hash
                }
            
            with open(self.version_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved version records for {len(self.task_versions)} tasks")
            
        except Exception as e:
            logger.warning(f"Failed to save version records: {e}")
