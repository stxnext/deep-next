# flake8: noqa

import textwrap
from pathlib import Path

from deep_next.core.steps.action_plan.data_model import (
    ActionPlan,
    ExistingCodeContext,
    Step,
)

# TODO: Fix project knowledge schema. Make it pydantic model.
project_knowledge = """
<PROJECT_DESCRIPTION>
# Project Name: deep_next

## Purpose / Primary Goals
DeepNext is a monorepo project aimed at providing a comprehensive solution for managing and evaluating software projects. \
It is designed for developers and project managers who need to streamline project workflows, evaluate project performance, \
and integrate various tools and services. The application fits into the larger ecosystem by solving problems related to \
project management, evaluation, and integration with external services like AWS, GitLab, and Slack.

## Project Structure
The project is organized into several main directories:
- `apps`: Contains application-specific modules such as `app`, `evaluation`, and `swe_bench`.
- `libs`: Includes shared libraries like `common`, `connectors`, and `core`.
- `ops`: Appears to be related to operational scripts or configurations.
- `omtm`: Contains a module named `omtm.py`, purpose unclear from the data.

## Entry Points
The main entry points for the application are likely located in the `entrypoint.py` files found in various modules such \
as `apps/app/deep_next/app/entrypoint.py`, `apps/evaluation/deep_next/evaluation/entrypoint.py`, and \
`apps/swe_bench/deep_next/swe_bench/entrypoint.py`.

## Important Classes / Modules
- `deep_next_core`: A core library that likely contains base classes and core utilities.
- `deep_next_connectors`: Provides integration with external services like AWS, GitLab, and Slack.
- `deep_next_common`: Contains common utilities and configurations used across the project.

## Tech Stack Overview
- **Python Version**: >=3.11.0,<3.12.0
- **Frameworks and Libraries**: Click, Loguru, Python-dotenv, Langchain, Pydantic, Pandas, Docker, and more.
- **Databases**: <NOT ENOUGH DATA>
- **Caching Mechanisms**: <NOT ENOUGH DATA>

## Architecture Overview
- **Architecture Type**: Monolithic, as indicated by the monorepo structure.
- **Module Interaction**: Different modules interact through shared libraries and connectors.
- **Design Patterns**: <NOT ENOUGH DATA>
</PROJECT_DESCRIPTION>

<PROJECT_MAP>
📁 apps
├── 📁 app
│   └── 📁 deep_next
│       └── 📁 app
│           ├── 📄 add_new_project.py
│           ├── 📄 common.py
│           ├── 📄 config.py
│           ├── 📄 entrypoint.py
│           ├── 📄 entrypoint_scheduled.py
│           └── 📄 git.py
├── 📁 evaluation
│   └── 📁 deep_next
│       └── 📁 evaluation
│           ├── 📄 config.py
│           ├── 📁 custom_bench
│           │   ├── 📄 __init__.py
│           │   ├── 📁 _data
│           │   ├── 📄 cli.py
│           │   ├── 📄 config.py
│           │   ├── 📁 dataset
│           │   │   ├── 📄 __init__.py
│           │   │   ├── 📄 cli.py
│           │   │   ├── 📄 create_record.py
│           │   │   └── 📄 model.py
│           │   ├── 📁 eval
│           │   │   ├── 📄 __init__.py
│           │   │   ├── 📄 cli.py
│           │   │   ├── 📄 experiment.py
│           │   │   ├── 📄 runners.py
│           │   │   └── 📄 upload_dataset.py
│           │   └── 📄 utils.py
│           ├── 📁 data
│           │   ├── 📄 __init__.py
│           │   ├── 📁 designs
│           │   ├── 📄 example_tasks.py
│           │   ├── 📄 example_tasks_165.py
│           │   ├── 📄 example_tasks_mini.py
│           │   ├── 📁 gt_apply_edits
│           │   │   ├── 📄
│           │   │   │   fix_typehints-added_indentation_in_before_and_after_
│           │   │   │   patch.py
│           │   │   ├── 📄
│           │   │   │   fix_typehints-added_indentation_in_before_patch.py
│           │   │   ├── 📄 fix_typehints-docstring_added.py
│           │   │   ├── 📄 fix_typehints-docstring_removed.py
│           │   │   ├── 📄 fix_typehints-exact_match.py
│           │   │   ├── 📄 fix_typehints-line_1_mismatch.py
│           │   │   ├── 📄 fix_typehints-line_2_mismatch.py
│           │   │   ├── 📄 fix_typehints-line_3_mismatch.py
│           │   │   ├── 📄
│           │   │   │   fix_typehints-missing_indentation_in_before_and_afte
│           │   │   │   r_patch.py
│           │   │   ├── 📄
│           │   │   │   fix_typehints-missing_indentation_in_before_patch.py
│           │   │   ├── 📄 fix_typehints-newline_added_in_the_middle.py
│           │   │   ├── 📄 fix_typehints-newline_removed_in_the_middle.py
│           │   │   ├── 📄 fix_typehints-typehint_added.py
│           │   │   └── 📄 fix_typehints-typehint_removed.py
│           │   ├── 📁 gt_select_related_files_results
│           │   ├── 📁 gt_solution_design_templates
│           │   │   └── 📁 <found 186 items>
│           │   └── 📁 project_knowledge
│           ├── 📄 entrypoint.py
│           ├── 📄 generate_gt_select_related_files_results.py
│           ├── 📄 generate_gt_solution_desing_templates.py
│           ├── 📄 generate_project_knowledge.py
│           ├── 📄 results_evaluation.py
│           ├── 📄 run_swe_prediction.py
│           ├── 📁 steps
│           │   ├── 📄 __init__.py
│           │   ├── 📁 apply_edits
│           │   │   ├── 📄 __init__.py
│           │   │   ├── 📄 evaluators.py
│           │   │   └── 📄 job.py
│           │   ├── 📁 e2e
│           │   │   ├── 📄 __init__.py
│           │   │   ├── 📄 evaluators.py
│           │   │   └── 📄 job.py
│           │   ├── 📁 engineer
│           │   │   ├── 📄 __init__.py
│           │   │   ├── 📄 evaluators.py
│           │   │   └── 📄 job.py
│           │   ├── 📁 solution_designer
│           │   │   ├── 📄 __init__.py
│           │   │   ├── 📄 evaluators.py
│           │   │   └── 📄 job.py
│           │   └── 📁 srf
│           │       ├── 📄 __init__.py
│           │       ├── 📄 evaluators.py
│           │       └── 📄 job.py
│           ├── 📄 upload_datasets.py
│           ├── 📄 upload_swe_to_langsmith.py
│           └── 📁 utils
│               ├── 📄 __init__.py
│               ├── 📄 git_repo.py
│               ├── 📄 swe_bench_dataset.py
│               └── 📄 utils.py
└── 📁 swe_bench
    ├── 📁 data
    │   └── 📁 tasks
    └── 📁 deep_next
        └── 📁 swe_bench
            ├── 📄 build_images.py
            ├── 📄 common.py
            ├── 📄 config.py
            ├── 📄 dataset.py
            ├── 📄 docker_container.py
            ├── 📄 entrypoint.py
            ├── 📄 runtime_environment.py
            └── 📄 summarize_results.py
📁 libs
├── 📁 common
│   └── 📁 deep_next
│       └── 📁 common
│           ├── 📄 cmd.py
│           ├── 📄 common.py
│           ├── 📄 config.py
│           └── 📁 utils
│               └── 📄 fs.py
├── 📁 connectors
│   └── 📁 deep_next
│       └── 📁 connectors
│           ├── 📄 aws.py
│           ├── 📄 gitlab_connector.py
│           └── 📄 slack.py
└── 📁 core
    └── 📁 deep_next
        └── 📁 core
            ├── 📄 __init__.py
            ├── 📄 base_graph.py
            ├── 📄 base_node.py
            ├── 📄 common.py
            ├── 📄 config.py
            ├── 📄 const.py
            ├── 📄 entrypoint.py
            ├── 📄 graph.py
            ├── 📄 io.py
            ├── 📄 parser.py
            ├── 📄 project_info.py
            └── 📁 steps
                ├── 📄 __init__.py
                ├── 📁 detailed_design
                │   ├── 📄 __init__.py
                │   ├── 📄 detailed_design.py
                │   ├── 📄 graph.py
                │   └── 📁 srf
                │       ├── 📄 __init__.py
                │       ├── 📄 common.py
                │       ├── 📁 file_selection
                │       │   ├── 📄 __init__.py
                │       │   ├── 📄 analysis_model.py
                │       │   ├── 📄 graph.py
                │       │   ├── 📁 tools
                │       │   │   ├── 📄 __init__.py
                │       │   │   ├── 📁 acr
                │       │   │   │   ├── 📄 __init__.py
                │       │   │   │   ├── 📄 search_tools.py
                │       │   │   │   └── 📄 utils.py
                │       │   │   ├── 📄 list_file_structure.py
                │       │   │   ├── 📄 module_public_interface_lookup.py
                │       │   │   ├── 📄 read_file.py
                │       │   │   ├── 📄 read_imports.py
                │       │   │   ├── 📄 search.py
                │       │   │   └── 📄 tools.py
                │       │   └── 📄 utils.py
                │       ├── 📄 graph.py
                │       └── 📄 list_dir.py
                ├── 📁 gather_project_knowledge
                │   ├── 📄 __init__.py
                │   ├── 📄 graph.py
                │   ├── 📄 project_description.py
                │   └── 📄 project_map.py
                └── 📁 implement
                    ├── 📄 __init__.py
                    ├── 📁 apply_edits
                    │   ├── 📄 __init__.py
                    │   ├── 📄 acr.py
                    │   ├── 📄 apply_patch.py
                    │   ├── 📄 git_diff.py
                    │   └── 📄 graph.py
                    ├── 📄 common.py
                    ├── 📁 develop_edits
                    │   ├── 📄 __init__.py
                    │   ├── 📄 acr.py
                    │   ├── 📄 common.py
                    │   ├── 📄 graph.py
                    │   └── 📄 utils.py
                    └── 📄 graph.py
📁 ops
└── 📁 omtm
    └── 📄 omtm.py

</PROJECT_MAP>
"""

issue_statement = textwrap.dedent(
    """
    <title>
    Add mechanism that will log to a file.
    </title>

    <description>
    Create logging mechanism that will make the loguru.logger log to a file. \
    Mechanism should be used in DeepNext core pipeline, \
    so that all logs for a single task are saved to a file. \
    Logs should be saved in dedicated directory. \
    This is additional feature supporting log inspection post execution.
    </description>
    """
)

existing_code_context = ExistingCodeContext(
    **{
        "code_context": [
            {
                "path": Path(
                    "/home/user/projects/deep-next/libs/core/deep_next/core/graph.py"
                ),
                "code_snippet": 'from pathlib import Path\n\nfrom deep_next.core.base_graph import BaseGraph, State\nfrom deep_next.core.common import build_issue_statement\nfrom deep_next.core.steps.detailed_design.detailed_design import Modifications\nfrom deep_next.core.steps.detailed_design.graph import create_detailed_design_graph\nfrom deep_next.core.steps.gather_project_knowledge.graph import (\n    gather_project_knowledge_graph,\n)\nfrom deep_next.core.steps.implement.graph import implement_graph\nfrom langgraph.graph import END, START\n\n\nclass DeepNextGraphState(State):\n\n    # Input\n    root_path: Path\n    """Path to the root project directory."""\n\n    problem_statement: str\n    """The issue title and body."""\n\n    hints: str\n    """Comments made on the issue."""\n\n    # Internal\n    _project_knowledge: str\n    """Project knowledge gathered from analyzing the repository structure and the source\n     code."""\n\n    _detailed_design: Modifications\n    """A list of files and the changes that need to be made to each of them."""\n\n    # Output arguments\n    git_diff: str\n    """Final result of the graf flow: git diff of the changes made to the source code.\n    """\n\n\nclass _Node:\n    @staticmethod\n    def gather_project_knowledge(state: DeepNextGraphState) -> dict:\n        initial_state = gather_project_knowledge_graph.create_init_state(\n            root_path=state["root_path"],\n        )\n        final_state = gather_project_knowledge_graph.compiled.invoke(initial_state)\n\n        return {"_project_knowledge": final_state["project_knowledge"]}\n\n    @staticmethod\n    def create_detailed_design(state: DeepNextGraphState) -> dict:\n        issue_statement = build_issue_statement(\n            problem_statement=state["problem_statement"],\n            hints=state["hints"],\n        )\n        initial_state = create_detailed_design_graph.create_init_state(\n            root_path=state["root_path"],\n            issue_statement=issue_statement,\n            project_knowledge=state["_project_knowledge"],\n        )\n        final_state = create_detailed_design_graph.compiled.invoke(initial_state)\n\n        return {"_detailed_design": final_state["detailed_design"]}\n\n    @staticmethod\n    def implement(state: DeepNextGraphState) -> dict:\n        initial_state = implement_graph.create_init_state(\n            root_path=state["root_path"],\n            detailed_design=state["_detailed_design"],\n        )\n        final_state = implement_graph.compiled.invoke(initial_state)\n\n        return {"git_diff": final_state["git_diff"]}\n\n\nclass DeepNextGraph(BaseGraph):\n    def __init__(self):\n        super().__init__(DeepNextGraphState)\n\n    def _build(self):\n        self.add_quick_node(_Node.gather_project_knowledge)\n        self.add_node(_Node.create_detailed_design)\n        self.add_node(_Node.implement)\n\n        self.add_quick_edge(START, _Node.gather_project_knowledge)\n        self.add_quick_edge(\n            _Node.gather_project_knowledge, _Node.create_detailed_design\n        )\n        self.add_quick_edge(_Node.create_detailed_design, _Node.implement)\n        self.add_quick_edge(_Node.implement, END)\n\n    def create_init_state(\n        self, root: Path, problem_statement: str, hints: str\n    ) -> DeepNextGraphState:\n        return DeepNextGraphState(\n            root_path=root,\n            problem_statement=problem_statement,\n            hints=hints,\n            _project_knowledge="",\n            _detailed_design=Modifications(),\n            git_diff="",\n        )\n\n    def __call__(self, *_, problem_statement: str, hints: str, root: Path) -> str:\n        initial_state = self.create_init_state(\n            root=root, problem_statement=problem_statement, hints=hints\n        )\n        final_state = self.compiled.invoke(initial_state)\n\n        return final_state["git_diff"]\n\n\ndeep_next_graph = DeepNextGraph()\n\n\nif __name__ == "__main__":\n    print(f"Saved to: {deep_next_graph.visualize(subgraph_depth=3)}")\n',
                "explanation": "<missing>",
            },
            {
                "path": Path(
                    "/home/user/projects/deep-next/libs/core/deep_next/core/entrypoint.py"
                ),
                "code_snippet": 'from pathlib import Path\n\nimport click\nfrom deep_next.core.common import gitignore_name\nfrom deep_next.core.config import ROOT_DIR\nfrom deep_next.core.graph import deep_next_graph\nfrom deep_next.core.io import read_txt, write_txt\nfrom loguru import logger\n\n\ndef main(\n    problem_statement: str,\n    hints: str,\n    root_dir: Path,\n    output_file: Path | str = ROOT_DIR / gitignore_name("result.diff"),\n) -> str:\n    """Deep NEXT data pipeline."""\n    logger.info(f"\\n{problem_statement=}\\n{hints=}\\n{root_dir=}")\n\n    git_diff: str = deep_next_graph(\n        problem_statement=problem_statement, hints=hints, root=root_dir\n    )\n\n    logger.debug(git_diff)\n    write_txt(txt=git_diff, path=output_file)\n    logger.info(f"Result saved to: \'{output_file}\'")\n\n    logger.success("DeepNext pipeline completed successfully.")\n\n    return git_diff\n\n\ndef _validate_exclusive_options(\n    ctx, param1, param2, param1_name: str, param2_name: str\n):\n    """\n    Validates that exactly one of two mutually exclusive options is provided.\n\n    :param ctx: Click context object.\n    :param param1: First parameter value.\n    :param param2: Second parameter value.\n    :param param1_name: Name of the first parameter (used in error messages).\n    :param param2_name: Name of the second parameter (used in error messages).\n    :return: The resolved value, using `param2` if it is provided.\n    """\n    if param1 and param2:\n        raise click.UsageError(\n            f"You cannot use both {param1_name} and {param2_name} at the same time."\n        )\n    if not param1 and not param2:\n        raise click.UsageError(\n            f"You must provide exactly one of {param1_name} or {param2_name}."\n        )\n    return param1 or param2\n\n\n@click.command()\n@click.option(\n    "--problem-statement",\n    type=str,\n    help="The issue title and body. Cannot be used with --problem-statement-file.",\n)\n@click.option(\n    "--problem-statement-file",\n    type=click.Path(\n        exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path\n    ),\n    help=(\n        "Path to a file containing the issue title and body. "\n        "Cannot be used with --problem-statement."\n    ),\n)\n@click.option(\n    "--hints",\n    type=str,\n    help="Comments made on the issue. Cannot be used with --hints-file.",\n)\n@click.option(\n    "--hints-file",\n    type=click.Path(\n        exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path\n    ),\n    help=(\n        "Path to a file containing comments made on the issue. "\n        "Cannot be used with --hints."\n    ),\n)\n@click.option(\n    "--root_dir",\n    type=click.Path(\n        exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path\n    ),\n    required=True,\n    help="Absolute path to the repo root directory.",\n)\n@click.option(\n    "--output_file",\n    type=click.Path(\n        exists=False, file_okay=True, dir_okay=False, writable=True, path_type=Path\n    ),\n    default=ROOT_DIR / gitignore_name("result.diff"),\n    help=(\n        "Path to a file where the output will be saved. "\n        "If not provided, the output will be printed to the console."\n    ),\n)\n@click.pass_context\ndef cli(\n    ctx,\n    problem_statement: str,\n    problem_statement_file: Path,\n    hints: str,\n    hints_file: Path,\n    root_dir: Path,\n    output_file: Path | str | None,\n) -> None:\n    """Command-line interface for Deep NEXT pipeline."""\n    problem_statement = _validate_exclusive_options(\n        ctx,\n        problem_statement,\n        problem_statement_file,\n        "--problem-statement",\n        "--problem-statement-file",\n    )\n    hints = _validate_exclusive_options(\n        ctx, hints, hints_file, "--hints", "--hints-file"\n    )\n\n    if isinstance(problem_statement, Path):\n        problem_statement = read_txt(problem_statement)\n    if isinstance(hints, Path):\n        hints = read_txt(hints)\n\n    main(\n        problem_statement=problem_statement,\n        hints=hints,\n        root_dir=root_dir,\n        output_file=output_file,\n    )\n\n\nif __name__ == "__main__":\n    from deep_next.common.config import MONOREPO_ROOT_PATH\n    from dotenv import load_dotenv\n\n    assert load_dotenv(MONOREPO_ROOT_PATH / ".env")\n\n    cli()\n',
                "explanation": "<missing>",
            },
            {
                "path": Path(
                    "/home/user/projects/deep-next/libs/core/deep_next/core/common.py"
                ),
                "code_snippet": 'import textwrap\nfrom pathlib import Path\n\nfrom deep_next.core.io import read_txt\n\n\n# TODO: Remove. It\'s moved to common lib.\ndef gitignore_name(name: str) -> str:\n    """Converts the name so that it\'ll be ignored by git."""\n    return f"___{name}"\n\n\ndef build_issue_statement(problem_statement: str, hints: str) -> str:\n    issue_statement_template = textwrap.dedent(\n        """\n        PROBLEM STATEMENT:\n        -------------\n        {problem_statement}\n        -------------\n\n        HINTS:\n        -------------\n        {hints}\n        -------------\n        """\n    )\n    return issue_statement_template.format(\n        problem_statement=problem_statement,\n        hints=hints,\n    )\n\n\ndef dump_filepaths(file_paths: list[Path | str]) -> str:\n    """Create a dump of the contents of the given file paths."""\n    file_repr_tmpl = textwrap.dedent(\n        """\n        Path: {abs_path}\n        ```python\n        {code}\n        ```\n        """\n    )\n    file_paths = [str(Path(path).resolve()) for path in file_paths]\n\n    dump = [\n        file_repr_tmpl.format(abs_path=file_path, code=read_txt(file_path))\n        for file_path in file_paths\n    ]\n\n    return "\\n".join(dump)\n\n\ndef find_files(dir_path: Path | str, file_extension: str = ".py") -> list[Path]:\n    """Recursively finds all files in given directory and its subdirectories."""\n    dir_path = Path(dir_path)\n\n    if not dir_path.exists():\n        raise ValueError(f"The path \'{dir_path}\' does not exist.")\n\n    if not dir_path.is_dir():\n        raise ValueError(f"The path \'{dir_path}\' is not a directory.")\n\n    return list(dir_path.rglob(f"*{file_extension}"))\n',
                "explanation": "<missing>",
            },
        ]
    }
)

action_plan = ActionPlan(
    reasoning=textwrap.dedent(
        """
        ### Understanding the Task & Approach
        This task requires implementing a structured logging mechanism to ensure all logs \
        for a single task in the DeepNext core pipeline are captured in dedicated log files.

        Since these logs will be used for post-execution inspection, they must be structured,
        reliable, and seamlessly integrated into the existing pipeline.

        ### Project Context & Code Integration
        The core execution starts in `libs/core/deep_next/core/entrypoint.py`, \
        making it the logical place to initialize logging. \
        Given that DeepNext is a monorepo, the `core` module serves as the backbone of pipeline execution.

        The project already utilizes Loguru, which simplifies structured logging and file-based \
        log management. Instead of introducing unnecessary complexity with alternative logging solutions, \
        leveraging Loguru aligns with existing practices.

        ### Where to Implement the Logging Mechanism?
        There are two main options based on project conventions:

        1. `common.py` (For Simple Utility Functions)
           - If logging setup requires only a few helper functions \
           (e.g., setting log paths, initializing Loguru), `common.py` is an appropriate location.

        2. `log.py` (For a Dedicated Logging Module)
           - If logging requires configurable settings, structured log file management, \
           or potential future enhancements (e.g., log rotation, external integrations), \
           introducing a dedicated `log.py` is a cleaner and more scalable approach.

        Given that the task requires per-task log files with structured management, \
        creating `log.py` is the better choice. This ensures clear separation of concerns while keeping \
        `common.py` focused on generic utilities.

        ### Configuration Considerations
        A pattern in DeepNext suggests that configuration values and constants belong in `config.py`. \
        However, the provided input does not include `config.py`, which raises an important question:
        - Does `config.py` already exist but was omitted from input data?
        - Or is it missing and needs to be created or extended to define logging-related settings?

        Regardless, logging-related constants (e.g., log directory paths, log file naming conventions, and retention policies) \
        should be defined in `config.py`. This ensures consistency, maintainability, and adherence to existing project structure.

        ### Implementation Considerations & Trade-offs
        - **Task-Specific Log Files:** Each pipeline execution should have its **own dedicated log file**, ensuring logs are isolated per task for better debugging and post-execution analysis.
        - **Early Initialization:** Logging must be **set up at the very start** to ensure uniform log tracking across all pipeline stages.
        - **Separation of Concerns:** Keeping logging logic modular (`log.py`) prevents unnecessary clutter in `entrypoint.py` and makes future extensions (such as external log aggregators) easier.
        - **Avoiding False Positives:** The file **`graph.py` is not relevant** to logging and will not be modified.
        - **Handling Missing Data:** If `config.py` is indeed missing, it should be created and properly structured to hold logging-related constants.

        ### Final Decision
        The implementation will first define logging constants in `config.py`, then **introduce `log.py` to handle logging logic, \
        and finally integrate it into `entrypoint.py`. This approach ensures a structured, maintainable, and scalable \
        logging solution while adhering to DeepNext’s project conventions.
        """  # noqa: E501
    ),
    ordered_steps=[
        Step(
            title="Define logging-related constants in config.py",
            description=textwrap.dedent(
                """\
                Following project conventions, configuration values should be stored in `config.py`. \
                If the file exists, extend it with logging-specific constants such as the log directory path, \
                log file naming conventions, and any other relevant settings. \
                If `config.py` is missing, create it and structure it appropriately.
                """  # noqa: E501
            ),
            target_file=Path("libs/core/deep_next/core/config.py"),
        ),
        Step(
            title="Implement logging mechanism in log.py",
            description=textwrap.dedent(
                """\
                Create a dedicated `log.py` module to encapsulate the logging logic.

                This module should:
                - Read configuration values from `config.py`.
                - Initialize Loguru and configure it to log to per-task files.
                - Ensure log files are structured correctly in the designated directory.
                - Provide reusable logging setup functions to keep entry points clean.
                """
            ),
            target_file=Path("libs/core/deep_next/core/log.py"),
        ),
        Step(
            title="Integrate logging into entrypoint.py",
            description=textwrap.dedent(
                """\
                Modify `entrypoint.py` to initialize logging at the start of execution.

                Ensure that:
                - The logging mechanism from `log.py` is properly imported and used.
                - Each task execution logs to a dedicated file.
                - Existing log statements are migrated to use the new structured logging approach with Loguru.
                """
            ),
            target_file=Path("libs/core/deep_next/core/entrypoint.py"),
        ),
    ],
)
