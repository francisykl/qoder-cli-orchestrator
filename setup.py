from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="qoder-orchestrator",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Orchestrate development tasks using Qoder CLI subagents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/qoder-orchestrator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies - uses only Python stdlib
    ],
    entry_points={
        "console_scripts": [
            "qoder-orchestrate=qoder_orchestrator.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "qoder_orchestrator": ["subagents/*.md"],
    },
)
