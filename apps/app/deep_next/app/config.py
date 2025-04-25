from pathlib import Path

from deep_next.common.config import MONOREPO_DATA_PATH
from loguru import logger

SRC_PATH = Path(__file__).resolve().parent
ROOT_PATH = SRC_PATH.parent.parent

DATA_DIR = MONOREPO_DATA_PATH / "app"
RESULTS_DIR = DATA_DIR / "results"
REPOSITORIES_DIR = DATA_DIR / "repositories"

for dir_path in [DATA_DIR, RESULTS_DIR, REPOSITORIES_DIR]:
    if not dir_path.exists():
        logger.debug(f"Creating directory: `{dir_path}`")
    dir_path.mkdir(exist_ok=True, parents=True)

TODO_LABEL = "deep_next"
FAILED_LABEL = "deep_next_failed"
SOLVED_LABEL = "deep_next_solved"
IN_PROGRESS_LABEL = "deep_next_in_progress"

REF_BRANCH = "develop"

FEATURE_BRANCH_NAME_TMPL = "deep_next/issue_{issue_no}/{note}"

SCHEDULE_INTERVAL_ENV_VAR = "DEEP_NEXT_SCHEDULE_INTERVAL"
