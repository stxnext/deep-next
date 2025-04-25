import ast
import contextlib
import os
import re
from collections.abc import Callable
from functools import wraps
from pathlib import Path

from deep_next.core.config import SRF_INDEXER_IGNORE_DIR_PREFIXES
from loguru import logger


@contextlib.contextmanager
def cd(newdir):  # noqa
    """
    Context manager for changing the current working directory
    :param newdir: path to the new directory
    :return: None
    """
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def to_relative_path(file_path: str, project_root: str) -> str:
    """Convert an absolute path to a path relative to the project root.

    Args:
        - file_path (str): The absolute path.
        - project_root (str): Absolute path of the project root dir.

    Returns:
        The relative path.
    """
    if Path(file_path).is_absolute():
        return str(Path(file_path).relative_to(project_root))
    else:
        return file_path


def catch_all_and_log(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(e)
            # log_exception(e)
            err = str(e)
            # TODO: this string is there for legacy reasons
            summary = "The tool returned error message."
            return err, summary, False

    return wrapper


def is_test_file(file_path: str) -> bool:
    """Check if a file is a test file.

    This is a simple heuristic to check if a file is a test file.
    """
    return (
        "test" in Path(file_path).parts
        or "tests" in Path(file_path).parts
        or file_path.endswith("_test.py")
    )


def _get_python_files(
    dir_path: str, ignore_prefixes: list[str] | None = None
) -> list[str]:
    """
    Retrieves all .py files from a directory while ignoring specified directories.

    Parameters:
    - dir_path (str): The base directory to scan.
    - ignore_prefixes (list[str]): A list of directory prefixes to ignore.
    - ignore_literals (list[str]): A list of exact directory names to ignore.

    Returns:
    - list[str]: A list of Python file paths.
    """
    msg = f"Gathering all python files within `{dir_path}`"
    if ignore_prefixes is None:
        ignore_prefixes = []
        msg += " recursively for all dirs"
    else:
        msg += f" ignoring dirs with prefixes: `{ignore_prefixes}`"

    logger.debug(msg)

    py_files = []

    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [
            d
            for d in dirs
            if not any(d.startswith(prefix) for prefix in ignore_prefixes)
        ]

        py_files.extend(os.path.join(root, f) for f in files if f.endswith(".py"))

    return [p for p in py_files if not is_test_file(p[len(dir_path) + 1 :])]


def find_python_files(dir_path: str) -> list[str]:  # noqa
    """Get all .py files recursively from a directory.

    Skips files that are obviously not from the source code, such third-party library
    code.

    Args:
        dir_path (str): Path to the directory.
    Returns:
        List[str]: List of .py file paths. These paths are ABSOLUTE path!
    """
    return _get_python_files(
        dir_path,
        ignore_prefixes=SRF_INDEXER_IGNORE_DIR_PREFIXES,
    )


def parse_class_def_args(source: str, node: ast.ClassDef) -> list[str]:
    # TODO this is simple enough to cover a lot of cases but can be improved
    super_classes = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            if base.id in ["type", "object"]:
                continue
            super_classes.append(ast.get_source_segment(source, base))
        if (
            isinstance(base, ast.Call)
            and ast.get_source_segment(source, base.func) == "type"
        ):
            super_classes.append(ast.get_source_segment(source, base.args[0]))
    return super_classes


def parse_python_file(
    file_full_path: str,
) -> (
    tuple[
        list[tuple[str, int, int]],
        dict[str, list[tuple[str, int, int]]],
        list[tuple[str, int, int]],
        dict[tuple[str, int, int], list[str]],
    ]
    | None
):  # noqa
    """
    Main method to parse AST and build search index.
    Handles complication where python ast module cannot parse a file.
    """
    try:
        file_content = Path(file_full_path).read_text()
        tree = ast.parse(file_content)
    except Exception:
        # failed to read/parse one file, we should ignore it
        return None

    # (1) get all classes defined in the file
    classes: list[tuple[str, int, int]] = []
    # (2) for each class in the file, get all functions defined in the class.
    class_to_funcs: dict[str, list[tuple[str, int, int]]] = {}
    # (3) get top-level functions in the file (excludes functions defined in classes)
    top_level_funcs: list[tuple[str, int, int]] = []
    # (4) get class relations
    class_relation_map: dict[tuple[str, int, int], list[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # class part (1): collect class info
            class_name = node.name
            start_lineno = node.lineno
            end_lineno = node.end_lineno
            assert end_lineno is not None, "class should have end_lineno in AST."
            # line numbers are 1-based
            classes.append((class_name, start_lineno, end_lineno))
            class_relation_map[
                (class_name, start_lineno, end_lineno)
            ] = parse_class_def_args(file_content, node)

            # class part (2): collect function info inside this class
            class_funcs = [
                (n.name, n.lineno, n.end_lineno)
                for n in ast.walk(node)
                if isinstance(n, ast.FunctionDef) and n.end_lineno is not None
            ]
            class_to_funcs[class_name] = class_funcs

        elif isinstance(node, ast.FunctionDef):
            function_name = node.name
            start_lineno = node.lineno
            end_lineno = node.end_lineno
            assert end_lineno is not None, "function should have end_lineno in AST."
            # line numbers are 1-based
            top_level_funcs.append((function_name, start_lineno, end_lineno))

    return classes, class_to_funcs, top_level_funcs, class_relation_map


def get_code_region_containing_code(
    file_full_path: str, code_str: str, with_lineno=True
) -> list[tuple[int, str]]:
    """In a file, get the region of code that contains a specific string.

    Args:
        - file_full_path: Path to the file. (absolute path)
        - code_str: The string that the function should contain.
    Returns:
        - A list of tuple, each of them is a pair of (line_no, code_snippet).
        line_no is the starting line of the matched code; code snippet is the
        source code of the searched region.
    """
    with open(file_full_path) as f:
        file_content = f.read()

    context_size = 3
    # since the code_str may contain multiple lines, let's not split the source file.

    # we want a few lines before and after the matched string. Since the matched string
    # can also contain new lines, this is a bit trickier.
    pattern = re.compile(re.escape(code_str))
    # each occurrence is a tuple of (line_no, code_snippet) (1-based line number)
    occurrences: list[tuple[int, str]] = []
    for match in pattern.finditer(file_content):
        matched_start_pos = match.start()
        # first, find the line number of the matched start position (0-based)
        matched_line_no = file_content.count("\n", 0, matched_start_pos)

        file_content_lines = file_content.splitlines()

        window_start_index = max(0, matched_line_no - context_size)
        window_end_index = min(
            len(file_content_lines), matched_line_no + context_size + 1
        )

        if with_lineno:
            context = ""
            for i in range(window_start_index, window_end_index):
                context += f"{i+1} {file_content_lines[i]}\n"
        else:
            context = "\n".join(file_content_lines[window_start_index:window_end_index])
        occurrences.append((matched_line_no, context))

    return occurrences


def get_code_snippets(
    file_full_path: str, start: int, end: int, with_lineno=True
) -> str:
    """Get the code snippet in the range in the file, without line numbers.

    Args:
        file_path (str): Full path to the file.
        start (int): Start line number. (1-based)
        end (int): End line number. (1-based)
    """
    with open(file_full_path) as f:
        file_content = f.readlines()
    snippet = ""
    for i in range(start - 1, end):
        if with_lineno:
            snippet += f"{i+1} {file_content[i]}"
        else:
            snippet += file_content[i]
    return snippet


def extract_func_sig_from_ast(func_ast: ast.FunctionDef) -> list[int]:
    """Extract the function signature from the AST node.

    Includes the decorators, method name, and parameters.

    Args:
        func_ast (ast.FunctionDef): AST of the function.

    Returns:
        The source line numbers that contains the function signature.
    """
    func_start_line = func_ast.lineno
    if func_ast.decorator_list:
        # has decorators
        decorator_start_lines = [d.lineno for d in func_ast.decorator_list]
        decorator_first_line = min(decorator_start_lines)
        func_start_line = min(decorator_first_line, func_start_line)
    # decide end line from body
    if func_ast.body:
        # has body
        body_start_line = func_ast.body[0].lineno
        end_line = body_start_line - 1
    else:
        # no body
        end_line = func_ast.end_lineno
    assert end_line is not None
    return list(range(func_start_line, end_line + 1))


def extract_class_sig_from_ast(class_ast: ast.ClassDef) -> list[int]:
    """Extract the class signature from the AST.

    Args:
        class_ast (ast.ClassDef): AST of the class.

    Returns:
        The source line numbers that contains the class signature.
    """
    # STEP (1): extract the class signature
    sig_start_line = class_ast.lineno
    if class_ast.body:
        # has body
        body_start_line = class_ast.body[0].lineno
        sig_end_line = body_start_line - 1
    else:
        # no body
        sig_end_line = class_ast.end_lineno
    assert sig_end_line is not None
    sig_lines = list(range(sig_start_line, sig_end_line + 1))

    # STEP (2): extract the function signatures and assign signatures
    for stmt in class_ast.body:
        if isinstance(stmt, ast.FunctionDef):
            sig_lines.extend(extract_func_sig_from_ast(stmt))
        elif isinstance(stmt, ast.Assign):
            # for Assign, skip some useless cases where the assignment is to create docs
            stmt_str_format = ast.dump(stmt)
            if "__doc__" in stmt_str_format:
                continue
            # otherwise, Assign is easy to handle
            assert stmt.end_lineno is not None
            assign_range = list(range(stmt.lineno, stmt.end_lineno + 1))
            sig_lines.extend(assign_range)

    return sig_lines


def get_class_signature(file_full_path: str, class_name: str) -> str:
    """Get the class signature.

    Args:
        file_path (str): Path to the file.
        class_name (str): Name of the class.
    """
    with open(file_full_path) as f:
        file_content = f.read()

    tree = ast.parse(file_content)
    relevant_lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            # we reached the target class
            relevant_lines = extract_class_sig_from_ast(node)
            break
    if not relevant_lines:
        return ""
    else:
        with open(file_full_path) as f:
            file_content = f.readlines()
        result = ""
        for line in relevant_lines:
            line_content: str = file_content[line - 1]
            if line_content.strip().startswith("#"):
                # this kind of comment could be left until this stage.
                # reason: # comments are not part of func body if they appear at
                # beginning of func
                continue
            result += line_content
        return result
