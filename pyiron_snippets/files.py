from __future__ import annotations

import shutil
from pathlib import Path


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
    if not folder_path.is_dir():
        return {}
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


class DirectoryObject:
    def __init__(self, directory: str | Path | DirectoryObject):
        if isinstance(directory, str):
            self.path = Path(directory)
        elif isinstance(directory, Path):
            self.path = directory
        elif isinstance(directory, DirectoryObject):
            self.path = directory.path
        self.create()
        self._protected = False

    def __getstate__(self):
        self._protected = True
        return super().__getstate__()

    def __del__(self):
        if not self._protected:
            self.delete(only_if_empty=False)

    def create(self):
        self.path.mkdir(parents=True, exist_ok=True)

    def delete(self, only_if_empty: bool = False):
        if self.is_empty() or not only_if_empty:
            delete_files_and_directories_recursively(self.path)

    def list_content(self):
        return categorize_folder_items(self.path)

    def __len__(self):
        return sum([len(cc) for cc in self.list_content().values()])

    def __repr__(self):
        return f"DirectoryObject(directory='{self.path}')\n{self.list_content()}"

    def get_path(self, file_name):
        return self.path / file_name

    def file_exists(self, file_name):
        return self.get_path(file_name).is_file()

    def write(self, file_name, content, mode="w"):
        with self.get_path(file_name).open(mode=mode) as f:
            f.write(content)

    def create_subdirectory(self, path):
        return DirectoryObject(self.path / path)

    def is_empty(self) -> bool:
        return len(self) == 0

    def remove_files(self, *files: str):
        for file in files:
            path = self.get_path(file)
            if path.is_file():
                path.unlink()
