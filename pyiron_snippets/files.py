from __future__ import annotations

from pathlib import Path, PosixPath, WindowsPath
import shutil
import sys

# Determine the correct base class based on the platform
BasePath = WindowsPath if sys.platform == "win32" else PosixPath


def delete_files_and_directories_recursively(path):
    if not path.exists():
        return
    for item in path.rglob("*"):
        if item.is_file():
            item.unlink()
        else:
            delete_files_and_directories_recursively(item)
    path.rmdir()


def categorize_folder_items(folder_path):
    types = [
        "dir",
        "file",
        "mount",
        "symlink",
        "block_device",
        "char_device",
        "fifo",
        "socket",
    ]
    results = {t: [] for t in types}

    for item in folder_path.iterdir():
        for tt in types:
            try:
                if getattr(item, f"is_{tt}")():
                    results[tt].append(str(item))
            except NotImplementedError:
                pass
    return results


class DirectoryObject(BasePath):
    def __new__(cls, *args, **kwargs):
        # Create an instance of PosixPath or WindowsPath depending on the platform
        instance = super().__new__(cls, *args, **kwargs)
        instance.create()
        return instance

    def create(self):
        self.mkdir(parents=True, exist_ok=True)

    def delete(self, only_if_empty: bool = False):
        if self.is_empty() or not only_if_empty:
            delete_files_and_directories_recursively(self)

    def list_content(self):
        return categorize_folder_items(self)

    def __len__(self):
        return sum([len(cc) for cc in self.list_content().values()])

    def __repr__(self):
        return f"DirectoryObject(directory='{self}')\n{self.list_content()}"

    def file_exists(self, file_name):
        return self.joinpath(file_name).is_file()

    def write(self, file_name, content, mode="w"):
        with self.joinpath(file_name).open(mode=mode) as f:
            f.write(content)

    def create_subdirectory(self, path):
        return DirectoryObject(self.joinpath(path))

    def create_file(self, file_name):
        return FileObject(file_name, self)

    def is_empty(self) -> bool:
        return len(self) == 0

    def remove_files(self, *files: str):
        for file in files:
            path = self.joinpath(file)
            if path.is_file():
                path.unlink()


class NoDestinationError(ValueError):
    """A custom error for when neither a new file name nor new location are provided"""


class FileObject(BasePath):
    def __new__(cls, file_name: str, directory: DirectoryObject = None):
        # Resolve the full path of the file
        if directory is None:
            full_path = Path(file_name)
        else:
            if isinstance(directory, str):
                directory = DirectoryObject(directory)
            full_path = directory.joinpath(file_name)
        instance = super().__new__(cls, full_path)
        return instance

    def write(self, content, mode="x"):
        with self.open(mode=mode) as f:
            f.write(content)

    def read(self, mode="r"):
        with self.open(mode=mode) as f:
            return f.read()

    def is_file(self):
        return self.exists() and super().is_file()

    def delete(self):
        self.unlink()

    def copy(
        self,
        new_file_name: str | None = None,
        directory: DirectoryObject | str | None = None,
    ):
        if new_file_name is None and directory is None:
            raise NoDestinationError(
                "Either new file name or directory must be specified"
            )

        if new_file_name is None:
            new_file_name = self.name

        if directory is None:
            directory = self.parent
        elif isinstance(directory, str):
            directory = DirectoryObject(directory)

        new_file = directory.joinpath(new_file_name)
        shutil.copy(str(self), str(new_file))
        return FileObject(new_file_name, DirectoryObject(directory))
