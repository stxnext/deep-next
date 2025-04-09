from pathlib import Path
from typing import Annotated

from deep_next.core.steps.action_plan.srf.file_selection.tools.acr.search_tools import (  # noqa: E501
    SearchBackend,
)
from langchain_core.tools import tool
from loguru import logger

# Running SRF in parallel requires handling multiple search backends at the same time.
# To do this, each search backend is stored in a dictionary with the root path as the
# key.
_acr_backend_dict: dict[Path, SearchBackend] = {}


def _acr_backend(root_path: Path) -> SearchBackend:
    return _acr_backend_dict[root_path]


def init_acr_backend(root_path: Path):
    logger.debug(f"Initializing ACR backend for '{root_path}'")
    _acr_backend_dict[root_path] = SearchBackend(str(root_path))
    logger.debug(f"Initialized ACR backend for '{root_path}'")


def dispose_acr_backend(root_path: Path):
    del _acr_backend_dict[root_path]


def search_class_tool_builder(root_path: Path):
    """Build a tool to search for a class by a given name in the source code."""

    @tool
    def search_class(
        class_name: Annotated[str, "Name of the class to search for."],
    ) -> Annotated[
        str, "The class definitions and methods of the classes if found."
    ]:  # noqa: D205
        """
        Search for a class by a given name in the entire code repository and return the
        class definitions.

        Example output:

        ```text
        Found 1 classes with name `HelloWorldResponse` in the codebase:

            - Search result 1:
            ```
            <file>src/model.py</file>
            <class>HelloWorldResponse</class>
            <code>
            class HelloWorldResponse:
                def __init__(self, message: str):
                def __eq__(self, other):
                def __repr__(self):
                def greet(self):

            </code>
            ```

        ```
        """
        tool_output, _, _ = _acr_backend(root_path).search_class(class_name)

        return tool_output

    return search_class


def search_method_tool_builder(root_path: Path):
    """Build a tool to search for a method by a given name in the source code."""

    @tool
    def search_method(
        method_name: Annotated[str, "Name of the method to search for."],
    ) -> Annotated[str, "The method definitions if found."]:  # noqa: D205
        '''
        Search for a method by a given name in the in the entire code repository and
        return the method definition.

        Example output:

        ```text
            Found 1 methods with name `say_hello` in the codebase:

            - Search result 1:
            ```
            <file>src/hello_world.py</file>
            <func>say_hello</func>
            <code>
            1 def say_hello():
            2     """Say hello!"""
            3     print("Hello World")

            </code>
            ```

        ```
        '''
        tool_output, _, _ = _acr_backend(root_path).search_method(method_name)

        return tool_output

    return search_method


def search_code_tool_builder(root_path: Path):
    """
    Build a `search_code` tool.

    Build a tool to search for a code snippet by a given search query in the source
    code.
    """

    @tool
    def search_code(
        search_query: Annotated[str, "The search query to search for."],
    ) -> Annotated[str, "The search results if found."]:  # noqa: D205
        '''
        Search for a code snippet by a given search query in the entire code repository
        and return the search results.

        Example output:

        ```text
        Found 1 snippets containing `def say_hello` in the codebase:

            - Search result 1:
            ```
            <file>src/hello_world.py</file>

            <code>
            1 def say_hello():
            2     """Say hello!"""
            3     print("Hello World")
            4

            </code>
            ```

        ```
        '''
        tool_output, _, _ = _acr_backend(root_path).search_code(search_query)

        return tool_output

    return search_code


def search_class_in_file_tool_builder(root_path: Path):
    """
    Build a `search_class_in_file` tool.

    Build a tool to search for a class in a given file by a given name in the source
    code.
    """

    @tool
    def search_class_in_file(
        class_name: Annotated[str, "Name of the class to search for."],
        file_path: Annotated[str, "Path to the file to search in."],
    ) -> Annotated[
        str, "The class definitions and methods of the classes if found."
    ]:  # noqa: D205
        """
        Search for a class by a given name in a file and return the class definitions
        and methods.

        Example output:

        ```text
        Found 1 classes with name `HelloWorldResponse` in file `model.py`:

            - Search result 1:
            ```
            <file>src/model.py</file>
            <class>HelloWorldResponse</class>
            <code>
            1 class HelloWorldResponse:
            2     def __init__(self, message: str):
            3         self.times_greeted = 0
            4         self.message = message
            5
            6     def __eq__(self, other):
            7         return self.message == other.message
            8
            9     def __repr__(self):
            10         return f"HelloWorldResponse(message={self.message})"
            11
            12     def greet(self):
            13         self.times_greeted += 1
            14         return self.message

            </code>
            ```

        ```
        """
        tool_output, _, _ = _acr_backend(root_path).search_class_in_file(
            class_name, file_path
        )

        return tool_output

    return search_class_in_file


def search_method_in_file_tool_builder(root_path: Path):
    """
    Build a `search_method_in_file` tool.

    Build a tool to search for a method in a given file by a given name in the
    source code.
    """

    @tool
    def search_method_in_file(
        method_name: Annotated[str, "Name of the method to search for."],
        file_path: Annotated[str, "Path to the file to search in."],
    ) -> Annotated[str, "The method definitions if found."]:  # noqa: D205
        '''
        Search for a method by a given name in a file and return the method definition.

        Example output:

        ```text
        Found 1 methods with name `say_hello` in file `hello_world.py`:

            - Search result 1:
            ```
            <file>src/hello_world.py</file>
            <func>say_hello</func>
            <code>
            1 def say_hello():
            2     """Say hello!"""
            3     print("Hello World")

            </code>
            ```

        ```
        '''
        tool_output, _, _ = _acr_backend(root_path).search_method_in_file(
            method_name, file_path
        )

        return tool_output

    return search_method_in_file


def search_method_in_class_tool_builder(root_path: Path):
    """
    Build a `search_method_in_class` tool.

    Build a tool to search for a method in a given class by a given name in the source
    code.
    """

    @tool
    def search_method_in_class(
        method_name: Annotated[str, "Name of the method to search for."],
        class_name: Annotated[str, "Name of the class to search in."],
    ) -> Annotated[str, "The method definitions if found."]:  # noqa: D205
        """
        Search for a method by a given name in a class and return the method
        definition.

        Example output:

        ```text
        Found 1 methods with name `greet` in class `HelloWorldResponse`:

            - Search result 1
            ```
            <file>src/model.py</file>
            <class>HelloWorldResponse</class> <func>greet</func>
            <code>
            12     def greet(self):
            13         self.times_greeted += 1
            14         return self.message

            </code>
            ```

        ```
        """
        tool_output, _, _ = _acr_backend(root_path).search_method_in_class(
            method_name, class_name
        )

        return tool_output

    return search_method_in_class


def search_code_in_file_tool_builder(root_path: Path):
    """
    Build a `search_code_in_file` tool.

    Build a tool to search for a code snippet in a given file by a given search query in
    the source code.
    """

    @tool
    def search_code_in_file(
        search_query: Annotated[str, "The search query to search for."],
        file_path: Annotated[str, "Path to the file to search in."],
    ) -> Annotated[str, "The search results if found."]:  # noqa: D205
        '''
        Search for a code snippet by a given search query in a file and return the
        search results.

        Example output:

        ```text
        Found 1 snippets with code `def say_hello` in file `hello_world.py`:

            - Search result 1:
            ```
            <file>src/hello_world.py</file>

            <code>
            1 def say_hello():
            2     """Say hello!"""
            3     print("Hello World")
            4

            </code>
            ```

        ```
        '''
        tool_output, _, _ = _acr_backend(root_path).search_code_in_file(
            search_query, file_path
        )

        return tool_output

    return search_code_in_file
