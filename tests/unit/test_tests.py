import unittest
import pyiron_snippets


class TestVersion(unittest.TestCase):
    def test_version(self):
        version = pyiron_snippets.__version__
        print(version)
        self.assertTrue(version.startswith('0'))
