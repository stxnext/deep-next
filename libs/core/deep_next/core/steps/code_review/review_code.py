import json
import textwrap

from deep_next.common.llm import LLMConfigType, create_llm
from deep_next.common.llm_retry import invoke_retriable_llm_chain
from deep_next.core import parser
from deep_next.core.steps.code_review.model.base import CodeReviewModel
from deep_next.core.steps.code_review.model.code_style import code_style_code_reviewer
from deep_next.core.steps.code_review.model.diff_consistency import (
    diff_consistency_code_reviewer,
)
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger


class Prompt:

    role_description = textwrap.dedent(
        """
        You are one of many code reviewers. Your task is to review a merge request
        containing code changes. Focus only on fragments of code that are being impacted
        by the merge request. Don't bother looking at the rest of the code - someone
        else will handle that.

        Also, focus ONLY on the specific type of review you are asked to do. Don't try
        to do more than that, as other reviewers are responsible for other types of
        reviews. For example, if you are asked to review the code for logical errors,
        don't try to find code style issues even if they are self-evident.

        You have been provided with an issue statement, a git diff, and a code file \
        containing only relevant pieces of code. Your task is to review the code \
        and provide feedback on the issues found in the code.

        Always be absolutely precise in pointing out the issues. Always refer to full \
        file paths, directly name classes, functions, methods or any fragments of code \
        you are referring to. When pointing out an issue, describe what is wrong with \
        the code and how it should be fixed.

        If the code changes are correct and the code is working as expected, don't \
        force yourself to find or make up issues. We have to work with great precision \
        but also with great efficiency and move on quickly as soon as the code is \
        correct.
        """
    )

    issue_statement = textwrap.dedent(
        """
        # Issue Statement
        {issue_statement}
        """
    )

    project_knowledge = textwrap.dedent(
        """
        # Project Knowledge
        {project_knowledge}
        """
    )

    git_diff = textwrap.dedent(
        """
        # Git Diff
        ```git-diff
        {git_diff}
        ```
        """
    )

    code_fragments = textwrap.dedent(
        """
        # Relevant Code Fragments
        ```code-fragments
        {relevant_code_fragments}
        ```
        """
    )

    output_format = textwrap.dedent(
        """
        Always keep the output format as in the examples below (The lines -------------------- are not part of the example, they are separators)!

        EXAMPLE OUTPUT:
        --------------------
        {example_output_code_review}
        --------------------
        {empty_output_code_review}
        --------------------
        """  # noqa: E501
    )


def _call_code_review_llm(
    issue_statement: str,
    project_knowledge: str,
    git_diff: str,
    combined_code_fragments: dict[str, str],
    *,
    example_output: CodeReviewModel,
    code_review_parser: PydanticOutputParser,
) -> CodeReviewModel:
    messages = [
        ("system", Prompt.role_description),
        ("human", Prompt.issue_statement),
        ("human", Prompt.project_knowledge),
        ("human", Prompt.git_diff),
        ("human", Prompt.code_fragments),
        ("human", Prompt.output_format),
    ]

    prompt = ChatPromptTemplate.from_messages(messages)

    relevant_code_fragments = "\n\n\n--------------------\n\n\n".join(
        [
            f"# {file_name}:\n\n{combined_code}"
            for file_name, combined_code in combined_code_fragments.items()
        ]
    )

    data = {
        "issue_statement": issue_statement,
        "project_knowledge": project_knowledge,
        "git_diff": git_diff,
        "relevant_code_fragments": relevant_code_fragments,
        "example_output_code_review": json.dumps(example_output.model_dump()),
        "empty_output_code_review": json.dumps({"issues": []}),
    }

    return invoke_retriable_llm_chain(
        n_retry=3,
        llm_chain_builder=lambda iter_idx: prompt
        | create_llm(LLMConfigType.CODE_REVIEW, seed_increment=iter_idx)
        | OutputFixingParser.from_llm(
            parser=code_review_parser, llm=create_llm(LLMConfigType.CODE_REVIEW)
        ),
        prompt_arguments=data,
    )


def _parse(message: str) -> tuple[str, bool]:
    if not parser.has_code_block(message, "python"):
        raise Exception(f"Missing `python` code block {message}")

    resp = parser.extract_code_from_block(message).strip()

    return resp, message.strip().lower().endswith("approved")


def _combine_code_fragments(code_fragments: dict[str, list[str]]) -> dict[str, str]:
    return {
        filename: "\n\n---\n\n".join(fragments)
        for filename, fragments in code_fragments.items()
    }


def review_code(
    issue_statement: str,
    project_knowledge: str,
    git_diff: str,
    code_fragments: dict[str, list[str]],
) -> tuple[list[tuple[str, str]], dict[str, bool]]:
    issues = []

    all_code_reviewers = [diff_consistency_code_reviewer, code_style_code_reviewer]

    code_review_completed = {
        code_reviewer.name: True for code_reviewer in all_code_reviewers
    }

    for code_reviewer in all_code_reviewers:
        try:
            code_review = _call_code_review_llm(
                issue_statement,
                project_knowledge,
                git_diff,
                _combine_code_fragments(code_fragments),
                example_output=code_reviewer.example_output,
                code_review_parser=code_reviewer.parser,
            )
            issues.extend([(code_reviewer.name, issue) for issue in code_review.issues])
        except Exception as e:
            logger.warning(
                f"Code reviewer {code_reviewer.name} failed to review the code. "
                f"Exception:\n{e}"
            )
            code_review_completed[code_reviewer.name] = False

    return issues, code_review_completed
