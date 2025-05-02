import textwrap
from pathlib import Path

from deep_next.core.steps.action_plan import example
from deep_next.core.steps.action_plan.common import _create_llm
from deep_next.core.steps.action_plan.data_model import ActionPlan, ExistingCodeContext
from deep_next.core.steps.action_plan.path_tools import try_to_resolve_path
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import OutputParserException
from tenacity import retry, retry_if_exception_type, stop_after_attempt


class ActionPlanValidationError(Exception):
    """Raised when action plan is invalid."""


class _Prompt:
    role = textwrap.dedent(
        """
        You are an expert software engineer tasked with breaking down a software issue \
        into an ordered action plan with explicit dependencies.

        Following steps should be ordered list of high level actionable goals for the developer \
        allowing him to solve the issue and keep the dependencies intact.

        It is required to include reasoning behind the action plan. Focus on input data, \
        analyze trade-offs and provide complete solution. Be concise and professional.

        Relate to input data while creating a solution.
        """  # noqa: E501
    )
    issue_statement = textwrap.dedent(
        """
        This is the issue statement you need to solve.

        <issue_statement>
        {issue_statement}
        </issue_statement>
        """
    )
    project_knowledge = textwrap.dedent(
        """
        This is additional project knowledge that will help You to see the broader context of repo itself.
        It describes project structure, dependencies, conventions and other important overview information.

        <project_knowledge>
        {project_knowledge}
        </project_knowledge>
        """  # noqa: E501
    )
    existing_code_snippet = textwrap.dedent(
        """
        Related EXISTING code context provides You all necessary information about the codebase. \
        This consist of only currently existing code snippets that are related to the issue.

        Analyze carefully following code snippets and consider them in the final action plan.

        <existing_code_snippets>
        {existing_code_snippets}
        </existing_code_snippets>
        """  # noqa: E501
    )
    output_requirements = textwrap.dedent(
        """
        --------------------
        OUTPUT REQUIREMENTS (Warning! This is very important part to keep output quality high)
        --------------------

        Acceptance criteria:
        1. List high-level steps needed to solve the issue.
        2. Mind steps order. It is important from dependencies perspective.
        3. If steps are independent, their order does not matter.
        4. Do not overcomplicate the solution. Keep it simple, clear and professional.
        5. It's ok to provide only one step if it's simple enough for developer to understand.

        --------------------
        Adhere to following format instructions.
        <format_instructions>
        {format_instructions}
        </format_instructions>
        --------------------
        """  # noqa: E501
    )
    ai_asks_for_example = textwrap.dedent(
        """
        To keep the output quality high, I'd like to confirm that I fully understand the task. \
        Please provide me the example action plan that will be my guide for better understanding.

        Then I'll right away start working on the action plan for the issue.
        """  # noqa: E501
    )
    example_action_plan = textwrap.dedent(
        """
        Sure! This is example to follow. It was reviewed and approved by the team.

        <example_action_plan>
        {example_action_plan}
        </example_action_plan>
        """  # noqa: E501
    )


def _validate_paths(action_plan: ActionPlan, root_path: Path) -> ActionPlan:
    """Validates the action plan.

    Raises:
        ActionPlanValidationError: If the action plan is invalid.
    """
    if not action_plan.ordered_steps:
        raise ActionPlanValidationError("Action has no steps.")

    for step in action_plan.ordered_steps:
        try:
            step.target_file = try_to_resolve_path(step.target_file, root_path)
        except FileNotFoundError as e:
            raise ActionPlanValidationError(str(e))

        if step.target_file.is_dir():
            raise ActionPlanValidationError(
                f"Target file '{step.target_file}' is a directory, not a file"
            )

        if not step.target_file.is_relative_to(root_path):
            raise ActionPlanValidationError(
                f"Target file '{step.target_file}' is not part of project dir "
                f"'{root_path}'"
            )

    return action_plan


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((OutputParserException, ActionPlanValidationError)),
    reraise=True,
)
def create_action_plan(
    root_path: Path,
    issue_statement: str,
    existing_code_context: ExistingCodeContext,
    project_knowledge: str,
) -> ActionPlan:
    """Creates structured and dependency-ordered action plan for solving the issue."""
    parser = PydanticOutputParser(pydantic_object=ActionPlan)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _Prompt.role),
            ("human", _Prompt.issue_statement),
            ("human", _Prompt.project_knowledge),
            ("human", _Prompt.existing_code_snippet),
            ("human", _Prompt.output_requirements),
            ("ai", _Prompt.ai_asks_for_example),
            ("human", _Prompt.example_action_plan),
        ],
    ).partial(
        format_instructions=parser.get_format_instructions(),
        example_action_plan=example.action_plan,
    )

    action_plan = (prompt | _create_llm() | parser).invoke(
        {
            "issue_statement": issue_statement,
            "project_knowledge": project_knowledge,
            "existing_code_snippets": existing_code_context.dump(),
        }
    )

    # Ensure reasoning is present and surfaced in the returned object
    validated_action_plan = _validate_paths(action_plan, root_path)
    # Optionally, you could add formatting or further processing here if needed
    return validated_action_plan
