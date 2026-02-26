"""
Tools for reliably and robustly extracting versioning info from python objects.
"""

from __future__ import annotations

import dataclasses
import importlib
import sys
from collections.abc import Callable
from types import BuiltinMethodType, ModuleType
from typing import Any, Self, TypeAlias

VersionScraperType: TypeAlias = Callable[[str], str | None]
VersionScrapingMap: TypeAlias = dict[str, VersionScraperType]


@dataclasses.dataclass(frozen=True)
class VersionInfo:
    """
    Immutable record of an object's module, qualified name, and module version.

    This is useful for capturing provenance metadata about classes and instances,
    e.g. for serialization or reproducibility tracking.

    Attributes:
        module: The dotted module path where the object's type is defined.
        qualname: The qualified name of the object's type within its module. A None
            qualname indicates that the object is itself a module.
        version: The version string of the top-level package, or ``None`` if no version
            could be determined.

    Example:
        >>> from pyiron_snippets import versions
        >>>
        >>> versions.VersionInfo.of(42)  # doctest: +ELLIPSIS
        VersionInfo(module='builtins', qualname='int', version=...)

    Note:
        For object instances, this is version info about that object's _type_, not
        information about where the instance itself is living.
    """

    module: str
    qualname: str | None
    version: str | None

    @property
    def fully_qualified_name(self) -> str:
        if self.qualname is None:
            return self.module
        return f"{self.module}.{self.qualname}"

    @classmethod
    def of(
        cls,
        obj: object,
        version_scraping: VersionScrapingMap | None = None,
        forbid_main: bool = False,
        forbid_locals: bool = False,
        require_version: bool = False,
    ) -> VersionInfo:
        """
        Construct a :class:`VersionInfo` by introspecting *obj*.

        If a `__module__` or `__qualname__` is immediately available, they are used,
        otherwise the same fields are sought on the object's type.

        Args:
            obj: The object to introspect.
            version_scraping: Optional mapping from top-level package names to
                callables that return a version string (or ``None``). Used to
                handle packages that don't expose ``__version__``.
            forbid_main: If ``True``, raise :exc:`ValueError` when the module
                is ``__main__``.
            forbid_locals: If ``True``, raise :exc:`ValueError` when the
                qualname contains ``<locals>`` (i.e. the type was defined
                inside a function).
            require_version: If ``True``, raise :exc:`ValueError` when no
                version can be determined for the module.

        Returns:
            A new :class:`VersionInfo` instance.

        Raises:
            ValueError: If any of the ``forbid_*`` / ``require_*`` constraints
                are violated.
        """
        module = get_module(obj)
        qualname = get_qualname(obj)
        version = get_version(module, version_scraping=version_scraping)
        info = cls(module=module, qualname=qualname, version=version)
        info.validate_constraints(
            forbid_main=forbid_main,
            forbid_locals=forbid_locals,
            require_version=require_version,
        )
        return info

    def validate_constraints(
        self,
        forbid_main: bool = False,
        forbid_locals: bool = False,
        require_version: bool = False,
    ) -> Self:
        if forbid_main and "__main__" in self.module:
            raise ValueError(f"Found forbidden module '__main__' in module for {self}")

        if forbid_locals and self.qualname is not None and "<locals>" in self.qualname:
            raise ValueError(f"Found forbidden <locals> in qualname for {self}")

        if require_version and self.version is None:
            raise ValueError(f"Could not find a version for {self}")

        return self


@dataclasses.dataclass(frozen=True)
class VersionInfoFactory:
    """
    A simple stateful wrapper for :class:`VersionInfo` that is useful when getting
    info from multiple objects with the same settings.
    """

    version_scraping: VersionScrapingMap | None = None
    forbid_main: bool = False
    forbid_locals: bool = False
    require_version: bool = False

    def of(self, obj: object) -> VersionInfo:
        return VersionInfo.of(
            obj,
            version_scraping=self.version_scraping,
            forbid_main=self.forbid_main,
            forbid_locals=self.forbid_locals,
            require_version=self.require_version,
        )

    def validate_constraints(self, info: VersionInfo) -> VersionInfo:
        return info.validate_constraints(
            forbid_main=self.forbid_main,
            forbid_locals=self.forbid_locals,
            require_version=self.require_version,
        )


def get_module(obj: Any) -> str:
    """
    Get module information for an arbitrary object.

    Note:
        For object instances, this is version info about that object's _type_, not
        information about where the instance itself is living.
    """
    if isinstance(obj, ModuleType):
        return obj.__name__

    # Try the obvious path first
    module = getattr(obj, "__module__", None)
    if module is not None:
        return module

    # For bound builtin methods, look up the defining class
    if isinstance(obj, BuiltinMethodType):
        # obj.__self__ is the instance, obj.__name__ is the method name
        self_obj = getattr(obj, "__self__", None)
        if self_obj is not None:
            for cls in type(self_obj).__mro__:
                if obj.__name__ in cls.__dict__:
                    module = getattr(cls.__dict__[obj.__name__], "__module__", None)
                    if module is not None:
                        return module
            # Fall back to the type's module
            module = getattr(type(self_obj), "__module__", None)
            if module is not None:
                return module

    # Last resort
    module = getattr(type(obj), "__module__", None)
    if module is not None:
        return module

    raise AttributeError(
        f"Could not find a module on obj {obj} or type(obj) {type(obj)}."
    )


def get_qualname(obj: Any) -> str | None:
    """
    Get module information for an arbitrary object.

    Note:
        For object instances, this is version info about that object's _type_, not
        information about where the instance itself is living.
    """
    if isinstance(obj, ModuleType):
        return None
    qualname = getattr(
        obj,
        "__qualname__",
        getattr(type(obj), "__qualname__", None)
    )
    if not isinstance(qualname, str):
        raise TypeError(f"Expected a string __qualname__, but {obj} had {qualname}.")
    if len(qualname) == 0:
        raise ValueError(f"Expected a non-empty qualname string for {obj}.")
    return qualname


def get_version(
    module_name: str,
    version_scraping: VersionScrapingMap | None = None,
) -> str | None:
    """
    Given a module name, get its associated version (if any) by iteratively checking
    each module level for an available version. By default, this simply looks for the
    :attr:`__version__` attribute on the imported module, but searching behaviour can
    be customized with the :arg:`version_scraping` argument.

    The first found version walking up the module path takes precedence over higher
    versions, and the version scraping map entries take precedence over the default
    :attr:`__version__` check at each step while walking.

    For :mod:`builtins`, the python interpreter version is given.

    Args:
        module_name (str): The module to recursively examine.
        version_scraping (VersionScrapingMap | None): Since some modules may store
            their version in other ways, this provides an optional map between module
            names and callables to leverage for extracting that module's version.

    Returns:
        (str | None): The module's version as a string, if any can be found.

    Warnings:
        This imports the module in the process, so it is not "safe".
    """
    if module_name == "builtins":
        return _python_version()

    scraper = (version_scraping or {}).get(module_name, _scrape_version_attribute)
    scraped_version = scraper(module_name)

    next_module = module_name.rsplit(".", maxsplit=1)[0]
    if scraped_version is not None or next_module == module_name:
        return scraped_version
    else:
        return get_version(next_module, version_scraping=version_scraping)


def _scrape_version_attribute(module_name: str) -> str | None:
    if module_name in sys.stdlib_module_names:
        return _python_version()
    module = importlib.import_module(module_name)
    try:
        return str(module.__version__)
    except AttributeError:
        return None


def _python_version() -> str:
    vi = sys.version_info
    return f"{vi.major}.{vi.minor}.{vi.micro}"
