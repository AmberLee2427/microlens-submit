#!/usr/bin/env python3
"""
Sanity check used in the release workflow.

After installing the microlens-submit wheel into a clean virtual environment,
this script prints the package location and confirms the CLI module is importable.
"""

from __future__ import annotations

import pkgutil

import microlens_submit
import microlens_submit.cli  # noqa: F401


def main() -> None:
    print("microlens_submit located at:", microlens_submit.__file__)
    submodules = [m.name for m in pkgutil.iter_modules(microlens_submit.__path__)]
    print("Available subpackages:", submodules)
    print("CLI module path:", microlens_submit.cli.__file__)


if __name__ == "__main__":
    main()
