from __future__ import annotations

import hashlib
import tarfile
import uuid
from pathlib import Path
from typing import cast


def delete_files_and_directories_recursively(path: Path) -> None:
    """Recursively delete all files and subdirectories under ``path``, then remove ``path`` itself.

    Args:
        path (Path): The root directory to delete.
    """
    if not path.exists():
        return
    for item in path.rglob("*"):
        if item.is_file():
            item.unlink()
        else:
            delete_files_and_directories_recursively(item)
    path.rmdir()


def categorize_folder_items(folder_path: Path) -> dict[str, list[str]]:
    """Categorize all items in a directory by their filesystem type.

    Args:
        folder_path (Path): The directory to inspect.

    Returns:
        dict[str, list[str]]: A mapping from type name (e.g. ``"file"``, ``"dir"``,
            ``"symlink"``) to a list of absolute string paths belonging to that type.
            Returns an empty dict if ``folder_path`` is not a directory.
    """
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
    results: dict[str, list[str]] = {t: [] for t in types}

    for item in folder_path.iterdir():
        for tt in types:
            try:
                if getattr(item, f"is_{tt}")():
                    results[tt].append(str(item))
            except NotImplementedError:
                pass
    return results


class DirectoryObject:
    """
    A class to represent a directory object that can be created, deleted,
    and managed. It can also compress and decompress its contents.
    It supports unique directory generation and can be protected from deletion
    on garbage collection.
    """

    def __init__(
        self,
        directory: str | Path | DirectoryObject | None = None,
        generate_unique_directory: bool | None = None,
        protected: bool | None = None,
    ):
        """
        Initialize a DirectoryObject.

        Args:
            directory (str | Path | DirectoryObject | None): The directory path or
                DirectoryObject instance. If None, a unique directory is created.
            generate_unique_directory (bool | None): If True, generates a unique
                subdirectory name under ``directory``.
            protected (bool | None): If True, prevents deletion of the
                directory object on garbage collection. If None, it defaults to
                True if the directory already exists.
        """
        if directory is None:
            path = Path(f"data_{uuid.uuid4().hex}")
        elif isinstance(directory, str):
            path = Path(directory)
        elif isinstance(directory, Path):
            path = directory
        elif isinstance(directory, DirectoryObject):
            path = directory.path
        else:
            raise TypeError(
                "directory must be str, pathlib.Path, DirectoryObject, or None"
            )
        if generate_unique_directory and directory is not None:
            path = path / f"data_{uuid.uuid4().hex}"
        if protected is None:
            protected = path.exists()
        self._protected = protected
        self.path: Path = path
        self.create()

    def __getstate__(self) -> object:
        """Protect the directory from deletion when pickling."""
        self._protected = True
        return self.path.__getstate__()

    def __del__(self) -> None:
        """Delete the directory on garbage collection unless protected."""
        if not self._protected:
            self.delete(only_if_empty=False)

    def create(self) -> None:
        """Create the directory (and any missing parents) if it does not already exist."""
        self.path.mkdir(parents=True, exist_ok=True)

    def delete(self, only_if_empty: bool = False) -> None:
        """Delete the directory and all its contents.

        Args:
            only_if_empty (bool): If True, only delete when the directory is empty.
        """
        if self.is_empty() or not only_if_empty:
            delete_files_and_directories_recursively(self.path)

    def list_content(self) -> dict[str, list[str]]:
        """Return a categorized listing of the directory's contents.

        Returns:
            dict[str, list[str]]: See :func:`categorize_folder_items`.
        """
        return categorize_folder_items(self.path)

    def __len__(self) -> int:
        """Return the total number of items in the directory across all types."""
        return sum([len(cc) for cc in self.list_content().values()])

    def __repr__(self) -> str:
        """Return a human-readable representation showing the path and contents."""
        return f"DirectoryObject(directory='{self.path}')\n{self.list_content()}"

    def get_path(self, file_name: str | Path) -> Path:
        """Return the full path for a file name relative to this directory.

        Args:
            file_name (str | Path): The relative file name or sub-path.

        Returns:
            Path: Absolute path within the directory.
        """
        return self.path / file_name

    def file_exists(self, file_name: str | Path) -> bool:
        """Check whether a file exists inside this directory.

        Args:
            file_name (str | Path): The relative file name or sub-path.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        return self.get_path(file_name).is_file()

    def dump(
        self,
        content: str,
        file_name: str | Path | None = None,
        mode: str = "w",
    ) -> Path:
        """
        Write content to a file and return the file path.

        Args:
            content (str): The content to write.
            file_name (str | Path | None): The file name. If None, a name is generated
                from a hash of the content.
            mode (str): The file opening mode.

        Returns:
            Path: The path of the written file.
        """
        if file_name is None:
            file_name = (
                "file_" + hashlib.sha256(content.encode()).hexdigest()[:16] + ".dat"
            )
        path = self.get_path(file_name)
        base = self.path.resolve()
        if not path.resolve().is_relative_to(base):
            raise ValueError("file_name must resolve within the directory")
        with path.open(mode=mode) as f:
            f.write(content)
        return path

    def write(self, file_name, content, mode="w"):
        """
        .. deprecated::
            Use :meth:`dump` instead.
        """
        import warnings

        warnings.warn(
            "DirectoryObject.write is deprecated, use dump instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.dump(content=content, file_name=file_name, mode=mode)

    def create_subdirectory(self, path: str | Path | None = None) -> DirectoryObject:
        """Create and return a subdirectory inside this directory.

        Args:
            path (str | Path | None): Relative path for the subdirectory. If None,
                a unique name is generated automatically.

        Returns:
            DirectoryObject: The newly created subdirectory.
        """
        if path is None:
            new_path = self.path / f"subdir_{uuid.uuid4().hex}"
        else:
            new_path = self.path / path
        return DirectoryObject(new_path)

    def is_empty(self) -> bool:
        """Return True if the directory contains no items."""
        return len(self) == 0

    def remove_files(self, *files: str) -> None:
        """Remove one or more files from this directory.

        Silently ignores names that do not correspond to an existing file.

        Args:
            *files (str): Relative file names to remove.
        """
        for file in files:
            path = self.get_path(file)
            if path.is_file():
                path.unlink()

    def compress(self, exclude_files: list[str | Path] | None = None) -> None:
        """Compress the directory contents into a ``<name>.tar.gz`` archive.

        Files included in the archive are removed from the directory afterwards.
        If the archive already exists, the method returns without doing anything.

        Args:
            exclude_files (list[str | Path] | None): Files to keep on disk and
                omit from the archive. Paths may be absolute or relative to the
                directory.
        """
        directory = self.path.resolve()
        output_tar_path = directory.with_suffix(".tar.gz")
        if output_tar_path.exists():
            return
        if exclude_files is None:
            exclude_files = []
        else:
            exclude_files = [Path(f) for f in exclude_files]
        exclude_set = {
            f.resolve() if f.is_absolute() else (directory / f).resolve()
            for f in cast(list[Path], exclude_files)
        }
        files_to_delete = []
        with tarfile.open(output_tar_path, "w:gz") as tar:
            for file in directory.rglob("*"):
                if file.is_file() and file.resolve() not in exclude_set:
                    arcname = file.relative_to(directory)
                    tar.add(file, arcname=arcname)
                    files_to_delete.append(file)
        for file in files_to_delete:
            file.unlink()

    def decompress(self) -> None:
        """Extract a ``<name>.tar.gz`` archive into this directory.

        The archive is removed after successful extraction. If no archive exists,
        the method returns without doing anything.
        """
        directory = self.path.resolve()
        tar_path = directory.with_suffix(".tar.gz")
        if not tar_path.exists():
            return
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=directory, filter="fully_trusted")
        tar_path.unlink()
