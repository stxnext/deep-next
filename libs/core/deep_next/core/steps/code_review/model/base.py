from typing import NamedTuple

from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel


class CodeReviewModel(BaseModel):
    issues: list[str]
    """Issues found in the code while performing code review."""


class CodeReviewer(NamedTuple):
    name: str
    parser: PydanticOutputParser
    example_output: CodeReviewModel
