"""Command line interface for microlens-submit."""

from __future__ import annotations

from pathlib import Path
import json
import typer

from .api import load

app = typer.Typer()


@app.command()
def init(
    team_name: str = typer.Option(..., help="Team name"),
    tier: str = typer.Option(..., help="Challenge tier"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Initialize a new submission project.

    Args:
        team_name: Name of the team.
        tier: Challenge tier.
        project_path: Directory where the project will be created.
    """
    sub = load(str(project_path))
    sub.team_name = team_name
    sub.tier = tier
    sub.save()
    typer.echo(f"Initialized project at {project_path}")


@app.command("add-solution")
def add_solution(
    event_id: str,
    model_type: str,
    param: list[str] = typer.Option(..., help="Model parameters as key=value"),
    notes: str = typer.Option("", help="Notes for the solution"),
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Add a new solution to an event.

    Args:
        event_id: Identifier of the event.
        model_type: Type of model used for the solution.
        param: List of ``key=value`` strings defining parameters.
        notes: Optional notes for the solution.
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))
    evt = sub.get_event(event_id)
    params: dict = {}
    for p in param:
        if "=" not in p:
            raise typer.BadParameter(f"Invalid parameter format: {p}")
        key, value = p.split("=", 1)
        try:
            params[key] = json.loads(value)
        except json.JSONDecodeError:
            params[key] = value
    sol = evt.add_solution(model_type=model_type, parameters=params)
    sol.notes = notes
    sub.save()
    typer.echo(sol.solution_id)


@app.command()
def deactivate(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Deactivate a specific solution.

    Args:
        solution_id: The ID of the solution to deactivate.
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))
    for event in sub.events.values():
        if solution_id in event.solutions:
            event.solutions[solution_id].deactivate()
            sub.save()
            typer.echo(f"Deactivated {solution_id}")
            return
    typer.echo(f"Solution {solution_id} not found", err=True)
    raise typer.Exit(code=1)


@app.command()
def export(
    output_path: Path,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Export the submission to a zip archive.

    Args:
        output_path: Path to the resulting zip file.
        project_path: Directory of the submission project.
    """
    sub = load(str(project_path))
    sub.export(str(output_path))
    typer.echo(f"Exported submission to {output_path}")


if __name__ == "__main__":  # pragma: no cover
    app()
