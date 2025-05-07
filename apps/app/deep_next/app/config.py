from enum import Enum
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

REF_BRANCH = "develop"


SCHEDULE_INTERVAL_ENV_VAR = "DEEP_NEXT_SCHEDULE_INTERVAL"


class DeepNextLabel(Enum):
    """State of the DeepNext process."""

    PENDING_E2E = "deep_next"
    PENDING_HITL = "deep_next_human_in_the_loop"

    IN_PROGRESS = "deep_next_in_progress"
    AWAITING_RESPONSE = "deep_next_awaiting_response"
    SOLVED = "deep_next_solved"
    FAILED = "deep_next_failed"
