#!/usr/bin/env python3.9

import errno
import logging
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from enum import Enum, auto
from functools import reduce
from pathlib import Path
from shutil import copy2, copytree
from sys import exit, platform


class BackupFileParser:
    def __init__(self, backup_file: Path) -> None:
        if not backup_file.exists():
            raise FileNotFoundError(f"The backup file '{backup_file}' does not exist.")
        if not backup_file.is_file():
            raise FileNotFoundError(
                f"The path '{backup_file}' does not refer to a file."
            )
        self._backup_file = backup_file.resolve()

    def get_paths(self) -> list[Path]:
        logging.info("Getting files to back up.")
        with open(self._backup_file) as lines:
            trimed = map(str.strip, lines)
            ignore_comments = filter(self._ignore_comments, trimed)
            ignore_empty_lines = filter(self._ignore_empty_lines, ignore_comments)
            paths = map(self._create_path, ignore_empty_lines)
            result = list(paths)
            logging.debug(f"Found files: {result}.")
            return result

    @staticmethod
    def _create_path(path: str) -> Path:
        return Path(path)

    @staticmethod
    def _ignore_comments(line: str) -> bool:
        return not line.startswith("#")

    @staticmethod
    def _ignore_empty_lines(line: str) -> bool:
        return line != ""


class FileFilter(ABC):
    @abstractmethod
    def filter(self, path: Path) -> bool:
        raise NotImplementedError("Implement filter(path: Path) -> bool")


class IsAbsolutePathFilter(FileFilter):
    def filter(self, path: Path) -> bool:
        if not path.is_absolute():
            logging.warning(f"Path '{path}' is not absolute. Is ignored.")
            return False
        else:
            return True


class FileExistsFilter(FileFilter):
    def filter(self, path: Path) -> bool:
        if not path.exists():
            logging.warning(f"Path '{path}' does not exists. Is ignored.")
            return False
        else:
            return True


class PathNotDestFolderFilter(FileFilter):
    def __init__(self, dest: Path) -> None:
        self._dest = dest

    def filter(self, path: Path) -> bool:
        if self._dest.samefile(path):
            logging.warning(
                f"Path '{path}' should be backed up and is the backup folder.  Is ignored."
            )
            return False
        else:
            return True


class PathNotIncludedInDestFolderFilter(FileFilter):
    def __init__(self, dest: Path) -> None:
        self._dest = dest

    def filter(self, path: Path) -> bool:
        if self._dest in path.parents:
            logging.warning(f"Path '{path}' is part of the backup folder. Is ignored.")
            return False
        else:
            return True


class DestFolderNotIncludedInPathFilter(FileFilter):
    def __init__(self, dest: Path) -> None:
        self._dest = dest

    def filter(self, path: Path) -> bool:
        if path in self._dest.parents:
            logging.warning(f"Path '{path}' includes the backup folder. Is ignored.")
            return False
        else:
            return True


class Filterer:
    def __init__(self, backup_file: Path, dest: Path, files: list[Path]) -> None:
        if not backup_file.exists():
            raise FileNotFoundError(f"The backup file '{backup_file}' does not exist.")
        if not backup_file.is_file():
            raise FileNotFoundError(
                f"The path '{backup_file}' does not refer to a file."
            )
        self._backup_file = backup_file.resolve()

        if not dest.exists():
            raise FileNotFoundError(
                f"The destination directory '{dest}' does not exist"
            )
        if not dest.is_dir():
            raise NotADirectoryError(
                f"The destination path '{dest}' does not refer to a directory"
            )
        self._dest = dest.resolve()
        self._files = files

        filters: list[FileFilter] = []
        filters.append(IsAbsolutePathFilter())
        filters.append(FileExistsFilter())
        filters.append(PathNotDestFolderFilter(self._dest))
        filters.append(PathNotIncludedInDestFolderFilter(self._dest))
        filters.append(DestFolderNotIncludedInPathFilter(self._backup_file))
        self._filters = filters

    def _filter(self, src: list[Path]) -> list[Path]:
        logging.info("Filtering paths")
        result = list(
            reduce(
                lambda s, f1lter: filter(lambda path: f1lter.filter(path), s),
                self._filters,
                iter(src),
            )
        )
        logging.debug(f"Passing paths: {result}")
        return result

    def filter(self) -> list[Path]:
        return self._filter(self._files)


class Optimizer:
    def __init__(self, files: list[Path]) -> None:
        self._files = files

    # Given a list S of paths to files or folder to copy.
    # How to find the minimal subset S' of S such that copying all files and
    # directories in S' has the same effect as copying all files and folders is S?
    #
    # Example: Let S = ['/home/user/pictures/kitty.jpeg',
    #                   '/home/user/music/chicken.mp3', /home/user/pictures/']
    # Then S' = {'/home/user/pictures/', '/home/user/music/chicken.mp3'}
    #
    # Formally: Let S be a set of Paths and let a, b be in S.
    # Define a relation <= on S: a == b <=> a.samefile(b)
    #                            a < b <=> b in a.parents
    # Then <= is a partial order.
    # Moreover, S' then is the set of maximal elements of S using <=.
    #
    # To find those set of maximum elements we build a graph G=(V,E) where V = S and
    # (a,b) in E <=> a < b for all a, b in S. Then we need to find all vertices that
    # have no successor. Those are the maximal elements of S with regards to <=.
    def _minimize_paths(self, paths: list[Path]) -> set[Path]:
        # TODO: This can probably be done more efficiently
        logging.info("Minimizing paths to copy")
        successors: dict[Path, set[Path]] = {p: set() for p in paths}

        # We have Path("/a/b/../").samefile(Path("/a/")),
        # but Path("/a/b/../") != (Path("/a/"))
        paths = list(set(paths))

        for i in range(0, len(paths)):
            p1 = paths[i]
            for j in range(i + 1, len(paths)):
                p2 = paths[j]
                if p1.samefile(p2):
                    successors[p2].add(p1)
                elif p1 in p2.parents:
                    successors[p2].add(p1)
                elif p2 in p1.parents:
                    successors[p1].add(p2)

        logging.debug(f"Successors: {successors}")
        no_successor_entry = filter(lambda t: len(t[1]) == 0, successors.items())
        no_successors = map(lambda e: e[0], no_successor_entry)
        result = set(no_successors)
        logging.debug(f"Paths left after minimizing: {result}")
        return result

    def optimize(self) -> set[Path]:
        return self._minimize_paths(self._files)


class CopyFiles:
    class CopyConflictMode(Enum):
        NO_OVERWRITE = auto()
        OVERWRITE = auto()
        ASK = auto()

    def __init__(
        self, dest: Path, files: set[Path], *, conflict_mode: CopyConflictMode
    ) -> None:
        if not dest.exists():
            raise FileNotFoundError(
                f"The destination directory '{dest}' does not exist"
            )
        if not dest.is_dir():
            raise NotADirectoryError(
                f"The destination path '{dest}' does not refer to a directory"
            )
        self._dest = dest.resolve()
        self._files = files
        self._conflict_mode = conflict_mode

    def copy(self, *, pretend: bool = False) -> None:
        logging.info(f"Copying to backup directory '{self._dest}'")
        logging.debug("Resolving paths")
        for path in map(lambda p: Path.resolve(p), self._files):
            logging.debug(f"Source: '{path}")
            target = self._concat_paths(self._dest, path)
            logging.debug(f"Target: '{target}'")
            if path.is_file():
                logging.debug("Source is file")
                copy = (
                    not target.exists()
                    or self._conflict_mode == self.CopyConflictMode.OVERWRITE
                )
                if not copy and self._conflict_mode == self.CopyConflictMode.ASK:
                    copy = self._overwrite_confirmation(path)
                if copy:
                    logging.info(f"Copying '{path}' to '{target}'")
                    if not pretend:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        copy2(path, target)
            else:
                logging.debug("Source is directory")
                if not target.exists():
                    logging.info(f"Copying '{path}' to '{target}'")
                    if not pretend:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        copytree(path, target)
                else:
                    self._merge_copy(path, target, pretend=pretend)

    def _merge_copy(self, src: Path, dest: Path, pretend: bool = False) -> None:
        logging.debug(f"Merging '{src}' and '{dest}'")
        for path in src.iterdir():
            logging.debug(f"Source: '{path}'")
            target = self._concat_paths(self._dest, path)
            logging.debug(f"Target: '{target}'")
            if path.is_file():
                logging.debug("Source is file")
                copy = (
                    not target.exists()
                ) or self._conflict_mode == self.CopyConflictMode.OVERWRITE
                if not copy and self._conflict_mode == self.CopyConflictMode.ASK:
                    copy = self._overwrite_confirmation(path)
                if copy:
                    logging.info(f"Copying '{path}' to '{target}'")
                    if not pretend:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        copy2(path, target)
            else:
                if not target.exists():
                    logging.info(f"Copying '{path}' to '{target}'")
                    if not pretend:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        copytree(path, target)
                else:
                    self._merge_copy(path, target, pretend=pretend)
        logging.debug(f"Done merging '{src}' and '{dest}'")

    @staticmethod
    def _overwrite_confirmation(path: Path) -> bool:
        confirmations = ["", "y", "yes"]
        declines = ["n", "no"]
        while True:
            answer = input(f"Overwrite file '{path}'? [Yes/No]: ")
            answer = answer.strip().lower()
            if answer in confirmations:
                return True
            elif answer in declines:
                return False

    @staticmethod
    def _concat_paths(p1: Path, p2: Path) -> Path:
        return Path(str(p1) + str(p2))


class Main:
    @staticmethod
    def _create_parser() -> ArgumentParser:
        parser = ArgumentParser(description="Backup files")
        parser.add_argument(
            "backup_file_path",
            help="Path to the file containing the list of paths to files or folder that should be backedup.",
            default=".",
            type=Path,
        )
        parser.add_argument(
            "backup_destination",
            help="Path to the folder to which other files or folders should be copied.",
            type=Path,
        )

        parser.add_argument(
            "-p",
            "--pretend",
            action="store_true",
            help="Show output without actually copying anything",
        )

        conflicts = parser.add_mutually_exclusive_group()
        conflicts.add_argument(
            "-f", "--force", action="store_true", help="Overwrite existing files"
        )
        conflicts.add_argument(
            "-i",
            "--interactive",
            action="store_true",
            help="Ask before overwriting a file",
        )

        verbosity = parser.add_mutually_exclusive_group()
        verbosity.add_argument(
            "-q", "--quite", action="store_true", help="Do not show warnings"
        )
        verbosity.add_argument(
            "-v", "--verbose", action="store_true", help="Show more information"
        )
        verbosity.add_argument(
            "-d", "--debug", action="store_true", help="Show debug output"
        )
        return parser

    def __init__(self) -> None:
        self._parser = Main._create_parser()

    def _configure_logging(self, args: Namespace) -> None:
        format = "%(levelname)-8s - %(message)s"
        if args.quite:
            logging.basicConfig(level=logging.ERROR, format=format)
        elif args.verbose:
            logging.basicConfig(level=logging.INFO, format=format)
        elif args.debug:
            logging.basicConfig(level=logging.DEBUG, format=format)
        else:
            logging.basicConfig(level=logging.WARNING, format=format)

    def main(self) -> None:
        args: Namespace = self._parser.parse_args()
        self._configure_logging(args)
        try:
            reader = BackupFileParser(args.backup_file_path)
        except FileNotFoundError as e:
            logging.error(e)
            exit(errno.ENOENT)

        files = reader.get_paths()
        try:
            filterer = Filterer(args.backup_file_path, args.backup_destination, files)
        except FileNotFoundError as e:
            logging.error(e)
            exit(errno.ENOENT)
        except NotADirectoryError as e:
            logging.error(e)
            exit(errno.ENOTDIR)

        filtered_files = filterer.filter()
        optimizer = Optimizer(filtered_files)
        optimized_files = optimizer.optimize()

        conflict_mode = CopyFiles.CopyConflictMode.NO_OVERWRITE
        if args.force:
            conflict_mode = CopyFiles.CopyConflictMode.OVERWRITE
        elif args.interactive:
            conflict_mode = CopyFiles.CopyConflictMode.ASK

        try:
            copyer = CopyFiles(
                args.backup_destination,
                optimized_files,
                conflict_mode=conflict_mode,
            )
        except FileNotFoundError as e:
            logging.error(e)
            exit(errno.ENOENT)
        except NotADirectoryError as e:
            logging.error(e)
            exit(errno.ENOTDIR)

        copyer.copy(pretend=args.pretend)


if __name__ == "__main__":
    if platform != "linux":
        print("For now, the only supported platform is Linux")
        exit(errno.ENOSYS)
    main = Main()
    main.main()