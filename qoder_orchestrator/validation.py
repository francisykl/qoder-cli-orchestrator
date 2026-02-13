#!/usr/bin/env python3
"""
Pre-flight validation for Qoder orchestration.
Validates project structure, dependencies, and environment before execution.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    severity: str  # "error", "warning", "info"
    category: str  # "git", "qoder", "dependencies", "structure"
    message: str
    fix_suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Report of validation results."""
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    
    def add_error(self, category: str, message: str, fix: Optional[str] = None):
        """Add an error to the report."""
        self.issues.append(ValidationIssue("error", category, message, fix))
        self.passed = False
    
    def add_warning(self, category: str, message: str, fix: Optional[str] = None):
        """Add a warning to the report."""
        self.issues.append(ValidationIssue("warning", category, message, fix))
    
    def add_info(self, category: str, message: str):
        """Add an info message to the report."""
        self.issues.append(ValidationIssue("info", category, message))
    
    def get_errors(self) -> List[ValidationIssue]:
        """Get all errors."""
        return [i for i in self.issues if i.severity == "error"]
    
    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warnings."""
        return [i for i in self.issues if i.severity == "warning"]
    
    def print_report(self):
        """Print formatted validation report."""
        if self.passed and not self.issues:
            logger.info("✓ All validation checks passed")
            return
        
        print("\n" + "="*60)
        print("VALIDATION REPORT")
        print("="*60)
        
        errors = self.get_errors()
        warnings = self.get_warnings()
        
        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            for issue in errors:
                print(f"  [{issue.category}] {issue.message}")
                if issue.fix_suggestion:
                    print(f"    → Fix: {issue.fix_suggestion}")
        
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for issue in warnings:
                print(f"  [{issue.category}] {issue.message}")
                if issue.fix_suggestion:
                    print(f"    → Suggestion: {issue.fix_suggestion}")
        
        print("\n" + "="*60 + "\n")


class PreFlightValidator:
    """Validates environment and project structure before orchestration."""
    
    def __init__(self, project_dir: Path, config: Any):
        """
        Initialize validator.
        
        Args:
            project_dir: Project directory path
            config: OrchestratorConfig instance
        """
        self.project_dir = project_dir
        self.config = config
        self.report = ValidationReport(passed=True)
    
    def validate_all(self) -> ValidationReport:
        """Run all validation checks."""
        logger.info("Running pre-flight validation...")
        
        if self.config.validation.check_git:
            self._validate_git()
        
        if self.config.validation.check_qoder_cli:
            self._validate_qoder_cli()
        
        if self.config.validation.check_dependencies:
            self._validate_dependencies()
        
        self._validate_project_structure()
        self._validate_qoder_context()
        
        # Fail on warnings if configured
        if self.config.validation.fail_on_warnings and self.report.get_warnings():
            self.report.passed = False
        
        return self.report
    
    def _validate_git(self):
        """Validate git repository."""
        # Check if git is installed
        if not shutil.which("git"):
            self.report.add_error(
                "git",
                "Git is not installed",
                "Install git: https://git-scm.com/downloads"
            )
            return
        
        # Check if we're in a git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                check=True
            )
            self.report.add_info("git", "Git repository detected")
        except subprocess.CalledProcessError:
            if self.config.rollback.enabled:
                self.report.add_error(
                    "git",
                    "Not a git repository (required for rollback feature)",
                    "Run: git init"
                )
            else:
                self.report.add_warning(
                    "git",
                    "Not a git repository (rollback disabled)",
                    "Consider initializing git for better tracking"
                )
            return
        
        # Check for uncommitted changes
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                self.report.add_warning(
                    "git",
                    "Uncommitted changes detected",
                    "Consider committing changes before orchestration"
                )
        except subprocess.CalledProcessError:
            pass
    
    def _validate_qoder_cli(self):
        """Validate Qoder CLI installation."""
        if not shutil.which("qoder"):
            self.report.add_error(
                "qoder",
                "Qoder CLI is not installed",
                "Install: npm install -g qoder"
            )
            return
        
        # Check version
        try:
            result = subprocess.run(
                ["qoder", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            self.report.add_info("qoder", f"Qoder CLI version: {version}")
        except subprocess.CalledProcessError as e:
            self.report.add_error(
                "qoder",
                f"Failed to get Qoder CLI version: {e}",
                "Reinstall Qoder CLI"
            )
            return
        
        # Check for PAT
        env_file = self.project_dir / ".env.local"
        pat_found = False
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip().startswith("qoder_pat="):
                        pat_found = True
                        break
        
        if not pat_found:
            self.report.add_warning(
                "qoder",
                "Qoder PAT not found in .env.local",
                "You will be prompted for PAT during execution"
            )
    
    def _validate_dependencies(self):
        """Validate Python dependencies."""
        required_packages = {
            "yaml": "pyyaml",
            "git": "gitpython",
        }
        
        if self.config.semantic_search.enabled:
            required_packages["sentence_transformers"] = "sentence-transformers"
        
        if self.config.llm.provider == "openai":
            required_packages["openai"] = "openai"
        elif self.config.llm.provider == "anthropic":
            required_packages["anthropic"] = "anthropic"
        
        missing = []
        for import_name, package_name in required_packages.items():
            try:
                __import__(import_name)
            except ImportError:
                missing.append(package_name)
        
        if missing:
            self.report.add_error(
                "dependencies",
                f"Missing Python packages: {', '.join(missing)}",
                f"Run: pip install {' '.join(missing)}"
            )
    
    def _validate_project_structure(self):
        """Validate basic project structure."""
        # Check if project directory exists
        if not self.project_dir.exists():
            self.report.add_error(
                "structure",
                f"Project directory does not exist: {self.project_dir}",
                "Verify the --project-dir argument"
            )
            return
        
        # Check for common project indicators
        indicators = [
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
        ]
        
        has_indicator = any((self.project_dir / ind).exists() for ind in indicators)
        
        if not has_indicator:
            self.report.add_warning(
                "structure",
                "No common project files detected",
                "Ensure you're in the correct project directory"
            )
    
    def _validate_qoder_context(self):
        """Validate Qoder context structure."""
        qoder_dir = self.project_dir / ".qoder"
        
        if not qoder_dir.exists():
            self.report.add_warning(
                "structure",
                ".qoder directory not found",
                "Create .qoder directory with wiki/, skills/, and rules.md"
            )
            return
        
        # Check for wiki
        wiki_dir = qoder_dir / "wiki"
        if not wiki_dir.exists():
            self.report.add_info("structure", "No wiki directory found")
        else:
            wiki_count = len(list(wiki_dir.glob("*.md")))
            if wiki_count == 0:
                self.report.add_info("structure", "Wiki directory is empty")
            else:
                self.report.add_info("structure", f"Found {wiki_count} wiki pages")
        
        # Check for skills
        skills_dir = qoder_dir / "skills"
        if not skills_dir.exists():
            self.report.add_info("structure", "No skills directory found")
        else:
            skill_count = len([d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
            if skill_count == 0:
                self.report.add_info("structure", "Skills directory is empty")
            else:
                self.report.add_info("structure", f"Found {skill_count} skills")
        
        # Check for rules
        rules_file = qoder_dir / "rules.md"
        if not rules_file.exists():
            self.report.add_info("structure", "No rules.md found")
        else:
            self.report.add_info("structure", "Found rules.md")
        
        # Validate subagents directory
        subagents_dir = self.project_dir / "subagents"
        if not subagents_dir.exists():
            self.report.add_warning(
                "structure",
                "No subagents directory found",
                "Create subagents/ directory with .md files for each subagent"
            )
        else:
            subagent_count = len(list(subagents_dir.glob("*.md")))
            if subagent_count == 0:
                self.report.add_warning(
                    "structure",
                    "Subagents directory is empty",
                    "Add subagent definitions as .md files"
                )
            else:
                self.report.add_info("structure", f"Found {subagent_count} subagents")


def validate_project(project_dir: Path, config: Any) -> ValidationReport:
    """
    Convenience function to run validation.
    
    Args:
        project_dir: Project directory path
        config: OrchestratorConfig instance
        
    Returns:
        ValidationReport
    """
    validator = PreFlightValidator(project_dir, config)
    report = validator.validate_all()
    report.print_report()
    return report
