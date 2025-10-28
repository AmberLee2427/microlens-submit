#!/usr/bin/env python3
"""Install a wheel from the dist/ directory.

This helper is used in CI to ensure the wheel built earlier in the workflow
can be installed without relying on shell-specific globbing behaviour.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys


def main(dist_dir: pathlib.Path) -> None:
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError(f"No wheel files found in {dist_dir!s}")

    wheel = wheels[0]
    subprocess.check_call([sys.executable, "-m", "pip", "install", str(wheel)])


if __name__ == "__main__":
    directory = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("dist")
    main(directory.resolve())
