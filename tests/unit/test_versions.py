from __future__ import annotations

import collections
import dataclasses
import io
import os
import re
import sys
import unittest
from types import BuiltinMethodType, ModuleType
from unittest import mock

from pyiron_snippets.versions import (
    VersionInfo,
    VersionScrapingMap,
    get_module,
    get_qualname,
    get_version,
)


class _Dummy:
    """A class defined at module level for testing."""


def _dummy_function() -> None:
    """Module-level function for testing."""


PYTHON_VERSION = (
    f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
)


class _SyntheticPackage:
    """
    Context manager that injects a synthetic package hierarchy into sys.modules
    and cleans up on exit.

    Usage::

        with _SyntheticPackage({
            "_fakepkg":          "1.0.0",
            "_fakepkg.sub":      None,
            "_fakepkg.sub.deep": "2.0.0",
        }):
            assert versions.get_version("_fakepkg.sub.deep") == "2.0.0"
    """

    def __init__(self, modules: dict[str, str | None]):
        self._modules = modules
        self._originals: dict[str, ModuleType | None] = {}

    def __enter__(self):
        for name, ver in self._modules.items():
            self._originals[name] = sys.modules.get(name)
            mod = ModuleType(name)
            mod.__package__ = name.rsplit(".", 1)[0] if "." in name else name
            if ver is not None:
                mod.__version__ = ver
            sys.modules[name] = mod
        return self

    def __exit__(self, *exc):
        for name in reversed(list(self._modules)):
            prev = self._originals[name]
            if prev is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prev


class PathologicalMeta(type):
    """Go way out of our way to build something that fails to get a module."""
    @property
    def __module__(cls):
        raise AttributeError("no module here")


class Pathological(metaclass=PathologicalMeta):
    @property
    def __module__(self):
        raise AttributeError("no module here")


# ---------------------------------------------------------------------------
# get_module / get_qualname
# ---------------------------------------------------------------------------


class TestGetModule(unittest.TestCase):
    def test_class(self) -> None:
        self.assertEqual(get_module(_Dummy), _Dummy.__module__)

    def test_function(self) -> None:
        self.assertEqual(get_module(_dummy_function), _dummy_function.__module__)

    def test_instance(self) -> None:
        self.assertEqual(get_module(_Dummy()), _Dummy.__module__)

    def test_builtin_instance(self) -> None:
        self.assertEqual(get_module(42), "builtins")

    def test_builtin_type(self) -> None:
        self.assertEqual(get_module(int), "builtins")

    def test_instance_with_overridden_module(self) -> None:
        """
        hasattr finds __module__ on the instance __dict__, returning the override
        rather than the type's module.  Document this behaviour even if it's not ideal.
        """
        inst = _Dummy()
        inst.__module__ = "fake_module"  # type: ignore[attr-defined]
        self.assertEqual(get_module(inst), "fake_module")

    def test_module_returns_name(self) -> None:
        self.assertEqual(get_module(os), "os")

    def test_submodule_returns_dotted_name(self) -> None:
        import os.path

        self.assertEqual(get_module(os.path), os.path.__name__)

    def test_instance_methods(self) -> None:
        """C-bindings to instances can leave the module as None, so we need caution"""
        for instance, method_name in [
            ({"a": 1}, "get"),
            (collections.OrderedDict(), "move_to_end"),
            (io.BytesIO(b"hello"), "read"),
            (re.match(r".", "x"), "group"),
        ]:
            with self.subTest(instance=instance, method_name=method_name):
                method = getattr(instance, method_name)
                self.assertIsInstance(method, BuiltinMethodType)
                expected_module = type(instance).__module__
                self.assertEqual(get_module(method), expected_module)

    def test_pathologically_unmoduled_object_raises(self):
        with self.assertRaises(AttributeError) as ctx:
            get_module(Pathological())
        self.assertIn("Could not find a module", str(ctx.exception))



class TestGetQualname(unittest.TestCase):
    def test_class(self) -> None:
        self.assertEqual(get_qualname(_Dummy), "_Dummy")

    def test_function(self) -> None:
        self.assertEqual(get_qualname(_dummy_function), "_dummy_function")

    def test_instance(self) -> None:
        self.assertEqual(get_qualname(_Dummy()), "_Dummy")

    def test_builtin_type(self) -> None:
        self.assertEqual(get_qualname(int), "int")

    def test_instance_with_overridden_qualname(self) -> None:
        """
        If an instance has __qualname__ in its own __dict__, hasattr finds it and
        returns the override.
        """
        inst = _Dummy()
        inst.__qualname__ = "totally_bogus"  # type: ignore[attr-defined]
        self.assertEqual(get_qualname(inst), "totally_bogus")

    def test_module_returns_none(self) -> None:
        self.assertIsNone(get_qualname(os))


# ---------------------------------------------------------------------------
# get_version
# ---------------------------------------------------------------------------


class TestGetVersion(unittest.TestCase):
    def test_builtins(self) -> None:
        self.assertEqual(get_version("builtins"), PYTHON_VERSION)

    def test_stdlib_module_returns_python_version(self) -> None:
        self.assertEqual(get_version("os"), PYTHON_VERSION)

    def test_stdlib_submodule_returns_python_version(self) -> None:
        self.assertEqual(get_version("os.path"), PYTHON_VERSION)

    def test_submodule_uses_base(self) -> None:
        # "os.path" should look up "os", which is stdlib.
        result = get_version("os.path")
        self.assertEqual(result, PYTHON_VERSION)

    def test_custom_scraper_is_used(self) -> None:
        scraping: VersionScrapingMap = {"os": lambda _: "1.2.3"}
        self.assertEqual(get_version("os", version_scraping=scraping), "1.2.3")

    def test_custom_scraper_for_submodule(self) -> None:
        scraping: VersionScrapingMap = {"os": lambda _: "9.9.9"}
        self.assertEqual(get_version("os.path", version_scraping=scraping), "9.9.9")

    def test_custom_scraper_returning_none(self) -> None:
        scraping: VersionScrapingMap = {"os": lambda _: None}
        self.assertIsNone(get_version("os", version_scraping=scraping))

    def test_custom_scraper_overrides_stdlib(self) -> None:
        """Custom scrapers take priority over the stdlib short-circuit."""
        scraping: VersionScrapingMap = {"json": lambda _: "0.0.0"}
        self.assertEqual(get_version("json", version_scraping=scraping), "0.0.0")

    def test_module_with_dunder_version(self) -> None:
        fake_mod = mock.MagicMock()
        fake_mod.__version__ = "4.5.6"
        with mock.patch.dict("sys.modules", {"fake_pkg": fake_mod}):
            self.assertEqual(get_version("fake_pkg"), "4.5.6")

    def test_nonexistent_module_raises(self) -> None:
        with self.assertRaises(ImportError) as ctx:
            get_version("this_package_does_not_exist_abc123")
        self.assertIn("this_package_does_not_exist_abc123", str(ctx.exception))

    def test_main_module(self) -> None:
        """
        __main__ is not 'builtins', so it falls through to the normal scraper path.
        It should not raise.
        """
        result = get_version("__main__")
        self.assertIsInstance(result, (str, type(None)))


class TestGetVersionWalksModuleLevels(unittest.TestCase):
    """get_version should return the deepest (most specific) version found."""

    _HIERARCHY: dict[str, str | None] = {
        "_fakepkg": "1.0.0",
        "_fakepkg.mid": None,
        "_fakepkg.mid.deep": "2.0.0",
    }

    def setUp(self):
        self._ctx = _SyntheticPackage(self._HIERARCHY)
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__(None, None, None)

    def test_returns_deepest_version_when_present(self):
        self.assertEqual(get_version("_fakepkg.mid.deep"), "2.0.0")

    def test_walks_up_when_intermediate_has_no_version(self):
        self.assertEqual(get_version("_fakepkg.mid"), "1.0.0")

    def test_top_level_returns_own_version(self):
        self.assertEqual(get_version("_fakepkg"), "1.0.0")


class TestGetVersionWalkAllUnversioned(unittest.TestCase):
    """When no level has a version, get_version should return None."""

    def test_returns_none(self):
        with _SyntheticPackage({"_nover": None, "_nover.sub": None}):
            self.assertIsNone(get_version("_nover.sub"))


class TestGetVersionWalkMiddleOnly(unittest.TestCase):
    """When only an intermediate level has a version, that version wins."""

    _HIERARCHY: dict[str, str | None] = {
        "_midver": None,
        "_midver.sub": "3.0.0",
        "_midver.sub.leaf": None,
    }

    def test_leaf_walks_up_to_middle(self):
        with _SyntheticPackage(self._HIERARCHY):
            self.assertEqual(get_version("_midver.sub.leaf"), "3.0.0")

    def test_middle_returns_own(self):
        with _SyntheticPackage(self._HIERARCHY):
            self.assertEqual(get_version("_midver.sub"), "3.0.0")

    def test_top_returns_none(self):
        with _SyntheticPackage(self._HIERARCHY):
            self.assertIsNone(get_version("_midver"))


class TestGetVersionWalkWithScrapingMap(unittest.TestCase):
    """version_scraping keys should match at the corresponding recursion level."""

    def test_scraper_used_at_matching_level(self):
        with _SyntheticPackage({"_scr": None, "_scr.sub": None}):
            scraping = {"_scr": lambda _: "99.0.0"}
            self.assertEqual(
                get_version("_scr.sub", version_scraping=scraping),
                "99.0.0",
            )

    def test_submodule_scraper_takes_precedence(self):
        with _SyntheticPackage({"_scr2": None, "_scr2.sub": None}):
            scraping = {
                "_scr2": lambda _: "1.0.0",
                "_scr2.sub": lambda _: "2.0.0",
            }
            self.assertEqual(
                get_version("_scr2.sub", version_scraping=scraping),
                "2.0.0",
            )

    def test_dunder_version_at_leaf_beats_scraper_at_parent(self):
        with _SyntheticPackage({"_scr3": None, "_scr3.sub": "5.0.0"}):
            scraping = {"_scr3": lambda _: "1.0.0"}
            self.assertEqual(
                get_version("_scr3.sub", version_scraping=scraping),
                "5.0.0",
            )


# ---------------------------------------------------------------------------
# VersionInfo
# ---------------------------------------------------------------------------


class TestVersionInfoFrozen(unittest.TestCase):
    def test_is_frozen(self) -> None:
        info = VersionInfo(module="builtins", qualname="int", version="3.12.0")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            info.module = "other"  # type: ignore[misc]


class TestVersionInfoOf(unittest.TestCase):
    def test_class(self) -> None:
        info = VersionInfo.of(_Dummy)
        self.assertEqual(info.module, _Dummy.__module__)
        self.assertEqual(info.qualname, "_Dummy")

    def test_instance(self) -> None:
        info = VersionInfo.of(_Dummy())
        self.assertEqual(info.qualname, "_Dummy")

    def test_function(self) -> None:
        info = VersionInfo.of(_dummy_function)
        self.assertEqual(info.qualname, "_dummy_function")

    def test_builtin_instance(self) -> None:
        info = VersionInfo.of(42)
        self.assertEqual(info.module, "builtins")
        self.assertEqual(info.qualname, "int")
        self.assertIsNotNone(info.version)

    def test_builtin_type(self) -> None:
        info = VersionInfo.of(int)
        self.assertEqual(info.module, "builtins")
        self.assertEqual(info.qualname, "int")
        self.assertIsNotNone(info.version)

    # -- modules ------------------------------------------------------------

    def test_module(self) -> None:
        info = VersionInfo.of(os)
        self.assertEqual(info.module, "os")
        self.assertIsNone(info.qualname)
        self.assertEqual(info.version, PYTHON_VERSION)

    def test_third_party_module(self) -> None:
        """A non-stdlib module with __version__ should report it."""
        fake_mod = mock.MagicMock()
        fake_mod.__name__ = "fake_pkg"
        fake_mod.__version__ = "1.2.3"
        # ModuleType check needs a real module; patch the relevant bits.
        import types

        mod = types.ModuleType("fake_pkg")
        mod.__version__ = "1.2.3"  # type: ignore[attr-defined]
        with mock.patch.dict("sys.modules", {"fake_pkg": mod}):
            info = VersionInfo.of(mod)
        self.assertEqual(info.module, "fake_pkg")
        self.assertIsNone(info.qualname)
        self.assertEqual(info.version, "1.2.3")

    # -- forbid_main --------------------------------------------------------

    def test_forbid_main_raises(self) -> None:
        obj = mock.MagicMock(spec=type)
        obj.__module__ = "__main__"
        obj.__qualname__ = "Foo"
        with self.assertRaises(ValueError, msg="__main__"):
            VersionInfo.of(obj, forbid_main=True)

    def test_forbid_main_false_allows_main(self) -> None:
        obj = mock.MagicMock(spec=type)
        obj.__module__ = "__main__"
        obj.__qualname__ = "Foo"
        info = VersionInfo.of(obj, forbid_main=False)
        self.assertEqual(info.module, "__main__")

    # -- forbid_locals ------------------------------------------------------

    def test_forbid_locals_raises(self) -> None:
        def _make_local() -> type:
            class _Local:
                pass

            return _Local

        local_cls = _make_local()
        self.assertIn("<locals>", local_cls.__qualname__)
        with self.assertRaises(ValueError, msg="<locals>"):
            VersionInfo.of(local_cls, forbid_locals=True)

    def test_forbid_locals_false_allows_locals(self) -> None:
        def _make_local() -> type:
            class _Local:
                pass

            return _Local

        local_cls = _make_local()
        info = VersionInfo.of(local_cls, forbid_locals=False)
        self.assertIn("<locals>", info.qualname)

    def test_forbid_locals_ok_for_module(self) -> None:
        """forbid_locals should not crash when qualname is None (modules)."""
        info = VersionInfo.of(os, forbid_locals=True)
        self.assertIsNone(info.qualname)

    # -- require_version ----------------------------------------------------

    def test_require_version_raises_when_missing(self) -> None:
        fake_obj = mock.MagicMock(spec=type)
        fake_obj.__module__ = "os"
        fake_obj.__qualname__ = "FakeObj"
        # os is now stdlib so it *has* a version; use a non-stdlib fake instead.
        fake_mod = mock.MagicMock()
        del fake_mod.__version__
        fake_obj.__module__ = "no_version_pkg"
        with (
            mock.patch.dict("sys.modules", {"no_version_pkg": fake_mod}),
            self.assertRaises(ValueError, msg="could not be found"),
        ):
            VersionInfo.of(fake_obj, require_version=True)

    def test_require_version_ok_when_present(self) -> None:
        info = VersionInfo.of(42, require_version=True)
        self.assertIsNotNone(info.version)

    # -- version_scraping ---------------------------------------------------

    def test_version_scraping_passed_through(self) -> None:
        module_base = _Dummy.__module__.split(".")[0]
        scraping: VersionScrapingMap = {
            module_base: lambda _: "0.0.1",
        }
        info = VersionInfo.of(_Dummy, version_scraping=scraping)
        self.assertEqual(info.version, "0.0.1")


class TestFullyQualifiedName(unittest.TestCase):
    def test_basic(self) -> None:
        info = VersionInfo(module="foo.bar", qualname="Baz", version=None)
        self.assertEqual(info.fully_qualified_name, "foo.bar.Baz")

    def test_from_real_class(self) -> None:
        info = VersionInfo.of(_Dummy)
        self.assertEqual(info.fully_qualified_name, f"{_Dummy.__module__}._Dummy")

    def test_nested_qualname(self) -> None:
        info = VersionInfo(module="m", qualname="Outer.Inner", version=None)
        self.assertEqual(info.fully_qualified_name, "m.Outer.Inner")

    def test_module_fqn_is_just_module(self) -> None:
        info = VersionInfo.of(os)
        self.assertEqual(info.fully_qualified_name, "os")


if __name__ == "__main__":
    unittest.main()
