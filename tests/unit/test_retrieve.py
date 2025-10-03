import importlib
import pathlib
import shutil
import sys
import textwrap
import unittest

from pyiron_snippets import retrieve, singleton


class SomeClass: ...


class TestImportFromString(unittest.TestCase):
    """Test cases for import_from_string function."""

    def setUp(self):
        """Add static test files to path for testing."""
        self.static_path = pathlib.Path(__file__).parent.parent / "static"
        if str(self.static_path) not in sys.path:
            sys.path.insert(0, str(self.static_path))

    def tearDown(self):
        """Clean up sys.path and modules."""
        if str(self.static_path) in sys.path:
            sys.path.remove(str(self.static_path))
        keys_to_remove = [k for k in sys.modules if k.startswith("test_module")]
        for key in keys_to_remove:
            del sys.modules[key]

    def test_import_builtin_module(self):
        """Test importing a standard library module."""
        result = retrieve.import_from_string("os")
        import os

        self.assertIs(result, os)

    def test_import_builtin_function(self):
        """Test importing a function from standard library."""
        result = retrieve.import_from_string("os.path.join")
        from os.path import join

        self.assertIs(result, join)

    def test_import_builtin_class(self):
        """Test importing a class from standard library."""
        result = retrieve.import_from_string("pathlib.Path")
        from pathlib import Path

        self.assertIs(result, Path)

    def test_import_nested_attribute(self):
        """Test importing deeply nested attributes."""
        result = retrieve.import_from_string("unittest.TestCase.assertEqual")
        self.assertEqual(result, unittest.TestCase.assertEqual)

    def test_import_from_pyiron_snippets(self):
        """Test importing from the pyiron_snippets package itself."""
        result = retrieve.import_from_string("pyiron_snippets.singleton.Singleton")
        self.assertIs(result, singleton.Singleton)

    def test_import_nonexistent_module(self):
        """Test that importing non-existent module raises ModuleNotFoundError."""
        with self.assertRaises(ModuleNotFoundError) as cm:
            retrieve.import_from_string("nonexistent_module")
        self.assertIn("nonexistent_module", str(cm.exception))
        self.assertIn("PYTHONPATH", str(cm.exception))

    def test_import_nonexistent_attribute(self):
        """Test that importing non-existent attribute raises AttributeError."""
        with self.assertRaises(ModuleNotFoundError) as cm:
            retrieve.import_from_string("os.nonexistent_attr")
        self.assertIn("nonexistent_attr", str(cm.exception))

    def test_import_empty_string(self):
        """Test edge case with empty string."""
        with self.assertRaises(ValueError):
            retrieve.import_from_string("")

    def test_import_single_name(self):
        """Test importing just a module name without any dots."""
        result = retrieve.import_from_string("sys")
        import sys

        self.assertIs(result, sys)

    def test_import_from_uninitialized_submodule(self):
        """Test importing from a submodule that hasn't been initialized yet."""
        test_pkg_dir = self.static_path / "test_module_uninit"
        test_pkg_dir.mkdir(parents=True, exist_ok=True)

        (test_pkg_dir / "__init__.py").write_text("")

        submodule_content = textwrap.dedent(
            """
            class UnInitClass:
                value = 42
            """
        ).strip()
        (test_pkg_dir / "submodule.py").write_text(submodule_content)

        try:
            uninitialized = importlib.import_module("test_module_uninit")
            self.assertNotIn("submodule", dir(uninitialized))
            result = retrieve.import_from_string(
                "test_module_uninit.submodule.UnInitClass"
            )
            self.assertEqual(
                result.value,
                42,
                msg="Even with an unitialized submodule, the class value still be importable",
            )
        finally:
            shutil.rmtree(test_pkg_dir)

    def test_import_class_method(self):
        """Test importing a method from a class."""
        result = retrieve.import_from_string("pathlib.Path.exists")
        from pathlib import Path

        self.assertEqual(result, Path.exists)

    def test_nonsense(self):
        with self.assertRaises(ValueError):
            retrieve.import_from_string("")

        with self.assertRaises(ValueError):
            retrieve.import_from_string(42)


class TestGetImportableStringFromStringReduction(unittest.TestCase):
    """Test cases for get_importable_string_from_string_reduction function."""

    def test_already_importable_string(self):
        """Test with a string that's already importable."""
        obj = pathlib.Path(".")
        result = retrieve.get_importable_string_from_string_reduction(
            "pathlib.Path", obj
        )
        self.assertEqual(result, "pathlib.Path")

    def test_needs_module_scoping(self):
        """Test with a string that needs module scoping."""
        # Using this test class as an example
        obj = SomeClass()
        # If we just provide the class name, it should scope with module
        result = retrieve.get_importable_string_from_string_reduction("SomeClass", obj)
        self.assertIn(
            result,
            ["unit.test_retrieve.SomeClass", "test_retrieve.SomeClass"],
            msg="Note that the unit test folder has an __init__.py file, and is may "
            "be interpreted as part of the module path, so either result is possible",
        )

    def test_singleton_reduction(self):
        """Test the singleton use case mentioned in docstring."""

        class TestSingleton(metaclass=singleton.Singleton): ...

        obj = TestSingleton()
        # Simulating what pickle might return for a singleton
        # Since TestSingleton is local to this test, we need to handle it carefully
        with self.assertRaises(retrieve.StringNotImportableError):
            retrieve.get_importable_string_from_string_reduction(
                "NonExistentSingleton", obj
            )

    def test_invalid_reduction_string(self):
        """Test with a completely invalid reduction string."""
        obj = SomeClass()
        with self.assertRaises(retrieve.StringNotImportableError) as cm:
            retrieve.get_importable_string_from_string_reduction(
                "this_is_not_a_reduction", obj
            )
        self.assertIn("this_is_not_a_reduction", str(cm.exception))
        self.assertIn("edge case", str(cm.exception))

    def test_reduction_with_nested_class(self):
        """Test reduction with a nested class."""

        class OuterClass:
            class InnerClass:
                pass

        obj = OuterClass.InnerClass()
        with self.assertRaises(
            retrieve.StringNotImportableError,
            msg="This should raise an error because <locals> objects aren't "
            "importable",
        ):
            retrieve.get_importable_string_from_string_reduction(
                "InnerClass",
                obj,
            )

    def test_reduction_from_stdlib(self):
        """Test reduction from standard library objects."""
        from collections import OrderedDict

        obj = OrderedDict()
        result = retrieve.get_importable_string_from_string_reduction(
            "collections.OrderedDict", obj
        )
        self.assertEqual(result, "collections.OrderedDict")

    def test_reduction_from_builtin_type(self):
        """Test reduction from built-in objects."""
        result = retrieve.get_importable_string_from_string_reduction("int", int)
        self.assertEqual(result, "builtins.int")

    def test_object_without_module_attribute(self):
        """Test with an object that doesn't have __module__ attribute."""
        with self.assertRaises(
            AttributeError, msg="1.__module__ should raise an error"
        ):
            retrieve.get_importable_string_from_string_reduction(
                "ints have no module", 1
            )


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for real-world scenarios."""

    def setUp(self):
        """Set up test environment."""
        self.static_path = pathlib.Path(__file__).parent.parent / "static"
        if str(self.static_path) not in sys.path:
            sys.path.insert(0, str(self.static_path))

    def tearDown(self):
        """Clean up test environment."""
        if str(self.static_path) in sys.path:
            sys.path.remove(str(self.static_path))
        keys_to_remove = [k for k in sys.modules if k.startswith("test_package")]
        for key in keys_to_remove:
            del sys.modules[key]

    def test_complex_package_structure(self):
        """Test with a complex package structure."""
        # Create a test package structure
        pkg_dir = self.static_path / "test_package_complex"
        sub_pkg_dir = pkg_dir / "subpackage"
        sub_pkg_dir.mkdir(parents=True, exist_ok=True)

        (pkg_dir / "__init__.py").write_text(
            "from .module1 import Class1\n__all__ = ['Class1']"
        )
        (sub_pkg_dir / "__init__.py").write_text("")

        (pkg_dir / "module1.py").write_text(
            textwrap.dedent(
                """
                class Class1:
                    value = 'from_module1'
                """
            ).strip()
        )

        (sub_pkg_dir / "module2.py").write_text(
            textwrap.dedent(
                """
                class Class2:
                    value = 'from_module2'
        
                    class NestedClass:
                        nested_value = 'nested'
                """
            ).strip()
        )

        try:
            result1 = retrieve.import_from_string("test_package_complex.Class1")
            self.assertEqual(result1.value, "from_module1")

            result2 = retrieve.import_from_string("test_package_complex.module1.Class1")
            self.assertEqual(result2.value, "from_module1")

            result3 = retrieve.import_from_string(
                "test_package_complex.subpackage.module2.Class2"
            )
            self.assertEqual(result3.value, "from_module2")

            result4 = retrieve.import_from_string(
                "test_package_complex.subpackage.module2.Class2.NestedClass"
            )
            self.assertEqual(result4.nested_value, "nested")

        finally:
            shutil.rmtree(pkg_dir)

    def test_circular_import_handling(self):
        """Test that circular imports are handled gracefully."""
        pkg_dir = self.static_path / "test_circular"
        pkg_dir.mkdir(parents=True, exist_ok=True)

        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "module_a.py").write_text(
            textwrap.dedent(
                """
                from .module_b import ClassB
        
                class ClassA:
                    related = ClassB
                    value = 'A'
                """
            ).strip()
        )
        (pkg_dir / "module_b.py").write_text(
            textwrap.dedent(
                """
                class ClassB:
                    value = 'B'
        
                # Circular import:
                from .module_a import ClassA
                """
            ).strip()
        )

        try:
            with self.assertRaises(ImportError, msg="Circular imports never work"):
                retrieve.import_from_string("test_circular.module_a.ClassA")

        finally:
            shutil.rmtree(pkg_dir)


if __name__ == "__main__":
    unittest.main()
