import textwrap
from pathlib import Path

from deep_next.core.steps.action_plan.srs._agentless import (
    extract_locs_for_files,
    get_repo_files,
    get_skeleton,
)
from deep_next.core.steps.action_plan.srs.common import (
    ExistingCodeContext,
    FileCodeContext,
    _create_llm,
)
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable


class Prompt:
    file_content_in_block_template = textwrap.dedent(
        """
        ### File: {file_name} ###
        ```python
        {file_content}
        ```
        """
    )

    get_relevant_classes_and_func_from_compressed_files_prompt = textwrap.dedent(
        """
        Please look through the following Issue Description and the Skeleton of Relevant Files.

        Identify all locations that need inspection or editing to fix the problem: directly related areas, any potentially related global variables, functions, and classes.
        For each location you provide, give either:
        - the name of the class,
        - the name of a method in a class,
        - the name of a function, or
        - the name of a global variable.

        ### Issue Description ###
        {problem_statement}

        ### Skeleton of Relevant Files ###
        {file_contents}


        Please provide the complete set of locations as either a class name or a function name.
        Note that if you include a class, you do not need to list its specific methods.
        You can either:
        - include the entire class, or
        - not include the class name and instead include a specific method (or methods) in the class.

        Mark a class or a function as relevant even if you are not sure if it is directly related to the issue.
        If a class inherits another class, include the parent class if you think it is relevant to the issue.
        If there is implemented function than needs to be invoked to resolve the issue include this function as well.

        EXAMPLE OUTPUT:
        --------------------
        {example_class_files_vars_out}
        --------------------
        """  # noqa: E501
    )


def _create_llm_agent() -> RunnableSerializable:
    """Creates LLM agent for localizing classes, functions and global variables"""
    design_solution_prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "user",
                Prompt.get_relevant_classes_and_func_from_compressed_files_prompt,
            ),
        ]
    )

    parser = PydanticOutputParser(pydantic_object=ExistingCodeContext)

    return design_solution_prompt_template | _create_llm() | parser


def localize_function_from_compressed_files(
    file_names: list[Path],
    structure: dict,
    problem_statement: str,
):
    """
    Localize classes, methods, and functions from compressed-skeleton files.

    Returns a dict mapping file names to names of localized classes, methods, functions

    Return example:
    {
        "src/utils.py": "class: MyClass1\nfunction: my_function_1",
        "src/models/foo.py": "class: MyClass3\nfunction: my_function_2\n variable: foo",
    }
    """
    file_contents = get_repo_files(structure, file_names)
    compressed_file_contents = {
        fn: get_skeleton(code) for fn, code in file_contents.items()
    }
    contents = [
        Prompt.file_content_in_block_template.format(file_name=fn, file_content=code)
        for fn, code in compressed_file_contents.items()
    ]

    raw_output = _create_llm_agent().invoke(
        {
            "problem_statement": problem_statement,
            "file_contents": "".join(contents),
            "example_class_files_vars_out": example_class_files_vars.model_dump_json(),
        }
    )

    model_found_locs_separated = extract_locs_for_files([raw_output.dump()], file_names)

    return model_found_locs_separated


example_class_files_vars = ExistingCodeContext(
    overview_description=(
        "The issue description mentions that the 'foo' function in "
        "'src/utils.py' is likely related to the issue. "
        "The 'bar' class in 'src/models/bar.py' contains methods that are used"
        " in 'foo'. To fix the issue, the 'foo' function in 'src/utils.py' "
        "should be reviewed and changed in a way that it works correctly with "
        "the 'bar' class in 'src/models/bar.py'."
    ),
    code_context=[
        FileCodeContext(
            path=Path("full_path1/file1.py"),
            reasoning=(
                "The bug appears to be in the 'MyClass1' class and their"
                " full context is needed to understand the issue in the next "
                "implementation step. my_function_1 may contain the implementation"
                " of xxx so it should be reviewed."
            ),
            localization_code_snippet=("class: MyClass1\nfunction: my_function_1"),
        ),
        FileCodeContext(
            path=Path("full_path2/file2.py"),
            reasoning=(
                "The 'my_method' method in 'MyClass2' class appears to "
                "be related to the issue. MyClass1 depends on MyClass2, so the "
                "MyClass2 context is needed to understand the issue in the next "
                "implementation step."
                "Argument bar: int should be added to the method signature."
            ),
            localization_code_snippet=("function: MyClass2.my_method"),
        ),
        FileCodeContext(
            path=Path("full_path3/file3.py"),
            reasoning=(
                "MyClass1 inherits MyClass3, so the MyClass3 context is"
                " needed to understand the issue in the next implementation step."
                "my_function_2 is potentially related to the issue, because the name of"
                " the function suggests that it is related to the issue. "
                "Global variable foo is used in the function. The context of the "
                "variable is important to understand the issue."
            ),
            localization_code_snippet=(
                "class: MyClass3\nfunction: my_function_2\n variable: foo"
            ),
        ),
    ],
)
