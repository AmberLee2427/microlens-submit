"""Dossier generation commands for microlens-submit CLI."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from microlens_submit.dossier import generate_dashboard_html, generate_event_page, generate_solution_page
from microlens_submit.dossier.full_report import generate_full_dossier_report_html
from microlens_submit.utils import load

console = Console()


def generate_dossier(
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
    event_id: Optional[str] = typer.Option(
        None,
        "--event-id",
        help="Generate dossier for a specific event only " "(omit for full dossier)",
    ),
    solution_id: Optional[str] = typer.Option(
        None,
        "--solution-id",
        help="Generate dossier for a specific solution only " "(omit for full dossier)",
    ),
) -> None:
    """Generate an HTML dossier for the submission."""
    sub = load(str(project_path))
    output_dir = Path(project_path) / "dossier"

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
            Panel(
                f"Generating dossier for solution {solution_id} " f"in event {containing_event_id}...",
                style="cyan",
            )
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
        console.print(Panel(f"Generating dossier for event {event_id}...", style="cyan"))
        generate_event_page(event, sub, output_dir)

    else:
        # Generate full dossier (all events and solutions)
        console.print(
            Panel(
                "Generating comprehensive dossier for all events " "and solutions...",
                style="cyan",
            )
        )
        generate_dashboard_html(sub, output_dir)

        # Generate comprehensive printable dossier
        console.print(Panel("Generating comprehensive printable dossier...", style="cyan"))
        generate_full_dossier_report_html(sub, output_dir)

        # Replace placeholder in index.html with the real link
        dashboard_path = output_dir / "index.html"
        if dashboard_path.exists():
            with dashboard_path.open("r", encoding="utf-8") as f:
                dashboard_html = f.read()
            dashboard_html = dashboard_html.replace(
                "<!--FULL_DOSSIER_LINK_PLACEHOLDER-->",
                '<div class="text-center">'
                '<a href="./full_dossier_report.html" '
                'class="inline-block bg-rtd-accent text-white py-3 px-6 '
                "rounded-lg shadow-md hover:bg-rtd-secondary "
                'transition-colors duration-200 text-lg font-semibold mt-8">'
                "View Full Comprehensive Dossier (Printable)</a></div>",
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
