from pydantic import BaseModel, Field


class ProjectDescriptionContext(BaseModel):
    reasoning: str = Field(default="", description="Reasoning for the observation")
    key_observation: str = Field(default="", description="Key observation")


class ExistingProjectDescriptionContext(BaseModel):
    overview_description: str = Field(default="", description="Overview of the project")
    project_description_context: list[ProjectDescriptionContext] = Field(
        default_factory=list, description="List of project description contexts"
    )
    project_description: str = Field(default="", description="Project description")

    def to_str(self) -> str:
        project_description = ""
        project_description += (
            f"\nOverview description:\n{self.overview_description}\n\n"
        )

        project_description += "\nProject description context:\n"
        for context in self.project_description_context:
            project_description += f"- Key observation: {context.key_observation}\n"
            project_description += (
                f"|___ Rationale (Reasoning): {context.reasoning}\n\n"
            )

        project_description += f"\nProject description:\n{self.project_description}\n"

        return project_description


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


class QuestionContext(BaseModel):
    reasoning: str = Field(default="", description="Reasoning for the question")
    question: str = Field(default="", description="Question to the git repository")


class ExistingQuestionContext(BaseModel):
    overview_description: str = Field(
        default="", description="Overview description of the project"
    )
    question_context: list[QuestionContext] = Field(
        default_factory=list, description="List of questions to the git repository"
    )

    def dump(self) -> str:
        return "\n".join([question.question for question in self.question_context])


example_output_loc_cfl = ExistingQuestionContext(
    overview_description=(
        "The repository is a Python project that has readme.md and setup.py in the "
        "root directory. The project uses main.py as the entry point, so definitely we"
        " need to read this file. The project contain tests, so we need to read some "
        "test files to check the test framework. We should read some .py files to "
        "check for the important classes and functions. "
    ),
    question_context=[
        QuestionContext(
            reasoning=(
                "The project uses main.py as the entry point, so definitely we "
                "need to read this file."
            ),
            question=(
                "What is the main.py file doing? What is the entry point of the "
                "project?"
            ),
        ),
        QuestionContext(
            reasoning=(
                "The project contain tests, so we need to read some test files "
                "to check the test framework."
            ),
            question="What is the test framework used in the project?",
        ),
        QuestionContext(
            reasoning=(
                "We should read some .py files to check for the important "
                "classes and functions."
            ),
            question="What are the important classes and functions in the project?",
        ),
        QuestionContext(
            reasoning=(
                "We should check for readme.md to understand the project " "better."
            ),
            question="What is the content of the readme.md file?",
        ),
        QuestionContext(
            reasoning=(
                "There is setup.py in the repo tree. "
                "We should check for setup.py to understand the project better."
            ),
            question="What is the content of the setup.py file?",
        ),
        QuestionContext(
            reasoning=(
                "I see in the project tree that the project uses "
                "pyproject.toml. We should check for pyproject.toml to "
                "understand the libraries used in the project."
            ),
            question="What is the content of the pyproject.toml file?",
        ),
    ],
)
