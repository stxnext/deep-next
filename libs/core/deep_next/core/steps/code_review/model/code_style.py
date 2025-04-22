import textwrap

from deep_next.core.steps.code_review.model.base import CodeReviewer, CodeReviewModel
from langchain.output_parsers import PydanticOutputParser
from pydantic import Field

_issues_desc = textwrap.dedent(
    """\
        Analyze the changes made in the code. List all code style issues, that is:
        - Missing or incorrect docstrings in places where they are needed.
        - Missing or incorrect type hints in places where they are needed.
        - Incorrect naming of variables, functions, classes, etc.
        - Incorrect formatting of the code, e.g.: missing or extra spaces, \
        parenthesis, etc.

        Don't look for major issues, code logic issues, code consistency, etc.. List \
        only issues that are code style related.
        """
)


class CodeStyleCodeReview(CodeReviewModel):
    issues: list[str] = Field(default_factory=list, description=_issues_desc)


_code_style_code_review_parser = PydanticOutputParser(
    pydantic_object=CodeStyleCodeReview
)

_example_output_code_style_code_review = CodeStyleCodeReview(
    issues=[
        "The function 'calculate_price' in the file 'src/utils.py' does not have a "
        "docstring. It should have a docstring explaining what the function does and "
        "describing its parameters.",
        "The function 'calculate_price' in the file 'src/utils.py' does not have a "
        "type hint for its return value. It should have a type hint indicating that it "
        "returns a float.",
    ],
)

code_style_code_reviewer = CodeReviewer(
    name="code_style_code_reviewer",
    parser=_code_style_code_review_parser,
    example_output=_example_output_code_style_code_review,
)
