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
    microlens-submit init --team-name "Team Alpha" --tier "advanced" ./my_project
    
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

import json
import math
from pathlib import Path
from typing import List, Optional, Literal
import os
import subprocess

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .api import load, import_solutions_from_csv
from .dossier import generate_dashboard_html
from . import __version__

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


def _parse_pairs(pairs: Optional[List[str]]) -> Optional[dict]:
    """Convert CLI key=value options into a dictionary.

    Parses command-line arguments in the format "key=value" and converts
    them to a Python dictionary. Handles JSON parsing for numeric and
    boolean values, falling back to string values.

    Args:
        pairs: List of strings in "key=value" format, or None.

    Returns:
        dict: Parsed key-value pairs, or None if pairs is None/empty.

    Raises:
        typer.BadParameter: If any pair is not in "key=value" format.

    Example:
        >>> _parse_pairs(["t0=2459123.5", "u0=0.1", "active=true"])
        {'t0': 2459123.5, 'u0': 0.1, 'active': True}

        >>> _parse_pairs(["name=test", "value=123"])
        {'name': 'test', 'value': 123}

    Note:
        This function attempts to parse values as JSON first (for numbers,
        booleans, etc.), then falls back to string values if JSON parsing fails.
    """
    if not pairs:
        return None
    out: dict = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"Invalid format: {item}")
        key, value = item.split("=", 1)
        try:
            out[key] = json.loads(value)
        except json.JSONDecodeError:
            out[key] = value
    return out


def _params_file_callback(ctx: typer.Context, value: Optional[Path]) -> Optional[Path]:
    """Validate mutually exclusive parameter options.

    Ensures that --params-file and --param options are not used together,
    as they are mutually exclusive ways of specifying parameters.

    Args:
        ctx: Typer context containing other parameter values.
        value: The value of the --params-file option.

    Returns:
        Path: The validated file path, or None.

    Raises:
        typer.BadParameter: If both --params-file and --param are specified,
            or if neither is specified when required.

    Example:
        # This would raise an error:
        # microlens-submit add-solution EVENT001 1S1L --param t0=123 --params-file params.json

        # This is valid:
        # microlens-submit add-solution EVENT001 1S1L --params-file params.json

    Note:
        This is a Typer callback function used for parameter validation.
        It's automatically called when processing command-line arguments.
    """
    param_vals = ctx.params.get("param")
    if value is not None and param_vals:
        raise typer.BadParameter("Cannot use --param with --params-file")
    if value is None and not param_vals and not ctx.resilient_parsing:
        raise typer.BadParameter("Provide either --param or --params-file")
    return value


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


@app.command()
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


@app.command("nexus-init")
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


@app.command("add-solution")
def add_solution(
    event_id: str,
    model_type: str = typer.Argument(
        ...,
        metavar="{1S1L|1S2L|2S1L|2S2L|1S3L|2S3L|other}",
        help="Type of model used for the solution (e.g., 1S1L, 1S2L)",
    ),
    param: Optional[List[str]] = typer.Option(
        None, help="Model parameters as key=value"
    ),
    params_file: Optional[Path] = typer.Option(
        None,
        "--params-file",
        help="Path to JSON or YAML file with model parameters and uncertainties",
        callback=_params_file_callback,
    ),
    bands: Optional[List[str]] = typer.Option(
        None,
        "--bands",
        help="Comma-separated list of photometric bands used (e.g., 0,1,2)",
    ),
    higher_order_effect: Optional[List[str]] = typer.Option(
        None,
        "--higher-order-effect",
        help="List of higher-order effects (e.g., parallax, finite-source)",
    ),
    t_ref: Optional[float] = typer.Option(
        None,
        "--t-ref",
        help="Reference time for the model",
    ),
    used_astrometry: bool = typer.Option(False, help="Set if astrometry was used"),
    used_postage_stamps: bool = typer.Option(
        False, help="Set if postage stamps were used"
    ),
    limb_darkening_model: Optional[str] = typer.Option(
        None, help="Limb darkening model name"
    ),
    limb_darkening_coeff: Optional[List[str]] = typer.Option(
        None,
        "--limb-darkening-coeff",
        help="Limb darkening coefficients as key=value",
    ),
    parameter_uncertainty: Optional[List[str]] = typer.Option(
        None,
        "--param-uncertainty",
        help="Parameter uncertainties as key=value",
    ),
    physical_param: Optional[List[str]] = typer.Option(
        None,
        "--physical-param",
        help="Physical parameters as key=value",
    ),
    relative_probability: Optional[float] = typer.Option(
        None,
        "--relative-probability",
        help="Relative probability of this solution",
    ),
    log_likelihood: Optional[float] = typer.Option(None, help="Log likelihood"),
    n_data_points: Optional[int] = typer.Option(
        None,
        "--n-data-points",
        help="Number of data points used in this solution",
    ),
    cpu_hours: Optional[float] = typer.Option(
        None,
        "--cpu-hours",
        help="CPU hours used for this solution",
    ),
    wall_time_hours: Optional[float] = typer.Option(
        None,
        "--wall-time-hours",
        help="Wall time hours used for this solution",
    ),
    lightcurve_plot_path: Optional[Path] = typer.Option(
        None, "--lightcurve-plot-path", help="Path to lightcurve plot file"
    ),
    lens_plane_plot_path: Optional[Path] = typer.Option(
        None, "--lens-plane-plot-path", help="Path to lens plane plot file"
    ),
    alias: Optional[str] = typer.Option(
        None,
        "--alias",
        help="Optional human-readable alias for the solution (must be unique within the event)",
    ),
    notes: Optional[str] = typer.Option(
        None, help="Notes for the solution (supports Markdown formatting)"
    ),
    notes_file: Optional[Path] = typer.Option(
        None,
        "--notes-file",
        help="Path to a Markdown file for solution notes (mutually exclusive with --notes)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Parse inputs and display the resulting Solution without saving",
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Add a new solution entry for a microlensing event.
    
    Creates a new solution with the specified model type and parameters,
    automatically generating a unique solution ID. The solution is added
    to the specified event and saved to disk.
    
    **Model Types Supported:**
    - 1S1L: Single source, single lens (point source, point lens)
    - 1S2L: Single source, binary lens
    - 2S1L: Binary source, single lens
    - 2S2L: Binary source, binary lens
    - 1S3L: Single source, triple lens
    - 2S3L: Binary source, triple lens
    - other: Custom model type
    
    **Parameter Specification:**
    Parameters can be specified either via individual --param options
    or using a structured file with --params-file. The file can be JSON
    or YAML format and can include both parameters and uncertainties.
    
    **Higher-Order Effects:**
    - parallax: Annual parallax effect
    - finite-source: Finite source size effects
    - lens-orbital-motion: Lens orbital motion
    - limb-darkening: Limb darkening effects
    - xallarap: Xallarap (source orbital motion)
    - stellar-rotation: Stellar rotation effects
    - fitted-limb-darkening: Fitted limb darkening coefficients
    - gaussian-process: Gaussian process noise modeling
    - other: Custom higher-order effects
    
    **Alias:**
    - Use --alias to specify a human-readable alias for the solution (e.g., "best_fit", "parallax_model").
    - The combination of event_id and alias must be unique within the project. If not, an error will be raised during validation or save operations.
    
    Args:
        event_id: Identifier for the microlensing event (e.g., "EVENT001").
        model_type: Type of microlensing model used for the fit.
        param: Model parameters as key=value pairs (e.g., "t0=2459123.5").
        params_file: Path to JSON/YAML file containing parameters and uncertainties.
        bands: List of photometric bands used in the fit (e.g., ["0", "1", "2"]).
        higher_order_effect: List of higher-order physical effects included.
        t_ref: Reference time for time-dependent effects (Julian Date).
        used_astrometry: Whether astrometric data was used in the fit.
        used_postage_stamps: Whether postage stamp data was used.
        limb_darkening_model: Name of the limb darkening model employed.
        limb_darkening_coeff: Limb darkening coefficients as key=value pairs.
        parameter_uncertainty: Parameter uncertainties as key=value pairs.
        physical_param: Derived physical parameters as key=value pairs.
        relative_probability: Probability of this solution being the best model.
        log_likelihood: Log-likelihood value of the fit.
        n_data_points: Number of data points used in the fit.
        cpu_hours: Total CPU time consumed by the fit.
        wall_time_hours: Real-world time consumed by the fit.
        lightcurve_plot_path: Path to the lightcurve plot file.
        lens_plane_plot_path: Path to the lens plane plot file.
        alias: Optional human-readable alias for the solution (must be unique within the event).
        notes: Markdown-formatted notes for the solution.
        notes_file: Path to a Markdown file containing solution notes.
        dry_run: If True, display the solution without saving.
        project_path: Directory of the submission project.
    
    Raises:
        typer.BadParameter: If parameter format is invalid or model type is unsupported.
        OSError: If unable to write files or create directories.
    
    Example:
        # Simple 1S1L solution with alias
        microlens-submit add-solution EVENT001 1S1L ./project \
            --param t0=2459123.5 --param u0=0.1 --param tE=20.0 \
            --alias best_fit \
            --log-likelihood -1234.56 --n-data-points 1250 \
            --cpu-hours 2.5 --wall-time-hours 0.5 \
            --relative-probability 0.8 \
            --notes "# Simple Point Lens Fit\n\nThis is a basic 1S1L solution."
        
    Note:
        The solution is automatically assigned a unique UUID and marked as active.
        If notes are provided, they are saved as a Markdown file in the project
        structure. Use --dry-run to preview the solution before saving.
        The command automatically validates the solution and displays any warnings.
    """
    sub = load(str(project_path))
    evt = sub.get_event(event_id)
    params: dict = {}
    uncertainties: dict = {}
    if params_file is not None:
        params, uncertainties = _parse_structured_params_file(params_file)
    else:
        for p in param or []:
            if "=" not in p:
                raise typer.BadParameter(f"Invalid parameter format: {p}")
            key, value = p.split("=", 1)
            try:
                params[key] = json.loads(value)
            except json.JSONDecodeError:
                params[key] = value
    allowed_model_types = [
        "1S1L",
        "1S2L",
        "2S1L",
        "2S2L",
        "1S3L",
        "2S3L",
        "other",
    ]
    if model_type not in allowed_model_types:
        raise typer.BadParameter(f"model_type must be one of {allowed_model_types}")
    if bands and len(bands) == 1 and "," in bands[0]:
        bands = bands[0].split(",")
    if (
        higher_order_effect
        and len(higher_order_effect) == 1
        and "," in higher_order_effect[0]
    ):
        higher_order_effect = higher_order_effect[0].split(",")
    sol = evt.add_solution(model_type=model_type, parameters=params, alias=alias)
    sol.bands = bands or []
    sol.higher_order_effects = higher_order_effect or []
    sol.t_ref = t_ref
    sol.used_astrometry = used_astrometry
    sol.used_postage_stamps = used_postage_stamps
    sol.limb_darkening_model = limb_darkening_model
    sol.limb_darkening_coeffs = _parse_pairs(limb_darkening_coeff)
    sol.parameter_uncertainties = _parse_pairs(parameter_uncertainty) or uncertainties
    sol.physical_parameters = _parse_pairs(physical_param)
    sol.log_likelihood = log_likelihood
    sol.relative_probability = relative_probability
    sol.n_data_points = n_data_points
    if cpu_hours is not None or wall_time_hours is not None:
        sol.set_compute_info(cpu_hours=cpu_hours, wall_time_hours=wall_time_hours)
    sol.lightcurve_plot_path = (
        str(lightcurve_plot_path) if lightcurve_plot_path else None
    )
    sol.lens_plane_plot_path = (
        str(lens_plane_plot_path) if lens_plane_plot_path else None
    )
    # Handle notes file logic
    canonical_notes_path = (
        Path(project_path) / "events" / event_id / "solutions" / f"{sol.solution_id}.md"
    )
    if notes_file is not None:
        sol.notes_path = str(notes_file)
    else:
        sol.notes_path = str(canonical_notes_path.relative_to(project_path))
    if dry_run:
        parsed = {
            "event_id": event_id,
            "model_type": model_type,
            "parameters": params,
            "bands": bands,
            "higher_order_effects": higher_order_effect,
            "t_ref": t_ref,
            "used_astrometry": used_astrometry,
            "used_postage_stamps": used_postage_stamps,
            "limb_darkening_model": limb_darkening_model,
            "limb_darkening_coeffs": _parse_pairs(limb_darkening_coeff),
            "parameter_uncertainties": _parse_pairs(parameter_uncertainty),
            "physical_parameters": _parse_pairs(physical_param),
            "log_likelihood": log_likelihood,
            "relative_probability": relative_probability,
            "n_data_points": n_data_points,
            "cpu_hours": cpu_hours,
            "wall_time_hours": wall_time_hours,
            "lightcurve_plot_path": (
                str(lightcurve_plot_path) if lightcurve_plot_path else None
            ),
            "lens_plane_plot_path": (
                str(lens_plane_plot_path) if lens_plane_plot_path else None
            ),
            "alias": alias,
            "notes_path": sol.notes_path,
        }
        console.print(Panel("Parsed Input", style="cyan"))
        console.print(json.dumps(parsed, indent=2))
        console.print(Panel("Schema Output", style="cyan"))
        console.print(sol.model_dump_json(indent=2))
        validation_messages = sol.run_validation()
        if validation_messages:
            console.print(Panel("Validation Warnings", style="yellow"))
            for msg in validation_messages:
                console.print(f"  • {msg}")
        else:
            console.print(Panel("Solution validated successfully!", style="green"))
        return
    # Only write files if not dry_run
    if notes_file is not None:
        # If a notes file is provided, do not overwrite it, just ensure path is set
        pass
    else:
        if notes is not None:
            canonical_notes_path.parent.mkdir(parents=True, exist_ok=True)
            canonical_notes_path.write_text(notes, encoding="utf-8")
        elif not canonical_notes_path.exists():
            canonical_notes_path.parent.mkdir(parents=True, exist_ok=True)
            canonical_notes_path.write_text("", encoding="utf-8")
    sub.save()
    validation_messages = sol.run_validation()
    if validation_messages:
        console.print(Panel("Validation Warnings", style="yellow"))
        for msg in validation_messages:
            console.print(f"  • {msg}")
    else:
        console.print(Panel("Solution validated successfully!", style="green"))
    console.print(f"Created solution: [bold cyan]{sol.solution_id}[/bold cyan]")


@app.command()
def deactivate(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Mark a solution as inactive so it is excluded from exports.

    Deactivates a solution by setting its is_active flag to False. Inactive
    solutions are excluded from submission exports and dossier generation,
    but their data remains intact and can be reactivated later.

    Args:
        solution_id: The unique identifier of the solution to deactivate.
        project_path: Directory of the submission project.

    Raises:
        typer.Exit: If the solution is not found in any event.

    Example:
        # Deactivate a specific solution
        microlens-submit deactivate abc12345-def6-7890-ghij-klmnopqrstuv ./project

        # The solution is now inactive and won't be included in exports
        microlens-submit export submission.zip ./project  # Excludes inactive solutions

    Note:
        This command only changes the active status. The solution data remains
        intact and can be reactivated using the activate command. Use this to
        keep alternative fits without including them in the final submission.
    """
    sub = load(str(project_path))
    for event in sub.events.values():
        if solution_id in event.solutions:
            event.solutions[solution_id].deactivate()
            sub.save()
            console.print(f"Deactivated {solution_id}")
            return
    console.print(f"Solution {solution_id} not found", style="bold red")
    raise typer.Exit(code=1)


@app.command()
def activate(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Activate a previously deactivated solution.

    Re-enables a solution that was previously deactivated, making it
    active again for inclusion in exports and dossier generation.

    Args:
        solution_id: UUID of the solution to activate.
        project_path: Path to the submission project directory.

    Example:
        >>> microlens-submit activate 12345678-1234-1234-1234-123456789abc ./my_project
        ✅ Activated solution 12345678...

    Note:
        This command automatically saves the change to disk.
        Only active solutions are included in submission exports.
    """
    submission = load(project_path)

    # Find the solution across all events
    solution = None
    event_id = None
    for eid, event in submission.events.items():
        if solution_id in event.solutions:
            solution = event.solutions[solution_id]
            event_id = eid
            break

    if solution is None:
        console.print(f"[red]Error: Solution {solution_id} not found[/red]")
        raise typer.Exit(1)

    solution.activate()
    submission.save()
    console.print(
        f"[green]✅ Activated solution {solution_id[:8]}... in event {event_id}[/green]"
    )


@app.command("remove-solution")
def remove_solution(
    solution_id: str,
    force: bool = typer.Option(
        False, "--force", help="Force removal of saved solutions (use with caution)"
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Completely remove a solution from the submission.

    ⚠️  WARNING: This permanently removes the solution from memory and any
    associated files. This action cannot be undone. Use deactivate instead
    if you want to keep the solution but exclude it from exports.

    Args:
        solution_id: UUID of the solution to remove.
        force: If True, skip safety checks and remove immediately.
        project_path: Path to the submission project directory.

    Example:
        >>> # Remove an unsaved solution (safe)
        >>> microlens-submit remove-solution 12345678-1234-1234-1234-123456789abc ./my_project
        🗑️  Removed solution 12345678... from event EVENT001

        >>> # Force remove a saved solution (use with caution!)
        >>> microlens-submit remove-solution 12345678-1234-1234-1234-123456789abc --force ./my_project
        🗑️  Removed solution 12345678... from event EVENT001

    Note:
        - Unsaved solutions can be removed safely
        - Saved solutions require --force to prevent accidental data loss
        - Removal cannot be undone - use deactivate if you're unsure
        - Temporary files (notes in tmp/) are automatically cleaned up
    """
    submission = load(project_path)

    # Find the solution across all events
    solution = None
    event_id = None
    for eid, event in submission.events.items():
        if solution_id in event.solutions:
            solution = event.solutions[solution_id]
            event_id = eid
            break

    if solution is None:
        console.print(f"[red]Error: Solution {solution_id} not found[/red]")
        raise typer.Exit(1)

    try:
        removed = submission.events[event_id].remove_solution(solution_id, force=force)
        if removed:
            submission.save()
            console.print(
                f"[green]✅ Solution {solution_id[:8]}... removed from event {event_id}[/green]"
            )
        else:
            console.print(f"[red]Error: Failed to remove solution {solution_id}[/red]")
            raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            f"[yellow]💡 Use --force to override safety checks, or use deactivate to keep the solution[/yellow]"
        )
        raise typer.Exit(1)


@app.command()
def remove_event(
    event_id: str,
    force: bool = typer.Option(
        False, "--force", help="Force removal even if event has saved solutions"
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Remove an entire event and all its solutions from the submission.

    ⚠️  WARNING: This permanently removes the event and ALL its solutions from
    the submission. This action cannot be undone. Use event.clear_solutions()
    instead if you want to keep the event but exclude all solutions from exports.

    Args:
        event_id: Identifier of the event to remove.
        force: If True, skip confirmation prompts and remove immediately.
        project_path: Path to the submission project directory.

    Example:
        >>> microlens-submit remove-event EVENT001 --force ./my_project
        ✅ Removed event EVENT001 and all its solutions

    Note:
        This command automatically saves the change to disk.
        Only active solutions are included in submission exports.
    """
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


@app.command()
def export(
    output_path: Path,
    force: bool = typer.Option(False, "--force", help="Skip validation prompts"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Generate a zip archive containing all active solutions.

    Creates a compressed zip file containing the complete submission data,
    including all active solutions, parameters, notes, and referenced files.
    The archive is suitable for submission to the challenge organizers.

    Before creating the export, the command validates the submission and
    displays any warnings. If validation issues are found, the user is
    prompted to continue or cancel the export (unless --force is used).

    Args:
        output_path: Path where the zip archive will be created.
        force: If True, skip validation prompts and continue with export.
        project_path: Directory of the submission project.

    Raises:
        typer.Exit: If validation fails and user cancels export.
        ValueError: If referenced files (plots, posterior data) don't exist.
        OSError: If unable to create the zip file.

    Example:
        # Export with validation prompts
        microlens-submit export submission.zip ./project

        # Force export without prompts
        microlens-submit export submission.zip --force ./project

        # Export to specific directory
        microlens-submit export /path/to/submissions/my_submission.zip ./project

    Note:
        Only active solutions are included in the export. Inactive solutions
        are excluded even if they exist in the project. The export includes:
        - submission.json with metadata
        - All active solutions with parameters
        - Notes files for each solution
        - Referenced files (plots, posterior data)

        Relative probabilities are automatically calculated for solutions
        that don't have them set, using BIC if sufficient data is available.
    """
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


@app.command("generate-dossier")
def generate_dossier(
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
    event_id: Optional[str] = typer.Option(
        None,
        "--event-id",
        help="Generate dossier for a specific event only (omit for full dossier)",
    ),
    solution_id: Optional[str] = typer.Option(
        None,
        "--solution-id",
        help="Generate dossier for a specific solution only (omit for full dossier)",
    ),
) -> None:
    """Generate an HTML dossier for the submission.

    Creates a comprehensive HTML dashboard that provides an overview of the submission,
    including event summaries, solution statistics, and metadata. The dossier is saved
    to the `dossier/` subdirectory of the project directory with the main dashboard as index.html.

    The dossier includes:
    - Main dashboard (index.html) with submission overview and statistics
    - Individual event pages for each event with solution tables
    - Individual solution pages with parameters, notes, and metadata
    - Full comprehensive dossier (full_dossier_report.html) for printing

    All pages use Tailwind CSS for styling and include syntax highlighting for
    code blocks in participant notes.

    Args:
        project_path: Directory of the submission project.
        event_id: If specified, only generate dossier for this event.
        solution_id: If specified, only generate dossier for this solution.

    Raises:
        OSError: If unable to create output directory or write files.
        ValueError: If submission data is invalid or missing required fields.

    Example:
        # Generate complete dossier for all events and solutions
        microlens-submit generate-dossier ./project

        # Generate dossier for specific event only
        microlens-submit generate-dossier --event-id EVENT001 ./project

        # Generate dossier for specific solution only
        microlens-submit generate-dossier --solution-id abc12345-def6-7890-ghij-klmnopqrstuv ./project

        # Files created:
        # ./project/dossier/
        # ├── index.html (main dashboard)
        # ├── full_dossier_report.html (printable version)
        # ├── EVENT001.html (event page)
        # ├── solution_id.html (solution pages)
        # └── assets/ (logos and icons)

    Note:
        The dossier is generated in the dossier/ subdirectory of the project.
        The main dashboard provides navigation to individual event and solution pages.
        The full dossier report combines all content into a single printable document.
        GitHub repository links are included if available in the submission metadata.
    """
    sub = load(str(project_path))
    output_dir = Path(project_path) / "dossier"
    
    # Import dossier generation functions
    from .dossier import (
        generate_dashboard_html,
        generate_event_page,
        generate_solution_page,
        _generate_full_dossier_report_html,
    )

    if solution_id:
        # Find the solution across all events (same pattern as other CLI commands)
        solution = None
        containing_event_id = None
        for eid, event in sub.events.items():
            if solution_id in event.solutions:
                solution = event.solutions[solution_id]
                containing_event_id = eid
                break
        
        if solution is None:
            console.print(f"Solution {solution_id} not found", style="bold red")
            raise typer.Exit(1)
        
        # Create output directory and assets subdirectory
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "assets").mkdir(exist_ok=True)
        
        # Generate only the specific solution page
        event = sub.events[containing_event_id]
        console.print(
            Panel(f"Generating dossier for solution {solution_id} in event {containing_event_id}...", style="cyan")
        )
        generate_solution_page(solution, event, sub, output_dir)
        
    elif event_id:
        # Generate only the specific event page
        if event_id not in sub.events:
            console.print(f"Event {event_id} not found", style="bold red")
            raise typer.Exit(1)
        
        # Create output directory and assets subdirectory
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "assets").mkdir(exist_ok=True)
        
        event = sub.events[event_id]
        console.print(
            Panel(f"Generating dossier for event {event_id}...", style="cyan")
        )
        generate_event_page(event, sub, output_dir)
        
    else:
        # Generate full dossier (all events and solutions)
        console.print(
            Panel("Generating comprehensive dossier for all events and solutions...", style="cyan")
        )
        generate_dashboard_html(sub, output_dir)
        
        # Generate comprehensive printable dossier
        console.print(
            Panel("Generating comprehensive printable dossier...", style="cyan")
        )
        _generate_full_dossier_report_html(sub, output_dir)
        
        # Replace placeholder in index.html with the real link
        dashboard_path = output_dir / "index.html"
        if dashboard_path.exists():
            with dashboard_path.open("r", encoding="utf-8") as f:
                dashboard_html = f.read()
            dashboard_html = dashboard_html.replace(
                "<!--FULL_DOSSIER_LINK_PLACEHOLDER-->",
                '<div class="text-center"><a href="./full_dossier_report.html" class="inline-block bg-rtd-accent text-white py-3 px-6 rounded-lg shadow-md hover:bg-rtd-secondary transition-colors duration-200 text-lg font-semibold mt-8">View Full Comprehensive Dossier (Printable)</a></div>',
            )
            with dashboard_path.open("w", encoding="utf-8") as f:
                f.write(dashboard_html)
        console.print(Panel("Comprehensive dossier generated!", style="bold green"))

    console.print(
        Panel(
            f"Dossier generated successfully at {output_dir / 'index.html'}",
            style="bold green",
        )
    )


@app.command("list-solutions")
def list_solutions(
    event_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Display a table of solutions for a specific event.

    Shows a formatted table containing all solutions for the specified event,
    including their model types, active status, and notes snippets. The table
    is displayed using rich formatting with color-coded status indicators.

    Args:
        event_id: Identifier of the event to list solutions for.
        project_path: Directory of the submission project.

    Raises:
        typer.Exit: If the event is not found in the project.

    Example:
        # List all solutions for EVENT001
        microlens-submit list-solutions EVENT001 ./project

        # Output shows:
        # ┌─────────────────────────────────────────────────────────┬──────────┬────────┬─────────────────┐
        # │ Solution ID                                             │ Model    │ Status │ Notes           │
        # │                                                         │ Type     │        │                 │
        # ├─────────────────────────────────────────────────────────┼──────────┼────────┼─────────────────┤
        # │ abc12345-def6-7890-ghij-klmnopqrstuv                   │ 1S1L     │ Active │ Simple point... │
        # │ def67890-abc1-2345-klmn-opqrstuvwxyz                   │ 1S2L     │ Active │ Binary lens...  │
        # └─────────────────────────────────────────────────────────┴──────────┴────────┴─────────────────┘

    Note:
        The table shows both active and inactive solutions. Active solutions
        are marked in green, inactive solutions in red. Notes are truncated
        to fit the table display. Use the solution ID to reference specific
        solutions in other commands.
    """
    sub = load(str(project_path))
    if event_id not in sub.events:
        console.print(f"Event {event_id} not found", style="bold red")
        raise typer.Exit(code=1)
    evt = sub.events[event_id]
    table = Table(title=f"Solutions for {event_id}")
    table.add_column("Solution ID")
    table.add_column("Model Type")
    table.add_column("Status")
    table.add_column("Notes")
    for sol in evt.solutions.values():
        status = "[green]Active[/green]" if sol.is_active else "[red]Inactive[/red]"
        table.add_row(sol.solution_id, sol.model_type, status, sol.notes)
    console.print(table)


@app.command("compare-solutions")
def compare_solutions(
    event_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Rank active solutions for an event using the Bayesian Information Criterion.

    Compares all active solutions for the specified event using BIC to rank
    them by relative probability. The BIC is calculated as:

        BIC = k * ln(n) - 2 * ln(L)

    where k is the number of parameters, n is the number of data points,
    and L is the likelihood. Lower BIC values indicate better models.

    The command displays a table with solution rankings and automatically
    calculates relative probabilities for solutions that don't have them set.

    Args:
        event_id: Identifier of the event to compare solutions for.
        project_path: Directory of the submission project.

    Raises:
        typer.Exit: If the event is not found in the project.

    Example:
        # Compare solutions for EVENT001
        microlens-submit compare-solutions EVENT001 ./project

        # Output shows:
        # ┌─────────────────────────────────────────────────────────┬──────────┬─────────────────────┬─────────┬─────────────────┬─────────┬─────────────────┐
        # │ Solution ID                                             │ Model    │ Higher-Order        │ # Params│ Log-Likelihood  │ BIC     │ Relative Prob   │
        # │                                                         │ Type     │ Effects             │ (k)     │                 │         │                 │
        # ├─────────────────────────────────────────────────────────┼──────────┼─────────────────────┼─────────┼─────────────────┼─────────┼─────────────────┤
        # │ abc12345-def6-7890-ghij-klmnopqrstuv                   │ 1S1L     │ -                   │ 3       │ -1234.56        │ 2475.12 │ 0.600           │
        # │ def67890-abc1-2345-klmn-opqrstuvwxyz                   │ 1S2L     │ parallax,finite-... │ 6       │ -1189.34        │ 2394.68 │ 0.400           │
        # └─────────────────────────────────────────────────────────┴──────────┴─────────────────────┴─────────┴─────────────────┴─────────┴─────────────────┘

    Note:
        Only active solutions with valid log_likelihood and n_data_points
        are included in the comparison. Solutions missing these values are
        skipped with a warning. Relative probabilities are automatically
        calculated using BIC if not already set.
    """
    sub = load(str(project_path))
    if event_id not in sub.events:
        console.print(f"Event {event_id} not found", style="bold red")
        raise typer.Exit(code=1)

    evt = sub.events[event_id]
    solutions = []
    for s in evt.get_active_solutions():
        if s.log_likelihood is None or s.n_data_points is None:
            continue
        if s.n_data_points <= 0:
            console.print(
                f"Skipping {s.solution_id}: n_data_points <= 0",
                style="bold red",
            )
            continue
        solutions.append(s)

    table = Table(title=f"Solution Comparison for {event_id}")
    table.add_column("Solution ID")
    table.add_column("Model Type")
    table.add_column("Higher-Order Effects")
    table.add_column("# Params (k)")
    table.add_column("Log-Likelihood")
    table.add_column("BIC")
    table.add_column("Relative Prob")

    rel_prob_map: dict[str, float] = {}
    note = None
    if solutions:
        provided_sum = sum(
            s.relative_probability or 0.0
            for s in solutions
            if s.relative_probability is not None
        )
        need_calc = [s for s in solutions if s.relative_probability is None]
        if need_calc:
            can_calc = all(
                s.log_likelihood is not None
                and s.n_data_points
                and s.n_data_points > 0
                and len(s.parameters) > 0
                for s in need_calc
            )
            remaining = max(1.0 - provided_sum, 0.0)
            if can_calc:
                bic_vals = {
                    s.solution_id: len(s.parameters) * math.log(s.n_data_points)
                    - 2 * s.log_likelihood
                    for s in need_calc
                }
                bic_min = min(bic_vals.values())
                weights = {
                    sid: math.exp(-0.5 * (bic - bic_min))
                    for sid, bic in bic_vals.items()
                }
                wsum = sum(weights.values())
                for sid, w in weights.items():
                    rel_prob_map[sid] = (
                        remaining * w / wsum if wsum > 0 else remaining / len(weights)
                    )
                note = "Relative probabilities calculated using BIC"
            else:
                eq = remaining / len(need_calc) if need_calc else 0.0
                for s in need_calc:
                    rel_prob_map[s.solution_id] = eq
                note = "Relative probabilities set equal due to missing data"

    rows = []
    for sol in solutions:
        k = len(sol.parameters)
        bic = k * math.log(sol.n_data_points) - 2 * sol.log_likelihood
        rp = (
            sol.relative_probability
            if sol.relative_probability is not None
            else rel_prob_map.get(sol.solution_id)
        )
        rows.append(
            (
                bic,
                [
                    sol.solution_id,
                    sol.model_type,
                    (
                        ",".join(sol.higher_order_effects)
                        if sol.higher_order_effects
                        else "-"
                    ),
                    str(k),
                    f"{sol.log_likelihood:.2f}",
                    f"{bic:.2f}",
                    f"{rp:.3f}" if rp is not None else "N/A",
                ],
            )
        )

    for _, cols in sorted(rows, key=lambda x: x[0]):
        table.add_row(*cols)

    console.print(table)
    if note:
        console.print(note, style="yellow")


@app.command("validate-solution")
def validate_solution(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Validate a specific solution's parameters and configuration.

    This command uses the centralized validation logic to check:
    - Parameter completeness for the model type
    - Higher-order effect requirements
    - Parameter types and value ranges
    - Physical consistency of parameters

    The validation provides detailed feedback about any issues found,
    helping ensure solutions are complete and ready for submission.

    Args:
        solution_id: The unique identifier of the solution to validate.
        project_path: Directory of the submission project.

    Raises:
        typer.Exit: If the solution is not found in any event.

    Example:
        # Validate a specific solution
        microlens-submit validate-solution abc12345-def6-7890-ghij-klmnopqrstuv ./project

        # Output shows:
        # ✅ All validations passed for abc12345-def6-7890-ghij-klmnopqrstuv (event EVENT001)

        # Or if issues are found:
        # ┌─────────────────────────────────────────────────────────────────────────────┐
        # │ Validation Results for abc12345-def6-7890-ghij-klmnopqrstuv (event EVENT001) │
        # └─────────────────────────────────────────────────────────────────────────────┘
        #   • Missing required parameter 'tE' for model type '1S1L'
        #   • Parameter 'u0' has invalid value: -0.5 (must be positive)

    Note:
        The validation checks are comprehensive and cover all model types
        and higher-order effects. Always validate solutions before submission
        to catch any issues early.
    """
    sub = load(str(project_path))

    # Find the solution
    target_solution = None
    target_event_id = None
    for event_id, event in sub.events.items():
        if solution_id in event.solutions:
            target_solution = event.solutions[solution_id]
            target_event_id = event_id
            break

    if target_solution is None:
        console.print(f"Solution {solution_id} not found", style="bold red")
        raise typer.Exit(code=1)

    # Run validation
    messages = target_solution.run_validation()

    if not messages:
        console.print(
            Panel(
                f"✅ All validations passed for {solution_id} (event {target_event_id})",
                style="bold green",
            )
        )
    else:
        console.print(
            Panel(
                f"Validation Results for {solution_id} (event {target_event_id})",
                style="yellow",
            )
        )
        for msg in messages:
            console.print(f"  • {msg}")


@app.command("validate-submission")
def validate_submission(
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Validate the entire submission for missing or incomplete information.

    This command performs comprehensive validation of all active solutions
    and returns a list of warnings describing potential issues. It checks
    for common problems like missing metadata, incomplete solutions, and
    validation issues in individual solutions.

    The validation is particularly strict about the GitHub repository URL,
    which is required for submission. If repo_url is missing or invalid,
    the command will exit with an error.

    Args:
        project_path: Directory of the submission project.

    Raises:
        typer.Exit: If repo_url is missing or invalid (exit code 1).

    Example:
        # Validate the entire submission
        microlens-submit validate-submission ./project

        # Output if all validations pass:
        # ┌─────────────────────────────────────┐
        # │ ✅ All validations passed!          │
        # └─────────────────────────────────────┘

        # Output if issues are found:
        # ┌─────────────────────────────────────┐
        # │ Validation Warnings                 │
        # └─────────────────────────────────────┘
        #   • Hardware info is missing
        #   • Event EVENT001: Solution abc12345 is missing log_likelihood
        #   • Solution def67890 in event EVENT002: Missing required parameter 'tE'

    Note:
        This command checks for:
        - Missing or invalid repo_url (GitHub repository URL)
        - Missing hardware information
        - Events with no active solutions
        - Solutions with missing required metadata
        - Individual solution validation issues
        - Relative probability consistency

        Always run this command before exporting your submission to ensure
        all required information is present and valid.
    """
    sub = load(str(project_path))
    warnings = sub.run_validation()

    # Check for missing repo_url
    repo_url_warning = next(
        (w for w in warnings if "repo_url" in w.lower() or "github" in w.lower()), None
    )
    if repo_url_warning:
        console.print(
            Panel(
                f"[red]Error: {repo_url_warning}\nPlease add your GitHub repository URL using 'microlens-submit set-repo-url <url> <project_dir>'.[/red]",
                style="bold red",
            )
        )
        raise typer.Exit(code=1)

    if not warnings:
        console.print(Panel("\u2705 All validations passed!", style="bold green"))
    else:
        console.print(Panel("Validation Warnings", style="yellow"))
        for warning in warnings:
            console.print(f"  \u2022 {warning}")
        console.print(f"\nFound {len(warnings)} validation issue(s)", style="yellow")


@app.command("validate-event")
def validate_event(
    event_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Validate all solutions for a specific event.

    Runs validation on all solutions (both active and inactive) for the
    specified event. This provides a focused validation check for a single
    event, useful when working on specific events or debugging issues.

    Args:
        event_id: Identifier of the event to validate.
        project_path: Directory of the submission project.

    Raises:
        typer.Exit: If the event is not found in the project.

    Example:
        # Validate all solutions for EVENT001
        microlens-submit validate-event EVENT001 ./project

        # Output shows:
        # ┌─────────────────────────────────────┐
        # │ Validating Event: EVENT001          │
        # └─────────────────────────────────────┘
        #
        # Solution abc12345-def6-7890-ghij-klmnopqrstuv:
        #   • Missing required parameter 'tE' for model type '1S1L'
        #
        # ✅ Solution def67890-abc1-2345-klmn-opqrstuvwxyz: All validations passed

        # ┌─────────────────────────────────────┐
        # │ ✅ All solutions passed validation! │
        # └─────────────────────────────────────┘

    Note:
        This command validates all solutions in the event, regardless of
        their active status. It's useful for checking solutions that might
        be inactive but could be reactivated later.
    """
    sub = load(str(project_path))

    if event_id not in sub.events:
        console.print(f"Event {event_id} not found", style="bold red")
        raise typer.Exit(code=1)

    event = sub.events[event_id]
    all_messages = []

    console.print(Panel(f"Validating Event: {event_id}", style="cyan"))

    for solution in event.solutions.values():
        messages = solution.run_validation()
        if messages:
            console.print(f"\n[bold]Solution {solution.solution_id}:[/bold]")
            for msg in messages:
                console.print(f"  • {msg}")
                all_messages.append(f"{solution.solution_id}: {msg}")
        else:
            console.print(f"✅ Solution {solution.solution_id}: All validations passed")

    if not all_messages:
        console.print(Panel("✅ All solutions passed validation!", style="bold green"))
    else:
        console.print(
            f"\nFound {len(all_messages)} validation issue(s) across all solutions",
            style="yellow",
        )


def _parse_structured_params_file(params_file: Path) -> tuple[dict, dict]:
    """Parse a structured parameter file that can contain both parameters and uncertainties.

    Supports both JSON and YAML formats. The file can have either:
    1. Simple format: {"param1": value1, "param2": value2, ...}
    2. Structured format: {"parameters": {...}, "uncertainties": {...}}

    Args:
        params_file: Path to the parameter file (JSON or YAML format).

    Returns:
        tuple: (parameters_dict, uncertainties_dict) - Two dictionaries containing
               the parsed parameters and their uncertainties.

    Raises:
        OSError: If the file cannot be read.
        json.JSONDecodeError: If JSON parsing fails.
        yaml.YAMLError: If YAML parsing fails.

    Example:
        # Simple format (all keys are parameters)
        # params.json:
        # {
        #   "t0": 2459123.5,
        #   "u0": 0.1,
        #   "tE": 20.0
        # }

        # Structured format (separate parameters and uncertainties)
        # params.yaml:
        # parameters:
        #   t0: 2459123.5
        #   u0: 0.1
        #   tE: 20.0
        # uncertainties:
        #   t0: 0.1
        #   u0: 0.01
        #   tE: 0.5

        params, uncertainties = _parse_structured_params_file(Path("params.json"))

    Note:
        This function automatically detects the file format based on the file
        extension (.json, .yaml, .yml). For structured format, both parameters
        and uncertainties sections are optional - missing sections return empty
        dictionaries.
    """
    import yaml

    with params_file.open("r", encoding="utf-8") as fh:
        if params_file.suffix.lower() in [".yaml", ".yml"]:
            data = yaml.safe_load(fh)
        else:
            data = json.load(fh)

    # Handle structured format
    if isinstance(data, dict) and ("parameters" in data or "uncertainties" in data):
        parameters = data.get("parameters", {})
        uncertainties = data.get("uncertainties", {})
    else:
        # Simple format - all keys are parameters
        parameters = data
        uncertainties = {}

    return parameters, uncertainties


@app.command("edit-solution")
def edit_solution(
    solution_id: str,
    relative_probability: Optional[float] = typer.Option(
        None,
        "--relative-probability",
        help="Relative probability of this solution",
    ),
    log_likelihood: Optional[float] = typer.Option(None, help="Log likelihood"),
    n_data_points: Optional[int] = typer.Option(
        None,
        "--n-data-points",
        help="Number of data points used in this solution",
    ),
    alias: Optional[str] = typer.Option(
        None,
        "--alias",
        help="Set or update the human-readable alias for this solution (must be unique within the event)",
    ),
    notes: Optional[str] = typer.Option(
        None, help="Notes for the solution (supports Markdown formatting)"
    ),
    notes_file: Optional[Path] = typer.Option(
        None,
        "--notes-file",
        help="Path to a Markdown file for solution notes (mutually exclusive with --notes)",
    ),
    append_notes: Optional[str] = typer.Option(
        None,
        "--append-notes",
        help="Append text to existing notes (use --notes to replace instead)",
    ),
    clear_notes: bool = typer.Option(False, help="Clear all notes"),
    clear_relative_probability: bool = typer.Option(
        False, help="Clear relative probability"
    ),
    clear_log_likelihood: bool = typer.Option(False, help="Clear log likelihood"),
    clear_n_data_points: bool = typer.Option(False, help="Clear n_data_points"),
    clear_parameter_uncertainties: bool = typer.Option(
        False, help="Clear parameter uncertainties"
    ),
    clear_physical_parameters: bool = typer.Option(
        False, help="Clear physical parameters"
    ),
    cpu_hours: Optional[float] = typer.Option(None, help="CPU hours used"),
    wall_time_hours: Optional[float] = typer.Option(None, help="Wall time hours used"),
    param: Optional[List[str]] = typer.Option(
        None, help="Model parameters as key=value (updates existing parameters)"
    ),
    param_uncertainty: Optional[List[str]] = typer.Option(
        None,
        "--param-uncertainty",
        help="Parameter uncertainties as key=value (updates existing uncertainties)",
    ),
    higher_order_effect: Optional[List[str]] = typer.Option(
        None,
        "--higher-order-effect",
        help="Higher-order effects (replaces existing effects)",
    ),
    clear_higher_order_effects: bool = typer.Option(
        False, help="Clear all higher-order effects"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be changed without saving",
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Edit an existing solution's attributes, including file-based notes and alias.
    
    This command allows you to modify various attributes of an existing solution
    without having to recreate it. It supports updating parameters, metadata,
    notes, alias, and compute information. The command provides detailed feedback about
    what changes were made.
    
    **Alias Management:**
    - Use --alias to set or update the human-readable alias for the solution (e.g., "best_fit").
    - The combination of event_id and alias must be unique within the project. If not, an error will be raised during validation or save operations.
    
    **Notes Management:**
    - Use --notes to replace existing notes with new content
    - Use --append-notes to add text to existing notes
    - Use --notes-file to reference an external Markdown file
    - Use --clear-notes to remove all notes
    
    **Parameter Updates:**
    - Use --param to update individual model parameters
    - Use --param-uncertainty to update parameter uncertainties
    - Use --higher-order-effect to replace all higher-order effects
    
    **Metadata Updates:**
    - Use --relative-probability, --log-likelihood, --n-data-points
    - Use --cpu-hours and --wall-time-hours to update compute info
    - Use --clear-* flags to remove specific fields
    
    Args:
        solution_id: The unique identifier of the solution to edit.
        alias: Set or update the human-readable alias for this solution (must be unique within the event).
        relative_probability: New relative probability value.
        log_likelihood: New log-likelihood value.
        n_data_points: New number of data points value.
        notes: New notes content (replaces existing notes).
        notes_file: Path to external notes file.
        append_notes: Text to append to existing notes.
        clear_notes: If True, clear all notes.
        clear_relative_probability: If True, clear relative probability.
        clear_log_likelihood: If True, clear log likelihood.
        clear_n_data_points: If True, clear n_data_points.
        clear_parameter_uncertainties: If True, clear parameter uncertainties.
        clear_physical_parameters: If True, clear physical parameters.
        cpu_hours: New CPU hours value.
        wall_time_hours: New wall time hours value.
        param: Model parameters as key=value pairs (updates existing).
        param_uncertainty: Parameter uncertainties as key=value pairs.
        higher_order_effect: Higher-order effects (replaces existing).
        clear_higher_order_effects: If True, clear all higher-order effects.
        dry_run: If True, show changes without saving.
        project_path: Directory of the submission project.
    
    Raises:
        typer.Exit: If the solution is not found.
        typer.BadParameter: If parameter format is invalid.
    
    Example:
        # Update solution alias
        microlens-submit edit-solution abc12345-def6-7890-ghij-klmnopqrstuv ./project \
            --alias best_fit
        
    Note:
        This command only modifies the specified fields. Unspecified fields
        remain unchanged. Use --dry-run to preview changes before applying them.
        The command automatically saves changes to disk after successful updates.
    """
    sub = load(str(project_path))
    target_solution = None
    target_event_id = None
    for event_id, event in sub.events.items():
        if solution_id in event.solutions:
            target_solution = event.solutions[solution_id]
            target_event_id = event_id
            break
    if target_solution is None:
        console.print(f"Solution {solution_id} not found", style="bold red")
        raise typer.Exit(code=1)
    changes = []
    if alias is not None:
        if target_solution.alias != alias:
            changes.append(f"Update alias: {target_solution.alias}  {alias}")
            target_solution.alias = alias
    if clear_relative_probability:
        if target_solution.relative_probability is not None:
            changes.append(
                f"Clear relative_probability: {target_solution.relative_probability}"
            )
            target_solution.relative_probability = None
    elif relative_probability is not None:
        if target_solution.relative_probability != relative_probability:
            changes.append(
                f"Update relative_probability: {target_solution.relative_probability}  {relative_probability}"
            )
            target_solution.relative_probability = relative_probability
    if clear_log_likelihood:
        if target_solution.log_likelihood is not None:
            changes.append(f"Clear log_likelihood: {target_solution.log_likelihood}")
            target_solution.log_likelihood = None
    elif log_likelihood is not None:
        if target_solution.log_likelihood != log_likelihood:
            changes.append(
                f"Update log_likelihood: {target_solution.log_likelihood}  {log_likelihood}"
            )
            target_solution.log_likelihood = log_likelihood
    if clear_n_data_points:
        if target_solution.n_data_points is not None:
            changes.append(f"Clear n_data_points: {target_solution.n_data_points}")
            target_solution.n_data_points = None
    elif n_data_points is not None:
        if target_solution.n_data_points != n_data_points:
            changes.append(
                f"Update n_data_points: {target_solution.n_data_points}  {n_data_points}"
            )
            target_solution.n_data_points = n_data_points
    # Notes file logic
    canonical_notes_path = (
        Path(project_path)
        / "events"
        / target_event_id
        / "solutions"
        / f"{target_solution.solution_id}.md"
    )
    if notes_file is not None:
        target_solution.notes_path = str(notes_file)
        changes.append(f"Set notes_path to {notes_file}")
    elif notes is not None:
        target_solution.notes_path = str(canonical_notes_path.relative_to(project_path))
        canonical_notes_path.parent.mkdir(parents=True, exist_ok=True)
        canonical_notes_path.write_text(notes, encoding="utf-8")
        changes.append(f"Updated notes in {canonical_notes_path}")
    elif append_notes is not None:
        if target_solution.notes_path:
            notes_file_path = Path(project_path) / target_solution.notes_path
            old_content = (
                notes_file_path.read_text(encoding="utf-8")
                if notes_file_path.exists()
                else ""
            )
            notes_file_path.parent.mkdir(parents=True, exist_ok=True)
            notes_file_path.write_text(
                old_content + "\n" + append_notes, encoding="utf-8"
            )
            changes.append(f"Appended notes in {notes_file_path}")
    elif clear_notes:
        if target_solution.notes_path:
            notes_file_path = Path(project_path) / target_solution.notes_path
            notes_file_path.parent.mkdir(parents=True, exist_ok=True)
            notes_file_path.write_text("", encoding="utf-8")
            changes.append(f"Cleared notes in {notes_file_path}")
    if clear_parameter_uncertainties:
        if target_solution.parameter_uncertainties:
            changes.append("Clear parameter_uncertainties")
            target_solution.parameter_uncertainties = None
    if clear_physical_parameters:
        if target_solution.physical_parameters:
            changes.append("Clear physical_parameters")
            target_solution.physical_parameters = None
    if cpu_hours is not None or wall_time_hours is not None:
        old_cpu = target_solution.compute_info.get("cpu_hours")
        old_wall = target_solution.compute_info.get("wall_time_hours")
        if cpu_hours is not None and old_cpu != cpu_hours:
            changes.append(f"Update cpu_hours: {old_cpu} → {cpu_hours}")
        if wall_time_hours is not None and old_wall != wall_time_hours:
            changes.append(f"Update wall_time_hours: {old_wall} → {wall_time_hours}")
        target_solution.set_compute_info(
            cpu_hours=cpu_hours if cpu_hours is not None else old_cpu,
            wall_time_hours=(
                wall_time_hours if wall_time_hours is not None else old_wall
            ),
        )
    if param:
        for p in param:
            if "=" not in p:
                raise typer.BadParameter(f"Invalid parameter format: {p}")
            key, value = p.split("=", 1)
            try:
                new_value = json.loads(value)
            except json.JSONDecodeError:
                new_value = value
            old_value = target_solution.parameters.get(key)
            if old_value != new_value:
                changes.append(f"Update parameter {key}: {old_value} → {new_value}")
                target_solution.parameters[key] = new_value
    if param_uncertainty:
        if target_solution.parameter_uncertainties is None:
            target_solution.parameter_uncertainties = {}
        for p in param_uncertainty:
            if "=" not in p:
                raise typer.BadParameter(f"Invalid uncertainty format: {p}")
            key, value = p.split("=", 1)
            try:
                new_value = json.loads(value)
            except json.JSONDecodeError:
                new_value = value
            old_value = target_solution.parameter_uncertainties.get(key)
            if old_value != new_value:
                changes.append(f"Update uncertainty {key}: {old_value} → {new_value}")
                target_solution.parameter_uncertainties[key] = new_value
    if clear_higher_order_effects:
        if target_solution.higher_order_effects:
            changes.append(
                f"Clear higher_order_effects: {target_solution.higher_order_effects}"
            )
            target_solution.higher_order_effects = []
    elif higher_order_effect:
        if target_solution.higher_order_effects != higher_order_effect:
            changes.append(
                f"Update higher_order_effects: {target_solution.higher_order_effects} → {higher_order_effect}"
            )
            target_solution.higher_order_effects = higher_order_effect
    if dry_run:
        if changes:
            console.print(
                Panel(
                    f"Changes for {solution_id} (event {target_event_id})", style="cyan"
                )
            )
            for change in changes:
                console.print(f"  • {change}")
        else:
            console.print(Panel("No changes would be made", style="yellow"))
        return
    if changes:
        sub.save()
        console.print(
            Panel(f"Updated {solution_id} (event {target_event_id})", style="green")
        )
        for change in changes:
            console.print(f"  • {change}")
    else:
        console.print(Panel("No changes made", style="yellow"))


@app.command("notes")
def edit_notes(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Open the notes file for a solution in the default text editor.

    Launches the system's default text editor (or a fallback) to edit the
    notes file for the specified solution. This provides a convenient way
    to edit solution notes without having to manually locate the file.

    The command uses the $EDITOR environment variable if set, otherwise
    falls back to nano, then vi. The notes file is created if it doesn't
    exist.

    Args:
        solution_id: The unique identifier of the solution to edit notes for.
        project_path: Directory of the submission project.

    Raises:
        typer.Exit: If the solution is not found or no editor is available.

    Example:
        # Edit notes for a specific solution
        microlens-submit notes abc12345-def6-7890-ghij-klmnopqrstuv ./project

        # This will open the notes file in your default editor:
        # ./project/events/EVENT001/solutions/abc12345-def6-7890-ghij-klmnopqrstuv.md

    Note:
        The notes file is opened in the system's default text editor.
        If $EDITOR is not set, the command tries nano, then vi as fallbacks.
        The notes file supports Markdown formatting and will be rendered
        as HTML in the dossier with syntax highlighting for code blocks.
    """
    sub = load(str(project_path))
    for event in sub.events.values():
        if solution_id in event.solutions:
            sol = event.solutions[solution_id]
            if not sol.notes_path:
                console.print(
                    f"No notes file associated with solution {solution_id}",
                    style="bold red",
                )
                raise typer.Exit(code=1)
            notes_file = Path(project_path) / sol.notes_path
            notes_file.parent.mkdir(parents=True, exist_ok=True)
            if not notes_file.exists():
                notes_file.write_text("", encoding="utf-8")
            editor = os.environ.get("EDITOR", None)
            if editor:
                os.system(f'{editor} "{notes_file}"')
            else:
                # Try nano, then vi
                for fallback in ["nano", "vi"]:
                    if os.system(f"command -v {fallback} > /dev/null 2>&1") == 0:
                        os.system(f'{fallback} "{notes_file}"')
                        break
                else:
                    console.print(
                        f"Could not find an editor to open {notes_file}",
                        style="bold red",
                    )
                    raise typer.Exit(code=1)
            return
    console.print(f"Solution {solution_id} not found", style="bold red")
    raise typer.Exit(code=1)


@app.command()
def set_repo_url(
    repo_url: str = typer.Argument(
        ..., help="GitHub repository URL (e.g. https://github.com/owner/repo)"
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Set or update the GitHub repository URL in the submission metadata.

    Updates the repo_url field in submission.json with the provided GitHub
    repository URL. This URL is required for submission validation and is
    displayed in the generated dossier.

    The command accepts various GitHub URL formats:
    - HTTPS: https://github.com/owner/repo
    - SSH: git@github.com:owner/repo.git
    - With or without .git extension

    Args:
        repo_url: GitHub repository URL in any standard format.
        project_path: Directory of the submission project.

    Raises:
        OSError: If unable to write to submission.json.

    Example:
        # Set repository URL using HTTPS format
        microlens-submit set-repo-url https://github.com/team-alpha/microlens-submit ./project

        # Set repository URL using SSH format
        microlens-submit set-repo-url git@github.com:team-alpha/microlens-submit.git ./project

        # Update existing repository URL
        microlens-submit set-repo-url https://github.com/team-alpha/new-repo ./project

    Note:
        The repository URL is used for:
        - Submission validation (required field)
        - Display in the generated dossier
        - Linking to specific commits in solution pages

        The URL should point to the repository containing your analysis code
        and submission preparation scripts.
    """
    sub = load(str(project_path))
    sub.repo_url = repo_url
    sub.save()
    console.print(
        Panel(
            f"Set repo_url to {repo_url} in {project_path}/submission.json",
            style="bold green",
        )
    )


@app.command("set-hardware-info")
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
    """Set or update hardware information in the submission metadata.

    Updates the hardware_info field in submission.json with computational
    resource details. This information is displayed in the generated dossier
    and helps with reproducibility and resource tracking.

    The command accepts various hardware information fields and can be used
    to update existing information or set it for the first time.

    Args:
        cpu: Basic CPU model/description (e.g., "Intel Xeon E5-2680 v4").
        cpu_details: Detailed CPU information (takes precedence over --cpu).
        memory_gb: Memory in gigabytes (e.g., 64.0).
        ram_gb: RAM in gigabytes (alternative to --memory-gb).
        platform: Platform description (e.g., "Local Analysis", "Roman Nexus").
        nexus_image: Roman Nexus image identifier.
        clear: If True, clear all existing hardware info before setting new values.
        dry_run: If True, show what would be changed without saving.
        project_path: Directory of the submission project.

    Raises:
        OSError: If unable to write to submission.json.

    Example:
        # Set basic hardware info
        microlens-submit set-hardware-info --cpu "Intel Xeon E5-2680 v4" --memory-gb 64 ./project

        # Set detailed platform info
        microlens-submit set-hardware-info --platform "Local Analysis" --cpu-details "Intel Xeon E5-2680 v4 @ 2.4GHz" ./project

        # Set Roman Nexus info
        microlens-submit set-hardware-info --platform "Roman Nexus" --nexus-image "roman-science-platform:latest" ./project

        # Update existing info
        microlens-submit set-hardware-info --memory-gb 128 ./project

        # Clear and set new info
        microlens-submit set-hardware-info --clear --cpu "AMD EPYC" --memory-gb 256 ./project

        # Dry run to preview changes
        microlens-submit set-hardware-info --cpu "Intel i7" --memory-gb 32 --dry-run ./project

    Note:
        Hardware information is used for:
        - Display in the generated dossier
        - Reproducibility documentation
        - Resource usage tracking

        The --cpu-details option takes precedence over --cpu if both are provided.
        The --memory-gb and --ram-gb options are equivalent; use whichever is clearer.
        Use --clear to replace all existing hardware info with new values.
    """
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


@app.command()
def import_solutions(
    csv_file: Path = typer.Argument(..., help="Path to CSV file containing solutions"),
    parameter_map_file: Optional[Path] = typer.Option(
        None,
        "--parameter-map-file",
        help="YAML file mapping CSV columns to solution attributes",
    ),
    project_path: Path = typer.Option(
        Path("."), "--project-path", help="Project directory"
    ),
    delimiter: Optional[str] = typer.Option(
        None, "--delimiter", help="CSV delimiter (auto-detected if not specified)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be imported without making changes"
    ),
    validate: bool = typer.Option(
        False, "--validate", help="Validate solution parameters during import"
    ),
    on_duplicate: str = typer.Option(
        "error",
        "--on-duplicate",
        help="How to handle duplicate alias keys: error, override, or ignore",
    ),
) -> None:
    """Import solutions from a CSV file into the current project.

    This command delegates all CSV parsing and solution creation to
    :func:`microlens_submit.api.import_solutions_from_csv` and focuses solely on
    validating command-line options, saving the project, and presenting a user
    friendly summary. The CSV file must contain the required columns described
    in the API documentation (``event_id``, ``solution_id`` or ``solution_alias``,
    ``model_tags`` and parameter columns).

    Args:
        csv_file: Path to the CSV file containing solutions.
        parameter_map_file: Optional YAML file mapping CSV columns to solution
            attributes.
        project_path: Directory of the submission project.
        delimiter: CSV delimiter. If not provided the delimiter is auto
            detected.
        dry_run: If ``True``, show what would be imported without saving
            changes.
        validate: If ``True``, run solution validation during the import.
        on_duplicate: How to handle duplicate alias keys. Choose from ``error``
            (abort that row), ``override`` (replace the existing solution), or
            ``ignore`` (skip the row).

    Example:
        >>> microlens-submit import-solutions solutions.csv \
        ...     --project-path ./my_project --validate --on-duplicate override

    Note:
        Only a short summary of results is printed to the console. For a full
        description of import behaviour, see ``import_solutions_from_csv`` in
        the API module.
    """

    if on_duplicate not in ["error", "override", "ignore"]:
        typer.echo(f"❌ Invalid --on-duplicate option: {on_duplicate}")
        typer.echo("   Valid options: error, override, ignore")
        raise typer.Exit(1)

    try:
        submission = load(str(project_path))
    except Exception as e:  # pragma: no cover - unexpected I/O errors
        typer.echo(f"❌ Failed to load submission: {e}")
        raise typer.Exit(1)

    try:
        stats = import_solutions_from_csv(
            submission=submission,
            csv_file=csv_file,
            parameter_map_file=parameter_map_file,
            delimiter=delimiter,
            dry_run=dry_run,
            validate=validate,
            on_duplicate=on_duplicate,
            project_path=project_path,
        )
    except Exception as e:  # pragma: no cover - unexpected parse errors
        typer.echo(f"❌ Failed to import solutions: {e}")
        raise typer.Exit(1)

    if not dry_run and stats["successful_imports"] > 0:
        try:
            submission.save()
        except Exception as e:  # pragma: no cover - disk failures
            typer.echo(f"❌ Failed to save submission: {e}")
            raise typer.Exit(1)

    typer.echo("\n📊 Import Summary:")
    typer.echo(f"   Total rows processed: {stats['total_rows']}")
    typer.echo(f"   Successful imports: {stats['successful_imports']}")
    typer.echo(f"   Skipped rows: {stats['skipped_rows']}")
    typer.echo(f"   Validation errors: {stats['validation_errors']}")
    typer.echo(f"   Duplicates handled: {stats['duplicate_handled']}")

    if stats["errors"]:
        typer.echo("\n⚠️  Errors encountered:")
        for error in stats["errors"][:10]:
            typer.echo(f"   {error}")
        if len(stats["errors"]) > 10:
            typer.echo(f"   ... and {len(stats['errors']) - 10} more errors")

    if dry_run:
        typer.echo("\n🔍 Dry run completed - no changes made")
    else:
        typer.echo("\n✅ Import completed successfully")


if __name__ == "__main__":  # pragma: no cover
    app()
