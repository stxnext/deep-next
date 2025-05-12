---
layout: default
title: Contributing
---

# Contributing to DeepNext

We welcome contributions to DeepNext! This document provides guidelines for contributing to the project.

## Development Environment

```bash
# Install dependencies
make install_venv

# Run linters
make lint

# Run tests
make test_unit
```

## Code Style

DeepNext follows these code style guidelines:

- **Formatting**: Black with 88 char line length
- **Imports**: Use isort with black profile
- **Typing**: Use Python type hints
- **Docstrings**: Follow pydocstyle (D200, D201, D202, D205, D209, D210, D300, D403)
- **Error handling**: Use loguru for logging errors
- **Naming**: Use snake_case for functions/variables, PascalCase for classes

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure linting passes: `make lint && make test_unit`
5. Submit a pull request

## Project Structure

The project is organized as a monorepo:

- **apps/app/**: Main DeepNext application
- **libs/core/**: Core processing logic
- **libs/connectors/**: Integration with external services
- **libs/common/**: Shared utilities

## Adding New Components

When adding new components, please follow the existing patterns in the codebase. Each component should:

1. Have appropriate tests
2. Be properly documented
3. Follow the project's code style

[Back to Home](./index.html)
