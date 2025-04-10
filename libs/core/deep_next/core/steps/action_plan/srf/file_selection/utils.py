import json
from pathlib import Path

from deep_next.core.steps.action_plan.srf.file_selection.analysis_model import (
    RelevantFile,
)


def tools_to_json(tools):
    return json.dumps(
        [
            {
                "name": tool.name,
                "description": tool.description.split("Example output:")[0].strip(),
                "args": {key: value["type"] for key, value in tool.args.items()},
            }
            for tool in tools
        ],
        indent=2,
    )


def validate_files(
    files: list[RelevantFile], root_path: Path
) -> tuple[list[Path], list[Path]]:
    relevant_files = []
    invalid_files = []
    for file in files:
        try:
            path = root_path / Path(file["path"])
            if path.is_file():
                relevant_files.append(path)
            else:
                invalid_files.append(path)
        except ValueError:
            pass

    return relevant_files, invalid_files
