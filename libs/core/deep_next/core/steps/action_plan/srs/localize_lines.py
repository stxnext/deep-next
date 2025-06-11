import textwrap
from pathlib import Path

from deep_next.common.llm import LLMConfigType, create_llm
from deep_next.core.steps.action_plan.srs._agentless import (
    construct_topn_file_context,
    extract_locs_for_files,
    get_repo_files,
)
from deep_next.core.steps.action_plan.srs.common import (
    ExistingCodeContext,
    FileCodeContext,
)
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable


class Prompt:
    obtain_relevant_code_combine_top_n_prompt = textwrap.dedent(
        """
        Please review the following Issue Description and relevant files,
        and provide a set of locations that need to be edited to fix the issue.
        The locations can be specified as class names, function or method names,
        or exact line numbers that require modification.

        ### Issue Description ###
        {problem_statement}

        ### Files content ###
        {file_contents}


        Please provide the class name, function or method name, or the exact line
        numbers that need to be edited.
        The possible location outputs should be either "class", "function", "line"
        or "variable".

        EXAMPLE OUTPUT:
        --------------------
        {example_output_localize_lines}
        --------------------
        """
    )


def _create_llm_agent() -> RunnableSerializable:
    """Creates LLM agent for localizing classes, functions and lines"""
    design_solution_prompt_template = ChatPromptTemplate.from_messages(
        [
            ("user", Prompt.obtain_relevant_code_combine_top_n_prompt),
        ]
    )

    parser = PydanticOutputParser(pydantic_object=ExistingCodeContext)

    return (
        design_solution_prompt_template | create_llm(LLMConfigType.SRS_ANALYZE) | parser
    )


def localize_line_from_coarse_function_locs(
    file_names: list[Path],
    coarse_locs: dict,
    structure: dict,
    problem_statement: str,
    context_window: int = 10,
):
    """
    Localize classes, methods, functions, and lines from the coarse localizations.

    Based on the source code of coarse classes, methods, and functions, provide
    the classes, methods, functions, and lines.
    The main difference with `localize_function_from_compressed_files` is that
    it takes source code, not skeletons.
    Returns a dict mapping file names to names of localized classes, methods,
    functions, and lines.

    Return example:
    {
        "src/utils.py": "class: MyClass1\nfunction: my_function_1",
        "src/models/bar.py": "line: 10\nfunction: my_function_2",
    }
    """
    file_contents = get_repo_files(structure, file_names)
    topn_content, file_loc_intervals = construct_topn_file_context(
        coarse_locs,
        file_names,
        file_contents,
        structure,
        context_window=context_window,
    )

    raw_output = _create_llm_agent().invoke(
        {
            "problem_statement": problem_statement,
            "file_contents": topn_content,
            "example_output_localize_lines": example_output_loc_lines.model_dump_json(),
        }
    )

    model_found_locs_separated = extract_locs_for_files([raw_output.dump()], file_names)
    return model_found_locs_separated


example_output_loc_lines = ExistingCodeContext(
    overview_description=(
        "The issue desctiption mentions that the 'foo' function in 'src/utils.py' is "
        "likely related to the issue. "
        "The 'bar' class in 'src/models/bar.py' contains methods that are "
        "used in 'foo'."
        "To fix the issue, the 'foo' function in 'src/utils.py' should be reviewed and "
        "changed in a way that it works correctly with the 'bar' class "
        "in 'src/models/bar.py'."
    ),
    code_context=[
        FileCodeContext(
            path=Path("full_path1/file1.py"),
            reasoning=(
                "The bug appears to be in the 'MyClass1' class and their full "
                "context is needed to understand the issue in the next implementation "
                "step. Variable foo=False located in line 10 and used in line 51 "
                "should be set to True."
            ),
            localization_code_snippet=("line: 10\n" "class: MyClass1\n" "line: 51"),
        ),
        FileCodeContext(
            path=Path("full_path2/file2.py"),
            reasoning=(
                "The 'my_method' method in 'MyClass2' class appears to be "
                "related to the issue."
                "MyClass1 depends on MyClass2, so the MyClass2 context is needed to "
                "understand the issue in the next implementation step."
                "Function definition of my_method is located in line 12. It should be "
                "reviewed. Argument bar: int should be added to the method signature."
            ),
            localization_code_snippet=("function: MyClass2.my_method\n" "line: 12"),
        ),
        FileCodeContext(
            path=Path("full_path3/file3.py"),
            reasoning=(
                "MyClass1 inherits MyClass3, so the MyClass3 context is "
                "needed to understand the issue in the next implementation step."
                "Global variable foo is used in the function. The context of the "
                "variable is important to understand the issue."
            ),
            localization_code_snippet=("class: MyClass3\n" "variable: foo\n"),
        ),
    ],
)
