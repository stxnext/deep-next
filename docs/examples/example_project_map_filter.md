---
layout: default
title: LLM-based Project Map Filtering
---

# LLM-based Project Map Filtering

When working with large codebases, the project map can become very lengthy, causing context window constraints for subsequent LLM processing. This example demonstrates how to add an LLM filter to the project map generation process that identifies and retains only the most relevant files and directories for a specific task.

## Implementation

Below are the specific changes needed to add LLM-based filtering to the `project_map.py` module:


### Step 1: Add required imports

**Location**: `libs/core/deep_next/core/steps/gather_project_knowledge/project_map.py`

```python
# Add these imports to the top of the file
import textwrap
from typing import List
from loguru import logger
from pydantic import BaseModel
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate

# Import LLM utilities
from deep_next.core.steps.gather_project_knowledge.common import _create_llm
```

### Step 2: Create a structured output model

**Location**: `libs/core/deep_next/core/steps/gather_project_knowledge/project_map.py`

```python
# Add this class after the existing _is_valid_file function
class ProjectMapFilter(BaseModel):
    """Model for the LLM to populate with important directories and files"""
    reasoning: str
    important_repo_map: str
```

```python
class Prompt:
    task_description = textwrap.dedent("""
        You are an expert software engineer tasked with identifying the most important
        directories and files for solving a specific task in a codebase.

        Task description:
        {task_description}

        Below is the full project map:
        {project_map}


        Please analyze the project structure and identify which directories and files
        are most likely to be relevant for this task. Many projects have large directories
        with hundreds of files that aren't relevant to most tasks.

        Your goal is to retain only the important parts of the project structure to reduce
        context length while preserving critical information.

        Respond with a list of the most important directories and files to keep, along with
        brief reasoning for your selections.

        EXAMPLE OUTPUT:
        --------------------
        {example_output_project_map}
        --------------------
    """
    )
```

### Step 3: Implement the filtering function

**Location**: `libs/core/deep_next/core/steps/gather_project_knowledge/project_map.py`

```python
def _create_llm_agent():
    """Creates LLM agent for filtering project map"""
    parser = PydanticOutputParser(pydantic_object=ProjectMapFilter)

    project_map_prompt_template = ChatPromptTemplate.from_messages(
        [
            ("human", Prompt.task_description),
        ]
    )

    return project_map_prompt_template | _create_llm() | parser


# Add this function before the tree function
def filter_project_map(project_map: str, task_description: str) -> str:
    """
        Use an LLM to filter the project map, keeping only relevant components for the task.

    Args:
        project_map: The full project map as a string
        task_description: Description of the task being performed

    Returns:
        A filtered version of the project map
    """

    # Get LLM response with structured output
    response = _create_llm_agent().invoke(
        {
            "task_description": task_description,
            "project_map": project_map,
            "example_output_project_map": example_output_project_map.model_dump_json(),
        }
    )

    return response.important_repo_map

example_output_project_map = ProjectMapFilter(
    reasoning="The src directory contains the main codebase, while tests are not relevant.",
    important_repo_map=textwrap.dedent(
        """\
        📁 src
        ├── 📁 module1
        │   ├── 📄 __init__.py
        │   ├── 📄 file1.py
        │   └── 📄 file2.py
        ├── 📁 module2
        │   └── 📄 file3.py
        │   📄 main.py
        """
    ),
)
```

### Step 4: Update the tree function signature and implementation

**Location**: `libs/core/deep_next/core/steps/gather_project_knowledge/project_map.py`

```python
# Modify the tree function signature to add the task_description parameter
def tree(path: Path | str, root_name: str | None = None, task_description: str = None) -> str:
    """
    Generates a visual directory tree structure for a given path.

    Generates a visual directory tree structure for a given path. If a tree node
    consists of more than {N_BIG_BRANCH_ITEMS} items, it is cut off and marked with:
    "📁 <found X items>".

    Args:
        path (Path | str): The root directory to generate the tree for.
        root_name (str | None): The name of the root node of the tree.
        task_description (str | None): Optional task description to filter the tree.

    Returns:
        str: A string representation of the directory tree, formatted using
             the `rich` library for visual clarity.
    """
```

#### Step 4.1: Modify the end of the `tree` function to apply filtering

**Location**: `libs/core/deep_next/core/steps/gather_project_knowledge/project_map.py`

```python
# ... existing code ...

# Replace the end of the tree function with this code

    # Apply LLM filtering if task description is provided
    if task_description:
        logger.info(f"Filtering project map for task: {task_description[:100]}...")
        return filter_project_map(flat_tree, task_description)

    return flat_tree
```

## Benefits

1. **Reduced context length**: Filters out directories and files that aren't relevant to the current task
2. **Improved focus**: Helps subsequent LLMs focus on the most important parts of the codebase
3. **Task-specific customization**: The filtering adapts based on the specific task description
4. **Preserves structure**: Maintains the hierarchical structure of the project while reducing size
5. **Better LLM performance**: With less irrelevant information, downstream LLMs can make more accurate decisions

## Usage Example

```python
from pathlib import Path
from deep_next.core.steps.gather_project_knowledge.project_map import tree

# Generate complete project map
full_map = tree(Path("/path/to/project"))

# Generate filtered project map for a specific task
task = "Add type hints to the database connection module"
filtered_map = tree(
    Path("/path/to/project"),
    task_description=task
)
```

[Back to Examples](../examples.html)
