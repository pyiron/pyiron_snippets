import os
import unittest

from pyiron_snippets.directory_context import set_directory


class TestContextDirectory(unittest.TestCase):
    def test_set_directory(self):
        current_directory = os.getcwd()
        test_directory = "context"
        with set_directory(path=test_directory):
            context_directory = os.getcwd()
        self.assertEqual(
            os.path.relpath(context_directory, current_directory), test_directory
        )


if __name__ == "__main__":
    unittest.main()
