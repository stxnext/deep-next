import textwrap

from deep_next.core.steps.code_review.run_review.llm.base import (
    BaseLLMCodeReviewer,
    CodeReviewModel,
)
from langchain.output_parsers import PydanticOutputParser
from pydantic import Field

_issues_desc = textwrap.dedent(
    """\
    Analyze the changes made in the code. List all fundamental issues with code \
    consistency, that is:
    - Situations, when a newly created or already existing utility, function, class or \
    other piece of code could be reused, but is not.
    - Situations, when a newly created or already existing utility, function, class or \
    other piece of code is used with a mistake, e.g.: when a method is misspelled, or \
    it seems like a developer was trying to GUESS the correct name of a function that \
    in reality is named differently.
    - Situations, when a newly created or already existing utility, function, class or \
    other piece of code is used with incorrect arguments, a wrong number of arguments, \
    or in a wrong context.
    - Situations, when a newly created or already existing utility, function, class or \
    other piece of code is used to obtain a certain return value which in reality is \
    not at all returned by the used entity, e.g.: when a function returns a list, but \
    the developer is trying to use it as a dictionary, or when two values are \
    returned, but the developer is trying to unpack it as three values.
    - If there's a big opportunity to extract common code or structure it in better way. Focus on most obvious scenarios.

    Don't look for minor issues, code style issues, etc.. List only issues that are \
    fundamental and prevent the code from working correctly or fulfilling the task.
    """  # noqa: E501
)


class DiffConsistencyCodeReview(CodeReviewModel):
    issues: list[str] = Field(default_factory=list, description=_issues_desc)


_diff_consistency_code_review_parser = PydanticOutputParser(
    pydantic_object=DiffConsistencyCodeReview
)

_example_output_diff_consistency_code_review = DiffConsistencyCodeReview(
    issues=[
        "The changes made to the code include a new function 'valid_discount' in the "
        "file 'src/utils/discount.py'. This function is not used anywhere in the code. "
        "It seems, however that the developer was trying to use the function in the "
        "file 'src/main.py' by calling 'validate_discount()' instead of "
        "'valid_discount()'.",
        "The changes made to the code include a calling the function 'calculate_price' "
        "in the file 'src/main.py'. The function `calculate_price` is defined in the "
        "file 'src/utils/utils.py'. The function is incorrectly imported in the file "
        "'src/main.py' as 'from src.utils import calculate_price' instead of "
        "'from src.utils.utils import calculate_price'.",
        "The changes made to the code include calling the function 'calculate_price' "
        "in the file 'src/main.py'. The function `calculate_price` is defined in the "
        "file 'src/utils/utils.py' as 'def calculate_price(price: float, *, discount: "
        "Discount) -> float`, however in the file 'src/main.py' it is called as "
        "'calculate_price(price, discount)'. The second argument should not be passed "
        "as a positional argument, but as a keyword argument. The correct call should "
        "be 'calculate_price(price, discount=discount).",
    ],
)


class DiffConsistencyCodeReviewer(BaseLLMCodeReviewer):
    """Code style code reviewer."""

    @property
    def name(self) -> str:
        return "diff_consistency_code_reviewer"

    def code_review_parser(self) -> PydanticOutputParser:
        return _diff_consistency_code_review_parser

    def example_output(self) -> CodeReviewModel:
        return _example_output_diff_consistency_code_review
