import unittest
from pathlib import Path
from platform import system

from pyiron_snippets.files import DirectoryObject, FileObject

class TestFiles(unittest.TestCase):
    def setUp(self):
        self.directory = DirectoryObject("test")

    def tearDown(self):
        if self.directory.exists():
            self.directory.delete()

    def test_directory_instantiation(self):
        directory = DirectoryObject(Path("test"))
        self.assertEqual(directory, self.directory)
        directory = DirectoryObject(self.directory)
        self.assertEqual(directory, self.directory)

    def test_file_instantiation(self):
        self.assertEqual(
            FileObject("test.txt", self.directory),
            FileObject("test.txt", "test"),
            msg="DirectoryObject and str must give the same object"
        )
        self.assertEqual(
            FileObject("test/test.txt"),
            FileObject("test.txt", "test"),
            msg="File path not the same as directory path"
        )

    def test_directory_exists(self):
        self.assertTrue(self.directory.exists() and self.directory.is_dir())

    def test_write(self):
        self.directory.write(file_name="test.txt", content="something")
        self.assertTrue(self.directory.file_exists("test.txt"))
        self.assertTrue(
            "test/test.txt" in [
                str(ff).replace("\\", "/")
                for ff in self.directory.list_content()['file']
            ]
        )
        self.assertEqual(len(self.directory), 1)

    def test_create_subdirectory(self):
        sub_dir = self.directory.create_subdirectory("another_test")
        self.assertTrue(sub_dir.exists() and sub_dir.is_dir())

    def test_path(self):
        f = FileObject("test.txt", self.directory)
        self.assertEqual(str(f), str(self.directory.joinpath("test.txt")))

    def test_read_and_write(self):
        f = FileObject("test.txt", self.directory)
        f.write("something")
        self.assertEqual(f.read(), "something")

    def test_is_file(self):
        f = FileObject("test.txt", self.directory)
        self.assertFalse(f.is_file())
        f.write("something")
        self.assertTrue(f.is_file())
        f.delete()
        self.assertFalse(f.is_file())

    def test_is_empty(self):
        self.assertTrue(self.directory.is_empty())
        self.directory.write(file_name="test.txt", content="something")
        self.assertFalse(self.directory.is_empty())

    def test_delete(self):
        self.assertTrue(
            self.directory.exists() and self.directory.is_dir(),
            msg="Sanity check on initial state"
        )
        self.directory.write(file_name="test.txt", content="something")
        self.directory.delete(only_if_empty=True)
        self.assertFalse(
            self.directory.is_empty(),
            msg="Flag argument on delete should have prevented removal"
        )
        self.directory.delete()
        self.assertFalse(
            self.directory.exists(),
            msg="Delete should remove the entire directory"
        )
        self.directory = DirectoryObject("test")  # Rebuild it so the tearDown works

    def test_remove(self):
        self.directory.write(file_name="test1.txt", content="something")
        self.directory.write(file_name="test2.txt", content="something")
        self.directory.write(file_name="test3.txt", content="something")
        self.assertEqual(
            3,
            len(self.directory),
            msg="Sanity check on initial state"
        )
        self.directory.remove_files("test1.txt", "test2.txt")
        self.assertEqual(
            1,
            len(self.directory),
            msg="Should be able to remove multiple files at once",
        )
        self.directory.remove_files("not even there", "nor this")
        self.assertEqual(
            1,
            len(self.directory),
            msg="Removing non-existent things should have no effect",
        )
        self.directory.remove_files("test3.txt")
        self.assertEqual(
            0,
            len(self.directory),
            msg="Should be able to remove just one file",
        )

    def test_copy(self):
        f = FileObject("test_copy.txt", self.directory)
        f.write("sam wrote this wonderful thing")
        new_file_1 = f.copy("another_test")
        self.assertEqual(new_file_1.read(), "sam wrote this wonderful thing")
        new_file_2 = f.copy("another_test", ".")
        with open("another_test", "r") as file:
            txt = file.read()
        self.assertEqual(txt, "sam wrote this wonderful thing")
        new_file_2.delete()  # needed because current directory
        new_file_3 = f.copy(str(f.parent / "another_test"), ".")
        self.assertEqual(new_file_1, new_file_3)
        new_file_4 = f.copy(directory=".")
        with open("test_copy.txt", "r") as file:
            txt = file.read()
        self.assertEqual(txt, "sam wrote this wonderful thing")
        new_file_4.delete()  # needed because current directory
        with self.assertRaises(ValueError):
            f.copy()

    def test_str(self):
        f = FileObject("test_copy.txt", self.directory)
        expected_path = str(self.directory / "test_copy.txt")
        self.assertEqual(str(f), expected_path)


if __name__ == '__main__':
    unittest.main()
