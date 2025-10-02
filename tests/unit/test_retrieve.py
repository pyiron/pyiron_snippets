import unittest

from pyiron_snippets import retrieve


class SomeClass: ...


class TestRetrieve(unittest.TestCase):
    def test_get_importable_string_from_string_reduction(self):
        obj = SomeClass()
        with self.assertRaises(retrieve.StringNotImportableError):
            retrieve.get_importable_string_from_string_reduction(
                "this_is_not_a_reduction", obj
            )
