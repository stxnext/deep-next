import pytest
from deep_next.app.git import RunCmdError, run_command


@pytest.mark.parametrize(
    "cmd, expected_err_msg_content",
    [
        (
            ["git", "status"],
            "fatal: not a git repository",
        ),
        (
            ["git", "not_a_git_command"],
            "git: 'not_a_git_command' is not a git command. See 'git --help'.",
        ),
    ],
)
def test_run_command_has_meaningful_error_message(
    tmp_path, cmd: list[str], expected_err_msg_content: str
):
    """Test that run_command raises a meaningful error."""
    non_git_dir = tmp_path

    with pytest.raises(RunCmdError) as exc_info:
        run_command(cmd, cwd=non_git_dir)

    error_msg = str(exc_info.value)
    assert expected_err_msg_content in error_msg
