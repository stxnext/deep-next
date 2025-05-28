import textwrap
from pathlib import Path

from deep_next.common.llm_retry import invoke_retriable_llm_chain
from deep_next.core.io import read_txt_or_none
from deep_next.core.project_info import ProjectInfo
from deep_next.core.steps.gather_project_knowledge.project_description.common import (
    _create_llm,
)
from deep_next.core.steps.gather_project_knowledge.project_description.data_model import (  # noqa: E501
    ExistingProjectDescriptionContext,
    example_output_existing_project_description_context,
)
from langchain.output_parsers import PydanticOutputParser
from langchain.schema.output_parser import OutputParserException
from langchain_core.prompts import ChatPromptTemplate


class Prompt:
    task_description = textwrap.dedent(
        """
        As a senior python developer that prepares documentation for newcomers to support onboarding process...

        Please analyze the key technical capabilities and characteristics of the "{project_name}" project based on given context.
        In return I want to receive a project description summarizing it's overall shape, purpose, structure, libraries,
        entry points, patterns and other important features of the project.
        """  # noqa: E501
    )
    generate_project_description_prompt = textwrap.dedent(
        """
        ### Repository tree
        {repository_tree}

        ### Files related to the issue (readme, Makefile, requirements.txt, etc.)
        {related_code_context}

        ### Questions worth to consider
        {questions}

        Consider following features:
        - Purpose / Primary Goals: Who the end users are. A brief summary of what the application does and how it fits into the larger ecosystem (e.g., what problems it solves for users).
        - Project Structure: High-level overview of the folder structure, including: main modules and their purpose.
        - Entry Points: Information about the main entry points for the application
        - Important Classes / Modules: Description of critical classes or modules, such as base classes, core utilities, or helper functions.
        - Tech Stack Overview: Information about the main technologies used, such as: Python version, Frameworks and libraries (e.g., Django, Flask, FastAPI, Pandas, NumPy), Databases (e.g., PostgreSQL, MySQL, SQLite), Caching mechanisms (e.g., Redis).
        - Architecture Overview: High-level overview of the project's architecture, such as: Monolithic vs. microservices, How different modules interact, Important design patterns used in the codebase.

        Based on the given context, provide the project description to the git repository to understand the problem. The project description
        should include the high level overview of the project structure, entry points, important classes, tech stack and architecture.
        The project description should help you in the next step to identify the part of the issue that needs to be clarified or anchored
        to the code context.

        ADDITIONAL INSTRUCTIONS:
        ------------------------
        1. Your answer should be submitted directly based on given data.
        ------------------------

        EXAMPLE OUTPUT:
        --------------------
        {example_project_description}
        --------------------
        """  # noqa: E501
    )


# @tenacity.retry(
#     stop=tenacity.stop_after_attempt(3),
#     retry=tenacity.retry_if_exception_type(OutputParserException),
#     reraise=True,
# )
def generate_project_description(
    questions: str,
    related_files: list[Path],
    repository_tree: str,
    project_info: ProjectInfo,
) -> ExistingProjectDescriptionContext:
    """Generate project description based on the repository tree and related files."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                Prompt.task_description,
            ),
            (
                "user",
                Prompt.generate_project_description_prompt,
            ),
        ]
    )

    parser = PydanticOutputParser(pydantic_object=ExistingProjectDescriptionContext)

    # llm_agent = prompt | _create_llm() | parser

    related_code_context = "\n".join(
        [
            f"File: {path}\n{read_txt_or_none(path) or '<Failed to read file>'}"
            for path in related_files
        ]
    )
    # return llm_agent.invoke(
    #     {
    #         "project_name": project_info.name,
    #         "repository_tree": repository_tree,
    #         "related_code_context": related_code_context,
    #         "questions": questions,
    #         "example_project_description": example_output_existing_project_description_context.model_dump_json(),  # noqa: E501
    #     }
    # )

    prompt_arguments = {
        "project_name": project_info.name,
        "repository_tree": repository_tree,
        "related_code_context": related_code_context,
        "questions": questions,
        "example_project_description": example_output_existing_project_description_context.model_dump_json(),  # noqa: E501
    }

    return invoke_retriable_llm_chain(
        n_retry=3,
        llm_chain_builder=lambda seed: prompt | _create_llm(seed=seed) | parser,
        prompt_arguments=prompt_arguments,
        exception_type=OutputParserException,
    )
