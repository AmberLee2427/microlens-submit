"""Solution management commands for microlens-submit CLI."""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from rich.console import Console
from rich.panel import Panel

from microlens_submit.error_messages import enhance_validation_messages, format_cli_error_with_suggestions
from microlens_submit.text_symbols import symbol
from microlens_submit.utils import import_solutions_from_csv, load

console = Console()


_NUMERIC_RE = re.compile(r"^[+-]?((\\d+(\\.\\d*)?)|(\\.\\d+))([eE][+-]?\\d+)?$")


def _parse_cli_value(value: str) -> Any:
    """Parse a CLI value using JSON, with a numeric fallback for .001-style input."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        if _NUMERIC_RE.match(value.strip()):
            try:
                if re.match(r"^[+-]?\\d+$", value.strip()):
                    return int(value)
                return float(value)
            except ValueError:
                pass
        return value


def _run_editor(editor_cmd: str, notes_file: Path) -> bool:
    parts = shlex.split(editor_cmd)
    if not parts:
        return False
    if os.name == "nt" and parts[0].lower() in ("code", "code.exe"):
        if "--wait" not in parts and "-w" not in parts:
            parts.append("--wait")
    try:
        subprocess.run(parts + [str(notes_file)], check=False)
        return True
    except FileNotFoundError:
        return False


def _parse_pairs(pairs: Optional[List[str]]) -> Optional[Dict]:
    """Convert CLI key=value options into a dictionary."""
    if not pairs:
        return None
    out: Dict = {}
    for item in pairs:
        if "=" not in item:
            raise typer.BadParameter(f"Invalid format: {item}")
        key, value = item.split("=", 1)
        out[key] = _parse_cli_value(value)
    return out


def _params_file_callback(ctx: typer.Context, value: Optional[Path]) -> Optional[Path]:
    """Validate mutually exclusive parameter options."""
    param_vals = ctx.params.get("param")
    if value is not None and param_vals:
        raise typer.BadParameter("Cannot use --param with --params-file")
    if value is None and not param_vals and not ctx.resilient_parsing:
        raise typer.BadParameter("Provide either --param or --params-file")
    return value


def _parse_structured_params_file(params_file: Path) -> Tuple[Dict, Dict]:
    """Parse a structured parameter file that can contain both parameters and
    uncertainties.
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


def add_solution(
    event_id: str,
    model_type: str = typer.Argument(
        ...,
        metavar="{1S1L|1S2L|2S1L|2S2L|1S3L|2S3L|other}",
        help="Type of model used for the solution (e.g., 1S1L, 1S2L)",
    ),
    param: Optional[List[str]] = typer.Option(
        None,
        help="Model parameters as key=value [BASIC]",
    ),
    log_likelihood: Optional[float] = typer.Option(
        None,
        help="Log likelihood [BASIC]",
    ),
    n_data_points: Optional[int] = typer.Option(
        None,
        "--n-data-points",
        help="Number of data points used in this solution [BASIC]",
    ),
    project_path: Path = typer.Argument(
        Path("."),
        help="Project directory [BASIC]",
    ),
    # ADVANCED OPTIONS
    params_file: Optional[Path] = typer.Option(
        None,
        "--params-file",
        help=("Path to JSON or YAML file with model parameters " "and uncertainties [ADVANCED]"),
        callback=_params_file_callback,
    ),
    bands: Optional[List[str]] = typer.Option(
        None,
        "--bands",
        help=("Photometric bands used (e.g., 0,1,2). " "Required if using band-specific flux parameters [ADVANCED]"),
    ),
    higher_order_effect: Optional[List[str]] = typer.Option(
        None,
        "--higher-order-effect",
        help=(
            "Higher-order effects: parallax, finite-source, lens-orbital-motion, "
            "xallarap, gaussian-process, stellar-rotation, fitted-limb-darkening "
            "[ADVANCED]"
        ),
    ),
    t_ref: Optional[float] = typer.Option(
        None,
        "--t-ref",
        help=(
            "Reference time for time-dependent effects (Julian Date). "
            "Required for parallax, xallarap, etc. [ADVANCED]"
        ),
    ),
    used_astrometry: bool = typer.Option(
        False,
        help="Set if astrometry data was used in the fit [ADVANCED]",
    ),
    used_postage_stamps: bool = typer.Option(
        False,
        help=("Set if postage stamp images were used in the analysis [ADVANCED]"),
    ),
    limb_darkening_model: Optional[str] = typer.Option(
        None,
        help=(
            "Fixed limb darkening model name (e.g., 'claret'). "
            "Use --higher-order-effect fitted-limb-darkening for fitted coefficients "
            "[ADVANCED]"
        ),
    ),
    limb_darkening_coeff: Optional[List[str]] = typer.Option(
        None,
        "--limb-darkening-coeff",
        help=(
            "Limb darkening coefficients as key=value. " "Use with fitted-limb-darkening higher-order effect [ADVANCED]"
        ),
    ),
    parameter_uncertainty: Optional[List[str]] = typer.Option(
        None,
        "--param-uncertainty",
        help=(
            "Parameter uncertainties as key=value. "
            "Can be single value (symmetric) or [lower,upper] (asymmetric) [ADVANCED]"
        ),
    ),
    physical_param: Optional[List[str]] = typer.Option(
        None,
        "--physical-param",
        help=("Physical parameters (Mtot, D_L, thetaE, etc.) " "derived from model parameters [ADVANCED]"),
    ),
    physical_param_uncertainty: Optional[List[str]] = typer.Option(
        None,
        "--physical-param-uncertainty",
        help=(
            "Physical parameter uncertainties as key=value. "
            "Can be single value (symmetric) or [lower,upper] (asymmetric) [ADVANCED]"
        ),
    ),
    uncertainty_method: Optional[str] = typer.Option(
        None,
        "--uncertainty-method",
        help=(
            "Method used to derive uncertainties [ADVANCED]. "
            "Options: mcmc_posterior, fisher_matrix, bootstrap, propagation, inference, literature, other"
        ),
    ),
    confidence_level: Optional[float] = typer.Option(
        None,
        "--confidence-level",
        help=(
            "Confidence level for uncertainties (default: 0.68 = 1σ) [ADVANCED]. "
            "Standard values: 0.68 (1σ), 0.95 (2σ), 0.997 (3σ)"
        ),
    ),
    relative_probability: Optional[float] = typer.Option(
        None,
        "--relative-probability",
        help=("Relative probability of this solution (0-1). " "Used for model comparison [ADVANCED]"),
    ),
    cpu_hours: Optional[float] = typer.Option(
        None,
        "--cpu-hours",
        help="CPU hours used for this solution. " "Automatically captured if not specified [ADVANCED]",
    ),
    wall_time_hours: Optional[float] = typer.Option(
        None,
        "--wall-time-hours",
        help="Wall time hours used for this solution. " "Automatically captured if not specified [ADVANCED]",
    ),
    lightcurve_plot_path: Optional[Path] = typer.Option(
        None,
        "--lightcurve-plot-path",
        help="Path to lightcurve plot file " "(relative to project directory) [ADVANCED]",
    ),
    lens_plane_plot_path: Optional[Path] = typer.Option(
        None,
        "--lens-plane-plot-path",
        help="Path to lens plane plot file " "(relative to project directory) [ADVANCED]",
    ),
    posterior_path: Optional[Path] = typer.Option(
        None,
        "--posterior-path",
        help="Path to posterior samples file " "(relative to project directory) [ADVANCED]",
    ),
    alias: Optional[str] = typer.Option(
        None,
        "--alias",
        help=("Set or update the human-readable alias for this solution " "(must be unique within the event)"),
    ),
    notes: Optional[str] = typer.Option(
        None,
        help=("Notes for the solution (supports Markdown formatting)"),
    ),
    notes_file: Optional[Path] = typer.Option(
        None,
        "--notes-file",
        help=("Path to a Markdown file for solution notes " "(mutually exclusive with --notes)"),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be created without saving. " "Useful for testing parameter parsing [ADVANCED]",
    ),
) -> None:
    """Add a new solution entry for a microlensing event.

    Basic usage: microlens-submit add-solution EVENT123 1S1L --param t0=2459123.5
    --param u0=0.1 --param tE=20.0 --log-likelihood -1234.56 --n-data-points 1250

    Use --help to see all options including higher-order effects, uncertainties,
    and metadata.
    """
    sub = load(str(project_path))
    evt = sub.get_event(event_id)
    params: Dict = {}
    uncertainties: Dict = {}
    if params_file is not None:
        params, uncertainties = _parse_structured_params_file(params_file)
    else:
        for p in param or []:
            if "=" not in p:
                raise typer.BadParameter(f"Invalid parameter format: {p}")
            key, value = p.split("=", 1)
            params[key] = _parse_cli_value(value)
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
        error_msg = f"model_type must be one of {allowed_model_types}"
        enhanced_error = format_cli_error_with_suggestions(error_msg, {"model_type": model_type})
        raise typer.BadParameter(enhanced_error)
    if bands and len(bands) == 1 and "," in bands[0]:
        bands = bands[0].split(",")
    if higher_order_effect and len(higher_order_effect) == 1 and "," in higher_order_effect[0]:
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
    sol.physical_parameter_uncertainties = _parse_pairs(physical_param_uncertainty)
    sol.uncertainty_method = uncertainty_method
    if confidence_level is not None:
        sol.confidence_level = confidence_level
    sol.log_likelihood = log_likelihood
    sol.relative_probability = relative_probability
    sol.n_data_points = n_data_points
    if cpu_hours is not None or wall_time_hours is not None:
        sol.set_compute_info(cpu_hours=cpu_hours, wall_time_hours=wall_time_hours, git_dir=sub.git_dir)
    sol.lightcurve_plot_path = str(lightcurve_plot_path) if lightcurve_plot_path else None
    sol.lens_plane_plot_path = str(lens_plane_plot_path) if lens_plane_plot_path else None
    sol.posterior_path = str(posterior_path) if posterior_path else None
    # Handle notes file logic
    canonical_notes_path = Path(project_path) / "events" / event_id / "solutions" / f"{sol.solution_id}.md"
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
            "lightcurve_plot_path": (str(lightcurve_plot_path) if lightcurve_plot_path else None),
            "lens_plane_plot_path": (str(lens_plane_plot_path) if lens_plane_plot_path else None),
            "posterior_path": (str(posterior_path) if posterior_path else None),
            "alias": alias,
            "notes_path": sol.notes_path,
        }
        console.print(Panel("Parsed Input", style="cyan"))
        console.print(json.dumps(parsed, indent=2))
        console.print(Panel("Schema Output", style="cyan"))
        console.print(sol.model_dump_json(indent=2))
        validation_messages = sol.run_validation()
        if validation_messages:
            enhanced_messages = enhance_validation_messages(validation_messages, model_type, params)
            console.print(Panel("Validation Warnings", style="yellow"))
            for msg in enhanced_messages:
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
        enhanced_messages = enhance_validation_messages(validation_messages, model_type, params)
        console.print(Panel("Validation Warnings", style="yellow"))
        for msg in enhanced_messages:
            console.print(f"  • {msg}")
    else:
        console.print(
            f"{symbol('check')} Solution {sol.solution_id} created successfully!",
            style="green",
        )


def deactivate(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Mark a solution as inactive so it is excluded from exports."""
    sub = load(str(project_path))
    for event in sub.events.values():
        if solution_id in event.solutions:
            event.solutions[solution_id].deactivate()
            sub.save()
            console.print(f"Deactivated {solution_id}")
            return
    console.print(f"Solution {solution_id} not found", style="bold red")
    raise typer.Exit(code=1)


def activate(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Activate a previously deactivated solution."""
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
    console.print(f"[green]{symbol('check')} Activated solution {solution_id[:8]}... in event {event_id}[/green]")


def remove_solution(
    solution_id: str,
    force: bool = typer.Option(False, "--force", help="Required to remove a solution (prevents accidents)"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Completely remove a solution from the submission.

    This action is destructive and requires --force to proceed.
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

    if not force:
        console.print(
            f"[yellow]{symbol('warning')}  Refusing to remove solution {solution_id[:8]}... without --force.[/yellow]"
        )
        console.print(
            f"[blue]{symbol('hint')} Consider using deactivate to keep the solution, "
            "or re-run with --force to proceed.[/blue]"
        )
        raise typer.Exit(0)

    try:
        removed = submission.events[event_id].remove_solution(solution_id, force=force)
        if removed:
            submission.save()
            console.print(
                f"[green]{symbol('check')} Solution {solution_id[:8]}... removed from event {event_id}[/green]"
            )
        else:
            console.print(f"[red]Error: Failed to remove solution {solution_id}[/red]")
            raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            f"[yellow]{symbol('hint')} Use --force to override safety checks, "
            "or use deactivate to keep the solution[/yellow]"
        )
        raise typer.Exit(1)


def edit_solution(
    solution_id: str,
    relative_probability: Optional[float] = typer.Option(
        None,
        "--relative-probability",
        help="Relative probability of this solution",
    ),
    log_likelihood: Optional[float] = typer.Option(
        None,
        help="Log likelihood [BASIC]",
    ),
    n_data_points: Optional[int] = typer.Option(
        None,
        "--n-data-points",
        help="Number of data points used in this solution",
    ),
    alias: Optional[str] = typer.Option(
        None,
        "--alias",
        help=("Set or update the human-readable alias for this solution " "(must be unique within the event)"),
    ),
    notes: Optional[str] = typer.Option(
        None,
        help=("Notes for the solution (supports Markdown formatting)"),
    ),
    notes_file: Optional[Path] = typer.Option(
        None,
        "--notes-file",
        help=("Path to a Markdown file for solution notes " "(mutually exclusive with --notes)"),
    ),
    append_notes: Optional[str] = typer.Option(
        None,
        "--append-notes",
        help=("Append text to existing notes (use --notes to replace instead)"),
    ),
    clear_notes: bool = typer.Option(False, help="Clear all notes"),
    clear_relative_probability: bool = typer.Option(False, help="Clear relative probability"),
    clear_log_likelihood: bool = typer.Option(False, help="Clear log likelihood"),
    clear_n_data_points: bool = typer.Option(False, help="Clear n_data_points"),
    clear_parameter_uncertainties: bool = typer.Option(False, help="Clear parameter uncertainties"),
    clear_physical_parameters: bool = typer.Option(False, help="Clear physical parameters"),
    hardware_info_json: Optional[str] = typer.Option(
        None,
        "--hardware-info-json",
        help='Solution-level hardware_info override as JSON (e.g., \'{"cpu_details": "Xeon"}\')',
    ),
    autofill_hardware_info: bool = typer.Option(
        False,
        "--autofill-hardware-info",
        help="Autofill solution-level hardware_info from current environment",
    ),
    autofill_nexus_info: bool = typer.Option(
        False,
        "--autofill-nexus-info",
        help="Alias for --autofill-hardware-info",
    ),
    clear_hardware_info: bool = typer.Option(False, help="Clear solution-level hardware_info"),
    cpu_hours: Optional[float] = typer.Option(None, help="CPU hours used"),
    wall_time_hours: Optional[float] = typer.Option(None, help="Wall time hours used"),
    param: Optional[List[str]] = typer.Option(
        None,
        help=("Model parameters as key=value (updates existing parameters)"),
    ),
    param_uncertainty: Optional[List[str]] = typer.Option(
        None,
        "--param-uncertainty",
        help=("Parameter uncertainties as key=value (updates existing uncertainties)"),
    ),
    higher_order_effect: Optional[List[str]] = typer.Option(
        None,
        "--higher-order-effect",
        help="Higher-order effects (replaces existing effects)",
    ),
    clear_higher_order_effects: bool = typer.Option(False, help="Clear all higher-order effects"),
    lightcurve_plot_path: Optional[Path] = typer.Option(
        None,
        "--lightcurve-plot-path",
        help="Path to lightcurve plot file (relative to project directory)",
    ),
    lens_plane_plot_path: Optional[Path] = typer.Option(
        None,
        "--lens-plane-plot-path",
        help="Path to lens plane plot file (relative to project directory)",
    ),
    posterior_path: Optional[Path] = typer.Option(
        None,
        "--posterior-path",
        help="Path to posterior samples file (relative to project directory)",
    ),
    clear_lightcurve_plot_path: bool = typer.Option(False, help="Clear lightcurve plot path"),
    clear_lens_plane_plot_path: bool = typer.Option(False, help="Clear lens plane plot path"),
    clear_posterior_path: bool = typer.Option(False, help="Clear posterior sample path"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be changed without saving",
    ),
    project_path: Path = typer.Argument(
        Path("."),
        help="Project directory [BASIC]",
    ),
) -> None:
    """Edit an existing solution's attributes, including file-based notes and alias."""
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
    arrow = symbol("arrow")
    changes = []
    if alias is not None:
        if target_solution.alias != alias:
            changes.append(f"Update alias: {target_solution.alias} {arrow} {alias}")
            target_solution.alias = alias
    if clear_relative_probability:
        if target_solution.relative_probability is not None:
            changes.append(f"Clear relative_probability: {target_solution.relative_probability}")
            target_solution.relative_probability = None
    elif relative_probability is not None:
        if target_solution.relative_probability != relative_probability:
            changes.append(
                f"Update relative_probability: {target_solution.relative_probability} {arrow} {relative_probability}"
            )
            target_solution.relative_probability = relative_probability
    if clear_log_likelihood:
        if target_solution.log_likelihood is not None:
            changes.append(f"Clear log_likelihood: {target_solution.log_likelihood}")
            target_solution.log_likelihood = None
    elif log_likelihood is not None:
        if target_solution.log_likelihood != log_likelihood:
            changes.append(f"Update log_likelihood: {target_solution.log_likelihood} {arrow} {log_likelihood}")
            target_solution.log_likelihood = log_likelihood
    if clear_n_data_points:
        if target_solution.n_data_points is not None:
            changes.append(f"Clear n_data_points: {target_solution.n_data_points}")
            target_solution.n_data_points = None
    elif n_data_points is not None:
        if target_solution.n_data_points != n_data_points:
            changes.append(f"Update n_data_points: {target_solution.n_data_points} {arrow} {n_data_points}")
            target_solution.n_data_points = n_data_points
    # Notes file logic
    canonical_notes_path = (
        Path(project_path) / "events" / target_event_id / "solutions" / f"{target_solution.solution_id}.md"
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
    if clear_hardware_info:
        if target_solution.hardware_info is not None:
            changes.append("Clear hardware_info")
            target_solution.hardware_info = None
    if hardware_info_json is not None:
        try:
            parsed = json.loads(hardware_info_json)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON for --hardware-info-json: {exc}")
        if not isinstance(parsed, dict):
            raise typer.BadParameter("--hardware-info-json must be a JSON object")
        changes.append("Update hardware_info")
        target_solution.hardware_info = parsed
    if autofill_hardware_info or autofill_nexus_info:
        target_solution.autofill_hardware_info()
        changes.append("Autofill hardware_info")
    if cpu_hours is not None or wall_time_hours is not None:
        old_cpu = target_solution.compute_info.get("cpu_hours")
        old_wall = target_solution.compute_info.get("wall_time_hours")
        if cpu_hours is not None and old_cpu != cpu_hours:
            changes.append(f"Update cpu_hours: {old_cpu} {arrow} {cpu_hours}")
        if wall_time_hours is not None and old_wall != wall_time_hours:
            changes.append(f"Update wall_time_hours: {old_wall} {arrow} {wall_time_hours}")
        target_solution.set_compute_info(
            cpu_hours=cpu_hours if cpu_hours is not None else old_cpu,
            wall_time_hours=(wall_time_hours if wall_time_hours is not None else old_wall),
            git_dir=sub.git_dir,
        )
    if param:
        for p in param:
            if "=" not in p:
                raise typer.BadParameter(f"Invalid parameter format: {p}")
            key, value = p.split("=", 1)
            new_value = _parse_cli_value(value)
            old_value = target_solution.parameters.get(key)
            if old_value != new_value:
                changes.append(f"Update parameter {key}: {old_value} {arrow} {new_value}")
                target_solution.parameters[key] = new_value
    if param_uncertainty:
        if target_solution.parameter_uncertainties is None:
            target_solution.parameter_uncertainties = {}
        for p in param_uncertainty:
            if "=" not in p:
                raise typer.BadParameter(f"Invalid uncertainty format: {p}")
            key, value = p.split("=", 1)
            new_value = _parse_cli_value(value)
            old_value = target_solution.parameter_uncertainties.get(key)
            if old_value != new_value:
                changes.append(f"Update uncertainty {key}: {old_value} {arrow} {new_value}")
                target_solution.parameter_uncertainties[key] = new_value
    if clear_higher_order_effects:
        if target_solution.higher_order_effects:
            changes.append(f"Clear higher_order_effects: {target_solution.higher_order_effects}")
            target_solution.higher_order_effects = []
    elif higher_order_effect:
        if target_solution.higher_order_effects != higher_order_effect:
            changes.append(
                f"Update higher_order_effects: {target_solution.higher_order_effects} {arrow} {higher_order_effect}"
            )
            target_solution.higher_order_effects = higher_order_effect

    if clear_lightcurve_plot_path:
        if target_solution.lightcurve_plot_path:
            changes.append(f"Clear lightcurve_plot_path: {target_solution.lightcurve_plot_path}")
            target_solution.lightcurve_plot_path = None
    elif lightcurve_plot_path is not None:
        old_val = target_solution.lightcurve_plot_path
        new_val = str(lightcurve_plot_path)
        if old_val != new_val:
            changes.append(f"Update lightcurve_plot_path: {old_val} {arrow} {new_val}")
            target_solution.lightcurve_plot_path = new_val

    if clear_lens_plane_plot_path:
        if target_solution.lens_plane_plot_path:
            changes.append(f"Clear lens_plane_plot_path: {target_solution.lens_plane_plot_path}")
            target_solution.lens_plane_plot_path = None
    elif lens_plane_plot_path is not None:
        old_val = target_solution.lens_plane_plot_path
        new_val = str(lens_plane_plot_path)
        if old_val != new_val:
            changes.append(f"Update lens_plane_plot_path: {old_val} {arrow} {new_val}")
            target_solution.lens_plane_plot_path = new_val

    if clear_posterior_path:
        if target_solution.posterior_path:
            changes.append(f"Clear posterior_path: {target_solution.posterior_path}")
            target_solution.posterior_path = None
    elif posterior_path is not None:
        old_val = target_solution.posterior_path
        new_val = str(posterior_path)
        if old_val != new_val:
            changes.append(f"Update posterior_path: {old_val} {arrow} {new_val}")
            target_solution.posterior_path = new_val

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


def edit_notes(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Open the notes file for a solution in the default text editor."""
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
            editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
            if editor and _run_editor(editor, notes_file):
                return
            fallbacks = ["nano", "vi", "vim", "code"]
            if os.name == "nt":
                fallbacks = ["code", "notepad", "notepad.exe"]
            for fallback in fallbacks:
                if shutil.which(fallback):
                    if _run_editor(fallback, notes_file):
                        return
            if os.name == "nt":
                try:
                    os.startfile(notes_file)  # type: ignore[attr-defined]
                    return
                except OSError:
                    pass
            elif sys.platform == "darwin":
                if shutil.which("open"):
                    subprocess.run(["open", "-W", str(notes_file)], check=False)
                    return
            else:
                if shutil.which("xdg-open"):
                    subprocess.run(["xdg-open", str(notes_file)], check=False)
                    return
            console.print(
                f"Could not find an editor to open {notes_file}",
                style="bold red",
            )
            raise typer.Exit(code=1)
            return
    console.print(f"Solution {solution_id} not found", style="bold red")
    raise typer.Exit(code=1)


def import_solutions(
    csv_file: Path = typer.Argument(..., help="Path to CSV file containing solutions"),
    parameter_map_file: Optional[Path] = typer.Option(
        None,
        "--parameter-map-file",
        help="YAML file mapping CSV columns to solution attributes",
    ),
    project_path: Path = typer.Option(Path("."), "--project-path", help="Project directory"),
    delimiter: Optional[str] = typer.Option(None, "--delimiter", help="CSV delimiter (auto-detected if not specified)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported without making changes"),
    validate: bool = typer.Option(False, "--validate", help="Validate solution parameters during import"),
    on_duplicate: str = typer.Option(
        "error",
        "--on-duplicate",
        help="How to handle duplicate alias keys: error, override, or ignore",
    ),
) -> None:
    """Import solutions from a CSV file into the current project."""
    if on_duplicate not in ["error", "override", "ignore"]:
        typer.echo(f"{symbol('error')} Invalid --on-duplicate option: {on_duplicate}")
        typer.echo("   Valid options: error, override, ignore")
        raise typer.Exit(1)

    try:
        submission = load(str(project_path))
    except Exception as e:  # pragma: no cover - unexpected I/O errors
        typer.echo(f"{symbol('error')} Failed to load submission: {e}")
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
        typer.echo(f"{symbol('error')} Failed to import solutions: {e}")
        raise typer.Exit(1)

    if not dry_run and stats["successful_imports"] > 0:
        try:
            submission.save()
        except Exception as e:  # pragma: no cover - disk failures
            typer.echo(f"{symbol('error')} Failed to save submission: {e}")
            raise typer.Exit(1)

    typer.echo(f"\n{symbol('progress')} Import Summary:")
    typer.echo(f"   Total rows processed: {stats['total_rows']}")
    typer.echo(f"   Successful imports: {stats['successful_imports']}")
    typer.echo(f"   Skipped rows: {stats['skipped_rows']}")
    typer.echo(f"   Validation errors: {stats['validation_errors']}")
    typer.echo(f"   Duplicates handled: {stats['duplicate_handled']}")

    if stats["errors"]:
        typer.echo(f"\n{symbol('warning')}  Errors encountered:")
        for error in stats["errors"][:10]:
            typer.echo(f"   {error}")
        if len(stats["errors"]) > 10:
            typer.echo(f"   ... and {len(stats['errors']) - 10} more errors")

    if dry_run:
        typer.echo(f"\n{symbol('search')} Dry run completed - no changes made")
    else:
        typer.echo(f"\n{symbol('check')} Import completed successfully")
