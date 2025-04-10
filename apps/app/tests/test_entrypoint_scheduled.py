from unittest.mock import patch

import pytest
from click.testing import CliRunner
from deep_next.app.config import SCHEDULE_INTERVAL_ENV_VAR
from deep_next.app.entrypoint_scheduled import cli


@patch("deep_next.app.entrypoint_scheduled.task_scheduler")
def test_default_value(mock_task_scheduler, monkeypatch):
    """Test that default value is used when no env var or CLI argument is provided."""
    monkeypatch.delenv(SCHEDULE_INTERVAL_ENV_VAR, raising=False)

    CliRunner().invoke(cli)

    default_schedule_interval = 60
    mock_task_scheduler.assert_called_once_with(default_schedule_interval)


@patch("deep_next.app.entrypoint_scheduled.task_scheduler")
@pytest.mark.parametrize("interval", (30, 0))
def test_env_var(mock_task_scheduler, monkeypatch, interval):
    """Test that env var is respected when set."""
    monkeypatch.setenv(SCHEDULE_INTERVAL_ENV_VAR, str(interval))

    CliRunner().invoke(cli)
    mock_task_scheduler.assert_called_once_with(interval)


@patch("deep_next.app.entrypoint_scheduled.task_scheduler")
@pytest.mark.parametrize("interval", (30, 0))
def test_cli_arg_overrides_env(mock_task_scheduler, monkeypatch, interval):
    """Test that the CLI argument overrides the env var."""
    monkeypatch.setenv(SCHEDULE_INTERVAL_ENV_VAR, "99")

    CliRunner().invoke(cli, ["--interval-s", str(interval)])

    mock_task_scheduler.assert_called_once_with(interval)
