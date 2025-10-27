#!/usr/bin/env python3
"""
Version management utility for microlens-submit.

This script centralises the workflow for bumping the project version,
creating skeleton changelog entries, and preparing release notes.  It
mirrors the tooling used on the Gulls project while being tailored to
the microlens-submit repository layout.

Typical usage:
    python scripts/bump_version.py patch
    python scripts/bump_version.py minor
    python scripts/bump_version.py major
    python scripts/bump_version.py release

The patch/minor/major modes:
    * increment the semantic version number
    * update all versioned files (pyproject, package __init__, docs, citation)
    * insert an empty changelog section for the new version

The release mode expects the version to already be correct.  It will:
    * ensure RELEASE_NOTES.md exists for the target version (generated
      from CHANGELOG.md when possible)
    * stage changed files, create a release commit, and tag vX.Y.Z
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
SETUP_PY_PATH = PROJECT_ROOT / "setup.py"
PACKAGE_INIT_PATH = PROJECT_ROOT / "microlens_submit" / "__init__.py"
DOCS_CONF_PATH = PROJECT_ROOT / "docs" / "conf.py"
CITATION_PATH = PROJECT_ROOT / "CITATION.cff"
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"
RELEASE_NOTES_PATH = PROJECT_ROOT / "RELEASE_NOTES.md"


VERSION_PATTERN = re.compile(r'version\s*=\s*"(?P<version>\d+\.\d+\.\d+)"')
SETUP_PATTERN = re.compile(r'version\s*=\s*"(?P<version>\d+\.\d+\.\d+)"')
INIT_PATTERN = re.compile(r'__version__\s*=\s*"(?P<version>\d+\.\d+\.\d+)"')
DOCS_PATTERN = re.compile(r'release\s*=\s*"(?P<version>\d+\.\d+\.\d+)"')
CITATION_PATTERN = re.compile(r'version:\s*"(?P<version>\d+\.\d+\.\d+)"')


def is_git_repository() -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def prompt_yes_no(message: str) -> bool:
    try:
        response = input(f"{message} (y/N): ").strip().lower()
    except EOFError:
        return False
    return response in {"y", "yes"}


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def get_current_version() -> str:
    """Extract the current version from pyproject.toml."""
    content = read_text(PYPROJECT_PATH)
    match = VERSION_PATTERN.search(content)
    if not match:
        raise ValueError("Could not locate version in pyproject.toml")
    return match.group("version")


def bump_version(version: str, bump_type: str) -> str:
    major, minor, patch = map(int, version.split("."))
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:  # pragma: no cover - argparse guards this
        raise ValueError(f"Invalid bump type: {bump_type}")
    return f"{major}.{minor}.{patch}"


def replace_first(pattern: re.Pattern, replacement: str, content: str, path: Path) -> str:
    new_content, count = pattern.subn(replacement, content, count=1)
    if count == 0:
        raise ValueError(f"Failed to update version in {path}")
    return new_content


def update_pyproject(new_version: str) -> None:
    content = read_text(PYPROJECT_PATH)
    new_content = replace_first(
        VERSION_PATTERN,
        f'version = "{new_version}"',
        content,
        PYPROJECT_PATH,
    )
    write_text(PYPROJECT_PATH, new_content)


def update_setup_py(new_version: str) -> None:
    if not SETUP_PY_PATH.exists():
        return
    content = read_text(SETUP_PY_PATH)
    new_content = replace_first(SETUP_PATTERN, f'version = "{new_version}"', content, SETUP_PY_PATH)
    write_text(SETUP_PY_PATH, new_content)


def update_package_init(new_version: str) -> None:
    content = read_text(PACKAGE_INIT_PATH)
    new_content = replace_first(
        INIT_PATTERN,
        f'__version__ = "{new_version}"',
        content,
        PACKAGE_INIT_PATH,
    )
    write_text(PACKAGE_INIT_PATH, new_content)


def update_docs_conf(new_version: str) -> None:
    if not DOCS_CONF_PATH.exists():
        return
    content = read_text(DOCS_CONF_PATH)
    new_content = replace_first(
        DOCS_PATTERN,
        f'release = "{new_version}"',
        content,
        DOCS_CONF_PATH,
    )
    write_text(DOCS_CONF_PATH, new_content)


def update_citation(new_version: str) -> None:
    if not CITATION_PATH.exists():
        return
    content = read_text(CITATION_PATH)
    new_content = replace_first(
        CITATION_PATTERN,
        f'version: "{new_version}"',
        content,
        CITATION_PATH,
    )
    write_text(CITATION_PATH, new_content)


def ensure_changelog_entry(new_version: str) -> None:
    """Insert a templated changelog section if one does not already exist."""
    if not CHANGELOG_PATH.exists():
        return
    content = read_text(CHANGELOG_PATH)
    if f"## [{new_version}]" in content:
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    template = (
        f"## [{new_version}] - {today}\n\n"
        "### Added\n"
        "- _Add new features here_\n\n"
        "### Changed\n"
        "- _Describe notable changes here_\n\n"
        "### Fixed\n"
        "- _List bug fixes here_\n\n"
    )

    # Insert template after the main header if present
    marker = "\n## ["
    if marker in content:
        split_index = content.index(marker)
        new_content = content[:split_index] + "\n" + template + content[split_index:]
    else:
        # Changelog has no entries yet; append template
        new_content = content.rstrip() + "\n\n" + template

    write_text(CHANGELOG_PATH, new_content)


def extract_changelog_entry(version: str) -> Optional[str]:
    if not CHANGELOG_PATH.exists():
        return None

    content = read_text(CHANGELOG_PATH)
    pattern = re.compile(
        rf"## \[{re.escape(version)}\](.*?)(?=^## \[|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(content)
    if not match:
        return None
    return match.group(0).strip()


def generate_release_notes(version: str) -> None:
    """Create or overwrite RELEASE_NOTES.md based on the changelog entry."""
    changelog_entry = extract_changelog_entry(version)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    release_date = today

    if changelog_entry:
        date_match = re.search(r"\] - (\d{4}-\d{2}-\d{2})", changelog_entry)
        if date_match:
            release_date = date_match.group(1)

    header = f"# microlens-submit v{version} Release Notes\n\n"
    metadata = f"**Release Date:** {release_date}\n\n"

    if changelog_entry:
        body = f"## Changelog\n\n{changelog_entry}\n"
    else:
        body = "## Changelog\n\n" "_No changelog entry found. Update CHANGELOG.md before publishing._\n"

    write_text(RELEASE_NOTES_PATH, header + metadata + body)


def stage_files(paths: list[Path]) -> None:
    if not is_git_repository():
        print("Not inside a git repository; skipping git operations.")
        return

    files_to_stage = [str(path.relative_to(PROJECT_ROOT)) for path in paths if path.exists()]
    if not files_to_stage:
        return
    subprocess.run(["git", "add", *files_to_stage], check=False, cwd=PROJECT_ROOT)


def get_unstaged_changes() -> list[str]:
    if not is_git_repository():
        return []
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changes: list[str] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:]
        if status.startswith("??"):
            changes.append(path)
        elif len(status) >= 2 and status[1] != " ":
            changes.append(path)
    return changes


def maybe_stage_unstaged_changes() -> None:
    changes = get_unstaged_changes()
    if not changes:
        return

    print("Found unstaged changes:")
    for path in changes[:8]:
        print(f"  - {path}")
    if len(changes) > 8:
        print(f"  ... and {len(changes) - 8} more files")

    if prompt_yes_no("Include all unstaged changes in the release commit?"):
        subprocess.run(["git", "add", "."], cwd=PROJECT_ROOT, check=False)
        print("Added all unstaged changes.")
    else:
        print("Proceeding without staging unstaged changes.")


def create_release_commit(version: str) -> None:
    """Create a release commit and annotated tag."""
    if not is_git_repository():
        print("Not inside a git repository; skipping release commit and tagging.")
        return

    commit_message = f"Release version {version}"
    commit = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if commit.returncode != 0:
        print(commit.stdout.strip())
        print(commit.stderr.strip())
        print("Commit failed (see messages above). Resolve issues and rerun the release step.")
        return

    if "nothing to commit" in commit.stdout.lower() or "nothing to commit" in commit.stderr.lower():
        print("No new changes were committed; continuing with tagging.")
    else:
        print("Release commit created.")

    tag_name = f"v{version}"
    existing_tag = subprocess.run(
        ["git", "rev-parse", "--verify", tag_name],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if existing_tag.returncode == 0:
        print(f"Tag {tag_name} already exists.")
        if prompt_yes_no("Delete existing tag and recreate it?"):
            subprocess.run(["git", "tag", "-d", tag_name], cwd=PROJECT_ROOT, check=False)
            remote_delete = subprocess.run(
                ["git", "push", "--delete", "origin", tag_name],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
            if remote_delete.returncode == 0:
                print(f"Deleted remote tag {tag_name}.")
            else:
                print("Could not delete remote tag (it may not exist remotely).")
        else:
            print("Keeping existing tag; skipping tag recreation.")
            return

    tag_result = subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", f"Release {version}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if tag_result.returncode != 0:
        print(tag_result.stderr.strip())
        print(f"Skipping tag creation; ensure tag {tag_name} does not already exist.")


def handle_bump(bump_type: str) -> str:
    current_version = get_current_version()
    new_version = bump_version(current_version, bump_type)
    print(f"Bumping version {current_version} -> {new_version}")

    update_pyproject(new_version)
    update_setup_py(new_version)
    update_package_init(new_version)
    update_docs_conf(new_version)
    update_citation(new_version)
    ensure_changelog_entry(new_version)

    return new_version


def handle_release(dry_run: bool) -> None:
    version = get_current_version()
    print(f"Preparing release for version {version}")

    generate_release_notes(version)
    stage_files(
        [
            PYPROJECT_PATH,
            SETUP_PY_PATH,
            PACKAGE_INIT_PATH,
            DOCS_CONF_PATH,
            CITATION_PATH,
            CHANGELOG_PATH,
            RELEASE_NOTES_PATH,
        ]
    )
    maybe_stage_unstaged_changes()

    if dry_run:
        print("Dry run: release notes generated and files staged (if in git).")
        return

    create_release_commit(version)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="microlens-submit version management helper")
    parser.add_argument(
        "action",
        choices=["major", "minor", "patch", "release"],
        help="Version action to perform",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without committing/tagging (only meaningful for release)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        if args.action in {"major", "minor", "patch"}:
            new_version = handle_bump(args.action)
            print("Update complete. Review CHANGELOG.md and commit the changes.")
            print("Next steps:")
            print(f"  - Update changelog details for {new_version}")
            print("  - Run tests `pytest`")
            print("  - Commit the version bump `python scripts/bump_version.py release`")
            print("Note. to create an editable RELEASE_NOTES.md file, before release, run:")
            print("  python scripts/bump_version.py release --dry-run")
        else:
            handle_release(dry_run=args.dry_run)
            print("Release preparation complete.")
    except Exception as exc:  # pragma: no cover - defensive for CLI
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
