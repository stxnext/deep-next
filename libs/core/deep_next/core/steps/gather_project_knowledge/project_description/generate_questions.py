import textwrap

from deep_next.core.project_info import NOT_FOUND, ProjectInfo
from deep_next.core.steps.gather_project_knowledge.project_description.common import (
    _create_llm,
)
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


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


# overview_desc = (
#     "Analyze GitHub repository. Read the documentation to understand the repo "
#     "structure. Understand the project structure and the existing code context to "
#     "generate questions for the next step to identify the part of the code that is "
#     "important to perform project analysis."
# )


# reasoning_desc = (
#     "Think about the reasoning for generating the questions. "
#     "Provide the reasoning for the questions that you are going to ask."
#     "The reasoning should help you in the next step to identify the part "
#     "of the code that is important to perform project analysis."
# )


# questions_desc = (
#     "Provide the questions to the git repository to understand the github repository"
#     " better. This question will be used to search for the relevant code context that"
#     " needs to be clarified or anchored to the code context."
# )


# question_context_desc = (
#     "Provide the question context to the git repository to understand the problem "
#     "better with a brief reasoning for the question."
# )


class QuestionContext(BaseModel):
    reasoning: str = Field(default="", description="Reasoning for the question")
    question: str = Field(default="", description="Question to the git repository")


class ExistingQuestionContext(BaseModel):
    overview_description: str = Field(
        default="", description="Overview description of the project"
    )
    question_context: list[QuestionContext] = Field(
        default_factory=list, description="List of questions to the git repository"
    )

    def dump(self) -> str:
        return "\n".join([question.question for question in self.question_context])


def _create_llm_agent():
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

    return design_solution_prompt_template | _create_llm() | parser


def generate_questions(
    repository_tree: str, project_info: ProjectInfo
) -> ExistingQuestionContext:
    response = _create_llm_agent().invoke(
        {
            "project_name": project_info.name,
            "documentation": get_documentation(project_info),
            "repository_tree": repository_tree,
            "example_generate_questions": example_output_loc_cfl.model_dump_json(),
        }
    )

    return response


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


example_output_loc_cfl = ExistingQuestionContext(
    overview_description=(
        "The repository is a Python project that has readme.md and setup.py in the "
        "root directory. The project uses main.py as the entry point, so definitely we"
        " need to read this file. The project contain tests, so we need to read some "
        "test files to check the test framework. We should read some .py files to "
        "check for the important classes and functions. "
    ),
    question_context=[
        QuestionContext(
            reasoning=(
                "The project uses main.py as the entry point, so definitely we "
                "need to read this file."
            ),
            question=(
                "What is the main.py file doing? What is the entry point of the "
                "project?"
            ),
        ),
        QuestionContext(
            reasoning=(
                "The project contain tests, so we need to read some test files "
                "to check the test framework."
            ),
            question="What is the test framework used in the project?",
        ),
        QuestionContext(
            reasoning=(
                "We should read some .py files to check for the important "
                "classes and functions."
            ),
            question="What are the important classes and functions in the project?",
        ),
        QuestionContext(
            reasoning=(
                "We should check for readme.md to understand the project " "better."
            ),
            question="What is the content of the readme.md file?",
        ),
        QuestionContext(
            reasoning=(
                "There is setup.py in the repo tree. "
                "We should check for setup.py to understand the project better."
            ),
            question="What is the content of the setup.py file?",
        ),
        QuestionContext(
            reasoning=(
                "I see in the project tree that the project uses "
                "pyproject.toml. We should check for pyproject.toml to "
                "understand the libraries used in the project."
            ),
            question="What is the content of the pyproject.toml file?",
        ),
    ],
)
