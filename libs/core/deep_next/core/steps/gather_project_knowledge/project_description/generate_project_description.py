import textwrap
from pathlib import Path

from deep_next.core.project_info import ProjectInfo
from deep_next.core.steps.gather_project_knowledge.project_description.common import (
    _create_llm,
)
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


class Prompt:
    task_description = textwrap.dedent(
        """
        As a senior python developer that prepares documentation for newcomers to support onboarding process...

        Please analyze the key technical capabilities and characteristics of the "{project_name}" project based on given context.
        In return I want to receive a project description summarizing it's overall shape, purpose, structure, libraries,
        entry points, patterns and other important features of the project.
        """  # noqa: E501
    )
    generate_project_description_prompt = textwrap.dedent(
        """
        ### Repository tree
        {repository_tree}

        ### Files related to the issue (readme, Makefile, requirements.txt, etc.)
        {related_files}

        ### Questions worth to consider
        {questions}

        Consider following features:
        - Purpose / Primary Goals: Who the end users are. A brief summary of what the application does and how it fits into the larger ecosystem (e.g., what problems it solves for users).
        - Project Structure: High-level overview of the folder structure, including: main modules and their purpose.
        - Entry Points: Information about the main entry points for the application
        - Important Classes / Modules: Description of critical classes or modules, such as base classes, core utilities, or helper functions.
        - Tech Stack Overview: Information about the main technologies used, such as: Python version, Frameworks and libraries (e.g., Django, Flask, FastAPI, Pandas, NumPy), Databases (e.g., PostgreSQL, MySQL, SQLite), Caching mechanisms (e.g., Redis).
        - Architecture Overview: High-level overview of the project's architecture, such as: Monolithic vs. microservices, How different modules interact, Important design patterns used in the codebase.

        ADDITIONAL INSTRUCTIONS:
        ------------------------
        1. Your answer should be submitted directly based on given data.
        ------------------------

        EXAMPLE OUTPUT:
        --------------------
        {example_project_description}
        --------------------
        """  # noqa: E501
    )


overview_desc = (
    "Analyze GitHub Repository. Prepare high level project description based on the "
    "given context. Prepare hight level overview of the project structure, entry "
    "points, important classes, tech stack and architecture."
)


reasoning_desc = (
    "Think about the reasoning for key project observations. Provide the reasoning for"
    " the observation. It could be related to the project structure, entry points, "
    "important classes, tech stack, architecture or any other key observation that "
    "could be important for the project."
)


key_observation_desc = (
    "Provide the key observation for the project description to the git repository to"
    " understand the problem better. The key observation could be related to the "
    "project structure, entry points, important classes, tech stack, architecture or"
    " any other key observation that could be important for the project."
)


project_description_context_desc = (
    "Provide the project description context to the git repository to understand the"
    " repository better with a brief reasoning for the observation."
)

project_description_desc = (
    "Based on the given context, provide the project description to the git repository"
    " to understand the problem. The project description should include the high level"
    " overview of the project structure, entry points, important classes, tech stack "
    "and architecture. The project description should help you in the next step to "
    "identify the part of the issue that needs to be clarified or anchored to the "
    "code context."
)


class ProjectDescriptionContext(BaseModel):
    reasoning: str = Field(default="", description=reasoning_desc)
    key_observation: str = Field(default="", description=key_observation_desc)


class ExistingProjectDescriptionContext(BaseModel):
    overview_description: str = Field(default="", description=overview_desc)
    project_description_context: list[ProjectDescriptionContext] = Field(
        default_factory=list, description=project_description_context_desc
    )
    project_description: str = Field(default="", description=project_description_desc)


def _create_llm_agent():
    design_solution_prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                Prompt.task_description,
            ),
            (
                "user",
                Prompt.generate_project_description_prompt,
            ),
        ]
    )

    parser = PydanticOutputParser(pydantic_object=ExistingProjectDescriptionContext)

    return design_solution_prompt_template | _create_llm() | parser


def generate_project_description(
    questions: str,
    related_files: list[Path],
    repository_tree: str,
    project_info: ProjectInfo,
) -> ExistingProjectDescriptionContext:
    response = _create_llm_agent().invoke(
        {
            "project_name": project_info.name,
            "repository_tree": repository_tree,
            "related_files": related_files,
            "questions": questions,
            "example_project_description": example_output_loc_cfl.model_dump_json(),
        }
    )

    return response


example_output_loc_cfl = ExistingProjectDescriptionContext(
    overview_description=(
        "Browser-use combines Playwright browser automation with LLM orchestration "
        "using Python 3.11+ async features. The architecture employs multiple design "
        "patterns for extensibility, with clear separation between browser control, "
        "AI processing, and state management layers through dedicated modules."
    ),
    project_description_context=[
        ProjectDescriptionContext(
            reasoning=(
                "The async/await implementation was chosen to handle concurrent "
                "browser tabs and network requests efficiently. Playwright's async "
                "API requires proper event loop management, implemented through "
                "asyncio.run(main()) in entry.py. This pattern enables non-blocking "
                "execution of long-running tasks like page navigation and DOM parsing."
            ),
            key_observation=(
                "entry.py uses async context managers (lines 22-35) for browser "
                "instance lifecycle management, ensuring proper resource cleanup."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "Dependency injection through factory pattern allows runtime "
                "selection of LLM providers without code changes. The BaseLLMProvider "
                "abstract class (llm_providers.py:15-28) enforces interface "
                "compliance. Environment variables drive concrete implementation "
                "instantiation based on available API keys."
            ),
            key_observation=(
                "LLM_PROVIDER_MAP dictionary (llm_providers.py:44-51) dynamically "
                "maps provider names to initialization functions with error handling."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "Repository pattern implementation for DOM state management "
                "decouples storage from usage. DOMSnapshot class (dom_management.py) "
                "implements versioned snapshots using difflib. This allows rollback "
                "capabilities and differential analysis between page states."
            ),
            key_observation=(
                "Snapshots are stored in SQLite database (dom_states.db) with "
                "compression using zlib (storage.py:112-125)."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "Singleton browser instance management prevents resource leaks "
                "across coroutines. BrowserController.__new__ method (browser.py:33) "
                "ensures single instance via thread-local storage. Connection pooling "
                "is implemented through Playwright's built-in context reuse."
            ),
            key_observation=(
                "ACTIVE_BROWSER global variable (browser.py:37) wrapped in "
                "WeakReference for garbage collection safety."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "Pydantic settings management provides type-safe configuration. "
                "Settings class (config.py:12-18) validates 12+ environment variables "
                "with regex patterns. Nested configurations enable complex setups "
                "like LLM fallback chains and proxy configurations."
            ),
            key_observation=(
                "Dotenv loading uses python-dotenv 1.0+ with override prevention "
                "(config.py:22-25) for production safety."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "MVC pattern in Gradio interface separates UI concerns from business "
                "logic. View components (gradio_demo.py:55-72) use gr.Blocks API for "
                "dynamic layout construction. Controller methods handle event binding "
                "while models interact directly with Agent class."
            ),
            key_observation=(
                "State is managed through SessionState class (gradio_demo.py:88-95) "
                "with async locks for concurrent access prevention."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "Strategy pattern enables polymorphic browser actions. "
                "ActionHandlerBase (actions.py:30-45) defines execute() contract. "
                "Concrete strategies implement provider-specific optimizations like "
                "Chromium selector prioritization vs Firefox compatibility."
            ),
            key_observation=(
                "ACTION_REGISTRY (actions.py:122-130) maps CSS selector patterns to "
                "handler classes using priority-based resolution."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "Observer pattern implementation enables extensible logging. "
                "ActionLogger (logging.py:77-89) maintains list of registered "
                "output handlers. Custom handlers can be added through "
                "register_handler() method without modifying core logging logic."
            ),
            key_observation=(
                "Default handlers include JSONFileLogger and CloudWatchLogger "
                "(logging.py:92-105) with async write queues."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "Facade pattern simplifies complex workflows through unified "
                "interfaces. JobApplicationWorkflow (workflows/job_app.py) "
                "orchestrates CV parsing, form filling, and email subsystems. "
                "Internal complexity is hidden behind submit_application() method."
            ),
            key_observation=(
                "Workflow exceptions are captured using composite pattern "
                "(ErrorAggregator class: job_app.py:133-145) for batch processing."
            ),
        ),
        ProjectDescriptionContext(
            reasoning=(
                "Template method pattern ensures consistent browser task execution. "
                "BaseTask (tasks.py:15-30) defines setup/execute/teardown workflow. "
                "Concrete implementations override validation rules and retry logic "
                "while maintaining execution sequence."
            ),
            key_observation=(
                "Retry policies are configured through TASK_RETRY_CONFIG dictionary "
                "(tasks.py:88-92) with exponential backoff settings."
            ),
        ),
    ],
    project_description=(
        "The architecture combines multiple design patterns for maintainability:\n"
        "1. **Core Patterns**:\n"
        "   - Factory Method: LLM provider initialization\n"
        "   - Strategy: Browser action implementations\n"
        "   - Observer: Distributed logging system\n\n"
        "2. **Key Global State**:\n"
        "   - BROWSER_POOL: Playwright context manager (browser.py:112)\n"
        "   - LLM_CACHE: LRU cache for model responses (llm_providers.py:88)\n"
        "   - TASK_QUEUE: PriorityQueue for action scheduling (tasks.py:45)\n\n"
        "3. **Framework Integration**:\n"
        "   - Playwright 1.42+ with custom selector engine extensions\n"
        "   - Pydantic 2.5+ for settings validation\n"
        "   - LangChain 0.1.4+ for prompt templating\n\n"
        "Code structure follows PEP-8 with type hints, organized into:\n"
        "- /core: Abstract base classes and interfaces\n"
        "- /integrations: Provider-specific implementations\n"
        "- /workflows: Prebuilt automation sequences\n"
        "- /utils: Shared helpers and decorators"
    ),
)
