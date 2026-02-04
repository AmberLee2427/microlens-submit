"""Validation commands for microlens-submit CLI."""

import math
from pathlib import Path
from typing import Dict

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from microlens_submit.error_messages import enhance_validation_messages
from microlens_submit.text_symbols import symbol
from microlens_submit.utils import load
from microlens_submit.validate_parameters import count_model_parameters

console = Console()


def validate_solution(
    solution_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Validate a specific solution's parameters and configuration."""
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
    enhanced_messages = enhance_validation_messages(messages, target_solution.model_type, target_solution.parameters)

    if not enhanced_messages:
        console.print(
            Panel(
                f"{symbol('check')} All validations passed for {solution_id} (event {target_event_id})",
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
        for msg in enhanced_messages:
            console.print(f"  • {msg}")


def validate_submission(
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Validate the entire submission for missing or incomplete information."""
    sub = load(str(project_path))
    warnings = sub.run_validation_warnings()

    if not warnings:
        console.print(Panel(f"{symbol('check')} All validations passed!", style="bold green"))
    else:
        console.print(Panel("Validation Warnings", style="yellow"))
        for warning in warnings:
            console.print(f"  \u2022 {warning}")
        console.print(f"\nFound {len(warnings)} validation issue(s)", style="yellow")

        # Provide helpful guidance for common issues
        has_repo_issue = any("repo_url" in w.lower() or "github" in w.lower() for w in warnings)
        has_hardware_issue = any("hardware" in w.lower() for w in warnings)

        if has_repo_issue:
            console.print(
                f"\n[blue]{symbol('hint')} To fix repository URL issues:[/blue]\n"
                "   microlens-submit set-repo-url <url> <project_dir>",
                style="blue",
            )

        if has_hardware_issue:
            console.print(
                f"\n[blue]{symbol('hint')} To fix hardware info issues:[/blue]\n"
                "   microlens-submit nexus-init --team-name <name> --tier <tier> <project_dir>\n"
                "   (or manually set hardware_info in submission.json)",
                style="blue",
            )

        console.print(
            "\n[yellow]"
            f"{symbol('warning')}  Note: These warnings will become errors when saving or exporting."
            "[/yellow]",
            style="yellow",
        )


def validate_event(
    event_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Validate all solutions for a specific event."""
    sub = load(str(project_path))

    if event_id not in sub.events:
        console.print(f"Event {event_id} not found", style="bold red")
        raise typer.Exit(1)

    event = sub.events[event_id]
    all_messages = []

    console.print(Panel(f"Validating Event: {event_id}", style="cyan"))

    for solution in event.solutions.values():
        messages = solution.run_validation()
        enhanced_messages = enhance_validation_messages(messages, solution.model_type, solution.parameters)
        if enhanced_messages:
            console.print(f"\n[bold]Solution {solution.solution_id}:[/bold]")
            for msg in enhanced_messages:
                console.print(f"  • {msg}")
                all_messages.append(f"{solution.solution_id}: {msg}")
        else:
            console.print(f"{symbol('check')} Solution {solution.solution_id}: All validations passed")

    if not all_messages:
        console.print(Panel(f"{symbol('check')} All solutions passed validation!", style="bold green"))
    else:
        console.print(
            f"\nFound {len(all_messages)} validation issue(s) across all solutions",
            style="yellow",
        )


def list_solutions(
    event_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Display a table of solutions for a specific event."""
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


def compare_solutions(
    event_id: str,
    project_path: Path = typer.Argument(Path("."), help="Project directory"),
) -> None:
    """Rank active solutions for an event using the Bayesian Information Criterion."""
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

    rel_prob_map: Dict[str, float] = {}
    note = None
    if solutions:
        provided_sum = sum(s.relative_probability or 0.0 for s in solutions if s.relative_probability is not None)
        need_calc = [s for s in solutions if s.relative_probability is None]
        if need_calc:
            can_calc = all(
                s.log_likelihood is not None
                and s.n_data_points
                and s.n_data_points > 0
                and count_model_parameters(s.parameters) > 0
                for s in need_calc
            )
            remaining = max(1.0 - provided_sum, 0.0)
            if can_calc:
                bic_vals = {
                    s.solution_id: count_model_parameters(s.parameters) * math.log(s.n_data_points)
                    - 2 * s.log_likelihood
                    for s in need_calc
                }
                bic_min = min(bic_vals.values())
                weights = {sid: math.exp(-0.5 * (bic - bic_min)) for sid, bic in bic_vals.items()}
                wsum = sum(weights.values())
                for sid, w in weights.items():
                    rel_prob_map[sid] = remaining * w / wsum if wsum > 0 else remaining / len(weights)
                note = "Relative probabilities calculated using BIC"
            else:
                eq = remaining / len(need_calc) if need_calc else 0.0
                for s in need_calc:
                    rel_prob_map[s.solution_id] = eq
                note = "Relative probabilities set equal due to missing data"

    rows = []
    for sol in solutions:
        k = count_model_parameters(sol.parameters)
        bic = k * math.log(sol.n_data_points) - 2 * sol.log_likelihood
        rp = sol.relative_probability if sol.relative_probability is not None else rel_prob_map.get(sol.solution_id)
        rows.append(
            (
                bic,
                [
                    sol.solution_id,
                    sol.model_type,
                    (",".join(sol.higher_order_effects) if sol.higher_order_effects else "-"),
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
