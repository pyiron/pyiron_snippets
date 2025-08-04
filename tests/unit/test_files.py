import pickle
import tarfile
import unittest
from pathlib import Path

from pyiron_snippets.files import DirectoryObject


class TestFiles(unittest.TestCase):
    def setUp(self):
        self.directory = DirectoryObject("test")

    def tearDown(self):
        self.directory.delete()

    def test_directory_instantiation(self):
        directory = DirectoryObject(Path("test"))
        self.assertEqual(directory.path, self.directory.path)
        directory = DirectoryObject(self.directory)
        self.assertEqual(directory.path, self.directory.path)

    def test_directory_exists(self):
        self.assertTrue(Path("test").exists() and Path("test").is_dir())

    def test_write(self):
        self.directory.write(file_name="test.txt", content="something")
        self.assertTrue(self.directory.file_exists("test.txt"))
        self.assertTrue(
            "test/test.txt"
            in [ff.replace("\\", "/") for ff in self.directory.list_content()["file"]]
        )
        self.assertEqual(len(self.directory), 1)

    def test_del(self):
        self.directory = DirectoryObject("something")
        self.assertTrue(Path("something").exists())
        self.directory = None
        self.assertFalse(Path("something").exists())
        self.directory = DirectoryObject("something")
        self.assertTrue(Path("something").exists())
        _ = pickle.dumps(self.directory)
        self.directory = DirectoryObject("something_else")
        self.assertTrue(Path("something").exists())
        self.directory = DirectoryObject("something")

    def test_create_subdirectory(self):
        _ = self.directory.create_subdirectory("another_test")
        self.assertTrue(Path("test/another_test").exists())

    def test_is_empty(self):
        self.assertTrue(self.directory.is_empty())
        self.directory.write(file_name="test.txt", content="something")
        self.assertFalse(self.directory.is_empty())

    def test_delete(self):
        self.assertTrue(
            Path("test").exists() and Path("test").is_dir(),
            msg="Sanity check on initial state",
        )
        self.directory.write(file_name="test.txt", content="something")
        self.directory.delete(only_if_empty=True)
        self.assertFalse(
            self.directory.is_empty(),
            msg="Flag argument on delete should have prevented removal",
        )
        self.directory.delete()
        self.assertFalse(
            Path("test").exists(), msg="Delete should remove the entire directory"
        )
        self.directory = DirectoryObject("test")  # Rebuild it so the tearDown works

    def test_remove(self):
        self.directory.write(file_name="test1.txt", content="something")
        self.directory.write(file_name="test2.txt", content="something")
        self.directory.write(file_name="test3.txt", content="something")
        self.assertEqual(3, len(self.directory), msg="Sanity check on initial state")
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

    def test_compress(self):
        self.directory.write(file_name="test1.txt", content="something")
        self.directory.write(file_name="test2.txt", content="something")
        self.directory.compress(exclude_files=["test1.txt"])
        self.assertTrue(Path("test.tar.gz").exists())
        with tarfile.open("test.tar.gz", "r:*") as f:
            content = [name for name in f.getnames()]
            self.assertNotIn(
                "test1.txt", content, msg="Excluded file should not be in archive"
            )
            self.assertIn(
                "test2.txt", content, msg="Included file should be in archive"
            )
        self.assertFalse(
            self.directory.file_exists("test2.txt"),
            msg="Compressed files should not be in the directory",
        )
        self.assertTrue(
            self.directory.file_exists("test1.txt"),
            msg="Excluded file should still be in the directory",
        )
        # Test that compressing again does not raise an error
        self.directory.compress()
        self.assertTrue(Path("test.tar.gz").exists())
        while Path("test.tar.gz").exists():
            Path("test.tar.gz").unlink()


if __name__ == "__main__":
    unittest.main()
