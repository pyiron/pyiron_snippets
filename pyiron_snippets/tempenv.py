import contextlib
import os


@contextlib.contextmanager
def TemporaryEnvironment(**kwargs):
    """
    Context manager for temporarily setting environment variables.

    Takes any number of keyword arguments where the key is the environment
    variable to set and the value is the value to set it to. For the duration
    of the context, the environment variables are set as per the provided arguments.
    The original environment setting is restored once the context is exited,
    even if an exception is raised within the context.

    Non-string values are coerced with `str()`.

    Can also be used as a function decorator.

    Examples:

    >>> import os
    >>> with TemporaryEnvironment(PATH='/tmp', HOME='/', USER='foobar'):
    ...     print(os.getenv('PATH'))  # Outputs: /tmp
    ...     print(os.getenv('HOME'))  # Outputs: /
    ...     print(os.getenv('USER'))  # Outputs: foobar
    /tmp
    /
    foobar
    """
    old_vars = {}
    for k, v in kwargs.items():
        try:
            old_vars[k] = os.environ[k]
        except KeyError:
            pass
        os.environ[k] = str(v)
    try:
        yield
    finally:
        for k, v in kwargs.items():
            if k in old_vars:
                os.environ[k] = old_vars[k]
            else:
                del os.environ[k]
