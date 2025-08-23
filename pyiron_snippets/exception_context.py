import contextlib


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

        No exception raised: callbacks do not run.

        >>> history = []
        >>> with ExceptionExitStack() as stack:
        ...     _ = stack.callback(its_historical, history, "we shouldn't see this")
        ...     # because there's no exception here
        >>> history
        []
    """

    def __init__(self, *exceptions: type[Exception]):
        super().__init__()
        self._exception_types = [Exception] if len(exceptions) == 0 else exceptions

    def __exit__(self, exc_type, exc_val, exc_tb):
        if any(isinstance(exc_val, e) for e in self._exception_types):
            return super().__exit__(exc_type, exc_val, exc_tb)
        self.pop_all()
