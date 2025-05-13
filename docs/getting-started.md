---
layout: default
title: Getting Started
---

# Getting Started

## Installation

```bash
# Clone the repository
git clone git@github.com:stxnext/deep-next.git
cd deep-next

# Install dependencies
make install_venv

# Test the installation
make test_unit
```

## Example Usage

```bash
# Process a single issue
poetry run python -m deep_next.core.entrypoint \
  --problem-statement "Add type hints in file.py" \
  --hints "The error occurs in file.py" \
  --root-dir /path/to/repository
```

## Requirements

- Python 3.11
- Poetry 1.8.2
- Access to an LLM provider (OpenAI or AWS Bedrock)

[Back to Home](./index.html)
