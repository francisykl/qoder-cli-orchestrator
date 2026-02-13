#!/usr/bin/env python3
"""
Setup script for Qoder Orchestrator.
Allows global installation: pip install -e .
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="qoder-orchestrator",
    version="1.0.0",
    description="Production-ready orchestration system for CLI-based AI assistants",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Qoder Team",
    author_email="support@qoder.com",
    url="https://github.com/qoder/qoder-orchestrator",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'qoder_orchestrator': ['*.yaml', '*.md'],
    },
    install_requires=[
        "pyyaml>=6.0.1",
        "gitpython>=3.1.40",
        "sentence-transformers>=2.3.1",
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
    ],
    extras_require={
        'dev': [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        'console_scripts': [
            'qoder-orchestrate=qoder_orchestrator.cli:main',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="orchestration ai cli automation qoder claude",
)
