#!/usr/bin/env python3
"""
Configuration management for Qoder orchestration.
Supports YAML config files, CLI arguments, and environment variables.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for task retry behavior."""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    max_backoff: float = 300.0  # 5 minutes max
    retry_on_errors: list = field(default_factory=lambda: ["timeout", "network", "temporary"])


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    provider: str = "qoder"  # qoder, openai, anthropic
    model: Optional[str] = None  # e.g., gpt-4, claude-3-opus
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 60


@dataclass
class SemanticSearchConfig:
    """Configuration for semantic search."""
    enabled: bool = True
    model_name: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = 0.5
    max_results: int = 5
    cache_embeddings: bool = True


@dataclass
class CacheConfig:
    """Configuration for context caching."""
    enabled: bool = True
    max_size_mb: int = 100
    ttl_seconds: int = 3600  # 1 hour
    cache_dir: str = ".qoder-cache"


@dataclass
class RollbackConfig:
    """Configuration for rollback behavior."""
    enabled: bool = True
    create_checkpoints: bool = True
    keep_checkpoints: int = 10
    auto_rollback_on_failure: bool = False


@dataclass
class ValidationConfig:
    """Configuration for pre-flight validation."""
    enabled: bool = True
    check_git: bool = True
    check_qoder_cli: bool = True
    check_dependencies: bool = True
    fail_on_warnings: bool = False


@dataclass
class ExecutionConfig:
    """Configuration for task execution."""
    max_parallel: int = 3
    max_iterations: int = 10
    task_timeout: int = 300  # 5 minutes
    enable_speculative: bool = True
    enable_batch_processing: bool = True
    batch_similarity_threshold: float = 0.7


@dataclass
class OrchestratorConfig:
    """Main configuration for the orchestrator."""
    project_dir: str = "."
    
    # Sub-configurations
    retry: RetryConfig = field(default_factory=RetryConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    semantic_search: SemanticSearchConfig = field(default_factory=SemanticSearchConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    rollback: RollbackConfig = field(default_factory=RollbackConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "orchestration.log"
    
    # Feature flags
    enable_learning: bool = True
    enable_contract_verification: bool = True
    enable_incremental_updates: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrchestratorConfig':
        """Create config from dictionary."""
        # Extract nested configs
        retry_data = data.pop('retry', {})
        llm_data = data.pop('llm', {})
        semantic_search_data = data.pop('semantic_search', {})
        cache_data = data.pop('cache', {})
        rollback_data = data.pop('rollback', {})
        validation_data = data.pop('validation', {})
        execution_data = data.pop('execution', {})
        
        return cls(
            retry=RetryConfig(**retry_data),
            llm=LLMConfig(**llm_data),
            semantic_search=SemanticSearchConfig(**semantic_search_data),
            cache=CacheConfig(**cache_data),
            rollback=RollbackConfig(**rollback_data),
            validation=ValidationConfig(**validation_data),
            execution=ExecutionConfig(**execution_data),
            **data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)


def load_config(
    config_file: Optional[str] = None,
    project_dir: str = ".",
    cli_overrides: Optional[Dict[str, Any]] = None
) -> OrchestratorConfig:
    """
    Load configuration from multiple sources with precedence:
    1. CLI arguments (highest priority)
    2. Config file
    3. Environment variables
    4. Defaults (lowest priority)
    
    Args:
        config_file: Path to YAML config file
        project_dir: Project directory
        cli_overrides: Dictionary of CLI argument overrides
        
    Returns:
        OrchestratorConfig instance
    """
    # Start with defaults
    config_data = {}
    
    # Try to find config file
    if config_file is None:
        # Look for config in project directory
        project_path = Path(project_dir).resolve()
        possible_configs = [
            project_path / ".qoder-orchestrate.yaml",
            project_path / ".qoder-orchestrate.yml",
            project_path / "qoder-orchestrate.yaml",
        ]
        
        for possible_config in possible_configs:
            if possible_config.exists():
                config_file = str(possible_config)
                break
    
    # Load from config file
    if config_file and os.path.exists(config_file):
        logger.info(f"Loading configuration from {config_file}")
        with open(config_file, 'r') as f:
            file_config = yaml.safe_load(f) or {}
            config_data.update(file_config)
    else:
        logger.info("No configuration file found, using defaults")
    
    # Load from environment variables
    env_config = _load_from_env()
    config_data.update(env_config)
    
    # Apply CLI overrides
    if cli_overrides:
        config_data.update(cli_overrides)
    
    # Ensure project_dir is set
    config_data['project_dir'] = project_dir
    
    # Create config object
    config = OrchestratorConfig.from_dict(config_data)
    
    # Validate configuration
    _validate_config(config)
    
    return config


def _load_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    env_config = {}
    
    # LLM configuration
    if os.getenv('QODER_LLM_PROVIDER'):
        env_config.setdefault('llm', {})['provider'] = os.getenv('QODER_LLM_PROVIDER')
    
    if os.getenv('QODER_LLM_API_KEY'):
        env_config.setdefault('llm', {})['api_key'] = os.getenv('QODER_LLM_API_KEY')
    
    if os.getenv('OPENAI_API_KEY'):
        env_config.setdefault('llm', {})['api_key'] = os.getenv('OPENAI_API_KEY')
    
    if os.getenv('ANTHROPIC_API_KEY'):
        env_config.setdefault('llm', {})['api_key'] = os.getenv('ANTHROPIC_API_KEY')
    
    # Execution configuration
    if os.getenv('QODER_MAX_PARALLEL'):
        env_config.setdefault('execution', {})['max_parallel'] = int(os.getenv('QODER_MAX_PARALLEL'))
    
    if os.getenv('QODER_MAX_ITERATIONS'):
        env_config.setdefault('execution', {})['max_iterations'] = int(os.getenv('QODER_MAX_ITERATIONS'))
    
    # Log level
    if os.getenv('QODER_LOG_LEVEL'):
        env_config['log_level'] = os.getenv('QODER_LOG_LEVEL')
    
    return env_config


def _validate_config(config: OrchestratorConfig) -> None:
    """Validate configuration values."""
    errors = []
    
    # Validate execution config
    if config.execution.max_parallel < 1:
        errors.append("execution.max_parallel must be >= 1")
    
    if config.execution.max_iterations < 1:
        errors.append("execution.max_iterations must be >= 1")
    
    if config.execution.task_timeout < 1:
        errors.append("execution.task_timeout must be >= 1")
    
    # Validate retry config
    if config.retry.max_attempts < 1:
        errors.append("retry.max_attempts must be >= 1")
    
    if config.retry.backoff_factor < 1.0:
        errors.append("retry.backoff_factor must be >= 1.0")
    
    # Validate LLM config
    valid_providers = ["qoder", "openai", "anthropic"]
    if config.llm.provider not in valid_providers:
        errors.append(f"llm.provider must be one of {valid_providers}")
    
    if config.llm.provider in ["openai", "anthropic"] and not config.llm.api_key:
        logger.warning(f"LLM provider is {config.llm.provider} but no API key provided")
    
    # Validate semantic search config
    if config.semantic_search.similarity_threshold < 0 or config.semantic_search.similarity_threshold > 1:
        errors.append("semantic_search.similarity_threshold must be between 0 and 1")
    
    # Validate cache config
    if config.cache.max_size_mb < 1:
        errors.append("cache.max_size_mb must be >= 1")
    
    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    
    logger.info("Configuration validated successfully")


def save_config(config: OrchestratorConfig, output_file: str) -> None:
    """Save configuration to YAML file."""
    config_dict = config.to_dict()
    
    with open(output_file, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Configuration saved to {output_file}")
