import textwrap
from pathlib import Path

from deep_next.core.project_info import ProjectInfo, get_project_info
from deep_next.core.steps.gather_project_knowledge.common import _create_llm
from deep_next.core.steps.gather_project_knowledge.project_map import tree
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

IDK_SENTENCE = "<NOT ENOUGH DATA>"


class Prompt:
    task_description = textwrap.dedent(
        """
        As a senior python developer that prepares documentation for newcomers to support onboarding process...

        Please analyze the key technical capabilities and characteristics of the "{project_name}" project based on given context.
        In return I want to receive a short project description summarizing it's overall shape and purpose.

        Consider following features:
        - Purpose / Primary Goals: Who the end users are. A brief summary of what the application does and how it fits into the larger ecosystem (e.g., what problems it solves for users).
        - Project Structure: High-level overview of the folder structure, including: main modules and their purpose.
        - Entry Points: Information about the main entry points for the application
        - Important Classes / Modules: Description of critical classes or modules, such as base classes, core utilities, or helper functions.
        - Tech Stack Overview: Information about the main technologies used, such as: Python version, Frameworks and libraries (e.g., Django, Flask, FastAPI, Pandas, NumPy), Databases (e.g., PostgreSQL, MySQL, SQLite), Caching mechanisms (e.g., Redis).
        - Architecture Overview: High-level overview of the project's architecture, such as: Monolithic vs. microservices, How different modules interact, Important design patterns used in the codebase.

        ADDITIONAL INSTRUCTIONS:
        ------------------------
        1. Your answer should be submitted directly based on given data.
        2. If there's not enough data to address specific feature, write "{idk_sentence}" as feature answer. I don't need a fairy tales stories.
        ------------------------
        """  # noqa: E501
    )

    output_format = textwrap.dedent(
        """
        Please adhere to following output format:
        ------------------------
        # Project Name: {project_name}

        ## Feature name #1
        Here goes the feature description / overview.

        ## Feature name #2
        {idk_sentence}

        ...
        ------------------------
        """
    )

    input_data = textwrap.dedent(
        """
        While generating the results, please reference the following repository details:

        CONTEXT DETAILS:
        ------------------------
        DOCUMENTATION:
        ```md
        {readme}
        ```

        PYPROJECT.TOML:
        ```toml
        {pyproject_toml}
        ```

        SETUP.PY:
        ```python
        {setup_py}
        ```

        PROJECT TREE:
        ```text
        {tree}
        ```
        ------------------------
        """
    )


def _create_llm_agent():
    """Creates LLM agent for project description task."""
    project_description_prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", Prompt.task_description),
            ("human", Prompt.output_format),
            ("human", Prompt.input_data),
        ]
    )

    parser = StrOutputParser()

    return project_description_prompt_template | _create_llm() | parser


def create_project_description(root_path: Path) -> str:
    """Creates project description."""
    project_info: ProjectInfo = get_project_info(root_dir=root_path)

    resp = _create_llm_agent().invoke(
        {
            "project_name": project_info.name,
            "idk_sentence": IDK_SENTENCE,
            "readme": project_info.readme,
            "pyproject_toml": project_info.pyproject_toml,
            "setup_py": project_info.setup_py,
            "tree": tree(root_path),
        }
    )

    return resp.strip().strip("-").strip()
