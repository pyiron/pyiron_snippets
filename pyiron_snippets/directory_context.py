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
        Change the directory to the path "context" within the context:

        >>> import os
        >>> os.getcwd()
        '/home/user'
        >>> from pyiron_snippets.directory_context import set_directory
        >>> with set_directory("context"):
        ...     os.getcwd()
        '/home/user/context'
       
    """
    origin = Path().absolute()
    try:
        os.makedirs(path, exist_ok=True)
        os.chdir(path)
        yield
    finally:
        os.chdir(origin)
