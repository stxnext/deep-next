from deep_next.core.steps.implement.acr import lint_python_content
from deep_next.core.steps.implement.apply_patch.common import ApplyPatchError, CodeMatch
from deep_next.core.steps.implement.utils import CodePatch

MAX_BF_INDENT_LEVELS = 7
MAX_BF_BASE_INDENT_SIZE = 24


def _get_unique_indentations(lines: list[str]) -> set[int]:
    """Get unique indentations from all 'lines'."""
    indentations = set()
    for line in lines:
        stripped_line = line.lstrip()

        leading_spaces = len(line) - len(stripped_line)
        indentations.add(leading_spaces)

    return indentations


def _get_indentation_size(lines: list[str]) -> int | None:
    """
    Get the number of spaces of each indentation level in 'lines'.

    If the number of spaces of the indentation level cannot be determined, return None.
    """
    indentations = _get_unique_indentations(lines)

    if len(indentations) < 2:
        # Not enough unique indentations to determine the indentation size.
        return None

    level_0_indent = min(indentations)
    indentations.remove(level_0_indent)
    level_1_indent = min(indentations)

    return level_1_indent - level_0_indent


def _add_matched_code_indentation(
    orig_prefix_lines: list[str],
    orig_suffix_lines: list[str],
    before_lines: list[str],
    after_lines: list[str],
    matched_orig_lines: list[str],
) -> str | None:
    """
    Try to add the indentation of the matched code to 'after_lines'.

    First, try to add the base indentation of the matched code to 'after_lines'. If
    this does not work, try to fix only the indentation of the first line of
    'after_lines'.

    Args:
        orig_prefix_lines: Lines before the matched code.
        orig_suffix_lines: Lines after the matched code.
        before_lines: All lines of the 'before' part of the patch.
        after_lines: All lines of the 'after' part of the patch.
        matched_orig_lines: All lines of the matched code.

    Returns:
        The new file text if the indentation was fixed, None otherwise.
    """
    if before_lines[0] not in matched_orig_lines[0]:
        return None

    abs_indent_of_first_line = matched_orig_lines[0].index(before_lines[0])

    # Case 1: Test if the patch is missing all indentation.
    fixed_after_lines = [" " * abs_indent_of_first_line + line for line in after_lines]
    new_file_text = _merge(orig_prefix_lines, orig_suffix_lines, fixed_after_lines)
    if lint_python_content(new_file_text):
        return new_file_text

    # Case 2: Test if only the first line of the patch is missing indentation.
    fixed_after_lines = [" " * abs_indent_of_first_line + after_lines[0]]
    fixed_after_lines.extend(after_lines[1:])
    new_file_text = _merge(orig_prefix_lines, orig_suffix_lines, fixed_after_lines)
    if lint_python_content(new_file_text):
        return new_file_text

    return None


def _brute_force_indentation_levels(
    orig_prefix_lines: list[str],
    orig_suffix_lines: list[str],
    no_indent_after_lines: list[str],
) -> str | None:
    """
    Brute-force all indentation levels for 'no_indent_after_lines'.

    Try all indentation levels for 'no_indent_after_lines' up to 'MAX_INDENT_FIX_LEVEL'.
    """
    indent_size = _get_indentation_size(no_indent_after_lines)

    if indent_size is None:
        indent_size = 1
        max_levels = MAX_BF_BASE_INDENT_SIZE
    else:
        max_levels = MAX_BF_INDENT_LEVELS

    for indent_level in range(max_levels):
        _fixed_after_lines = [
            " " * (indent_size * indent_level) + line for line in no_indent_after_lines
        ]
        new_file_text = _merge(orig_prefix_lines, orig_suffix_lines, _fixed_after_lines)
        if lint_python_content(new_file_text):
            return new_file_text

    return None


def _remove_indentation(lines: list[str]) -> list[str]:
    """
    Remove the base indentation from all 'lines'.

    Find the smallest indentation in `lines` and remove if from the beginning of each
    line.

    Example:
    ```python
    lines = [
        "    def foo():",
        "        return 'bar'",
    ]
    _remove_indentation(lines)
    # Output:
    # [
    #     "def foo():",
    #     "    return 'bar'",
    # ]
    ```
    """
    indentations = _get_unique_indentations(lines)

    if 0 in indentations:
        indentations.remove(0)

    if len(indentations) == 0:
        return lines

    patch_indentation = min(indentations)
    return [line[patch_indentation:] for line in lines]


def _merge(
    orig_prefix_lines: list[str],
    orig_suffix_lines: list[str],
    modification: str | list[str],
) -> str:
    """Merge the original code with the modification."""
    result = ""

    if orig_prefix_lines:
        result += "\n".join(orig_prefix_lines) + "\n"

    if isinstance(modification, list):
        modification = "\n".join(modification)

    result += modification
    if orig_suffix_lines:
        result += "\n" + "\n".join(orig_suffix_lines)

    return result


def lint_and_merge(
    file_lines: list[str],
    match: CodeMatch,
    patch: CodePatch,
) -> str:
    """Fix the linting of the code patch and merge it with the original code."""
    orig_prefix_lines = file_lines[: match.start]
    orig_suffix_lines = file_lines[match.end + 1 :]
    matched_orig_lines = file_lines[match.start : match.end + 1]

    new_file_text = _merge(orig_prefix_lines, orig_suffix_lines, patch.after)
    # Case 1: no need to lint non-python files, so just return the merged content.
    if patch.file_path.suffix != ".py":
        return new_file_text

    # Case 2: linting passes, so just return the new file text
    if lint_python_content(new_file_text):
        return new_file_text

    before_lines = patch.before.splitlines()
    after_lines = patch.after.splitlines()

    # Case 3: try adding matched code indentation to 'after_lines'
    if new_file_text := _add_matched_code_indentation(
        orig_prefix_lines,
        orig_suffix_lines,
        before_lines,
        after_lines,
        matched_orig_lines,
    ):
        return new_file_text

    # Case 4: try removing all indentation from 'after_lines'.
    no_indent_after_lines = _remove_indentation(after_lines)
    new_file_text = _merge(orig_prefix_lines, orig_suffix_lines, no_indent_after_lines)
    if lint_python_content(new_file_text):
        return new_file_text

    # Case 5: try using the exact indentation of 'matched_orig_lines' for 'after_lines'.
    if new_file_text := _add_matched_code_indentation(
        orig_prefix_lines,
        orig_suffix_lines,
        before_lines,
        no_indent_after_lines,
        matched_orig_lines,
    ):
        return new_file_text

    # Case 5: try all indentation levels for 'after_lines' up to 'MAX_INDENT_FIX_LEVEL'.
    if new_file_text := _brute_force_indentation_levels(
        orig_prefix_lines, orig_suffix_lines, no_indent_after_lines
    ):
        return new_file_text

    # There is no hope. Linting fails, and there is nothing we can do about this.
    original_code = "\n".join(file_lines)
    raise ApplyPatchError(
        f"Linting failed."
        f"\n"
        f"\nOriginal code:"
        f"\n```"
        f"\n{original_code}"
        f"\n```"
        f"\n"
        f"\nBefore:"
        f"\n```"
        f"\n{patch.before}"
        f"\n```"
        f"\n"
        f"\nAfter:"
        f"\n```"
        f"\n{patch.after}"
        f"\n```"
    )
