from __future__ import annotations

import os
from enum import Enum
from typing import Any, Callable, Iterable, Optional

import yaml
from boto3 import Session
from deep_next.common.common import load_monorepo_dotenv
from deep_next.common.config import MONOREPO_ROOT_PATH
from deep_next.core.common import RemoveThinkingBlocksParser
from langchain_aws import ChatBedrock
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler
from loguru import logger
from pydantic import BaseModel


class LLMConfigType(str, Enum):
    PROJECT_KNOWLEDGE = "project-knowledge"
    ACTION_PLAN = "action-plan"
    SRF_ANALYZE = "srf-analyze"
    SRF_TOOLS = "srf-tools"
    SRS_ANALYZE = "srs-analyze"
    IMPLEMENT = "implement"
    CODE_REVIEW = "code-review"
    DEFAULT = "default"


class Provider(str, Enum):
    BEDROCK = "aws-bedrock"
    OPENAI = "openai"
    OLLAMA = "ollama"


class Model(str, Enum):
    AWS_CLAUDE_3_5_SONNET_20240620_V1_0 = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    AWS_CLAUDE_3_7_SONNET_20240620_V1_0 = "anthropic.claude-3-7-sonnet-20250219-v1:0"
    AWS_DEEPSEEK_R1_v1_0 = "us.deepseek.r1-v1:0"
    AWS_MISTRAL_7B_INSTRUCT_V0_2 = "mistral.mistral-7b-instruct-v0:2"

    GPT_4O_2024_08_06 = "gpt-4o-2024-08-06"
    GPT_4_1_2025_04_14 = "gpt-4.1-2025-04-14"
    GPT_4O_MINI_2024_07_18 = "gpt-4o-mini-2024-07-18"

    CODELLAMA = "codellama"
    DEEPCODER = "deepcoder"
    DEEPSEEK_CODER_V2 = "deepseek-coder-v2"
    DEEPSEEK_V3 = "deepseek-v3"
    DEEPSEEK_R1 = "deepseek-r1"
    GEMMA3 = "gemma3"
    MISTRAL = "mistral"
    LLAMA4 = "llama4"
    LLAMA3_3 = "llama3.3"
    QWEN3 = "qwen3"

    @property
    def provider(self) -> Provider:
        return _provider[self]


models_with_thinking_blocks = [
    Model.QWEN3,
    Model.AWS_DEEPSEEK_R1_v1_0,
    Model.DEEPCODER,
    Model.DEEPSEEK_R1,
    Model.DEEPSEEK_CODER_V2,
    Model.DEEPSEEK_V3,
]


_provider = {
    Model.AWS_CLAUDE_3_5_SONNET_20240620_V1_0: Provider.BEDROCK,
    Model.AWS_CLAUDE_3_7_SONNET_20240620_V1_0: Provider.BEDROCK,
    Model.AWS_DEEPSEEK_R1_v1_0: Provider.BEDROCK,
    Model.AWS_MISTRAL_7B_INSTRUCT_V0_2: Provider.BEDROCK,
    Model.GPT_4O_MINI_2024_07_18: Provider.OPENAI,
    Model.GPT_4O_2024_08_06: Provider.OPENAI,
    Model.GPT_4_1_2025_04_14: Provider.OPENAI,
    Model.CODELLAMA: Provider.OLLAMA,
    Model.DEEPCODER: Provider.OLLAMA,
    Model.DEEPSEEK_CODER_V2: Provider.OLLAMA,
    Model.DEEPSEEK_V3: Provider.OLLAMA,
    Model.DEEPSEEK_R1: Provider.OLLAMA,
    Model.GEMMA3: Provider.OLLAMA,
    Model.MISTRAL: Provider.OLLAMA,
    Model.LLAMA4: Provider.OLLAMA,
    Model.LLAMA3_3: Provider.OLLAMA,
    Model.QWEN3: Provider.OLLAMA,
}


class LLMConfig(BaseModel):
    model: Model
    seed: int | None
    temperature: float | None
    config: dict | None = None

    @classmethod
    def load(cls, config_type: LLMConfigType = LLMConfigType.DEFAULT) -> LLMConfig:
        with open(MONOREPO_ROOT_PATH / "llm-config.yaml") as stream:
            config_dict = yaml.safe_load(stream)

        return cls(**config_dict[config_type])


class _ChatBedrock(ChatBedrock):

    max_tokens: int | None = None

    _no_system_messages_providers: list[str] = ["anthropic", "mistral"]
    _no_tool_messages_providers: list[str] = ["anthropic", "deepseek"]

    @staticmethod
    def _align_input_system_to_human(messages: Iterable) -> list:
        messages = [
            HumanMessage(message.content)
            if isinstance(message, SystemMessage)
            else message
            for message in messages
        ]

        messages = [
            ("human", message.content)
            if isinstance(message, tuple) and message[0] == "system"
            else message
            for message in messages
        ]

        return messages

    @staticmethod
    def _align_input_tool_to_human(messages: Iterable) -> list:
        messages = [
            HumanMessage(message.content)
            if isinstance(message, ToolMessage)
            else message
            for message in messages
        ]

        messages = [
            ("human", message.content)
            if isinstance(message, tuple) and message[0] == "tool"
            else message
            for message in messages
        ]

        return messages

    @staticmethod
    def _remove_tool_calls_from_ai(messages: Iterable, trim_empty: bool = True) -> list:
        result = []
        for message in messages:
            if not isinstance(message, AIMessage) or len(message.tool_calls) == 0:
                result.append(message)
                continue

            message.tool_calls.clear()
            if isinstance(message.content, list):
                fixed_content = [
                    content_item
                    for content_item in message.content
                    if content_item["type"] != "tool_use"
                ]
                message.content = fixed_content

            if trim_empty and not message.content:
                continue

            result.append(message)

        return result

    @staticmethod
    def _align_input(
        input: LanguageModelInput,
        input_fixer: Callable[[LanguageModelInput], LanguageModelInput],
    ) -> LanguageModelInput:
        if isinstance(input, list):
            return input_fixer(input)
        elif isinstance(input, ChatPromptValue):
            input.messages = input_fixer(input.messages)
            return input

        return input

    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> BaseMessage:

        if self._get_provider() in self._no_system_messages_providers:
            input = self._align_input(input, self._align_input_system_to_human)

        if self._get_provider() in self._no_tool_messages_providers:
            input = self._align_input(input, self._align_input_tool_to_human)
            input = self._align_input(input, self._remove_tool_calls_from_ai)

        if "max_tokens" not in kwargs:
            kwargs["max_tokens"] = self.max_tokens

        return super().invoke(input, config, stop=stop, **kwargs)


def _get_aws_bedrock_llm(
    config: LLMConfig, temperature: float | None = None
) -> ChatBedrock:
    boto3_session = Session(region_name=config.config["region"])

    model_kwargs = {}
    if temperature is not None:
        model_kwargs["temperature"] = temperature
    elif config.temperature is not None:
        model_kwargs["temperature"] = config.temperature

    return _ChatBedrock(
        beta_use_converse_api=True,
        model=config.model,
        client=boto3_session.client("bedrock-runtime"),
        model_kwargs=model_kwargs,
        max_tokens=8 * 1024,
        callbacks=_get_handler(),
    )


def _get_openai_llm(
    config: LLMConfig,
    seed: int | None = None,
    temperature: float | None = None,
) -> ChatOpenAI:
    """
    Creates an OpenAI LLM instance based on the provided configuration.

    Args:
        config (LLMConfig): The configuration for the LLM.
        seed (int | None): Optional seed for reproducibility. If provided, it will be
            added to the base seed from the config (as long as the config seed is not
            None. If the config seed is not provided, this value will be used as seed
            itself).
        temperature (float | None): Optional temperature setting for the model.
    """
    metadata = {}

    if config.seed is not None or seed is not None:
        metadata["seed"] = (config.seed or 0) + (seed or 0)

    return ChatOpenAI(
        model_name=config.model,
        temperature=temperature or config.temperature,
        metadata=metadata,
        callbacks=_get_handler(),
    )


def _get_ollama_llm(config: LLMConfig, temperature: float | None = None) -> ChatOllama:
    """Create a new Ollama LLM client.

    Args:
        config: LLM configuration instance
        temperature: Optional temperature override

    Returns:
        ChatOllama instance
    """
    model_kwargs = {"num_ctx": 8192}

    if temperature is not None:
        model_kwargs["temperature"] = temperature
    elif config.temperature is not None:
        model_kwargs["temperature"] = config.temperature

    return ChatOllama(
        model=config.model,
        model_kwargs=model_kwargs,
    )


def _get_handler() -> list[CallbackHandler]:
    if os.getenv("LANGFUSE_SECRET_KEY") is not None:
        langfuse_handler = CallbackHandler()
        return [langfuse_handler]
    else:
        return []


def llm_from_config(
    config_type: LLMConfigType,
    seed: int | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    config = LLMConfig.load(config_type=config_type)
    logger.info(f"LLM config: {config}")

    if config.model.provider == Provider.BEDROCK:
        return _get_aws_bedrock_llm(
            config=config,
            temperature=temperature,
        )
    elif config.model.provider == Provider.OPENAI:
        return _get_openai_llm(
            config=config,
            seed=seed,
            temperature=temperature,
        )
    elif config.model.provider == Provider.OLLAMA:
        return _get_ollama_llm(
            config=config,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {config.model.provider}")


def create_llm(
    config_type: LLMConfigType,
    seed: int | None = None,
    tools: list | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """Create a new LLM client"""
    llm = llm_from_config(config_type, seed=seed, temperature=temperature)

    llm = llm.bind_tools(tools) if tools else llm

    config = LLMConfig.load(config_type=config_type)
    if config.model in models_with_thinking_blocks:
        return llm | RemoveThinkingBlocksParser()
    else:
        return llm


if __name__ == "__main__":
    load_monorepo_dotenv()

    llm = llm_from_config(LLMConfigType.DEFAULT)
    response = llm.invoke("Tell me a short poem about machine learning.")
    print(response.content)
