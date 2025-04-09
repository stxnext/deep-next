from functools import wraps

from loguru import logger


class LoggingMeta(type):
    """Metaclass that automatically wraps methods in a class to log their execution."""

    def __new__(cls, cls_name: str, bases: tuple, cls_attrs: dict) -> type:
        """Intercept class creation to wrap methods for logging."""
        for attr_name, attr_value in cls_attrs.items():
            if callable(attr_value) and not attr_name.startswith("__"):
                if isinstance(attr_value, staticmethod):
                    original_method = attr_value.__func__
                    cls_attrs[attr_name] = staticmethod(
                        cls.wrap_method(attr_name, original_method)
                    )
                elif isinstance(attr_value, classmethod):
                    raise NotImplementedError("Class methods are not supported (yet).")
                else:
                    # Instance method
                    cls_attrs[attr_name] = cls.wrap_method(attr_name, attr_value)

        return super().__new__(cls, cls_name, bases, cls_attrs)

    @staticmethod
    def wrap_method(method_name: str, method: callable) -> callable:
        """Wraps method to log its execution before calling the original method."""

        @wraps(method)
        def wrapper(*args, **kwargs):
            formatted_name = method_name.replace("_", " ").title()
            logger.debug(f"Executing '{formatted_name}'")

            return method(*args, **kwargs)

        return wrapper


class BaseNode(metaclass=LoggingMeta):
    """Base class that uses LoggingMeta to automatically log method calls.

    Example:
        class MyNode(BaseNode):
            def example_method(self):
                logger.info("Hello from example!")

        MyNode().example_method()
        # Executing 'Example Method' from 'MyNode'
        # Hello from example!
    """
