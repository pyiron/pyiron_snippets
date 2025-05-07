import os
import unittest
from pyiron_snippets.tempenv import TemporaryEnvironment


class TestTemporaryEnvironment(unittest.TestCase):
    """
    Class to test TemporaryEnvironment context manager.
    """

    def setUp(self):
        """Ensures the original environment is kept intact before each test."""
        self.old_environ = dict(os.environ)

    def tearDown(self):
        """Ensures the original environment is restored after each test."""
        os.environ.clear()
        os.environ.update(self.old_environ)

    def test_value_int(self):
        """Should correctly convert and store integer values as strings."""
        with TemporaryEnvironment(FOO=12):
            self.assertEqual(
                os.environ.get("FOO"), "12", "Failed to convert integer to string"
            )

    def test_value_bool(self):
        """Should correctly convert and store boolean values as strings."""
        with TemporaryEnvironment(FOO=True):
            self.assertEqual(
                os.environ.get("FOO"), "True", "Failed to convert boolean to string"
            )

    def test_environment_set(self):
        """Should correctly set environment variables inside its scope."""
        with TemporaryEnvironment(FOO="1", BAR="2"):
            self.assertEqual(os.environ.get("FOO"), "1", "Failed to set FOO")
            self.assertEqual(os.environ.get("BAR"), "2", "Failed to set BAR")

    def test_environment_restored(self):
        """Should restore original environment variables state after leaving its scope."""
        os.environ["FOO"] = "0"
        with TemporaryEnvironment(FOO="1"):
            self.assertEqual(os.environ.get("FOO"), "1")
        self.assertEqual(
            os.environ.get("FOO"), "0", "Failed to restore original FOO value"
        )

    def test_environment_deleted(self):
        """Should correctly delete environment variables that didn't exist originally after leaving its scope."""
        with TemporaryEnvironment(FOO="1"):
            self.assertEqual(os.environ.get("FOO"), "1")
        self.assertIsNone(os.environ.get("FOO"), "Failed to delete FOO")

    def test_raise_exception(self):
        """Should restore original environment after handling an exception within its scope."""
        os.environ["FOO"] = "0"
        try:
            with TemporaryEnvironment(FOO="1"):
                self.assertEqual(os.environ.get("FOO"), "1")
                raise Exception("Some Error")
        except:
            self.assertEqual(
                os.environ.get("FOO"),
                "0",
                "Failed to restore environment after exception",
            )

    def test_as_decorator(self):
        """Should correctly set and restore environment variables when used as a decorator."""

        @TemporaryEnvironment(FOO="1")
        def test_func():
            return os.environ.get("FOO")

        self.assertEqual(test_func(), "1", "Failed to set environment as decorator")
        self.assertEqual(
            os.environ.get("FOO", None),
            None,
            "Failed to restore environment as decorator",
        )


if __name__ == "__main__":
    unittest.main()
