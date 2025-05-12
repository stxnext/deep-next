from deep_next.core import config
from deep_next.core.steps.action_plan.srf.file_selection.tools.acr.search_tools import (  # noqa: E501
    SearchBackend,
)

EXAMPLE_MODULE_PATH = config.ROOT_DIR / "tests" / "_resources" / "example_project"


class BaseTestSearchTools:
    def setup_method(self) -> None:
        assert EXAMPLE_MODULE_PATH.is_dir()
        self.backend = SearchBackend(str(EXAMPLE_MODULE_PATH))


class TestSearchClass(BaseTestSearchTools):
    def test_search_class(self) -> None:
        tool_output, search_result, success = self.backend.search_class(
            "HelloWorldResponse"
        )

        assert success
        assert len(search_result) == 1
        assert search_result[0].file_path == str(
            EXAMPLE_MODULE_PATH / "src" / "model.py"
        )

        expected_tool_output = (
            "Found 1 classes with name `HelloWorldResponse` in the codebase:"
            "\n"
            "\n- Search result 1:"
            "\n```"
            "\n<file>src/model.py</file>"
            "\n<class>HelloWorldResponse</class>"
            "\n<code>"
            "\nclass HelloWorldResponse(pydantic.BaseModel):"
            "\n    def __init__(self, message: str):"
            "\n    def __eq__(self, other):"
            "\n    def __repr__(self):"
            "\n    def greet(self):"
            "\n"
            "\n</code>"
            "\n```"
            "\n"
        )

        assert tool_output == expected_tool_output

    def test_search_class_invalid_arguments(self) -> None:
        tool_output, search_result, success = self.backend.search_class(
            "GoodbyeWorldResponse"
        )

        assert not success
        assert len(search_result) == 0
        assert (
            tool_output == "Could not find class `GoodbyeWorldResponse` in the "
            "codebase."
        )


class TestSearchClassInFile(BaseTestSearchTools):
    def test_search_class_in_file(self) -> None:
        tool_output, search_result, success = self.backend.search_class_in_file(
            class_name="HelloWorldResponse", file_name="src/model.py"
        )

        assert success
        assert len(search_result) == 1
        assert search_result[0].file_path == str(
            EXAMPLE_MODULE_PATH / "src" / "model.py"
        )

        expected_tool_output = (
            "Found 1 classes with name `HelloWorldResponse` in file `src/model.py`:"  # noqa: E501
            "\n"
            "\n- Search result 1:"
            "\n```"
            "\n<file>src/model.py</file>"
            "\n<class>HelloWorldResponse</class>"
            "\n<code>"
            "\n4 class HelloWorldResponse(pydantic.BaseModel):"
            "\n5     def __init__(self, message: str):"
            "\n6         self.times_greeted = 0"
            "\n7         self.message = message"
            "\n8 "
            "\n9     def __eq__(self, other):"
            "\n10         return self.message == other.message"
            "\n11 "
            "\n12     def __repr__(self):"
            '\n13         return f"HelloWorldResponse(message={self.message})"'
            "\n14 "
            "\n15     def greet(self):"
            "\n16         self.times_greeted += 1"
            "\n17         return self.message"
            "\n"
            "\n</code>"
            "\n```"
            "\n"
        )

        assert tool_output == expected_tool_output

    def test_search_class_in_file_invalid_class_name(self) -> None:
        tool_output, search_result, success = self.backend.search_class_in_file(
            class_name="GoodbyeWorldResponse", file_name="src/model.py"
        )

        assert not success
        assert len(search_result) == 0
        assert (
            tool_output
            == "Could not find class `GoodbyeWorldResponse` in the codebase."
        )

    def test_search_class_in_file_invalid_file_name(self) -> None:
        tool_output, search_result, success = self.backend.search_class_in_file(
            class_name="HelloWorldResponse", file_name="does_not_exist.py"
        )

        assert not success
        assert len(search_result) == 0
        assert tool_output == "Could not find file `does_not_exist.py` in the codebase."


class TestSearchMethodInFile(BaseTestSearchTools):
    def test_search_method_in_file(self) -> None:
        tool_output, search_result, success = self.backend.search_method_in_file(
            method_name="say_hello", file_name="src/hello_world.py"
        )

        assert success
        assert len(search_result) == 1
        assert search_result[0].file_path == str(
            EXAMPLE_MODULE_PATH / "src" / "hello_world.py"
        )

        expected_tool_output = (
            "Found 1 methods with name `say_hello` in file `src/hello_world.py`:"
            "\n"
            "\n- Search result 1:"
            "\n```"
            "\n<file>src/hello_world.py</file>"
            "\n<func>say_hello</func>"
            "\n<code>"
            "\n1 def say_hello():"
            '\n2     """Say hello!"""'
            '\n3     print("Hello World")'
            "\n"
            "\n</code>"
            "\n```"
            "\n"
        )

        assert tool_output == expected_tool_output

    def test_search_method_in_file_invalid_method_name(self) -> None:
        tool_output, search_result, success = self.backend.search_method_in_file(
            method_name="say_goodbye", file_name="src/hello_world.py"
        )

        assert not success
        assert len(search_result) == 0
        assert (
            tool_output == "The method `say_goodbye` does not appear in the codebase."
        )

    def test_search_method_in_file_invalid_file_name(self) -> None:
        tool_output, search_result, success = self.backend.search_method_in_file(
            method_name="say_hello", file_name="src/goodbye_world.py"
        )

        assert not success
        assert len(search_result) == 0
        assert (
            tool_output == "Could not find file `src/goodbye_world.py` in the codebase."
        )


class TestSearchMethodInClass(BaseTestSearchTools):
    def test_search_method_in_class(self) -> None:
        tool_output, search_result, success = self.backend.search_method_in_class(
            method_name="greet", class_name="HelloWorldResponse"
        )

        assert success
        assert len(search_result) == 1
        assert search_result[0].file_path == str(
            EXAMPLE_MODULE_PATH / "src" / "model.py"
        )

        expected_tool_output = (
            "Found 1 methods with name `greet` in class `HelloWorldResponse`:"
            "\n"
            "\n- Search result 1:"
            "\n```"
            "\n<file>src/model.py</file>"
            "\n<class>HelloWorldResponse</class><func>greet</func>"
            "\n<code>"
            "\n15     def greet(self):"
            "\n16         self.times_greeted += 1"
            "\n17         return self.message"
            "\n"
            "\n</code>"
            "\n```"
            "\n"
        )

        assert tool_output == expected_tool_output

    def test_search_method_in_class_invalid_class_name(self) -> None:
        tool_output, search_result, success = self.backend.search_method_in_class(
            method_name="goodbye", class_name="GoodbyeWorldResponse"
        )

        assert not success
        assert len(search_result) == 0
        assert (
            tool_output
            == "Could not find class `GoodbyeWorldResponse` in the codebase."
        )

    def test_search_method_in_class_invalid_method_name(self) -> None:
        tool_output, search_result, success = self.backend.search_method_in_class(
            method_name="goodbye", class_name="HelloWorldResponse"
        )

        assert not success
        assert len(search_result) == 0
        assert (
            tool_output
            == "Could not find method `goodbye` in class `HelloWorldResponse`."
        )


class TestSearchMethod(BaseTestSearchTools):
    def test_search_method(self) -> None:
        tool_output, search_result, success = self.backend.search_method("say_hello")

        assert success
        assert len(search_result) == 1
        assert search_result[0].file_path == str(
            EXAMPLE_MODULE_PATH / "src" / "hello_world.py"
        )

        expected_tool_output = (
            "Found 1 methods with name `say_hello` in the codebase:"
            "\n"
            "\n- Search result 1:"
            "\n```"
            "\n<file>src/hello_world.py</file>"
            "\n<func>say_hello</func>"
            "\n<code>"
            "\n1 def say_hello():"
            '\n2     """Say hello!"""'
            '\n3     print("Hello World")'
            "\n"
            "\n</code>"
            "\n```"
            "\n"
        )

        assert tool_output == expected_tool_output

    def test_search_method_invalid_arguments(self) -> None:
        tool_output, search_result, success = self.backend.search_method("say_goodbye")

        assert not success
        assert len(search_result) == 0
        assert tool_output == "Could not find method `say_goodbye` in the codebase."


class TestSearchCode(BaseTestSearchTools):
    def test_search_code(self) -> None:
        tool_output, search_result, success = self.backend.search_code("def say_hello")

        assert success
        assert len(search_result) == 1
        assert search_result[0].file_path == str(
            EXAMPLE_MODULE_PATH / "src" / "hello_world.py"
        )

        expected_tool_output = (
            "Found 1 snippets containing `def say_hello` in the codebase:"
            "\n"
            "\n- Search result 1:"
            "\n```"
            "\n<file>src/hello_world.py</file>"
            "\n"
            "\n<code>"
            "\n1 def say_hello():"
            '\n2     """Say hello!"""'
            '\n3     print("Hello World")'
            "\n4 "
            "\n"
            "\n</code>"
            "\n```"
            "\n"
        )

        assert tool_output == expected_tool_output

    def test_search_code_invalid_arguments(self) -> None:
        tool_output, search_result, success = self.backend.search_code(
            "def say_goodbye"
        )

        assert not success
        assert len(search_result) == 0
        assert tool_output == "Could not find code `def say_goodbye` in the codebase."


class TestSearchCodeInFile(BaseTestSearchTools):
    def test_search_code_in_file(self) -> None:
        tool_output, search_result, success = self.backend.search_code_in_file(
            code_str="def say_hello", file_name="src/hello_world.py"
        )

        assert success
        assert len(search_result) == 1
        assert search_result[0].file_path == str(
            EXAMPLE_MODULE_PATH / "src" / "hello_world.py"
        )

        expected_tool_output = (
            "Found 1 snippets with code `def say_hello` in file `src/hello_world.py`:"
            "\n"
            "\n- Search result 1:"
            "\n```"
            "\n<file>src/hello_world.py</file>"
            "\n"
            "\n<code>"
            "\n1 def say_hello():"
            '\n2     """Say hello!"""'
            '\n3     print("Hello World")'
            "\n4 "
            "\n"
            "\n</code>"
            "\n```"
            "\n"
        )  # noqa: E501

        assert tool_output == expected_tool_output

    def test_search_code_in_file_invalid_code_str(self) -> None:
        tool_output, search_result, success = self.backend.search_code_in_file(
            code_str="def say_goodbye", file_name="src/hello_world.py"
        )

        assert not success
        assert len(search_result) == 0
        assert (
            tool_output
            == "Could not find code `def say_goodbye` in file `src/hello_world.py`."  # noqa: E501
        )

    def test_search_code_in_file_invalid_file_name(self) -> None:
        tool_output, search_result, success = self.backend.search_code_in_file(
            code_str="def say_hello", file_name="src/goodbye_world.py"
        )

        assert not success
        assert len(search_result) == 0
        assert (
            tool_output
            == "Could not find file `src/goodbye_world.py` in the codebase."  # noqa: E501
        )
