import json

from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

overview_desc = (
    "Analyze all available knowledge, file dependencies, code location, import "
    "structure and the relevance of specific files to the issue. Use the previous "
    "overview for insight."
)

relevant_files_so_far_desc = (
    "List files that are likely related to the issue based on the current knowledge. "
    "Use their full path and a brief explanation of why they are relevant. Always keep "
    "the files previously identified as relevant, that have not been disproven to be "
    "related to the issue."
    ""
    "When listing files, always use their full path starting from one of the roots: "
    "{root_path_ls}"
)

reasoning_desc = (
    "Validate, if the most recent tool messages are sufficient to resolve any of the "
    'most recently identified "unknowns". Explain why the information is sufficient or '
    "why it is not. Support your reasoning with tool results and precise information."
)

unknowns_desc = (
    "List which traces require further investigation in order to identify the files "
    "relevant to the issue. Keep in mind: you are not solving the given issue, but "
    "tasked to identify relevant files. Each element of the list must contain an "
    "explanation of how it is related to identifying relevant files. Do not keep the "
    "unknowns that have been resolved. Don't create new unknowns if everything is "
    "clear. Returning a blank list is also a valid response."
)

next_steps_desc = (
    "Provide next steps for gathering knowledge needed to solve each point of "
    "uncertainty listed in the previous block. Be specific in what tools with which "
    "arguments should be used. Provide a brief explanation of why each step is "
    "necessary and how it will help to find relevant files."
)


class RelevantFile(BaseModel):
    path: str
    explanation: str

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        if isinstance(other, RelevantFile):
            return self.path == other.path
        return False


class Analysis(BaseModel):
    overview: str = Field(default="", description=overview_desc)
    relevant_files_so_far: list[RelevantFile] = Field(
        default_factory=list, description=relevant_files_so_far_desc
    )
    reasoning: str = Field(default="", description=reasoning_desc)
    unknowns: list[str] = Field(default_factory=list, description=unknowns_desc)
    next_steps: list[str] = Field(default_factory=list, description=next_steps_desc)

    @property
    def json_str(self) -> str:
        return json.dumps(self.model_dump())


analysis_parser = PydanticOutputParser(pydantic_object=Analysis)


example_output_next_steps = Analysis(
    overview=(
        "The function 'foo' in \"src/utils.py\" is likely related to the issue. The "
        "'bar' class in \"src/models/bar.py\" contains methods that are used in 'foo'. "
        'The "test/models/bar.py" file contains tests that show how these methods '
        "should behave. The result of the tool search for 'foo' in \"src/utils.py\" "
        "confirms this."
    ),
    relevant_files_so_far=[
        RelevantFile(
            path="src/utils.py", explanation="The 'foo' function is located here."
        ),
        RelevantFile(
            path="src/models/bar.py",
            explanation="The 'bar' class contains methods used in 'foo'.",
        ),
        RelevantFile(
            path="test/models/bar.py",
            explanation='Contains tests that show how methods in "src/models/bar.py" '
            "should behave.",
        ),
    ],
    reasoning=(
        "The 'foo' function is mentioned in the issue description, and the 'bar' class "
        "contains methods used in 'foo'. By analyzing the 'bar' class, we can "
        "understand the flow of the code and identify related files. The tools "
        "provided can help search for occurrences of the 'foo' function and analyze "
        "the 'bar' class. It's also worth making sure that the 'foo' function is "
        "located in the 'utils' module. If not, the search should be expanded to the "
        "entire codebase."
    ),
    unknowns=[
        "Unknown #1:"
        "\nThe logic flow of the 'foo' function."
        "\nThis step will help understand the exact logic flow of the 'foo' function "
        "and its relationship with other files that could turn out useful.",
        "Unknown #2:"
        "\nThe relationship between the 'bar' class and the 'foo' function."
        "\nThis step will help understand the relationship between the 'bar' class and "
        "the 'foo' function and if the files related to the 'bar' class are relevant.",
    ],
    next_steps=[
        "Search for occurrences of the function 'foo' in the codebase using the "
        "'find_function_in_file' tool."
        "\nRelated unknowns: #1, #2.",
        "Analyze the 'bar' class in the 'src/utils.py' module using the "
        "'analyze_class_in_file' tool."
        "\nRelated unknowns: #2.",
    ],
)

example_output_select_files = Analysis(
    overview=(
        "The function 'foo' was confirmed to be in \"src/utils.py\". The 'bar' class "
        "in \"src/models/bar.py\" contains methods that are used in 'foo'. The "
        '"test/models/bar.py" file contains tests that show how these methods should '
        "behave. The 'baz' function in \"src/utils.py\" is also related to the issue. "
        "The 'bar' class contains methods that are used in 'baz'. Baz is inherited "
        "from the 'qux' class in \"src/models/qux.py\", however, the 'qux' class does "
        "not have any logic related to the issue - it's a base class."
    ),
    relevant_files_so_far=[
        RelevantFile(
            path="src/utils.py",
            explanation="The 'foo' and 'baz' functions are located here.",
        ),
        RelevantFile(
            path="src/models/bar.py",
            explanation="The 'bar' class contains methods used in 'foo' and 'baz'.",
        ),
        RelevantFile(
            path="test/models/bar.py",
            explanation='Contains tests that show how methods in "src/models/bar.py" '
            "should behave.",
        ),
        RelevantFile(
            path="src/models/qux.py",
            explanation="The 'qux' class is inherited by 'baz'.",
        ),
    ],
    reasoning="",
    unknowns=[],
    next_steps=[],
)
