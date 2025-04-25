import os
import subprocess
from pathlib import Path

from loguru import logger

NO_OUTPUT = "<no output>"


class RunCmdError(Exception):
    """Run command error."""

    def __init__(self, message, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


def run_command(
    command: list[str],
    cwd: Path | str | None = None,
    env: dict | None = None,
) -> str:
    """Run a shell command and return its output."""
    cwd = os.getcwd() if cwd is None else str(cwd)
    cmd = f"> cd {cwd}\n> {' '.join(command)}"

    # TODO: Add to cmd
    if env is not None:
        _env = os.environ.copy()
        _env.update(env)
    else:
        _env = None

    try:
        resp = subprocess.run(
            command,
            check=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=_env,
        )
        stdout = resp.stdout.strip() if resp.stdout.strip() else NO_OUTPUT
        stderr = resp.stderr.strip() if resp.stderr.strip() else NO_OUTPUT

        # TODO: Sanitize command flag? Or verbose false?
        #  which is better for hidinbg url with access token secret?
        logger.debug(
            "Command executed successfully:\n"
            f"{cmd}\n\n"
            f"STDOUT:\n{stdout}\n\n"
            f"STDERR:\n{stderr}"
        )

        return stdout
    except subprocess.CalledProcessError as e:
        stdout = e.stdout.strip() if e.stdout else NO_OUTPUT
        stderr = e.stderr.strip() if e.stderr else NO_OUTPUT

        msg = (
            f"Failed with exit code {e.returncode}:\n"
            f"{cmd}\n\n"
            f"STDOUT:\n{stdout}\n\n"
            f"STDERR:\n{stderr}"
        )

        raise RunCmdError(msg, stdout=stdout, stderr=stderr) from None
    except Exception as e:
        raise RunCmdError(f"Unexpected error:\n{cmd}\n\n{e}") from None
