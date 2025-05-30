import json
from pathlib import Path

from deep_next.core.steps.action_plan.srf.file_selection.analysis_model import (
    RelevantFile,
)
from loguru import logger


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
) -> tuple[list[RelevantFile], list[RelevantFile]]:
    valid = []
    invalid = []
    for file in files:
        abs_path = root_path / Path(file.path)

        if abs_path.is_file():
            valid.append(RelevantFile(path=str(file.path), explanation=file.explanation))
        else:
            logger.warning(f"File not found: {abs_path}")
            invalid.append(
                RelevantFile(
                    path=str(file.path),
                    explanation=f"[Invalid path] {file.explanation}",
                )
            )

    return valid, invalid
