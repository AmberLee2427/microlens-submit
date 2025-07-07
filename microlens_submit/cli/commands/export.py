"""Export and metadata management commands for microlens-submit CLI."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from ...utils import load

console = Console()


def export(
    output_path: Path,
    force: bool = typer.Option(False, "--force", help="Skip validation prompts"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Generate a zip archive containing all active solutions."""
    sub = load(str(project_path))
    warnings = sub.run_validation()
    if warnings:
        console.print(Panel("Validation Warnings", style="yellow"))
        for w in warnings:
            console.print(f"- {w}")
        if not force:
            if not typer.confirm("Continue with export?"):
                console.print("Export cancelled", style="bold red")
                raise typer.Exit()
    sub.export(str(output_path))
    console.print(Panel(f"Exported submission to {output_path}", style="bold green"))


def remove_event(
    event_id: str,
    force: bool = typer.Option(
        False, "--force", help="Force removal even if event has saved solutions"
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Remove an entire event and all its solutions from the submission."""
    submission = load(str(project_path))

    if event_id not in submission.events:
        typer.echo(f"❌ Event '{event_id}' not found in submission")
        raise typer.Exit(1)

    event = submission.events[event_id]
    solution_count = len(event.solutions)

    if not force:
        typer.echo(
            f"⚠️  This will permanently remove event '{event_id}' and all {solution_count} solutions."
        )
        typer.echo("   This action cannot be undone.")
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            typer.echo("❌ Operation cancelled")
            raise typer.Exit(0)

    try:
        removed = submission.remove_event(event_id, force=force)
        if removed:
            typer.echo(
                f"✅ Removed event '{event_id}' and all {solution_count} solutions"
            )
            submission.save()
        else:
            typer.echo(f"❌ Failed to remove event '{event_id}'")
            raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"❌ Cannot remove event: {e}")
        raise typer.Exit(1)


def set_repo_url(
    repo_url: str = typer.Argument(
        ..., help="GitHub repository URL (e.g. https://github.com/owner/repo)"
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Set or update the GitHub repository URL in the submission metadata."""
    sub = load(str(project_path))
    sub.repo_url = repo_url
    sub.save()
    console.print(
        Panel(
            f"Set repo_url to {repo_url} in {project_path}/submission.json",
            style="bold green",
        )
    )


def set_hardware_info(
    cpu: Optional[str] = typer.Option(None, "--cpu", help="CPU model/description"),
    cpu_details: Optional[str] = typer.Option(
        None, "--cpu-details", help="Detailed CPU information"
    ),
    memory_gb: Optional[float] = typer.Option(None, "--memory-gb", help="Memory in GB"),
    ram_gb: Optional[float] = typer.Option(
        None, "--ram-gb", help="RAM in GB (alternative to --memory-gb)"
    ),
    platform: Optional[str] = typer.Option(
        None,
        "--platform",
        help="Platform description (e.g., 'Local Analysis', 'Roman Nexus')",
    ),
    nexus_image: Optional[str] = typer.Option(
        None, "--nexus-image", help="Roman Nexus image identifier"
    ),
    clear: bool = typer.Option(
        False, "--clear", help="Clear all existing hardware info"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be changed without saving"
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Set or update hardware information in the submission metadata."""
    sub = load(str(project_path))

    # Initialize hardware_info if it doesn't exist
    if sub.hardware_info is None:
        sub.hardware_info = {}

    changes = []
    old_hardware_info = sub.hardware_info.copy()

    # Clear existing info if requested
    if clear:
        if sub.hardware_info:
            changes.append("Clear all existing hardware info")
            sub.hardware_info = {}

    # Set new values
    if cpu_details is not None:
        if sub.hardware_info.get("cpu_details") != cpu_details:
            changes.append(f"Set cpu_details: {cpu_details}")
            sub.hardware_info["cpu_details"] = cpu_details
    elif cpu is not None:
        if sub.hardware_info.get("cpu") != cpu:
            changes.append(f"Set cpu: {cpu}")
            sub.hardware_info["cpu"] = cpu

    if memory_gb is not None:
        if sub.hardware_info.get("memory_gb") != memory_gb:
            changes.append(f"Set memory_gb: {memory_gb}")
            sub.hardware_info["memory_gb"] = memory_gb
    elif ram_gb is not None:
        if sub.hardware_info.get("ram_gb") != ram_gb:
            changes.append(f"Set ram_gb: {ram_gb}")
            sub.hardware_info["ram_gb"] = ram_gb

    if platform is not None:
        if sub.hardware_info.get("platform") != platform:
            changes.append(f"Set platform: {platform}")
            sub.hardware_info["platform"] = platform

    if nexus_image is not None:
        if sub.hardware_info.get("nexus_image") != nexus_image:
            changes.append(f"Set nexus_image: {nexus_image}")
            sub.hardware_info["nexus_image"] = nexus_image

    # Show dry run results
    if dry_run:
        if changes:
            console.print(Panel("Hardware info changes (dry run):", style="cyan"))
            for change in changes:
                console.print(f"  • {change}")
            console.print(f"\nNew hardware_info: {sub.hardware_info}")
        else:
            console.print(Panel("No changes would be made", style="yellow"))
        return

    # Apply changes
    if changes:
        sub.save()
        console.print(
            Panel(
                f"Updated hardware info in {project_path}/submission.json",
                style="bold green",
            )
        )
        for change in changes:
            console.print(f"  • {change}")
        console.print(f"\nCurrent hardware_info: {sub.hardware_info}")
    else:
        console.print(Panel("No changes made", style="yellow")) 