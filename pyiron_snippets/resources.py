"""
Classes to find data files and executables in global paths.
"""

from __future__ import annotations

import os
import os.path
import re
import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from fnmatch import fnmatch
from glob import glob
from typing import Any

if os.name == "nt":
    EXE_SUFFIX = "bat"
else:
    EXE_SUFFIX = "sh"


class ResourceNotFound(RuntimeError):
    pass


class ResolverWarning(RuntimeWarning):
    pass


class AbstractResolver(ABC):
    """
    Interface for resolvers.

    Implementations must define :meth:`._search`, taking a tuple of names to search for and yielding instances of any
    type.  Implementations should pick a single type to yield, e.g. :class:`.ResourceResolver` always yields absolute
    paths, while :class:`.ExecutableResolver` always yields 2-tuples of a version tag and absolute paths.
    """

    @abstractmethod
    def _search(self, name: tuple[str]) -> Iterator[Any]:
        pass

    def search(self, name: Iterable[str] | str = "*") -> Iterator[Any]:
        """
        Yield all matches.

        When `name` is given as an iterable, returned results match at least one of the `name` globs.

        Args:
            name (str, iterable of str): file name to search for; can be an exact file name, a glob or list of those

        Yields:
            object: resources matching `name`
        """
        if name is not None and not isinstance(name, str):
            name = tuple(name)
        else:
            name = (name,)
        yield from self._search(name)

    def list(self, name: Iterable[str] | str = "*") -> list[Any]:
        """
        Return all matches.

        Args:
            name (str, iterable of str): file name to search for; can be an exact file name, a glob or list of those

        Returns:
            list: all matches returned by :meth:`.search`.
        """
        return list(self.search(name))

    def first(self, name: Iterable[str] | str = "*") -> Any:
        """
        Return first match.

        Args:
            name (str, iterable of str): file name to search for; can be an exact file name, a glob or list of those

        Returns:
            object: the first match returned by :meth:`.search`.

        Raises:
            :class:`~.ResourceNotFound`: if no matches are found.
        """
        try:
            return next(iter(self.search(name)))
        except StopIteration:
            raise ResourceNotFound(f"Could not find {name} in {self}!") from None

    def chain(self, *resolvers: "AbstractResolver") -> "ResolverChain":
        """
        Return a new resolver that searches this and all given resolvers sequentially.

        You will likely want to ensure that all given resolvers yield the same types and e.g. not mix ExecutableResolver
        and ResourceResolver, but this is not checked.

        The advantage of using :meth:`.chain` rather than adding more paths to one resolver is when different paths have
        different internal sub structure, such as when combining resources from pyiron resources and conda data
        packages.  When searching for lammps potential files, e.g. we have some folders that are set up as

            <resources>/lammps/potentials/...

        but iprpy conda package that ships the NIST potentials doesn't have the lammps/potentials

            <iprpy>/...

        With chaining we can do very easily

        >>> ResourceResolver([<resources>], "lammps", "potentials").chain(
        ...     ResourceResolver([<iprpy>])) # doctest: +SKIP

        without we'd need to modify the resource paths ourselves explicitly

        >>> ResourceResolver([r + '/lammps/potentials' for r in <resources>] + [<iprpy>]) # doctest: +SKIP

        which is a bit more awkward.

        Args:
            resolvers (:class:`.AbstractResolver`): any number of sub resolvers

        Returns:
            self: if `resolvers` is empty
            :class:`.ResolverChain`: otherwise
        """
        if resolvers == ():
            return self
        return ResolverChain(self, *resolvers)


class ResolverChain(AbstractResolver):
    """
    A chain of resolvers.  Matches are returned sequentially.
    """

    __slots__ = ("_resolvers",)

    def __init__(self, *resolvers):
        """
        Args:
            *resolvers (:class:`.AbstractResolver`): sub resolvers to use
        """
        self._resolvers = resolvers

    def _search(self, name):
        for resolver in self._resolvers:
            yield from resolver.search(name)

    def __repr__(self):
        inner = ", ".join(repr(r) for r in self._resolvers)
        return f"{type(self).__name__}({inner})"


class ResourceResolver(AbstractResolver):
    """
    Generic resolver for files and directories.

    Resources are expected to conform to the following format:
        <resource_path>/<module>/<subdir0>/<subdir1>/...

    *All* entries within in this final `subdir` are yielded by :meth:`.search`, whether they are files or directories.
    Search results can be restricted by passing a (list of) globs.  If a list is given, entries matching at least one of
    them are returned.

    >>> res = ResourceResolver(..., "lammps")
    >>> res.list() # doctest: +SKIP
    [
        "bin",
        "potentials",
        "potentials.csv"
    ]
    """

    __slots__ = "_resource_paths", "_module", "_subdirs"

    def __init__(self, resource_paths, module, *subdirs):
        """
        Args:
            resource_paths (list of str): base paths for resource locations
            module (str): name of the module
            *subdirs (str): additional sub directories to descend into
        """
        self._resource_paths = resource_paths
        self._module = module
        self._subdirs = subdirs

    def __repr__(self):
        inner = repr(self._resource_paths)
        inner += f", {repr(self._module)}"
        if len(self._subdirs) > 0:
            inner += ", " + ", ".join(repr(s) for s in self._subdirs)
        return f"{type(self).__name__}({inner})"

    def _search(self, name):
        for p in self._resource_paths:
            sub = os.path.join(p, self._module, *self._subdirs)
            if os.path.exists(sub):
                for n in name:
                    yield from sorted(glob(os.path.join(sub, n)))


class ExecutableResolver(AbstractResolver):
    """
    A resolver for executable scripts.

    Executables are expected to conform to the following format:
        <resource_path>/<module>/bin/run_<code>_<version_string>.<suffix>

    and have the executable bit set. :meth:`.search` yields tuples of version strings and full paths to the executable
    instead of plain strings.

    Except on windows results are filtered to make sure all returned scripts have the executable bit set.
    When the bit is not set, a warning is printed.

    >>> exe = ExecutableResolver(..., "lammps")
    >>> exe.list() # doctest: +SKIP
    [
        ('v1', '/my/resources/lammps/bin/run_lammps_v1.sh),
        ('v1_mpi', '/my/resources/lammps/bin/run_lammps_v1_mpi.sh),
        ('v2_default', '/my/resources/lammps/bin/run_lammps_v2_default.sh),
    ]
    >>> exe.default_version # doctest: +SKIP
    "v2_default"
    >>> exe.dict("v1*") # doctest: +SKIP
    {
        'v1': '/my/resources/lammps/bin/run_lammps_v1.sh),
        'v1_mpi': '/my/resources/lammps/bin/run_lammps_v1_mpi.sh)
    }
    """

    __slots__ = "_regex", "_resolver"

    def __init__(self, resource_paths, code, module=None, suffix=EXE_SUFFIX):
        """
        Args:
            resource_paths (list of str): base paths for resource locations
            code (str): name of the simulation code
            module (str): name of the module the code is part of, same as `code` by default
            suffix (str, optional): file ending; if `None`, 'bat' on Windows 'sh' elsewhere
        """
        if suffix is None:
            suffix = EXE_SUFFIX
        if module is None:
            module = code
        self._regex = re.compile(f"run_{code}_(.*)\\.{suffix}$")
        self._glob = f"run_{code}_*.{suffix}"
        self._resolver = ResourceResolver(
            resource_paths,
            module,
            "bin",
        )

    def __repr__(self):
        inner = repr(self._resolver._resource_paths)
        inner += f", {repr(self._glob)}"
        inner += f", {repr(self._resolver._module)}"
        # recover suffix
        inner += f", {repr(self._glob.split('.')[-1])}"
        return f"{type(self).__name__}({inner})"

    def _search(self, name):
        seen = set()

        def cond(path):
            isfile = os.path.isfile(path)
            # HINT: this is always True on windows
            isexec = os.access(
                path, os.X_OK, effective_ids=os.access in os.supports_effective_ids
            )
            if isfile and not isexec:
                warnings.warn(
                    f"Found file '{path}', but skipping it because it is not executable!",
                    category=ResolverWarning,
                    # TODO: maybe used from python3.12 onwards
                    # skip_file_prefixes=(os.path.dirname(__file__),),
                    stacklevel=4,
                )
            return isfile and isexec

        for path in filter(cond, self._resolver.search(self._glob)):
            # we know that the regex has to match, because we constrain the resolver with the glob
            version = self._regex.search(path).group(1)
            if version not in seen and any(fnmatch(version, n) for n in name):
                yield (version, path)
                seen.add(version)

    def dict(self, name="*") -> dict[str, str]:
        """
        Construct dict from :meth:`.search` results.

        Args:
            name (str or list of str): glob(s) to filter the version strings

        Returns:
            dict: mapping version strings to full paths
        """
        return dict(self.search(name=name))

    @property
    def available_versions(self):
        """
        list of str: all found versions
        """
        return [x[0] for x in self.search("*")]

    @property
    def default_version(self):
        """
        str: the first version found in resources

        If a version matching `*default*` exists, the first matching is returned.

        Raises:
            :class:`.ResourceNotFound`: if no executables are found at all
        """
        try:
            return self.first("*default*")[0]
        except ResourceNotFound:
            pass
        # try again outside the except clause to avoid nested error in case this fails as well
        return self.first("*")[0]
