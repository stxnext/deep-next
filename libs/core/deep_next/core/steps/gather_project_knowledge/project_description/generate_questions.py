import textwrap

from deep_next.core.project_info import NOT_FOUND, ProjectInfo
from deep_next.core.steps.gather_project_knowledge.project_description.common import (
    _create_llm,
)
from deep_next.core.steps.gather_project_knowledge.project_description.data_model import (  # noqa: E501
    ExistingQuestionContext,
    example_output_existing_question_context,
)
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate


class Prompt:
    task_description = textwrap.dedent(
        """
        As a senior python developer that prepares documentation for newcomers to support onboarding process...

        Please look through the following GitHub Problem Description for project "{project_name}".
        Provide questions to the git repository owner to understand the repository.
        The questions should be related to the project structure, entry points, important classes, tech stack and architecture.
        """  # noqa: E501
    )

    generate_questions_prompt = textwrap.dedent(
        """
        DOCUMENTATION:
        {documentation}

        PROJECT TREE:
        ```text
        {repository_tree}
        ```

        Please provide the questions to the git repository to understand the problem better.
        This question will be used to search for the relevant code context that is relevant to
        understand the repository better.

        EXAMPLE OUTPUT:
        --------------------
        {example_generate_questions}
        --------------------
        """  # noqa: E501
    )


def generate_questions(
    repository_tree: str, project_info: ProjectInfo
) -> ExistingQuestionContext:

    design_solution_prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                Prompt.task_description,
            ),
            (
                "user",
                Prompt.generate_questions_prompt,
            ),
        ]
    )

    parser = PydanticOutputParser(pydantic_object=ExistingQuestionContext)

    llm_agent = design_solution_prompt_template | _create_llm() | parser

    return llm_agent.invoke(
        {
            "project_name": project_info.name,
            "documentation": get_documentation(project_info),
            "repository_tree": repository_tree,
            "example_generate_questions": example_output_existing_question_context.model_dump_json(),  # noqa: E501
        }
    )


def get_documentation(project_info: ProjectInfo) -> str:
    """Get documentation from project info."""
    documentation = ""
    if project_info.readme != NOT_FOUND:
        documentation += f"README:\n```md\n{project_info.readme}\n```\n\n"
    if project_info.pyproject_toml != NOT_FOUND:
        documentation += (
            f"PYPROJECT.TOML:\n```toml\n{project_info.pyproject_toml}\n```\n\n"
        )
    if project_info.setup_py != NOT_FOUND:
        documentation += f"SETUP.PY:\n```python\n{project_info.setup_py}\n```\n\n"
    if project_info.setup_cfg != NOT_FOUND:
        documentation += f"SETUP.CFG:\n```\n{project_info.setup_cfg}\n```\n\n"

    return documentation
