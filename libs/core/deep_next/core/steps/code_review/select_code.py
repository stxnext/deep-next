from collections import defaultdict
from pathlib import Path

from deep_next.core.steps.action_plan.srs import select_related_snippets_graph
from deep_next.core.steps.action_plan.srs._agentless import create_structure
from unidiff import PatchSet


def select_code(
    root_path: Path,
    issue_statement: str,
    git_diff: str,
) -> dict[str, list[str]]:
    """
    Select code fragments from the files in the git diff based on the issue statement.

    Use the select_related_snippets module to find the relevant code snippets based on
    the issue statement and the files present in the git diff.
    """
    modified_files_paths = []
    for patch in PatchSet(git_diff):
        modified_file_path: Path = root_path / Path(patch.path)

        if not modified_file_path.is_file():
            raise FileNotFoundError(
                f"Critical error - cannot resolve path based on git diff. "
                f"File {Path(patch.path)} not found within {root_path}."
            )
        modified_files_paths.append(modified_file_path)

    file_locations = select_related_snippets_graph(
        root_path=root_path,
        problem_statement=issue_statement,
        files=modified_files_paths,
        structure=create_structure(root_path),
    )

    _code_fragments = defaultdict(list)
    for file_name, locations in file_locations.items():
        for (start_line, end_line) in locations:
            file_lines = (root_path / file_name).read_text().splitlines()
            selected_lines = file_lines[start_line:end_line]

            selected_lines = [
                f"{i + 1:4} |{line}"
                for i, line in enumerate(selected_lines, start=start_line)
            ]

            _code_fragments[file_name].append("\n".join(selected_lines))

    return _code_fragments
