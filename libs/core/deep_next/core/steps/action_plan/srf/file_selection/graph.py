import json
import operator
import textwrap
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from deep_next.common.llm_retry import invoke_retriable_llm_chain
from deep_next.common.llm import LLMConfigType, create_llm
from deep_next.core.base_graph import BaseGraph
from deep_next.core.config import SRFConfig
from deep_next.core.steps.action_plan.srf.file_selection.analysis_model import (
    Analysis,
    RelevantFile,
    analysis_parser,
    example_output_next_steps,
    example_output_select_files,
)
from deep_next.core.steps.action_plan.srf.file_selection.tools.tools import (
    get_llm_tools,
    get_tool_node,
)
from deep_next.core.steps.action_plan.srf.file_selection.utils import (
    tools_to_json,
    validate_files,
)
from deep_next.core.steps.action_plan.srf.list_dir import ls_dir
from langchain.output_parsers import OutputFixingParser
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.constants import END, START
from langgraph.prebuilt import tools_condition
from loguru import logger


class SelectFilesPrompt:
    role_description = textwrap.dedent(
        """
        You are an advanced codebase analysis agent designed to take action based on the current knowledge \
        analysis provided to you. Your task is to decide whether to continue the investigation by using \
        the provided tools or to finalize the investigation by selecting the most relevant files.

        If you decide to use the tools, choose the ones that provide the most precise \
        answer, whose number of results is limited, and whose results are easy to interpret.
        """  # noqa: E501
    )

    output_format_tools = textwrap.dedent(
        """
        Use the provided tools to gather more information. Make sure you acquire all \
        necessary knowledge to make a final decision on the most relevant files.


        """  # noqa: E501
    )

    output_format = textwrap.dedent(
        """
        Your response must be a valid python list with full file paths. Always keep the output format as in the example!

        EXAMPLE OUTPUT:
        --------------------
        <python>
        ["src/main.py", "test/foo/bar.py"]
        </python>
        --------------------
        """  # noqa: E501
    )


class AnalyzeKnowledgePrompt:
    role_description = textwrap.dedent(
        """
        You are an advanced codebase analysis agent designed to assist in identifying files within \
        a software repository that are relevant to solving specific issues. When provided with an issue \
        statement and analysis your responsibility is to:

        1. Extract key concepts, components, or functionality that are likely affected \
        or involved in resolving the issue.
        2. Strategically search the repository for related files, using available \
        tools and information to identify matches based on filenames, directory \
        structures, or content such as function definitions, class names, or key variables.
        As advanced analyst, keep the broader context in mind, note the project conventions, \
        clean code principles, and the overall project architecture.
        3. Prioritize files that are logically connected to the problem, focusing on \
        modules, functions, or features described in the issue.

        ---
        {format_instructions}
        ---

        Requirements:
        - If your analysis proves, that no further investigation is needed, provide results \
        only for fields "analysis" and "relevant_files_so_far" and leave the rest empty.

        - Pick up new traces if the investigation is stuck or if the current traces are not informative. \
        The success of resolving the issue depends on how broad and deep the investigation is. \
        Return as many next steps as you find promising.

        - At all times, when relating to repository files, use their full path (starting from one of the roots).

        """  # noqa: E501
    )

    additional_context = textwrap.dedent(
        """
        # List of files in project root
        {root_path_ls}
        """
    )

    output_format = textwrap.dedent(
        """
        Your response will be used by codebase analysis agents having access to the \
        following tools:
        --------------------
        {tool_descriptions}
        --------------------

        Do not blindly repeat the previous analysis, unknowns, or next steps, they are only for guidance.

        Always keep the output format as in the example!

        EXAMPLE OUTPUT:
        --------------------
        {example_output_next_steps}
        --------------------
        {example_output_select_files}
        --------------------
        """  # noqa: E501
    )


class State(TypedDict):
    # Input
    root_path: Path
    query: str

    # Internal
    _iteration_count: int
    _root_path_ls: str
    _current_analysis: Analysis
    _previous_analysis: Analysis
    _messages: Annotated[list[AnyMessage], operator.add]

    # Output
    relevant_files: list[RelevantFile] | None
    invalid_files: list[RelevantFile] | None


def _fix_invalid_analysis(e: OutputParserException) -> Analysis | None:
    fixing_parser = OutputFixingParser.from_llm(
        parser=analysis_parser, llm=create_llm(LLMConfigType.SRF_ANALYZE)
    )
    try:
        fixing_parser.parse(e.llm_output)
    except OutputParserException:
        return None


ANALYZE_CHAIN_RETRY = 3


def _invoke_fixable_llm_analysis_chain(
    prompt: ChatPromptTemplate, prompt_arguments: dict
) -> Analysis:
    """
    Invoke the LLM chain and try {ANALYZE_CHAIN_RETRY} times if it fails.

    The retry mechanism includes two steps:
    1. Attempting to fix the current invalid output.
    2. Rerunning the chain with a different seed if the fix attempt fails.
    """
    return invoke_retriable_llm_chain(
        n_retry=ANALYZE_CHAIN_RETRY,
        llm_chain_builder=lambda seed: prompt
        | create_llm(LLMConfigType.SRF_ANALYZE, seed=i)
        | analysis_parser,
        prompt_arguments=prompt_arguments,
        on_exception=_fix_invalid_analysis,
        exception_type=OutputParserException,
    )


def _call_analyze_llm(state: State) -> Analysis:
    relevant_files_so_far_str = json.dumps(
        [f.model_dump() for f in state["_current_analysis"].relevant_files_so_far]
    )

    messages = [
        ("system", AnalyzeKnowledgePrompt.role_description),
        HumanMessage(state["query"]),
        ("human", AnalyzeKnowledgePrompt.additional_context),
        HumanMessage(f"Previous overview:\n{state['_current_analysis'].overview}"),
        HumanMessage(f"Previously relevant files:" f"\n{relevant_files_so_far_str}"),
        HumanMessage(f"Previous reasoning:\n{state['_current_analysis'].reasoning}"),
        HumanMessage(
            f"Previous unknowns:" f"\n{json.dumps(state['_current_analysis'].unknowns)}"
        ),
        HumanMessage(
            f"Previous next steps:"
            f"\n{json.dumps(state['_current_analysis'].next_steps)}"
        ),
        *get_latest_messages(state),
        ("human", AnalyzeKnowledgePrompt.output_format),
    ]

    prompt = ChatPromptTemplate.from_messages(messages)

    data = {
        "format_instructions": analysis_parser.get_format_instructions(),
        "root_path_ls": state["_root_path_ls"],
        "tool_descriptions": tools_to_json(get_llm_tools(state["root_path"])),
        "example_output_next_steps": json.dumps(example_output_next_steps.dict()),
        "example_output_select_files": json.dumps(example_output_select_files.dict()),
    }

    return _invoke_fixable_llm_analysis_chain(prompt, data)


class _Node:
    @staticmethod
    def analyze_knowledge(state: State) -> dict:
        """
        Analyze the knowledge and provide the next steps for the investigation.

        The analysis is based on the following pieces of information:
        - The issue statement,
        - The `_root_path_ls`,
        - The tools available,
        - The previous knowledge analysis.
        - The results of tools called after the previous knowledge analysis.
        """
        analysis: Analysis = _call_analyze_llm(state)

        return {
            "_previous_analysis": state["_current_analysis"],
            "_current_analysis": analysis,
            "_iteration_count": state["_iteration_count"] + 1,
        }

    @staticmethod
    def call_tools(state: State) -> dict:
        next_steps = json.dumps(state["_current_analysis"].next_steps)
        response = create_llm(
            LLMConfigType.SRF_TOOLS, tools=get_llm_tools(state["root_path"])
        ).invoke(
            [
                SystemMessage(SelectFilesPrompt.role_description),
                HumanMessage(f"Next steps:\n{next_steps}"),
                HumanMessage(SelectFilesPrompt.output_format_tools),
            ]
        )

        state["_messages"].append(response)

        if (value := tools_condition(state, "_messages")) != "tools":
            raise ValueError(f"Unexpected next node value: {value}")

        result = get_tool_node(state["root_path"]).invoke(state)
        result["_iteration_count"] = state["_iteration_count"] + 1
        return result

    @staticmethod
    def select_files(state: State) -> dict:
        if state["_current_analysis"].next_steps:
            logger.warning(
                "The analysis is not complete, however flow was forced to make final "
                f"decision. Next steps: `{state['_current_analysis'].next_steps}`"
            )

        valid_files, invalid_files = validate_files(
            state["_current_analysis"].relevant_files_so_far, state["root_path"]
        )

        return {"relevant_files": valid_files, "invalid_files": invalid_files}


def _is_analysis_stuck(state: State) -> bool:
    return state["_current_analysis"].json_str == state["_previous_analysis"].json_str


def _is_approaching_iteration_limit(state: State) -> bool:
    loop_step_count = 2
    """There are 2 steps in the "call_tools" -> "analyze_knowledge" loop."""

    steps_until_graph_end = 1
    """After we exit the analysis loop there is 1 step left: "select_files"."""

    return (
        state["_iteration_count"] + loop_step_count + steps_until_graph_end
        >= SRFConfig.CYCLE_ITERATION_LIMIT
    )


def _select_files_or_call_tools(
    state: State,
) -> Literal[_Node.select_files.__name__, _Node.call_tools.__name__]:
    if (
        _is_analysis_stuck(state)
        or not state["_current_analysis"].next_steps
        or _is_approaching_iteration_limit(state)
    ):
        return _Node.select_files.__name__

    return _Node.call_tools.__name__


def get_latest_messages(state: State, max_depth: int = 1) -> list[AnyMessage]:
    """
    Get the latest tool call and tool messages.

    The messages are stored in the following, repeating order:
    [analysis [AIToolMsg], tool_calls [AIMsg], tool_results [ToolMsg], ...]
    So: one depth means two AI messages. Note: the number of tool messages depends
    on the number of tool calls returned in the preview AI message.
    """
    ai_msgs_to_retrieve = max_depth

    current_ai_msgs = 0
    messages = []
    for message in state["_messages"][::-1]:
        messages.append(message)
        if isinstance(message, AIMessage):
            current_ai_msgs += 1
            if current_ai_msgs >= ai_msgs_to_retrieve:
                break

    return messages[::-1]


class FileSelectionGraph(BaseGraph):
    def __init__(self):
        super().__init__(State)

    def _build(self):
        self.add_quick_node(_Node.analyze_knowledge)
        self.add_quick_node(_Node.call_tools)
        self.add_quick_node(_Node.select_files)

        self.add_quick_edge(START, _Node.analyze_knowledge)
        self.add_quick_conditional_edges(
            _Node.analyze_knowledge, _select_files_or_call_tools
        )

        self.add_quick_edge(_Node.call_tools, _Node.analyze_knowledge)

        self.add_quick_edge(_Node.select_files, END)

    def create_init_state(
        self,
        query: str,
        root_path: Path,
    ) -> State:
        return State(
            root_path=root_path,
            query=query,
            _iteration_count=1,
            _root_path_ls=ls_dir(root_path),
            _current_analysis=Analysis(),
            _previous_analysis=Analysis(),
            _messages=[],
            relevant_files=[],
            invalid_files=[],
        )

    def __call__(
        self,
        query: str,
        root_path: Path,
        print_conversations: bool = False,
    ) -> list[RelevantFile]:
        initial_state = self.create_init_state(
            query=query,
            root_path=root_path,
        )

        resp: State = self.compiled.invoke(
            initial_state,
            config=RunnableConfig(recursion_limit=SRFConfig.CYCLE_ITERATION_LIMIT),
        )

        if print_conversations:
            for msg in resp["_messages"]:
                msg.pretty_print()

        return resp["relevant_files"]


file_selection_graph = FileSelectionGraph()


if __name__ == "__main__":
    print(f"Saved to: {file_selection_graph.visualize()}")
