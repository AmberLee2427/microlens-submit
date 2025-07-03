"""Command line interface for microlens-submit."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Optional, Literal
import os

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .api import load
from .dossier import generate_dashboard_html
from . import __version__

console = Console()
app = typer.Typer()


@app.command("version")
def version() -> None:
    """Show the version of microlens-submit."""
    console.print(f"microlens-submit version {__version__}")


def _parse_pairs(pairs: Optional[List[str]]) -> Optional[dict]:
    """Convert CLI key=value options into a dictionary."""
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
    """Validate mutually exclusive parameter options."""
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
    """Handle global CLI options."""
    if no_color:
        global console
        console = Console(color_system=None)


@app.command()
def init(
    team_name: str = typer.Option(..., help="Team name"),
    tier: str = typer.Option(..., help="Challenge tier"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Create a new submission project in ``project_path``.

    Args:
        team_name: Name of the team.
        tier: Challenge tier.
        project_path: Directory where the project will be created.
    """
    sub = load(str(project_path))
    sub.team_name = team_name
    sub.tier = tier
    sub.save()
    console.print(Panel(f"Initialized project at {project_path}", style="bold green"))


@app.command("nexus-init")
def nexus_init(
    team_name: str = typer.Option(..., help="Team name"),
    tier: str = typer.Option(..., help="Challenge tier"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Create a project and record Roman Nexus environment details."""

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
    notes: Optional[str] = typer.Option(None, help="Notes for the solution (supports Markdown formatting)"),
    notes_file: Optional[Path] = typer.Option(None, "--notes-file", help="Path to a Markdown file for solution notes (mutually exclusive with --notes)"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Parse inputs and display the resulting Solution without saving",
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Add a new solution entry for ``event_id``. Now supports file-based notes."""
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
    sol = evt.add_solution(model_type=model_type, parameters=params)
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
    canonical_notes_path = Path(project_path) / "events" / event_id / "solutions" / f"{sol.solution_id}.md"
    if notes_file is not None:
        sol.notes_path = str(notes_file)
    else:
        sol.notes_path = str(canonical_notes_path.relative_to(project_path))
        if notes is not None:
            canonical_notes_path.parent.mkdir(parents=True, exist_ok=True)
            canonical_notes_path.write_text(notes, encoding="utf-8")
        elif not canonical_notes_path.exists():
            canonical_notes_path.parent.mkdir(parents=True, exist_ok=True)
            canonical_notes_path.write_text("", encoding="utf-8")
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
            "notes_path": sol.notes_path,
        }
        console.print(Panel("Parsed Input", style="cyan"))
        console.print(json.dumps(parsed, indent=2))
        console.print(Panel("Schema Output", style="cyan"))
        console.print(sol.model_dump_json(indent=2))
        validation_messages = sol.validate()
        if validation_messages:
            console.print(Panel("Validation Warnings", style="yellow"))
            for msg in validation_messages:
                console.print(f"  • {msg}")
        else:
            console.print(Panel("Solution validated successfully!", style="green"))
        return
    sub.save()
    validation_messages = sol.validate()
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
    """Mark ``solution_id`` as inactive so it is excluded from exports.

    Args:
        solution_id: The ID of the solution to deactivate.
        project_path: Directory of the submission project.
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
    """Mark ``solution_id`` as active so it is included in exports.

    Args:
        solution_id: The ID of the solution to activate.
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))
    for event in sub.events.values():
        if solution_id in event.solutions:
            event.solutions[solution_id].activate()
            sub.save()
            console.print(f"Activated {solution_id}")
            return
    console.print(f"Solution {solution_id} not found", style="bold red")
    raise typer.Exit(code=1)


@app.command()
def export(
    output_path: Path,
    force: bool = typer.Option(False, "--force", help="Skip validation prompts"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Generate a zip archive containing all active solutions.

    Args:
        output_path: Path to the resulting zip file.
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))
    warnings = sub.validate()
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
) -> None:
    """Generate an HTML dossier for the submission.
    
    Creates a comprehensive HTML dashboard that provides an overview of the submission,
    including event summaries, solution statistics, and metadata. The dossier is saved
    to the `dossier/` subdirectory of the project directory with the main dashboard as index.html.
    
    Args:
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))
    output_dir = Path(project_path) / "dossier"
    generate_dashboard_html(sub, output_dir)
    console.print(Panel(f"Dossier generated successfully at {output_dir / 'index.html'}", style="bold green"))


@app.command("list-solutions")
def list_solutions(
    event_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Display a table of solutions for ``event_id``."""
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
    """Rank active solutions for ``event_id`` using the Bayesian Information Criterion."""

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

    Args:
        solution_id: The ID of the solution to validate.
        project_path: Directory of the submission project.

    The associated event ID is displayed in the output.
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
    messages = target_solution.validate()

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
    and returns a list of warnings describing potential issues.

    Args:
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))
    warnings = sub.validate()

    if not warnings:
        console.print(Panel("✅ All validations passed!", style="bold green"))
    else:
        console.print(Panel("Validation Warnings", style="yellow"))
        for warning in warnings:
            console.print(f"  • {warning}")

        console.print(f"\nFound {len(warnings)} validation issue(s)", style="yellow")


@app.command("validate-event")
def validate_event(
    event_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Validate all solutions for a specific event.

    Args:
        event_id: Identifier of the event to validate.
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))

    if event_id not in sub.events:
        console.print(f"Event {event_id} not found", style="bold red")
        raise typer.Exit(code=1)

    event = sub.events[event_id]
    all_messages = []

    console.print(Panel(f"Validating Event: {event_id}", style="cyan"))

    for solution in event.solutions.values():
        messages = solution.validate()
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
    """
    Parse a structured parameter file that can contain both parameters and uncertainties.
    
    Supports both JSON and YAML formats. The file can have either:
    1. Simple format: {"param1": value1, "param2": value2, ...}
    2. Structured format: {"parameters": {...}, "uncertainties": {...}}
    
    Args:
        params_file: Path to the parameter file
        
    Returns:
        tuple: (parameters_dict, uncertainties_dict)
    """
    import yaml
    
    with params_file.open("r", encoding="utf-8") as fh:
        if params_file.suffix.lower() in ['.yaml', '.yml']:
            data = yaml.safe_load(fh)
        else:
            data = json.load(fh)
    
    # Handle structured format
    if isinstance(data, dict) and ('parameters' in data or 'uncertainties' in data):
        parameters = data.get('parameters', {})
        uncertainties = data.get('uncertainties', {})
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
    notes: Optional[str] = typer.Option(None, help="Notes for the solution (supports Markdown formatting)"),
    notes_file: Optional[Path] = typer.Option(None, "--notes-file", help="Path to a Markdown file for solution notes (mutually exclusive with --notes)"),
    append_notes: Optional[str] = typer.Option(
        None,
        "--append-notes",
        help="Append text to existing notes (use --notes to replace instead)",
    ),
    clear_notes: bool = typer.Option(False, help="Clear all notes"),
    clear_relative_probability: bool = typer.Option(False, help="Clear relative probability"),
    clear_log_likelihood: bool = typer.Option(False, help="Clear log likelihood"),
    clear_n_data_points: bool = typer.Option(False, help="Clear n_data_points"),
    clear_parameter_uncertainties: bool = typer.Option(False, help="Clear parameter uncertainties"),
    clear_physical_parameters: bool = typer.Option(False, help="Clear physical parameters"),
    cpu_hours: Optional[float] = typer.Option(None, help="CPU hours used"),
    wall_time_hours: Optional[float] = typer.Option(None, help="Wall time hours used"),
    param: Optional[List[str]] = typer.Option(
        None, help="Model parameters as key=value (updates existing parameters)"
    ),
    param_uncertainty: Optional[List[str]] = typer.Option(
        None,
        "--param-uncertainty",
        help="Parameter uncertainties as key=value (updates existing uncertainties)"
    ),
    higher_order_effect: Optional[List[str]] = typer.Option(
        None,
        "--higher-order-effect",
        help="Higher-order effects (replaces existing effects)",
    ),
    clear_higher_order_effects: bool = typer.Option(False, help="Clear all higher-order effects"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be changed without saving",
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Edit an existing solution's attributes, including file-based notes."""
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
    if clear_relative_probability:
        if target_solution.relative_probability is not None:
            changes.append(f"Clear relative_probability: {target_solution.relative_probability}")
            target_solution.relative_probability = None
    elif relative_probability is not None:
        if target_solution.relative_probability != relative_probability:
            changes.append(f"Update relative_probability: {target_solution.relative_probability} → {relative_probability}")
            target_solution.relative_probability = relative_probability
    if clear_log_likelihood:
        if target_solution.log_likelihood is not None:
            changes.append(f"Clear log_likelihood: {target_solution.log_likelihood}")
            target_solution.log_likelihood = None
    elif log_likelihood is not None:
        if target_solution.log_likelihood != log_likelihood:
            changes.append(f"Update log_likelihood: {target_solution.log_likelihood} → {log_likelihood}")
            target_solution.log_likelihood = log_likelihood
    if clear_n_data_points:
        if target_solution.n_data_points is not None:
            changes.append(f"Clear n_data_points: {target_solution.n_data_points}")
            target_solution.n_data_points = None
    elif n_data_points is not None:
        if target_solution.n_data_points != n_data_points:
            changes.append(f"Update n_data_points: {target_solution.n_data_points} → {n_data_points}")
            target_solution.n_data_points = n_data_points
    # Notes file logic
    canonical_notes_path = Path(project_path) / "events" / target_event_id / "solutions" / f"{target_solution.solution_id}.md"
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
            old_content = notes_file_path.read_text(encoding="utf-8") if notes_file_path.exists() else ""
            notes_file_path.parent.mkdir(parents=True, exist_ok=True)
            notes_file_path.write_text(old_content + "\n" + append_notes, encoding="utf-8")
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
            wall_time_hours=wall_time_hours if wall_time_hours is not None else old_wall
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
            changes.append(f"Clear higher_order_effects: {target_solution.higher_order_effects}")
            target_solution.higher_order_effects = []
    elif higher_order_effect:
        if target_solution.higher_order_effects != higher_order_effect:
            changes.append(f"Update higher_order_effects: {target_solution.higher_order_effects} → {higher_order_effect}")
            target_solution.higher_order_effects = higher_order_effect
    if dry_run:
        if changes:
            console.print(Panel(f"Changes for {solution_id} (event {target_event_id})", style="cyan"))
            for change in changes:
                console.print(f"  • {change}")
        else:
            console.print(Panel("No changes would be made", style="yellow"))
        return
    if changes:
        sub.save()
        console.print(Panel(f"Updated {solution_id} (event {target_event_id})", style="green"))
        for change in changes:
            console.print(f"  • {change}")
    else:
        console.print(Panel("No changes made", style="yellow"))


@app.command("notes")
def edit_notes(solution_id: str, project_path: Path = typer.Argument(Path("."), help="Project directory")) -> None:
    """Open the notes file for a solution in $EDITOR (or nano/vi fallback)."""
    sub = load(str(project_path))
    for event in sub.events.values():
        if solution_id in event.solutions:
            sol = event.solutions[solution_id]
            if not sol.notes_path:
                console.print(f"No notes file associated with solution {solution_id}", style="bold red")
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
                    console.print(f"Could not find an editor to open {notes_file}", style="bold red")
                    raise typer.Exit(code=1)
            return
    console.print(f"Solution {solution_id} not found", style="bold red")
    raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    app()
