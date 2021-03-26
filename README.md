# The Simple Backup Utility (SBU)
SBU can be used to backup files and folders to another folder mounted in your
file system.

## Introduction
Given a plain text file "backups.txt" it interprets every line of that file as
path to a file (or folder) in the file system.  The files (or folders) which
are listed in the "backups.txt" file are then copied to a destination folder
"backup_folder".  So essentially SBU does this:
`xargs -a backup.txt -d '\n' cp -r -t /path/to/backup_folder`

Note that a copy itself is not a backup.  For this the backup folder needs to
be moved to another storage device.  For example to an external USB-Drive or to
a Network Attached Storage (NAS).  In both cases the backup destination is
mounted as a part of the local file system, so SBU works in these cases.  If
the backup should be moved to some location which cannot be mounted SBU can
still be used to create a backup folder in a temporary location.  Than the
backup folder be moved (manually or by some script) to its desired location.

## Basic Usage
A basic usage of SBU can look something like this:
`./sbu /path/to/backup.txt /path/to/backup_folder`

Hereby the "backup.txt" file has to contain a list of paths to files or folders
to copy, one entry per line.  Comments starting with an "#" symbol are allowed
as well.

If SBU refuses to be executed ensure that it is marked to be executable.

## Features
SBU supports several features which make it more useful for the purpose of
safely creating backups.  The most notable once are listed in this section.

### Checked copies
SBU does not just copy your files blindly but tries to prevent some easy to
make mistakes.  In particular SBU checks for the following conditions for every
file (or folder) path listed in the backup.txt file:
- Every file path has to be absolute.
- Every file path has to refer to a existing file or folder.
- No file path is allowed to refer to a file (or folder) inside of the backup
  folder.
- No file path is allowed to refer to the backup folder itself.
- If a file path refers to a folder then the folder must not contain the
  backup folder.

If a file path violates one on the rules listed above a warning is printed and
it is excluded from the copy operations.

### Updating backups
Backups are usually not just created once but updated periodically.  SBU offers
no support for storing multiple versions of the same file or any other support
for version control. Some form of version control could in principal be
achieved by combining SBU with Git. However, this will only work well if the
only files backed up are text files and not images or video files for example.
If more sophisticated methods for version control are desired then SBU is not
the right tool.

SBU can be used to updated backups if more files (or folders) to back up have
been added to the backups.txt file. Just run SBU again.  By default it will not
overwrite per-existing files. If all files in the backup folder should be
overwritten than this can be achieved using the `--force` or `-f` option.
Alternatively, the `--interactive` or `-i` option will ask every time if a
given file should be overwritten.

### Creating archives
SBU can also be used to create an (compressed) archive or a ZIP-Folder instead
of copying to a per-existing backup folder. This can be enabled by using the
`--compress` or `-c` option.  In this case the archive will be placed inside
the specified backup folder.

### Verbosity control
By default SBU only prints warnings and errors.  To silence warnings use the
`--quite` or `-q` option. However, errors will still be printed. To show more
information about what SBU is doing use the `--verbose` or `-v` option.  To
show debug output use `--debug` or `-d`.

## Dependencies
SBU is written in pure Python and requires Python 3.9 at the moment.  Note that
the specific required Python version might be increased at any time in the
future without further notice.  To check which specific version of Python prior
to running the script open the sbu.py file in a text editor and check the first
line of the script. It will read something like `#/usr/bin/env python3.x`.
This line determines which version of Python (here Python version 3.x) is used
to execute the script.

Besides Python you do not need to install other pieces of software to run SBU.
In particular SBU does not depend on any external packages from the Python
Package Index (PyPI).  SBU is intended to be kept simple and simple to use.
External dependencies (besides the Python standard library) would oppose this
goal.

Currently SBU only works on Linux. If it is executed on a different operating
system it **should** just print a warning and exit.  In principal SBU could
also be updated to work with other operating systems as well.  If anyone wants
to add support for another operating system feel free to implement
(and test it) and send a pull request.

# TODOs
There are several features that are deemed as worthwhile additions to SBU:
- Support for a Self-Updater.
- Support for restoring backups.
- Support for Windows/Mac OS.
- Writing tests using Pytest and possible Docker. Reach out for discussion on
  how to best do this.

Feel free to implement any of those and send a pull request!

# Contribution Notes
To contribute to SBU simply fork the repository, commit your changes in your
repository and a send a pull-request on GitHub.  If the original author of SBU
deems the changes to be worthwhile and code quality to be high enough then the
pull-request will be accepted. For a list of ideas on features that should be
implemented have a look at the TODO section.

To set up SBU for development install
[Pipenv](https://pipenv.pypa.io/en/latest/ "Pipenv"), clone the repository and
install the development dependencies using`pipenv install --dev`.

SBU requires [Black](https://pypi.org/project/black/ "Black") and
[isort](https://pypi.org/project/isort/ "isort") for code formatting,
[Flake8](https://pypi.org/project/flake8/ "Flake8") for linting and
[MyPy](https://pypi.org/project/mypy/ "MyPy") for static typing.
Additionally [Pre-commit](https://pypi.org/project/pre-commit/ "Pre-commit") is
used for automatically running those checks **before** every commit.  For a
pull-request to be accept the code must be formatted accordingly, the linter
must not give any warnings and the code must be statically typed and checked
using MyPy.

SBU is deliberately contained within one file and uses no external dependencies
from the PyPI.  Pull request which introduce additional source code files or
external dependencies will not be accepted.

# License
SBU is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty
of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
