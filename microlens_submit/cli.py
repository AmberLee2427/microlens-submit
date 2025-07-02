"""Command line interface for microlens-submit."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Optional, Literal, Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .api import load

console = Console()
app = typer.Typer()


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
        help="Path to JSON file with model parameters",
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
    log_prior: Optional[float] = typer.Option(None, help="Log prior"),
    n_data_points: Optional[int] = typer.Option(
        None,
        "--n-data-points",
        help="Number of data points used in this solution",
    ),
    lightcurve_plot_path: Optional[Path] = typer.Option(
        None, "--lightcurve-plot-path", help="Path to lightcurve plot file"
    ),
    lens_plane_plot_path: Optional[Path] = typer.Option(
        None, "--lens-plane-plot-path", help="Path to lens plane plot file"
    ),
    notes: str = typer.Option("", help="Notes for the solution"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Parse inputs and display the resulting Solution without saving",
    ),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Add a new solution entry for ``event_id``.

    Args:
        event_id: Identifier of the event.
        model_type: Type of model used for the solution.
        param: List of ``key=value`` strings defining parameters.
        params_file: Optional JSON file containing parameters.
        bands: Photometric bands used.
        higher_order_effect: Higher-order effects applied to the model.
        t_ref: Reference time for time-dependent effects.
        notes: Optional notes for the solution.
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))
    evt = sub.get_event(event_id)
    params: dict = {}
    if params_file is not None:
        with params_file.open("r", encoding="utf-8") as fh:
            params = json.load(fh)
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
    sol.notes = notes
    sol.used_astrometry = used_astrometry
    sol.used_postage_stamps = used_postage_stamps
    sol.limb_darkening_model = limb_darkening_model
    sol.limb_darkening_coeffs = _parse_pairs(limb_darkening_coeff)
    sol.parameter_uncertainties = _parse_pairs(parameter_uncertainty)
    sol.physical_parameters = _parse_pairs(physical_param)
    sol.log_likelihood = log_likelihood
    sol.log_prior = log_prior
    sol.relative_probability = relative_probability
    sol.n_data_points = n_data_points
    sol.lightcurve_plot_path = (
        str(lightcurve_plot_path) if lightcurve_plot_path else None
    )
    sol.lens_plane_plot_path = (
        str(lens_plane_plot_path) if lens_plane_plot_path else None
    )

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
            "log_prior": log_prior,
            "relative_probability": relative_probability,
            "n_data_points": n_data_points,
            "lightcurve_plot_path": (
                str(lightcurve_plot_path) if lightcurve_plot_path else None
            ),
            "lens_plane_plot_path": (
                str(lens_plane_plot_path) if lens_plane_plot_path else None
            ),
            "notes": notes,
        }
        console.print(Panel("Parsed Input", style="cyan"))
        console.print(json.dumps(parsed, indent=2))
        console.print(Panel("Schema Output", style="cyan"))
        console.print(sol.model_dump_json(indent=2))
        return

    sub.save()
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


if __name__ == "__main__":  # pragma: no cover
    app()
