"""
Graceful failure for missing optional dependencies.
"""

import functools
import warnings


class ImportAlarmError(ImportError):
    """To be raised instead of a warning when a package is missing."""


class ImportAlarm:
    """
    This class allows you to fail gracefully when some object has optional dependencies
    and the user does not have those dependencies installed.

    Example:

    >>> try:
    ...     from mystery_package import Enigma, Puzzle, Conundrum
    ...     import_alarm = ImportAlarm()
    ... except ImportError:
    ...     import_alarm = ImportAlarm(
    ...         "MysteryJob relies on mystery_package, but this was unavailable. Please ensure your python environment "
    ...         "has access to mystery_package, e.g. with `conda install -c conda-forge mystery_package`"
    ...     )
    ...
    >>> class MysteryJob:
    ...     @import_alarm
    ...     def __init__(self, project, job_name):
    ...         super().__init__()
    ...         self.riddles = [Enigma(), Puzzle(), Conundrum()]

    This class is also a context manager that can be used as a short-cut, like this:

    >>> with ImportAlarm(
    ...     "MysteryJob relies on mystery_package, but this was unavailable."
    ... ) as import_alarm:
    ...     import mystery_package

    If you do not use `import_alarm` as a decorator, but only to get a consistent
    warning message, call :meth:`.warn_if_failed()` after the with statement.

    >>> import_alarm.warn_if_failed()
    """

    def __init__(
        self,
        message=None,
        raise_exception: bool = False,
    ):
        """
        Initialize message value.

        If a `raise_exception` is `True`, raise a :class:`.ImportAlarmError`, which is a subclass of `ImportError`.

        Args:
            message (str): What to say alongside your ImportError when the decorated
            function is called. (Default is None, which says nothing and raises no
            error.)
            raise_exception (bool, optional): raise an exception instead of issuing a warning
        """
        self.message = message
        # Catching warnings in tests can be janky, so instead open a flag for failing
        # instead.
        self.raise_exception = raise_exception

    def __call__(self, func):
        return self.wrapper(func)

    def wrapper(self, function):
        @functools.wraps(function)
        def decorator(*args, **kwargs):
            self.warn_if_failed()
            return function(*args, **kwargs)

        return decorator

    def warn_if_failed(self):
        """
        Print warning message if import has failed.  In case you are not using
        :class:`ImportAlarm` as a decorator you can call this method manually to
        trigger the warning.
        """
        if self.message is not None:
            warnings.warn(self.message, category=ImportWarning, stacklevel=2)
            if self.raise_exception:
                raise ImportAlarmError(self.message)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None and exc_value is None and traceback is None:
            # import successful, so silence our warning
            self.message = None
            return
        # True: import broken; retain message, but suppress error
        # False: unrelated error during import, re-raise
        return issubclass(exc_type, ImportError)
