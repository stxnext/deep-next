from typing import Callable, TypeVar

from langchain_core.language_models import BaseChatModel

T = TypeVar("T")


def invoke_retriable_llm_chain(
    n_retry: int,
    llm_chain_builder: Callable[[int], BaseChatModel],
    prompt_arguments: dict,
    *,
    on_exception: Callable[[Exception], T | None] | None = None,
    exception_type: type[Exception] | tuple[type[Exception], ...] = Exception,
) -> T:
    """
    Invoke the LLM chain and retry up to `n_retry` times if it fails.

    The retry mechanism includes two steps:
    1. Attempting to fix the current invalid output.
    2. Rerunning the chain with a different seed if the fix attempt fails.

    Args:
        n_retry (int): Number of retry attempts.
        llm_chain_builder (Callable[[int], BaseChatModel]): A callable that builds the
            LLM chain.
        prompt_arguments (dict): The arguments to pass to the LLM chain.
        on_exception (Callable[[Exception], Optional[T]], optional):
            A callable that handles exceptions and returns a result or `None`.
        exception_type (type[Exception] | tuple[type[Exception], ...], optional):
            Exception type(s) to catch. Defaults to `Exception`.

    Returns:
        T: The result from the LLM chain or the `on_exception` handler.

    Raises:
        Exception: The last caught exception if all retries fail.
    """
    _e: exception_type | None = None
    for i in range(n_retry):
        chain = llm_chain_builder(i)
        try:
            return chain.invoke(prompt_arguments)
        except exception_type as e:
            _e = e
            if on_exception and (result := on_exception(e)):
                return result
    raise _e
