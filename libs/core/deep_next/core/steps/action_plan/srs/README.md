# Select Related Snippets (SRS) Module

## Overview

The SRS (Select Related Snippets) module is responsible for narrowing down the scope of a problem from entire files to specific code snippets. It analyzes issue descriptions and codebase structures to identify relevant code segments that need inspection or modification.

## Key Components

### Core Classes

- `SelectRelatedSnippetsGraph`: A directed graph that orchestrates the snippet selection workflow
- `ExistingCodeContext`: Data model for storing information about identified code segments
- `FileCodeContext`: Data model for storing file-specific code segments and reasoning

### Main Features

- **Function Localization**: Identifies relevant classes, functions, and global variables from compressed file skeletons
- **Line Localization**: Narrows down to specific line ranges within identified functions
- **Multiple Selection Cycles**: Runs multiple independent snippet selection cycles for improved coverage

## Workflow

1. The process starts with an **issue description** and a set of **relevant files**
2. The graph runs multiple independent cycles of:
   - Function localization (identifying classes/functions/global variables)
   - Line localization (narrowing to classes/functions/lines)
3. Results from all cycles are combined to produce the final set of code snippets

## Example Usage

```python
from deep_next.core.steps.action_plan.srs import select_related_snippets_graph

# Run the SRS graph to get relevant snippets
results = select_related_snippets_graph(
    problem_statement="Description of the issue to fix",
    root_path=Path("/path/to/repo"),
    files=list_of_files,
    structure=repo_structure
)

# Results contains file paths mapped to specific line ranges
# {"file1.py": [[10, 20], [35, 40]], "file2.py": [[5, 15]]}
```

## Architecture Notes

- Built on LangGraph for workflow orchestration
- Utilizes LLMs to analyze code and identify relevant segments
- Leverages code analysis techniques from the Agentless project to parse and manipulate Python code
