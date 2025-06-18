from deep_next.common.llm_retry import invoke_retriable_llm_chain


class LLMChainMock:
    def __init__(self, n_fails: int):
        self.n_fails = n_fails
        self.n_times_called = 0

    def invoke(self, data):
        self.n_times_called += 1

        if self.n_times_called < self.n_fails:
            raise ValueError

        return {"output": "Some output data", "n_times_called": self.n_times_called}


def test_invoke_retriable_llm_chain_single_exception():
    llm = LLMChainMock(n_fails=3)

    result = invoke_retriable_llm_chain(
        n_retry=3,
        llm_chain_builder=lambda iter_idx: llm,
        prompt_arguments={"input": "value1"},
        exception_type=ValueError,
    )

    assert result["n_times_called"] == 3


def test_invoke_retriable_llm_chain_multiple_exceptions():
    llm = LLMChainMock(n_fails=3)

    result = invoke_retriable_llm_chain(
        n_retry=3,
        llm_chain_builder=lambda iter_idx: llm,
        prompt_arguments={"input": "value1"},
        exception_type=(ValueError, BrokenPipeError),
    )

    assert result["n_times_called"] == 3
