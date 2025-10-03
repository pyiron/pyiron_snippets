"""
Helper functions for managing the relationship between strings and imports.
"""

from __future__ import annotations

import importlib


class StringNotImportableError(ImportError): ...


def import_from_string(library_path: str) -> object:
    """
    Import an object using a string of its python library location.

    Args:
        library_path (str): The full module path to the desired object.

    Returns:
        (object): The imported object.

    Example:
        >>> from pyiron_snippets import retrieve
        >>> ThreadPoolExecutor = retrieve.import_from_string(
        ...     "concurrent.futures.ThreadPoolExecutor"
        ... )
        >>> with ThreadPoolExecutor(max_workers=2) as executor:
        ...     future = executor.submit(pow, 2, 3)
        ...     print(future.result())
        8

    """
    if (not isinstance(library_path, str)) or len(library_path) == 0:
        raise ValueError(
            f"Expected a non-empty string, got '{library_path}'  of type {type(library_path)} instead."
        )

    split_path = library_path.split(".", 1)
    if len(split_path) == 1:
        module_name, path = split_path[0], ""
    else:
        module_name, path = split_path

    try:
        obj = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            f"The topmost entry of {library_path} could not be found. The most likely "
            f"causes of this problem are a typo, or that the module is not yet in your "
            f"system's PYTHONPATH. The latter can be checked from inside python with "
            f"`import sys; print(sys.path)`."
        ) from e

    for k in path.split("."):
        if k == "":
            break
        try:
            obj = getattr(obj, k)
        except AttributeError:
            # Try importing as a submodule
            # This can be necessary of an __init__.py is empty and nothing else has
            # referenced the module yet
            current_path = f"{obj.__name__}.{k}"
            obj = importlib.import_module(current_path)
    return obj


def get_importable_string_from_string_reduction(
    string_reduction: str, reduced_object: object
) -> str:
    """
    Per the pickle docs:

    > If a string is returned, the string should be interpreted as the name of a global
      variable. It should be the object’s local name relative to its module; the pickle
      module searches the module namespace to determine the object’s module. This
      behaviour is typically useful for singletons.

    To then import such an object from a non-local caller, we try scoping the string
    with the module of the object which returned it.
    """
    try:
        import_from_string(string_reduction)
        importable = string_reduction
    except ModuleNotFoundError:
        importable = reduced_object.__module__ + "." + string_reduction
        try:
            import_from_string(importable)
        except (ModuleNotFoundError, AttributeError) as e:
            raise StringNotImportableError(
                f"Couldn't import {string_reduction} after scoping it as {importable}. "
                f"Please contact the developers so we can figure out how to handle "
                f"this edge case."
            ) from e
    return importable
