import contextlib
from collections.abc import Callable, Collection
from typing import Any


class ExceptionExitStack(contextlib.ExitStack):
    """
    A variant of contextlib.ExitStack that only executes registered callbacks
    when an exception is raised, and only if that exception matches one of the
    specified exception types.

    Behavior:
    - If no exception types are given, callbacks run for any raised exception.
    - If one or more exception types are given, callbacks run only when the
      raised exception is an instance of at least one of those types.
    - On normal (non-exceptional) exit, callbacks are discarded and not run.
    - Exceptions are not suppressed by this context manager.

    Parameters:
        *exceptions: type[Exception]
            Zero or more exception types. If empty, callbacks run for any
            exception; otherwise, only for matching exception types.

    Examples:
        Let's take a toy callback and see how we do (or don't) trigger it.

        >>> def its_historical(history: list[str], message: str) -> None:
        ...     history.append(message)

        No types specified: callbacks run for any raised exception.

        >>> from pyiron_snippets.exception_context import ExceptionExitStack
        >>> history = []
        >>> try:
        ...     with ExceptionExitStack() as stack:
        ...         _ = stack.callback(its_historical, history, "with no types")
        ...         raise RuntimeError("Application error")
        ... except RuntimeError:
        ...     history
        ['with no types']

        Specified type(s) match(es) the raised exception: callbacks run.

        >>> history = []
        >>> try:
        ...     with ExceptionExitStack(RuntimeError) as stack:
        ...         _ = stack.callback(its_historical, history, "with matching type")
        ...         raise RuntimeError("Application error")
        ... except RuntimeError:
        ...     history
        ['with matching type']

        Specified type(s) do(es) not match the raised exception: callbacks do not run.

        >>> history = []
        >>> try:
        ...     with ExceptionExitStack(TypeError, ValueError) as stack:
        ...         _ = stack.callback(its_historical, history, "with mis-matching types")
        ...         raise RuntimeError("Application error")
        ... except RuntimeError:
        ...     history
        []

        No exception raised: callbacks do not run. But, the stack can be combined with
        other stacks.

        >>> import contextlib
        >>>
        >>> history = []
        >>> with ExceptionExitStack() as exc_stack, contextlib.ExitStack() as reg_stack:
        ...     _ = exc_stack.callback(its_historical, history, "we shouldn't see this")
        ...     _ = reg_stack.callback(its_historical, history, "but we should see this")
        >>> history
        ['but we should see this']
    """

    def __init__(self, *exceptions: type[Exception]):
        if not all(
            isinstance(e, type) and issubclass(e, Exception) for e in exceptions
        ):
            raise ValueError(
                f"Invalid exception type(s) provided. Expected only subclasses of "
                f"`Exception`, but got {exceptions}"
            )
        super().__init__()
        self._exception_types: tuple[type[Exception], ...] = (
            (Exception,) if len(exceptions) == 0 else exceptions
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None and any(
            isinstance(exc_val, e) for e in self._exception_types
        ):
            return super().__exit__(exc_type, exc_val, exc_tb)
        self.pop_all()


@contextlib.contextmanager
def on_error(
    func: Callable[..., Any],
    exceptions: type[Exception] | Collection[type[Exception]] | None,
    *args: Any,
    **kwargs: Any,
):
    """
    A context manager that invokes a callback only when an exception is raised,
    and only if that exception matches the specified type(s).

    This is analogous to ExceptionExitStack, but designed for use with an
    existing context manager stack (e.g., contextlib.ExitStack). It registers
    a single callback and defers calling it until an exception occurs and
    matches the provided exception type(s).

    Behavior:
    - If exceptions is None, the callback runs for any raised Exception.
    - If a single exception type is provided, the callback runs only when the
      raised exception is an instance of that type.
    - If a collection of exception types is provided, the callback runs when
      the raised exception matches any type in the collection.
    - On normal (non-exceptional) exit, the callback does not run.
    - Exceptions are never suppressed; they are always re-raised after the
      callback (if any) has been executed.

    Parameters:
        func: Callable[..., Any]
            The callback to execute on a matching exception.
        exceptions: type[Exception] | Collection[type[Exception]] | None
            The exception type(s) that should trigger the callback. Use None
            to match all Exceptions.
        *args: Any
            Positional arguments passed to the callback.
        **kwargs: Any
            Keyword arguments passed to the callback.

    Examples:
        A simple callback that records a message:

        >>> def its_historical(history: list[str], message: str) -> None:
        ...     history.append(message)

        Callback on all exceptions when no types are specified:

        >>> import contextlib
        >>> from pyiron_snippets.exception_context import on_error
        >>> history = []
        >>> msg = "with no types"
        >>> try:
        ...     with contextlib.ExitStack() as stack:
        ...         _ = stack.enter_context(on_error(its_historical, None, history, message=msg))
        ...         raise RuntimeError("Application error")
        ... except RuntimeError:
        ...     history
        ['with no types']

        Callback on matching exception with a specifier:

        >>> history = []
        >>> msg = "with matching type"
        >>> try:
        ...     with contextlib.ExitStack() as stack:
        ...         _ = stack.enter_context(on_error(its_historical, RuntimeError, history, message=msg))
        ...         raise RuntimeError("Application error")
        ... except RuntimeError:
        ...     history
        ['with matching type']

        No callback on mis-matching exception types:

        >>> history = []
        >>> try:
        ...     with contextlib.ExitStack() as stack:
        ...         _ = stack.enter_context(on_error(its_historical, (TypeError, ValueError), history, message="nope"))
        ...         raise RuntimeError("Application error")
        ... except RuntimeError:
        ...     history
        []

        No exception raised: callback does not run. But, we can add regular callbacks
        to the stack to combine effects.

        >>> history = []
        >>> with contextlib.ExitStack() as stack:
        ...     _ = stack.enter_context(on_error(its_historical, None, history, message="we shouldn't see this"))
        ...     _ = stack.callback(its_historical, history, message="but we should see this")
        >>> history
        ['but we should see this']
    """

    exception_types: tuple[type[Exception], ...]
    if exceptions is None:
        exception_types = (Exception,)
    elif isinstance(exceptions, type) and issubclass(exceptions, Exception):
        exception_types = (exceptions,)
    else:
        if not all(
            isinstance(e, type) and issubclass(e, Exception) for e in exceptions
        ):
            raise ValueError(
                f"Invalid exception type(s) provided. Expected only subclasses of "
                f"`Exception`, but got {exceptions}"
            )
        exception_types = tuple(exceptions)

    try:
        yield
    except Exception as e:
        if any(isinstance(e, exc_type) for exc_type in exception_types):
            func(*args, **kwargs)
        raise
