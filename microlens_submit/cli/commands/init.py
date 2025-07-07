"""Initialization commands for microlens-submit CLI."""

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from microlens_submit.utils import load

console = Console()


def init(
    team_name: str = typer.Option(..., help="Team name"),
    tier: str = typer.Option(..., help="Challenge tier"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Create a new submission project in the specified directory.

    Initializes a new microlensing submission project with the given team name
    and tier. The project directory structure is created automatically, and
    the submission.json file is initialized with basic metadata.

    This command also attempts to auto-detect the GitHub repository URL
    from the current git configuration and provides helpful feedback.

    Args:
        team_name: Name of the participating team (e.g., "Team Alpha").
        tier: Challenge tier level (e.g., "basic", "advanced").
        project_path: Directory where the project will be created.
            Defaults to current directory if not specified.

    Raises:
        OSError: If unable to create the project directory or write files.

    Example:
        # Create project in current directory
        microlens-submit init --team-name "Team Alpha" --tier "advanced"

        # Create project in specific directory
        microlens-submit init --team-name "Team Beta" --tier "basic" ./my_submission

        # Project structure created:
        # ./my_submission/
        # ├── submission.json
        # └── events/

    Note:
        If the project directory already exists, it will be used as-is.
        If a git repository is detected, the GitHub URL will be automatically
        set. Otherwise, a warning is shown and you can set it later with
        set-repo-url command.
    """
    sub = load(str(project_path))
    sub.team_name = team_name
    sub.tier = tier
    # Try to auto-detect repo_url
    try:
        repo_url = (
            subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        repo_url = None
    if repo_url:
        sub.repo_url = repo_url
        console.print(f"[green]Auto-detected GitHub repo URL:[/green] {repo_url}")
    else:
        console.print(
            "[yellow]Could not auto-detect a GitHub repository URL. Please add it using 'microlens-submit set-repo-url <url> <project_dir>'.[/yellow]"
        )
    sub.save()
    console.print(Panel(f"Initialized project at {project_path}", style="bold green"))


def nexus_init(
    team_name: str = typer.Option(..., help="Team name"),
    tier: str = typer.Option(..., help="Challenge tier"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Create a project and record Roman Nexus environment details.

    This command combines the functionality of init() with automatic
    detection of Roman Science Platform environment information. It
    populates hardware_info with CPU details, memory information, and
    the Nexus image identifier.

    Args:
        team_name: Name of the participating team (e.g., "Team Alpha").
        tier: Challenge tier level (e.g., "basic", "advanced").
        project_path: Directory where the project will be created.
            Defaults to current directory if not specified.

    Example:
        # Initialize project with Nexus platform info
        microlens-submit nexus-init --team-name "Team Alpha" --tier "advanced" ./project

        # This will automatically detect:
        # - CPU model from /proc/cpuinfo
        # - Memory from /proc/meminfo
        # - Nexus image from JUPYTER_IMAGE_SPEC

    Note:
        This command is specifically designed for the Roman Science Platform
        environment. It will silently skip any environment information that
        cannot be detected (e.g., if running outside of Nexus).
    """
    init(team_name=team_name, tier=tier, project_path=project_path)
    sub = load(str(project_path))
    sub.autofill_nexus_info()
    sub.save()
    console.print("Nexus platform info captured.", style="bold green") 