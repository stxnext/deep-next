import functools
import inspect

from tenacity import RetryCallState
from tenacity import retry as _retry


def retry(*dargs, **dkwargs):
    """Like @retry but injects `__attempt` keyword arg with attempt number."""

    def decorator(f):
        @_retry(*dargs, **dkwargs)
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            frame = inspect.currentframe()
            while frame:
                local_vars = frame.f_locals
                if "retry_state" in local_vars and isinstance(
                    local_vars["retry_state"], RetryCallState
                ):
                    kwargs["__attempt"] = local_vars["retry_state"].attempt_number
                    break
                frame = frame.f_back
            return f(*args, **kwargs)

        return wrapper

    # Support @retry and @retry(...)
    if len(dargs) == 1 and callable(dargs[0]):
        return decorator(dargs[0])
    else:
        return decorator
