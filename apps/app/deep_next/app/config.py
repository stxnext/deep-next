from enum import Enum
from pathlib import Path

from deep_next.common.config import MONOREPO_DATA_PATH

SRC_PATH = Path(__file__).resolve().parent
ROOT_PATH = SRC_PATH.parent.parent

DATA_DIR = MONOREPO_DATA_PATH / "app"
CONFIGS_DIR = DATA_DIR / "configs"
RESULTS_DIR = DATA_DIR / "results"
REPOSITORIES_DIR = DATA_DIR / "repositories"

for dir_path in [CONFIGS_DIR, RESULTS_DIR, REPOSITORIES_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

AWS_SM_PREFIX = "aws_sm/deep_next"
AWS_SM_ACCESS_TOKEN_NAME_TMPL = f"{AWS_SM_PREFIX}/{{project_name}}/access_token"

CONFIG_FILE_NAME_TMPL = "{project_name}-config.json"
FEATURE_BRANCH_NAME_TMPL = "deep_next/issue_{issue_no}/{note}"

SCHEDULE_INTERVAL_ENV_VAR = "DEEP_NEXT_SCHEDULE_INTERVAL"


class DeepNextState(Enum):
    """State of the DeepNext process."""
    PENDING_E2E = "deep_next"
    PENDING_AP = "deep_next_propose_action_plan"
    PENDING_IMPLEMENT_AP = "deep_next_implement_action_plan"

    IN_PROGRESS = "deep_next_in_progress"
    AWAITING_RESPONSE = 'deep_next_awaiting_response'
    SOLVED = "deep_next_solved"
    FAILED = "deep_next_failed"
