from pathlib import Path

import click
from deep_next.core.config import DATA_DIR
from deep_next.core.graph import deep_next_graph
from deep_next.core.io import read_txt, write_txt
from loguru import logger


def main(
    problem_statement: str,
    hints: str,
    root_dir: Path,
    output_file: Path | str = DATA_DIR / "result.diff",
) -> str:
    """Deep NEXT data pipeline."""
    logger.info(f"\n{problem_statement=}\n{hints=}\n{root_dir=}")

    git_diff: str = deep_next_graph(
        problem_statement=problem_statement, hints=hints, root=root_dir
    )

    logger.debug(git_diff)
    write_txt(txt=git_diff, path=output_file)
    logger.info(f"Result saved to: '{output_file}'")

    logger.success("DeepNext pipeline completed successfully.")

    return git_diff


def _validate_exclusive_options(
    ctx, param1, param2, param1_name: str, param2_name: str
):
    """
    Validates that exactly one of two mutually exclusive options is provided.

    :param ctx: Click context object.
    :param param1: First parameter value.
    :param param2: Second parameter value.
    :param param1_name: Name of the first parameter (used in error messages).
    :param param2_name: Name of the second parameter (used in error messages).
    :return: The resolved value, using `param2` if it is provided.
    """
    if param1 and param2:
        raise click.UsageError(
            f"You cannot use both {param1_name} and {param2_name} at the same time."
        )
    if not param1 and not param2:
        raise click.UsageError(
            f"You must provide exactly one of {param1_name} or {param2_name}."
        )
    return param1 or param2


@click.command()
@click.option(
    "--problem-statement",
    type=str,
    help="The issue title and body. Cannot be used with --problem-statement-file.",
)
@click.option(
    "--problem-statement-file",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path
    ),
    help=(
        "Path to a file containing the issue title and body. "
        "Cannot be used with --problem-statement."
    ),
)
@click.option(
    "--hints",
    type=str,
    help="Comments made on the issue. Cannot be used with --hints-file.",
)
@click.option(
    "--hints-file",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path
    ),
    help=(
        "Path to a file containing comments made on the issue. "
        "Cannot be used with --hints."
    ),
)
@click.option(
    "--root-dir",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path
    ),
    required=True,
    help="Absolute path to the repo root directory.",
)
@click.option(
    "--output-file",
    type=click.Path(
        exists=False, file_okay=True, dir_okay=False, writable=True, path_type=Path
    ),
    default=DATA_DIR / "result.diff",
    help=(
        "Path to a file where the output will be saved. "
        "If not provided, the output will be printed to the console."
    ),
)
@click.pass_context
def cli(
    ctx,
    problem_statement: str,
    problem_statement_file: Path,
    hints: str,
    hints_file: Path,
    root_dir: Path,
    output_file: Path | str | None,
) -> None:
    """Command-line interface for Deep NEXT pipeline."""
    problem_statement = _validate_exclusive_options(
        ctx,
        problem_statement,
        problem_statement_file,
        "--problem-statement",
        "--problem-statement-file",
    )
    hints = _validate_exclusive_options(
        ctx, hints, hints_file, "--hints", "--hints-file"
    )

    if isinstance(problem_statement, Path):
        problem_statement = read_txt(problem_statement)
    if isinstance(hints, Path):
        hints = read_txt(hints)

    main(
        problem_statement=problem_statement,
        hints=hints,
        root_dir=root_dir,
        output_file=output_file,
    )


if __name__ == "__main__":
    from deep_next.common.common import load_monorepo_dotenv, setup_logging

    load_monorepo_dotenv()
    setup_logging()

    cli()
