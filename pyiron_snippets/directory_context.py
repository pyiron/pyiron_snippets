import os
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def set_directory(path: Path | str):
    """
    A context manager that changes the current working directory to the given path
    upon entering the context and reverts to the original directory upon exiting.
    If the specified path does not exist, it is created.

    Parameters:
        path: Path | str
            The target directory path to set as the current working directory.
            If it does not exist, it will be created.

    Examples:
        Change the directory to the path "tmp" within the context:

        >>> import os
        >>> from pyiron_snippets.directory_context import set_directory
        >>> directory_before_context_is_applied = os.getcwd()
        >>> with set_directory("tmp"):
        ...     os.path.relpath(os.getcwd(), directory_before_context_is_applied)
        'tmp'

    """
    origin = Path().absolute()
    try:
        os.makedirs(path, exist_ok=True)
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)
