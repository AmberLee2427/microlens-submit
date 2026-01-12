"""Command line interface for microlens-submit.

This module provides a comprehensive CLI for managing microlensing challenge
submissions. It includes commands for project initialization, solution management,
validation, dossier generation, and export functionality.

The CLI is built using Typer and provides rich, colored output with helpful
error messages and validation feedback. All commands support both interactive
and scripted usage patterns.

**Key Commands:**
- init: Create new submission projects
- add-solution: Add microlensing solutions with parameters
- validate-submission: Check submission completeness
- generate-dossier: Create HTML documentation
- export: Create submission archives

**Example Workflow:**
    # Initialize a new project
    microlens-submit init --team-name "Team Alpha" --tier "experienced" ./my_project

    # Add a solution
    microlens-submit add-solution EVENT001 1S1L ./my_project \
        --param t0=2459123.5 --param u0=0.1 --param tE=20.0 \
        --log-likelihood -1234.56 --cpu-hours 2.5

    # Validate and generate dossier
    microlens-submit validate-submission ./my_project
    microlens-submit generate-dossier ./my_project

    # Export for submission
    microlens-submit export submission.zip ./my_project

**Note:**
    All commands that modify data automatically save changes to disk.
    Use --dry-run flags to preview changes without saving.
"""

from __future__ import annotations

import typer
from rich.console import Console

from .. import __version__

# Import command modules
from .commands import dossier, export, init, solutions, validation

console = Console()
app = typer.Typer()


@app.command("version")
def version() -> None:
    """Show the version of microlens-submit.

    Displays the current version of the microlens-submit package.

    Example:
        >>> microlens-submit version
        microlens-submit version 0.12.0-dev

    Note:
        This command is useful for verifying the installed version
        and for debugging purposes.
    """
    console.print(f"microlens-submit version {__version__}")


@app.callback()
def main(
    ctx: typer.Context,
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
) -> None:
    """Handle global CLI options.

    Sets up global configuration for the CLI, including color output
    preferences that apply to all commands.

    Args:
        ctx: Typer context for command execution.
        no_color: If True, disable colored output for all commands.

    Example:
        # Disable colors for all commands
        microlens-submit --no-color init --team-name "Team" --tier "basic" ./project

    Note:
        This is a Typer callback that runs before any command execution.
        It's used to configure global settings like color output.
    """
    if no_color:
        global console
        console = Console(color_system=None)


# Register all commands from modules
app.command("init")(init.init)
app.command("nexus-init")(init.nexus_init)

app.command("add-solution")(solutions.add_solution)
app.command("deactivate")(solutions.deactivate)
app.command("activate")(solutions.activate)
app.command("remove-solution")(solutions.remove_solution)
app.command("edit-solution")(solutions.edit_solution)
app.command("notes")(solutions.edit_notes)
app.command("import-solutions")(solutions.import_solutions)

app.command("validate-solution")(validation.validate_solution)
app.command("validate-submission")(validation.validate_submission)
app.command("validate-event")(validation.validate_event)
app.command("list-solutions")(validation.list_solutions)
app.command("compare-solutions")(validation.compare_solutions)

app.command("generate-dossier")(dossier.generate_dossier)

app.command("export")(export.export)
app.command("remove-event")(export.remove_event)
app.command("set-repo-url")(export.set_repo_url)
app.command("set-git-dir")(export.set_git_dir)
app.command("set-hardware-info")(export.set_hardware_info)
