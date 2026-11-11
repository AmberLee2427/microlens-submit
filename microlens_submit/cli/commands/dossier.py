"""Dossier generation commands for microlens-submit CLI."""

from pathlib import Path
from typing import Optional
import json

import typer
from rich.console import Console
from rich.panel import Panel

from microlens_submit.dossier import generate_dashboard_html, generate_event_page, generate_solution_page
from microlens_submit.dossier.anonymization import evaluator_submission
from microlens_submit.dossier.full_report import generate_full_dossier_report_html
from microlens_submit.dossier.evaluation_data import (
    SUPPORTED_EVALUATION_TIERS,
    default_evaluation_data_dir,
    evaluator_truth_available,
    resolve_evaluation_data,
)
from microlens_submit.dossier.utils import copy_dossier_assets
from microlens_submit.utils import load

console = Console()

_TRUTH_ASSET_FILENAMES = {
    "event_comparison_metrics.json",
    "category_ranks.json",
    "q_scatter.html",
    "te_scatter.html",
    "rho_scatter.html",
    "u0_scatter.html",
    "t0_scatter.html",
    "classification_metrics_table.html",
    "planet_metrics_table.html",
    "modelling_metrics_table.html",
    "efficiency_metrics_table.html",
    "parallax_hist.html",
    "bl_s_scatter.html",
    "bl_alpha_scatter.html",
    "bs_s_scatter.html",
    "bs_alpha_scatter.html",
    "bs_flux_ratio_scatter.html",
    "phys_mass_scatter.html",
    "phys_dl_scatter.html",
}


def _clear_truth_assets(assets_dir: Path) -> None:
    """Remove stale truth-derived assets before a no-truth evaluator render."""
    for filename in _TRUTH_ASSET_FILENAMES:
        path = assets_dir / filename
        if path.exists():
            path.unlink()
    for path in assets_dir.glob("uncertainties_*_hist.html"):
        path.unlink()


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
    open: bool = typer.Option(
        False,
        "--open",
        help="Open the generated dossier in your web browser after generation.",
    ),
    evaluator: bool = typer.Option(
        False,
        "--evaluator",
        help="Generate an evaluator report with simulation ground truth comparison. "
        "(Requires access to truth data files)",
    ),
    data_dir: Optional[Path] = typer.Option(
        None,
        "--data-dir",
        help="Path to the directory containing the true simulation data/lightcurves.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force regeneration of all lightcurve and lens plane plots.",
    ),
) -> None:
    """Generate an HTML dossier for the submission.

    Use --open to automatically open the main dossier page in your browser after generation.
    Use --evaluator to include hidden simulation truths (requires truth data on system).
    """
    project_path = Path(project_path).resolve()
    sub = load(str(project_path))
    report_sub = evaluator_submission(sub) if evaluator else sub
    truth_available = evaluator and evaluator_truth_available(sub.tier)
    # Direct Python callers see Typer's OptionInfo default rather than the
    # parsed CLI value. Treat that as an omitted option.
    if data_dir is not None and not isinstance(data_dir, (str, Path)):
        data_dir = None
    if truth_available and data_dir is None:
        data_dir = default_evaluation_data_dir(project_path.parent, sub.tier)
    elif data_dir is not None:
        data_dir = Path(data_dir).resolve()

    if truth_available:
        comp_metrics_file = project_path / "dossier" / "assets" / "event_comparison_metrics.json"
        if comp_metrics_file.exists():
            with comp_metrics_file.open("r", encoding="utf-8") as f:
                event_comparison_metrics = json.load(f)
            for eid, metrics in event_comparison_metrics.items():
                if eid in sub.events:
                    event = sub.events[eid]
                    event.truth_model = metrics.get("truth_model")
                    truth_params = metrics.get("truth_parameters") or {}
                    if "mass" in metrics:
                        truth_params["Planet_mass"] = metrics["mass"]
                    if "dl" in metrics:
                        truth_params["Lens_Dist"] = metrics["dl"]
                    event.truth_parameters = truth_params

    output_dir = project_path / "dossier"
    if evaluator and not truth_available:
        _clear_truth_assets(output_dir / "assets")

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

        # Copy shared assets for the dossier
        copy_dossier_assets(output_dir)

        # Generate only the specific solution page
        event = sub.events[containing_event_id]
        console.print(
            Panel(
                f"Generating dossier for solution {solution_id} in event {containing_event_id}...",
                style="cyan",
            )
        )
        generate_solution_page(solution, event, report_sub, output_dir, evaluator_mode=evaluator)
        if open:
            import webbrowser

            solution_path = output_dir / f"{solution_id}.html"
            if solution_path.exists():
                webbrowser.open(solution_path.resolve().as_uri())

    elif event_id:
        # Generate only the specific event page
        if event_id not in sub.events:
            console.print(f"Event {event_id} not found", style="bold red")
            raise typer.Exit(1)

        # Create output directory and assets subdirectory
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "assets").mkdir(exist_ok=True)

        event = sub.events[event_id]
        copy_dossier_assets(output_dir)
        console.print(Panel(f"Generating dossier for event {event_id}...", style="cyan"))
        generate_event_page(event, report_sub, output_dir, evaluator_mode=evaluator)
        if open:
            import webbrowser

            event_path = output_dir / f"{event_id}.html"
            if event_path.exists():
                webbrowser.open(event_path.resolve().as_uri())

    else:
        # Generate full dossier (all events and solutions)
        console.print(
            Panel(
                "Generating comprehensive dossier for all events and solutions...",
                style="cyan",
            )
        )

        # Automatically generate lightcurve and lens plane plots for active solutions if they don't exist
        from microlens_submit.dossier.plotting import generate_lightcurve_plot
        for eid, event in sub.events.items():
            for sol_id, solution in event.solutions.items():
                if solution.is_active and (force or not solution.lightcurve_plot_path or not (project_path / solution.lightcurve_plot_path).exists()):
                    # Find a matching dataset file in the event folder
                    event_dir = project_path / "events" / eid
                    lc_data_file = event_dir / "lightcurve.dat"
                    if not lc_data_file.exists():
                        lc_data_file = event_dir / "lightcurve.csv"
                    # Fallback to test_lc.dat in the project root if it exists
                    if not lc_data_file.exists() and (project_path / "test_lc.dat").exists():
                        lc_data_file = project_path / "test_lc.dat"

                    if lc_data_file.exists():
                        rel_plot_dir = Path("events") / eid / "solutions" / sol_id
                        abs_plot_dir = project_path / rel_plot_dir
                        abs_plot_dir.mkdir(parents=True, exist_ok=True)
                        output_plot_path = abs_plot_dir / "lightcurve.html"
                        rel_plot_path = rel_plot_dir / "lightcurve.html"
                        try:
                            generate_lightcurve_plot(
                                solution=solution,
                                event=event,
                                data_path=lc_data_file,
                                output_path=output_plot_path,
                                data_dir=data_dir,
                                include_truth=truth_available,
                            )
                            solution.lightcurve_plot_path = str(rel_plot_path)
                            solution.lens_plane_plot_path = str(rel_plot_dir / "lens_plane.png")
                        except Exception as pe:
                            console.print(f"[yellow]Warning: Could not automatically generate plots for {eid} solution {sol_id[:8]}: {pe}[/yellow]")
        sub.save()

        generate_dashboard_html(report_sub, output_dir, evaluator_mode=evaluator)

        # Generate comprehensive printable dossier
        console.print(Panel("Generating comprehensive printable dossier...", style="cyan"))
        generate_full_dossier_report_html(report_sub, output_dir, evaluator_mode=evaluator)

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

        # Open the main dashboard if requested
        if open:
            import webbrowser

            webbrowser.open(dashboard_path.resolve().as_uri())

    console.print(
        Panel(
            f"Dossier generated successfully at {output_dir / 'index.html'}",
            style="bold green",
        )
    )


def evaluate_cohort(
    cohort_dir: Path = typer.Argument(..., help="Directory containing team submission folders"),
    data_dir: Optional[Path] = typer.Option(
        None,
        "--data-dir",
        help="Directory containing truth data files (defaults to <cohort-parent>/evaluator_data/<tier>)",
    ),
    tier: Optional[str] = typer.Option(
        None,
        "--tier",
        help="Evaluation tier (inferred from submissions when omitted): beginner or experienced",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Directory to save cohort stats (defaults to <cohort_dir>/cohort_analysis)",
    ),
    generate_solution_plots: bool = typer.Option(
        False,
        "--generate-solution-plots",
        help="Generate missing MulensModel fit and lens-plane plots for active solutions.",
    ),
    refresh_metrics: bool = typer.Option(
        False,
        "--refresh-metrics",
        help="Recompute cached event comparison metrics from the truth lightcurves.",
    ),
) -> None:
    """Evaluate an entire cohort of submissions.

    This command runs the full evaluation pipeline for a directory of submissions.
    Beginner and experienced cohorts should be evaluated in separate directories.
    The tier is inferred from submission.json unless --tier is supplied.

    The pipeline:
    1. Generates local comparison metrics, confusion matrices, and interactive plots for each submission.
    2. Generates the individual evaluator dossiers/reports.
    3. Generates the aggregate cohort-level statistics and confusion matrix.
    """
    cohort_dir = Path(cohort_dir).resolve()

    if tier is not None:
        tier = str(tier).lower()
        if tier not in SUPPORTED_EVALUATION_TIERS:
            console.print(
                f"[bold red]Unsupported tier {tier!r}; choose beginner or experienced.[/bold red]"
            )
            raise typer.Exit(1)

    if not cohort_dir.is_dir():
        console.print(f"[bold red]Error: {cohort_dir} is not a directory.[/bold red]")
        raise typer.Exit(1)

    # 1. Identify valid submission subdirectories containing submission.json
    subdirs = [d for d in cohort_dir.iterdir() if d.is_dir() and (d / "submission.json").exists()]
    if not subdirs:
        console.print(f"[bold red]No valid submission projects containing submission.json found in {cohort_dir}[/bold red]")
        raise typer.Exit(1)

    # Cohort directories are tier-homogeneous.  Infer the tier from the saved
    # submission metadata, while retaining beginner as the compatibility
    # default for older projects that predate the tier field.
    detected_tiers = set()
    for project in subdirs:
        try:
            project_submission = load(str(project))
            project_tier = str(project_submission.tier or "beginner").lower()
            if project_tier in {"", "none"}:
                project_tier = "beginner"
        except Exception as exc:
            console.print(f"[bold red]Could not read tier for {project.name}: {exc}[/bold red]")
            raise typer.Exit(1)
        if project_tier not in SUPPORTED_EVALUATION_TIERS:
            console.print(
                f"[bold red]Submission {project.name} has unsupported evaluation tier "
                f"{project_tier!r}.[/bold red]"
            )
            raise typer.Exit(1)
        detected_tiers.add(project_tier)

    if tier is None:
        if len(detected_tiers) != 1:
            console.print(
                "[bold red]A cohort must contain one tier only; found: "
                f"{', '.join(sorted(detected_tiers))}.[/bold red]"
            )
            raise typer.Exit(1)
        tier = next(iter(detected_tiers))
    elif any(project_tier != tier for project_tier in detected_tiers):
        console.print(
            f"[bold red]The cohort contains submissions outside the requested {tier} tier.[/bold red]"
        )
        raise typer.Exit(1)

    if data_dir is None:
        data_dir = default_evaluation_data_dir(cohort_dir, tier)
    else:
        data_dir = Path(data_dir).resolve()
    console.print(f"Using evaluator data directory: {data_dir}")

    if tier == "beginner" and not data_dir.is_dir():
        console.print(f"[bold red]Error: Truth data directory {data_dir} does not exist.[/bold red]")
        raise typer.Exit(1)

    evaluation_data = None
    if data_dir.is_dir():
        try:
            evaluation_data = resolve_evaluation_data(
                data_dir,
                tier,
                require_truth=evaluator_truth_available(tier),
            )
        except (FileNotFoundError, ValueError) as exc:
            console.print(f"[bold red]Invalid {tier} evaluator data: {exc}[/bold red]")
            raise typer.Exit(1)

    # 2. Locate evaluation scripts
    repo_root = Path(__file__).resolve().parents[3]
    interactive_plots_script = repo_root / "scripts" / "generate_interactive_plots.py"
    cohort_stats_script = repo_root / "scripts" / "generate_cohort_stats.py"

    if not interactive_plots_script.exists() or not cohort_stats_script.exists():
        # Try finding relative to current working directory
        cwd = Path.cwd()
        interactive_plots_script = cwd / "scripts" / "generate_interactive_plots.py"
        cohort_stats_script = cwd / "scripts" / "generate_cohort_stats.py"

    if not interactive_plots_script.exists() or not cohort_stats_script.exists():
        console.print("[bold red]Error: Could not locate evaluation scripts (generate_interactive_plots.py and generate_cohort_stats.py) in scripts/ folder.[/bold red]")
        raise typer.Exit(1)

    # 3. Dynamically load the scripts as modules
    import sys
    import importlib.util

    def load_module(name, filepath):
        spec = importlib.util.spec_from_file_location(name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    try:
        plots_mod = load_module("generate_interactive_plots", interactive_plots_script)
        stats_mod = load_module("generate_cohort_stats", cohort_stats_script)
    except Exception as e:
        console.print(f"[bold red]Failed to load evaluation scripts: {e}[/bold red]")
        raise typer.Exit(1)

    # Set up shared output dir for lightcurves
    # Keep shared plots beside the tier-homogeneous cohort so generated event
    # pages can resolve them without depending on the external data location.
    shared_out = cohort_dir / f"interactive_plots_{tier}"
    shared_out.mkdir(parents=True, exist_ok=True)
    resolved_output_dir = Path(output_dir).resolve() if output_dir else cohort_dir / "cohort_analysis"
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel(f"Starting Cohort Evaluation of {len(subdirs)} teams...", style="bold magenta"))

    # 4. Evaluate each submission folder
    # Reuse the shared plot cache on reruns. Missing event plots are still
    # generated by generate_lightcurve_plots; forcing every plot for the first
    # team makes large experienced cohorts unnecessarily expensive to rebuild.
    refresh_shared_lightcurves = False
    for proj in subdirs:
        console.print(Panel(f"Evaluating submission: {proj.name}", style="cyan"))
        try:
            local_assets = proj / "dossier" / "assets"
            local_assets.mkdir(parents=True, exist_ok=True)

            # Generate interactive plots and metrics
            if evaluation_data is not None:
                plots_mod.generate_lightcurve_plots(
                    proj,
                    evaluation_data.parquet_path,
                    shared_out,
                    force=refresh_shared_lightcurves,
                )
                refresh_shared_lightcurves = False
            plots_mod.generate_confusion_matrix(proj, data_dir, local_assets, tier=tier)
            if evaluator_truth_available(tier):
                plots_mod.generate_comparison_metrics(
                    proj,
                    data_dir,
                    local_assets,
                    tier=tier,
                    force=refresh_metrics,
                )
            plots_mod.generate_precision_metrics(proj, local_assets)

            # Load the submission object to generate solution-specific plots
            sub = load(str(proj))
            if str(sub.tier or "").lower() in {"", "none"}:
                sub.tier = tier

            # Map truth parameters first
            comp_metrics_file = local_assets / "event_comparison_metrics.json"
            if evaluator_truth_available(tier) and comp_metrics_file.exists():
                with comp_metrics_file.open("r", encoding="utf-8") as f:
                    event_comparison_metrics = json.load(f)
                for eid, metrics in event_comparison_metrics.items():
                    if eid in sub.events:
                        event = sub.events[eid]
                        event.truth_model = metrics.get("truth_model")
                        truth_params = metrics.get("truth_parameters") or {}
                        if "mass" in metrics:
                            truth_params["Planet_mass"] = metrics["mass"]
                        if "dl" in metrics:
                            truth_params["Lens_Dist"] = metrics["dl"]
                        event.truth_parameters = truth_params

            # Generate fits and lens plane plots only when requested. These can
            # require thousands of MulensModel fits for an experienced cohort;
            # evaluator HTML reports do not depend on them.
            from microlens_submit.dossier.plotting import generate_lightcurve_plot
            if evaluation_data is not None and generate_solution_plots:
                for eid, event in sub.events.items():
                    for sol_id, solution in event.solutions.items():
                        if solution.is_active:
                            rel_plot_dir = Path("events") / eid / "solutions" / sol_id
                            abs_plot_dir = proj / rel_plot_dir
                            abs_plot_dir.mkdir(parents=True, exist_ok=True)

                            output_plot_path = abs_plot_dir / "lightcurve.html"
                            rel_plot_path = rel_plot_dir / "lightcurve.html"
                            lens_plot_path = abs_plot_dir / "lens_plane.png"
                            if (
                                solution.lightcurve_plot_path
                                and output_plot_path.exists()
                                and lens_plot_path.exists()
                            ):
                                continue

                            try:
                                generate_lightcurve_plot(
                                    solution=solution,
                                    event=event,
                                    data_path=evaluation_data.parquet_path,
                                    output_path=output_plot_path,
                                    data_dir=data_dir,
                                    include_truth=evaluator_truth_available(tier),
                                )
                                solution.lightcurve_plot_path = str(rel_plot_path)
                                solution.lens_plane_plot_path = str(lens_plot_path.relative_to(proj))
                            except Exception as pe:
                                console.print(f"[yellow]Warning: Could not generate plots for solution {sol_id}: {pe}[/yellow]")

            sub.save()

            console.print(f"[bold green]Prepared evaluator metrics for {proj.name}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Error evaluating {proj.name}: {e}[/bold red]")

    # 5. Generate cohort statistics
    console.print(Panel("Generating aggregate cohort-level statistics...", style="bold magenta"))
    try:
        stats_mod.generate_cohort_confusion_matrix(
            cohort_dir, data_dir, resolved_output_dir, tier=tier
        )
        console.print(f"[bold green]Cohort analysis successfully completed! Results saved to {resolved_output_dir}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error generating cohort statistics: {e}[/bold red]")

    # 6. Build the team dossiers after cohort metrics exist so dashboards and
    # category ranks include the current cohort rather than stale or missing data.
    for proj in subdirs:
        console.print(Panel(f"Generating evaluator dossier: {proj.name}", style="cyan"))
        try:
            local_assets = proj / "dossier" / "assets"
            if evaluator_truth_available(tier):
                plots_mod.generate_planet_metrics(
                    proj,
                    data_dir,
                    local_assets,
                    tier=tier,
                    cohort_analysis_dir=resolved_output_dir,
                )
            generate_dossier(
                project_path=proj,
                event_id=None,
                solution_id=None,
                open=False,
                evaluator=True,
                data_dir=data_dir,
            )
            console.print(f"[bold green]Successfully evaluated {proj.name}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Error generating dossier for {proj.name}: {e}[/bold red]")
