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

FAILED_LABEL = "deep_next_failed"
SOLVED_LABEL = "deep_next_solved"
IN_PROGRESS_LABEL = "deep_next_in_progress"

AWS_SM_PREFIX = "aws_sm/deep_next"
AWS_SM_ACCESS_TOKEN_NAME_TMPL = f"{AWS_SM_PREFIX}/{{project_name}}/access_token"

CONFIG_FILE_NAME_TMPL = "{project_name}-config.json"
FEATURE_BRANCH_NAME_TMPL = "deep_next/issue_{issue_no}/{note}"

SCHEDULE_INTERVAL_ENV_VAR = "DEEP_NEXT_SCHEDULE_INTERVAL"
