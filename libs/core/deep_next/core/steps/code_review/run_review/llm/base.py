import json
import textwrap
from abc import ABC, abstractmethod

from deep_next.core.steps.code_review.common import _create_llm
from deep_next.core.steps.code_review.run_review.code_reviewer import CodeReviewContext
from langchain.output_parsers import OutputFixingParser, PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel


class CodeReviewModel(BaseModel):
    issues: list[str]
    """Issues found in the code while performing code review."""


class _Prompt:

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


class BaseLLMCodeReviewer(ABC):

    CODE_REVIEW_CHAIN_RETRY = 3

    def _fix_invalid_code_review(
        self, e: OutputParserException, code_review_parser: PydanticOutputParser
    ) -> CodeReviewModel | None:
        fixing_parser = OutputFixingParser.from_llm(
            parser=code_review_parser, llm=_create_llm()
        )
        try:
            fixing_parser.parse(e.llm_output)
        except OutputParserException:
            return None

    def _invoke_fixable_llm_chain(
        self,
        prompt: ChatPromptTemplate,
        prompt_arguments: dict,
        code_review_parser: PydanticOutputParser,
    ) -> CodeReviewModel:
        """
        Invoke the LLM chain and try {CODE_REVIEW_CHAIN_RETRY} times if it fails.

        The retry mechanism includes two steps:
        1. Attempting to fix the current invalid output.
        2. Rerunning the chain with a different seed if the fix attempt fails.
        """
        _e: OutputParserException | None = None
        for i in range(self.CODE_REVIEW_CHAIN_RETRY):
            chain = prompt | _create_llm(seed=i) | code_review_parser
            try:
                return chain.invoke(prompt_arguments)
            except OutputParserException as e:
                _e = e
                if result := self._fix_invalid_code_review(e, code_review_parser):
                    return result
        raise _e

    def _combine_code_fragments(
        self, code_fragments: dict[str, list[str]]
    ) -> dict[str, str]:
        return {
            filename: "\n\n---\n\n".join(fragments)
            for filename, fragments in code_fragments.items()
        }

    @property
    @abstractmethod
    def example_output(self) -> CodeReviewModel:
        """Example output of the code review LLM chain"""

    @property
    @abstractmethod
    def code_review_parser(self) -> PydanticOutputParser:
        """Pydantic code review parser"""

    def run(
        self,
        context: CodeReviewContext,
    ) -> list[str]:

        combined_code_fragments = self._combine_code_fragments(context.code_fragments)

        messages = [
            ("system", _Prompt.role_description),
            ("human", _Prompt.issue_statement),
            ("human", _Prompt.project_knowledge),
            ("human", _Prompt.git_diff),
            ("human", _Prompt.code_fragments),
            ("human", _Prompt.output_format),
        ]

        prompt = ChatPromptTemplate.from_messages(messages)

        relevant_code_fragments = "\n\n\n--------------------\n\n\n".join(
            [
                f"# {file_name}:\n\n{combined_code}"
                for file_name, combined_code in combined_code_fragments.items()
            ]
        )

        data = {
            "issue_statement": context.issue_statement,
            "project_knowledge": context.project_knowledge,
            "git_diff": context.git_diff,
            "relevant_code_fragments": relevant_code_fragments,
            "example_output_code_review": json.dumps(self.example_output.model_dump()),
            "empty_output_code_review": json.dumps({"issues": []}),
        }

        code_review = self._invoke_fixable_llm_chain(
            prompt, data, self.code_review_parser
        )

        return code_review.issues
