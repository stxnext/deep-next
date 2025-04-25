import time

import click
from deep_next.app.config import SCHEDULE_INTERVAL_ENV_VAR
from deep_next.app.entrypoint import main
from deep_next.connectors.slack import slack_notifications
from loguru import logger


def log(msg: str) -> None:
    logger.debug(f"\n{13 * '~'}\n[SCHEDULER] {msg}\n{13 * '~'}")


@slack_notifications
def task_scheduler(interval_s: int) -> None:
    """Continuously runs the `main` function every `interval` seconds."""
    while True:
        log("Starting task scanning...")

        main()

        log(f"Task scanning completed. Sleeping for {interval_s} seconds...")
        time.sleep(interval_s)


@click.command()
@click.option(
    "--interval-s",
    "-s",
    default=30,
    show_default=True,
    envvar=SCHEDULE_INTERVAL_ENV_VAR,
    type=int,
    help=(
        f"Interval in seconds between task scans. "
        f"Can be set via the {SCHEDULE_INTERVAL_ENV_VAR} env var."
    ),
)
def cli(interval_s: int):
    task_scheduler(interval_s)


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv

    load_monorepo_dotenv()

    cli()
