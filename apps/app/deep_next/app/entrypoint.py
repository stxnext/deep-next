from loguru import logger

from deep_next.app.config import (
    REF_BRANCH,
    REPOSITORIES_DIR,
    DeepNextState,
)
from deep_next.app.git import GitRepository, setup_local_git_repo
from deep_next.app.handle_issues import handle_e2e, handle_human_in_the_loop
from deep_next.app.handle_mrs import handle_mr_e2e
from deep_next.app.utils import get_connector
from deep_next.app.vcs_config import VCSConfig, load_vcs_config_from_env
from deep_next.connectors.version_control_provider import (
    BaseConnector,
    BaseIssue,
    BaseMR,
)

MESSAGE_TO_DEEPNEXT_PREFIX = "@deepnext"

ACTION_PLAN_PREFIX = "## Action Plan"
ACTION_PLAN_RESPONSE_INSTRUCTIONS = (
    "## How to respond?"
    "\nTo ACCEPT the action plan, respond with:"
    "\n```"
    f"\n{MESSAGE_TO_DEEPNEXT_PREFIX}"
    "\nOK"
    "\n```"
    "\n"
    "\nTo REQUEST CHANGES to the action plan, talk to DeepNext using the following message format:"  # noqa: E501
    "\n```"
    f"\n{MESSAGE_TO_DEEPNEXT_PREFIX}"
    "\n*<message to deepnext>*"
    "\n```"
)


def find_issues(vcs_connector: BaseConnector, label: DeepNextState) -> list[BaseIssue]:
    """Fetches all issues to be solved by DeepNext.

    Excludes labels that are not allowed to be processed.
    """

    return vcs_connector.list_issues(label=label.value)


def find_mrs(vcs_connector: BaseConnector, label: DeepNextState) -> list[BaseMR]:
    """Fetches all merge requests to be solved by DeepNext.

    Excludes labels that are not allowed to be processed.
    """
    excluding_labels = [
        DeepNextState.FAILED.value,
        DeepNextState.SOLVED.value,
        DeepNextState.IN_PROGRESS.value,
    ]

    resp = []
    for mr in vcs_connector.list_mrs(label=label.value):
        if excluded := sorted([x for x in excluding_labels if x in mr.labels]):
            logger.warning(
                f"Skipping MR #{mr.no} ({mr.url}) due to label(s): {excluded}"
            )
            continue
        resp.append(mr)

    return resp


# def _solve_issue(
#     vcs_config: VCSConfig,
#     issue: BaseIssue,
#     local_repo: GitRepository,
#     ref_branch: str = REF_BRANCH,
# ) -> BaseMR | None:
#     """Solves a single issue."""
#     feature_branch: FeatureBranch = local_repo.new_feature_branch(
#         ref_branch,
#         feature_branch=_create_feature_branch_name(issue.no),
#     )
#     issue.add_comment(f"Assigned feature branch: `{feature_branch.name}`")
#
#     start_time = time.time()
#     try:
#         deep_next_graph(
#             root=local_repo.repo_dir,
#             problem_statement=issue.title + "\n" + issue.description,
#             hints="",
#         )
#     finally:
#         exec_time = time.time() - start_time
#
#         msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
#         logger.info(msg)
#         issue.add_comment(msg)
#
#     feature_branch.commit_all(
#         commit_msg=f"DeepNext resolves #{issue.no}: {issue.title}"
#     )
#     feature_branch.push_to_remote()
#
#     mr = vcs_config.create_mr(
#         merge_branch=feature_branch.name,
#         into_branch=ref_branch,
#         title=f"Resolve '{issue.title}'",
#     )
#
#     return mr


# def _solve_issue_and_label(
#     vcs_config: VCSConfig,
#     issue: BaseIssue,
#     local_repo: GitRepository,
#     ref_branch: str = REF_BRANCH,
# ) -> bool:
#     success: bool
#     try:
#         issue.add_label(DeepNextState.IN_PROGRESS)
#
#         mr = _solve_issue(
#             vcs_config,
#             issue,
#             local_repo,
#             ref_branch=ref_branch,
#         )
#     except Exception as e:
#         err_msg = f"🔴 DeepNext app failed for #{issue.no}: {str(e)}"
#         logger.error(err_msg)
#
#         issue.add_label(DeepNextState.FAILED)
#         issue.add_comment(
#             comment=err_msg, file_content=str(e), file_name="error_message.txt"
#         )
#
#         success = False
#     else:
#         msg = f"🟢 Issue #{issue.no} solved: {mr.url}"
#         logger.success(msg)
#
#         issue.add_label(DeepNextState.SOLVED)
#         issue.add_comment(msg)
#
#         success = True
#     finally:
#         issue.remove_label(DeepNextState.IN_PROGRESS)
#
#     return success


# def _propose_action_plan(
#     issue: BaseIssue,
#     local_repo: GitRepository,
#     old_action_plan: str | None = None,
#     edit_instructions: str | None = None,
# ) -> None:
#     """Propose an action plan."""
#     start_time = time.time()
#     try:
#         if old_action_plan and edit_instructions:
#             hints = (
#                 f"Edit the action plan:"
#                 f"\n```"
#                 f"\n{old_action_plan}"
#                 f"\n```"
#                 f"\nwith instructions:"
#                 f"\n```"
#                 f"\n{edit_instructions}"
#                 f"\n```"
#             )
#         else:
#             hints = ""
#
#         action_plan = deep_next_action_plan_graph(
#             root_path=local_repo.repo_dir,
#             problem_statement=issue.title + "\n" + issue.description,
#             hints=hints,
#         )
#     finally:
#         exec_time = time.time() - start_time
#
#         msg = f"DeepNext core total execution time: {exec_time:.0f} seconds"
#         logger.info(msg)
#         issue.add_comment(msg)
#
#     pretty_action_plan = json.dumps(
#         convert_paths_to_str(action_plan.model_dump()), indent=4
#     )
#
#     issue.add_comment(
#         f"{ACTION_PLAN_PREFIX}"
#         f"\n```action-plan"
#         f"\n{pretty_action_plan}"
#         f"\n```"
#         f"\n{ACTION_PLAN_RESPONSE_INSTRUCTIONS}",
#         independent=True
#     )
#
#
# def _modify_or_propose_new_action_plan(
#     issue: BaseIssue,
#     local_repo: GitRepository,
#     old_action_plan: str | None = None,
#     edit_instructions: str | None = None,
# ) -> None:
#     pass
#
#
# def _propose_action_plan_and_label(
#     issue: BaseIssue,
#     local_repo: GitRepository,
# ) -> bool:
#
#     try:
#         issue.add_label(DeepNextState.IN_PROGRESS)
#
#         _propose_action_plan(
#             issue,
#             local_repo,
#         )
#     except Exception as e:
#         err_msg = f"🔴 DeepNext app failed for #{issue.no}"
#         logger.error(err_msg)
#         issue.add_comment(
#             comment=err_msg, file_content=str(e), file_name="error_message.txt"
#         )
#
#         succeeded = False
#         issue.add_label(DeepNextState.FAILED)
#     else:
#         succeeded = True
#         issue.add_label(DeepNextState.AWAITING_RESPONSE)
#     finally:
#         issue.remove_label(DeepNextState.IN_PROGRESS)
#
#     return succeeded


def _get_last_action_plan(issue: BaseIssue) -> str | None:
    for comment in issue.comments[::-1]:
        if comment.body.startswith(ACTION_PLAN_PREFIX):
            action_plan = comment.body[len(ACTION_PLAN_PREFIX) :].strip()
            return action_plan
    return None


# def _handle_user_action_plan_response_and_label(
#     issue: BaseIssue,
#     local_repo: GitRepository,
# ) -> bool:
#
#     last_comment = issue.comments[-1]
#
#     if not last_comment.body.startswith(MESSAGE_TO_DEEPNEXT_PREFIX):
#         return True
#
#     message_to_deepnext = last_comment.body[len(MESSAGE_TO_DEEPNEXT_PREFIX) :].strip()
#     if message_to_deepnext.lower() == "ok":
#         issue.add_label(DeepNextState.PENDING_IMPLEMENT_AP)
#         issue.remove_label(DeepNextState.AWAITING_RESPONSE)
#         issue.add_comment("Action plan accepted. Proceeding with implementation.")
#     else:
#         issue.add_comment(
#             f"Received a request to change the action plan:"
#             f"\n> {message_to_deepnext[:25] + '(...)' + message_to_deepnext[25:] if len(message_to_deepnext) > 50 else message_to_deepnext}"
#             f"\nDeepNext is taking care of it.",
#             info_header=True
#         )
#
#         old_action_plan = _get_last_action_plan(issue)
#
#         issue.add_label(DeepNextState.IN_PROGRESS)
#         issue.remove_label(DeepNextState.AWAITING_RESPONSE)
#
#         # TODO(iwanicki) this does not handle well small modifications. Add a switch.
#         _propose_action_plan(
#             issue,
#             local_repo,
#             old_action_plan=old_action_plan,
#             edit_instructions=message_to_deepnext,
#         )
#
#     return last_comment


def handle_issues(vcs_config: VCSConfig) -> None:
    vcs_connector = get_connector(vcs_config)

    local_repo: GitRepository = setup_local_git_repo(
        repo_dir=REPOSITORIES_DIR / vcs_config.repo_path.replace("/", "_"),
        clone_url=vcs_config.clone_url,  # TODO: Security: logs url with access token
    )

    for issue in find_issues(vcs_connector, label=DeepNextState.PENDING_E2E):
        handle_e2e(
            vcs_config,
            issue,
            local_repo,
            ref_branch=REF_BRANCH
        )

    for issue in find_issues(vcs_connector, label=DeepNextState.PENDING_HITL):
        handle_human_in_the_loop(
            vcs_config,
            issue,
            local_repo,
            ref_branch=REF_BRANCH
        )


def handle_mrs(vcs_config: VCSConfig) -> None:
    vcs_connector = get_connector(vcs_config)

    local_repo: GitRepository = setup_local_git_repo(
        repo_dir=REPOSITORIES_DIR / vcs_config.repo_path.replace("/", "_"),
        clone_url=vcs_config.clone_url,  # TODO: Security: logs url with access token
    )

    for mr in find_mrs(vcs_connector, label=DeepNextState.PENDING_E2E):
        handle_mr_e2e(
            mr,
            local_repo,
            vcs_connector,
        )


# def solve_project_issues(vcs_config: VCSConfig) -> None:
#     """Solves all issues dedicated for DeepNext for a given project."""
#     logger.debug(f"Creating connector for '{vcs_config.repo_path}' project")
#     vcs_connector = _get_connector(vcs_config)
#
#     logger.debug(f"Preparing local git repo for '{vcs_config.repo_path}' project")
#     local_repo: GitRepository = setup_local_git_repo(
#         repo_dir=REPOSITORIES_DIR / vcs_config.repo_path.replace("/", "_"),
#         clone_url=vcs_config.clone_url,  # TODO: Security: logs url with access token
#     )
#
#     logger.debug(f"Looking for issues to handle in '{vcs_config.repo_path}' project")
#
#     results = []
#     for issue in find_issues(vcs_connector, label=DeepNextState.PENDING_E2E):
#         logger.success(f"Found an issue for '{vcs_config.repo_path}' repo: #{issue.no}")
#         succeeded = _solve_issue_and_label(
#             vcs_config, issue, local_repo, ref_branch=REF_BRANCH
#         )
#         results.append(succeeded)
#
#     for gitlab_issue in find_issues(vcs_connector, label=DeepNextState.PENDING_HITL):
#         if gitlab_issue.has_label(DeepNextState.AWAITING_RESPONSE):
#             succeeded = _handle_user_action_plan_response_and_label(
#                 gitlab_issue,
#                 local_repo,
#             )
#             results.append(succeeded)
#         else:
#             succeeded = _propose_action_plan_and_label(
#                 gitlab_issue,
#                 local_repo,
#             )
#             results.append(succeeded)
#
#     logger.success(
#         f"Project '{vcs_config.repo_path}' summary: "
#         f"total={len(results)}; solved={sum(results)}; failed={len(results) - sum(results)}"  # noqa: E501
#     )


def main() -> None:
    """Solves issues dedicated for DeepNext for given project."""
    vcs_config: VCSConfig = load_vcs_config_from_env()

    handle_issues(vcs_config)
    handle_mrs(vcs_config)

    # logger.info(f"Looking for issues in '{vcs_config.repo_path}' project...")
    # solve_project_issues(vcs_config)

    logger.success("DeepNext app run completed.")


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    main()
