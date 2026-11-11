"""
Event page generation module for microlens-submit.

This module provides functionality to generate HTML pages for individual
microlensing events, including event overview, solutions tables, and
evaluator-only visualizations.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .. import __version__
from ..models import Event, Submission
from .evaluation_data import evaluator_truth_available
from .solution_page import generate_solution_page
from .utils import resolve_dossier_asset_path
from .utils import get_tier_submissions_label, get_tier_submissions_url
from .plotting import generate_mass_distance_comparison_plot, generate_proper_motion_comparison_plot


def generate_event_page(
    event: Event,
    submission: Submission,
    output_dir: Path,
    evaluator_mode: bool = False,
) -> None:
    """Generate an HTML dossier page for a single event.

    Creates a detailed HTML page for a specific microlensing event, following
    the Event_Page_Design.md specification. The page includes event overview,
    solutions table, and evaluator-only visualizations.

    Args:
        event: The Event object containing solutions and metadata.
        submission: The parent Submission object for context and metadata.
        output_dir: The dossier directory where the HTML file will be saved.
            The file will be named {event.event_id}.html.
        evaluator_mode: If True, include simulation truth comparisons in the report.

    Raises:
        OSError: If unable to write the HTML file.
        ValueError: If event data is invalid.

    Example:
        >>> from microlens_submit import load
        >>> from microlens_submit.dossier import generate_event_page
        >>> from pathlib import Path
        >>>
        >>> submission = load("./my_project")
        >>> event = submission.get_event("EVENT001")
        >>>
        >>> # Generate event page
        >>> generate_event_page(event, submission, Path("./dossier_output"))
        >>>
        >>> # Creates: ./dossier_output/EVENT001.html

    Note:
        This function also triggers generation of solution pages for all
        solutions in the event. The event page includes navigation links
        to individual solution pages.
    """
    # Prepare output directory (already created)
    project_root = Path(submission.project_path)
    event_data_link = ""
    if hasattr(event, "event_data_path") and event.event_data_path:
        event_data_link = resolve_dossier_asset_path(
            event.event_data_path,
            project_root,
            output_dir,
            subdir="event-data",
            prefix=f"{event.event_id}_event_data",
        )

    # Check for interactive lightcurve plot
    # 1. Check project's own dossier directory
    interactive_plot_path = output_dir / "interactive" / f"{event.event_id}_lc.html"

    # 2. Check shared location (../rmdc26/interactive_plots) relative to project root
    if not interactive_plot_path.exists():
        # Fallback to shared location in the parent of the repo or current directory
        # Try several common locations for interactive plots
        possible_dirs = [
            project_root.parent / f"interactive_plots_{submission.tier}",
            project_root.parent / "rmdc26" / "interactive_plots",
            project_root.parent / "rmdc26" / f"interactive_plots_{submission.tier}",
            Path("../rmdc26/interactive_plots").resolve(),
            Path(f"../rmdc26/interactive_plots_{submission.tier}").resolve(),
            Path("./rmdc26/interactive_plots").resolve(),
            Path(f"./rmdc26/interactive_plots_{submission.tier}").resolve(),
        ]

        for shared_plots_dir in possible_dirs:
            if shared_plots_dir.exists():
                shared_plot = shared_plots_dir / f"{event.event_id}_lc.html"
                if shared_plot.exists():
                    interactive_plot_path = shared_plot
                    break

    interactive_plot_html = ""
    if interactive_plot_path.exists():
        with interactive_plot_path.open("r", encoding="utf-8") as f:
            interactive_plot_html = f.read()

    # Generate degeneracy comparison plots
    mass_dist_path = output_dir / "plots" / f"{event.event_id}_mass_dist.png"
    proper_motion_path = output_dir / "plots" / f"{event.event_id}_prop_mot.png"

    generate_mass_distance_comparison_plot(event, mass_dist_path)
    generate_proper_motion_comparison_plot(event, proper_motion_path)

    # Resolve paths for HTML
    mass_dist_link = ""
    if mass_dist_path.exists():
        mass_dist_link = resolve_dossier_asset_path(
            str(mass_dist_path),
            project_root,
            output_dir,
            subdir="plots",
            prefix=f"{event.event_id}_mass_dist",
        )
    proper_motion_link = ""
    if proper_motion_path.exists():
        proper_motion_link = resolve_dossier_asset_path(
            str(proper_motion_path),
            project_root,
            output_dir,
            subdir="plots",
            prefix=f"{event.event_id}_prop_mot",
        )

    html = _generate_event_page_content(
        event,
        submission,
        event_data_link=event_data_link,
        interactive_plot_html=interactive_plot_html,
        evaluator_mode=evaluator_mode,
        mass_dist_plot=mass_dist_link,
        proper_motion_plot=proper_motion_link,
    )
    with (output_dir / f"{event.event_id}.html").open("w", encoding="utf-8") as f:
        f.write(html)

    # After generating the event page, generate solution pages
    for sol in event.solutions.values():
        generate_solution_page(sol, event, submission, output_dir, evaluator_mode=evaluator_mode)


def _generate_event_page_content(
    event: Event,
    submission: Submission,
    *,
    event_data_link: str = "",
    interactive_plot_html: str = "",
    evaluator_mode: bool = False,
    mass_dist_plot: str = "",
    proper_motion_plot: str = "",
) -> str:
    """Generate the HTML content for an event dossier page.

    Creates the complete HTML content for a single event page, including
    event overview, solutions table with sorting, and evaluator-only
    visualization placeholders.

    Args:
        event: The Event object containing solutions and metadata.
        submission: The parent Submission object for context and metadata.
        event_data_link: Optional link to download raw event data.
        interactive_plot_html: Optional HTML snippet for an interactive lightcurve plot.
        evaluator_mode: If True, include simulation truth comparisons in the report.

    Returns:
        str: Complete HTML content as a string for the event page.

    Example:
        >>> from microlens_submit import load
        >>> from microlens_submit.dossier import _generate_event_page_content
        >>>
        >>> submission = load("./my_project")
        >>> event = submission.get_event("EVENT001")
        >>> html_content = _generate_event_page_content(event, submission)
        >>>
        >>> # Write to file
        >>> with open("event_page.html", "w", encoding="utf-8") as f:
        ...     f.write(html_content)

    Note:
        Solutions are sorted by: active status (active first), relative
        probability (descending), then solution ID. The page includes
        navigation back to the dashboard and links to individual solution pages.
    """

    # Sort solutions: active first, then by relative_probability (desc, None last), then by solution_id
    def sort_key(sol):
        return (
            not sol.is_active,  # active first
            -(sol.relative_probability if sol.relative_probability is not None else float("-inf")),
            sol.solution_id,
        )

    truth_available = evaluator_mode and evaluator_truth_available(submission.tier)
    tier_submissions_url = get_tier_submissions_url(submission.tier)
    tier_submissions_link = (
        f"<a href='{tier_submissions_url}' class='text-rtd-accent hover:underline'>"
        f"{get_tier_submissions_label(submission.tier)}</a>"
        if tier_submissions_url
        else ""
    )

    solutions = sorted(event.solutions.values(), key=sort_key)
    # Table rows
    rows = []
    for sol in solutions:
        status = (
            '<span class="text-green-600">Active</span>'
            if sol.is_active
            else '<span class="text-red-600">Inactive</span>'
        )
        logl = f"{sol.log_likelihood:.2f}" if sol.log_likelihood is not None else "N/A"
        ndp = str(sol.n_data_points) if sol.n_data_points is not None else "N/A"
        relprob = f"{sol.relative_probability:.3f}" if sol.relative_probability is not None else "N/A"
        # Read notes snippet from file
        notes_snip = (
            (
                sol.get_notes(project_root=Path(submission.project_path))[:50]
                + ("..." if len(sol.get_notes(project_root=Path(submission.project_path))) > 50 else "")
            )
            if sol.notes_path
            else ""
        )

        # Display alias as primary identifier, UUID as secondary
        if sol.alias:
            solution_display = f"""
                <div>
                    <a href="{sol.solution_id}.html"
                       class="font-medium text-rtd-accent hover:underline">{sol.alias}</a>
                    <div class="text-xs text-gray-500 font-mono">{sol.solution_id[:8]}...</div>
                </div>
            """
        else:
            solution_display = (
                f'<a href="{sol.solution_id}.html" '
                f'class="font-medium text-rtd-accent hover:underline">'
                f"{sol.solution_id[:8]}...</a>"
            )

        rows.append(
            f"""
            <tr class='border-b border-gray-200 hover:bg-gray-50'>
                <td class='py-3 px-4'>{solution_display}</td>
                <td class='py-3 px-4'>{sol.model_type}</td>
                <td class='py-3 px-4'>{status}</td>
                <td class='py-3 px-4'>{logl}</td>
                <td class='py-3 px-4'>{ndp}</td>
                <td class='py-3 px-4'>{relprob}</td>
                <td class='py-3 px-4 text-gray-600 italic'>{notes_snip}</td>
            </tr>
        """
        )
    table_body = (
        "\n".join(rows)
        if rows
        else """
        <tr class='border-b border-gray-200'>
            <td colspan='7' class='py-3 px-4 text-center text-gray-500'>
                No solutions found
            </td>
        </tr>
    """
    )
    # Optional raw data link
    raw_data_html = ""
    if event_data_link:
        raw_data_html = (
            f'<p class="text-rtd-text">Raw Event Data: '
            f'<a href="{event_data_link}" '
            f'class="text-rtd-accent hover:underline">Download Data</a></p>'
        )

    # Lightcurve visualization logic
    if interactive_plot_html:
        lightcurve_viz = f"""
            <div class='mb-6 flex flex-col items-center'>
                <div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200 w-full flex justify-center'>
                    {interactive_plot_html}
                </div>
                <p class='text-sm text-gray-600 mt-2 text-center'>
                    Interactive view of the event data for {event.event_id}. Use the tools on the right to zoom and pan.
                </p>
            </div>
        """
    else:
        lightcurve_description = (
            "Raw lightcurve data for this submitted event."
            if not truth_available
            else "Raw lightcurve data with the simulation truth overlaid (Evaluator View)."
        )
        lightcurve_viz = f"""
            <div class='mb-6'>
                <img
                    src='https://placehold.co/800x450/dfc5fa/361d49?text=Raw+Lightcurve+and+Astrometry+Data+
                    (Evaluator+Only)'
                    alt='Raw Data Plot'
                    class='w-full rounded-lg shadow-md'
                >
                <p class='text-sm text-gray-600 mt-2'>{lightcurve_description}</p>
            </div>
        """

    visualization_title = (
        "Event Data Visualizations (Evaluator-Only)"
        if truth_available
        else "Submitted Event Data Visualizations"
    )
    visualization_note = (
        "Note: These advanced plots include comparisons to simulation truths and other teams' results."
        if truth_available
        else "Note: This tier does not have trusted hidden truth data; plots show submitted solutions only."
    )
    mass_placeholder = (
        "https://placehold.co/600x400/dfc5fa/361d49?text=Mass+vs+Distance+Plot"
        if not truth_available
        else "https://placehold.co/600x400/dfc5fa/361d49?text=Mass+vs+Distance+Scatter+Plot+(Evaluator+Only)"
    )
    proper_motion_placeholder = (
        "https://placehold.co/600x400/dfc5fa/361d49?text=Proper+Motion+Plot"
        if not truth_available
        else "https://placehold.co/600x400/dfc5fa/361d49?text=Proper+Motion+N+vs+E+Plot+(Evaluator+Only)"
    )

    # HTML content
    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>Event Dossier: {event.event_id} - {submission.team_name}</title>
    <script src='https://cdn.tailwindcss.com'></script>
    <script>
      tailwind.config = {{
        theme: {{
          extend: {{
            colors: {{
              'rtd-primary': '#dfc5fa',
              'rtd-secondary': '#361d49',
              'rtd-accent': '#a859e4',
              'rtd-background': '#faf7fd',
              'rtd-text': '#000',
            }},
            fontFamily: {{
              inter: ['Inter', 'sans-serif'],
            }},
          }},
        }},
      }};
    </script>
    <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap' rel='stylesheet'>
    <!-- Highlight.js for code syntax highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>

    <!-- Bokeh for interactive plots -->
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-3.8.0.min.js"></script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-widgets-3.8.0.min.js"></script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-tables-3.8.0.min.js"></script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-gl-3.8.0.min.js"></script>

    <style>
        .prose {{
            color: #000;
            line-height: 1.6;
        }}
        .prose h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #361d49;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
        }}
        .prose h2 {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #361d49;
            margin-top: 1.25rem;
            margin-bottom: 0.5rem;
        }}
        .prose h3 {{
            font-size: 1.125rem;
            font-weight: 600;
            color: #a859e4;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }}
        .prose p {{
            margin-bottom: 0.75rem;
        }}
        .prose ul, .prose ol {{
            margin-left: 1.5rem;
            margin-bottom: 0.75rem;
        }}
        .prose ul {{ list-style-type: disc; }}
        .prose ol {{ list-style-type: decimal; }}
        .prose li {{
            margin-bottom: 0.25rem;
        }}
        .prose code {{
            background: #f3f3f3;
            padding: 2px 4px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.875rem;
        }}
        .prose pre {{
            background: #f8f8f8;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1rem 0;
            border: 1px solid #e5e5e5;
        }}
        .prose pre code {{
            background: none;
            padding: 0;
        }}
        .prose blockquote {{
            border-left: 4px solid #a859e4;
            padding-left: 1rem;
            margin: 1rem 0;
            font-style: italic;
            color: #666;
        }}
    </style>
</head>
<body class='font-inter bg-rtd-background'>
    <div class='max-w-7xl mx-auto p-6 lg:p-8'>
        <div class='bg-white shadow-xl rounded-lg'>
            <!-- Header & Navigation -->
            <div class='text-center py-8'>
                <img src='assets/rges-pit_logo.png' alt='RGES-PIT Logo' class='w-48 mx-auto mb-6'>
                <h1 class='text-4xl font-bold text-rtd-secondary text-center mb-2'>
                    Event Dossier: {event.event_id}
                </h1>
                <p class='text-xl text-rtd-accent text-center mb-4'>
                    Team: {submission.team_name or 'Not specified'} | Tier: {submission.tier or 'Not specified'}
                </p>
                <nav class='flex justify-center space-x-4 mb-8'>
                    <a href='index.html' class='text-rtd-accent hover:underline'>&larr; Back to Dashboard</a>
                    {tier_submissions_link}
                </nav>
            </div>

            <hr class="border-t-4 border-rtd-accent my-8 mx-8">

            <!-- Regex Start -->

            <!-- Event Summary -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Event Overview</h2>
                <p class='text-rtd-text'>
                    This page provides details for microlensing event {event.event_id}.
                </p>
                {raw_data_html}
            </section>

            <!-- Solutions Table -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                    Solutions for Event {event.event_id}
                </h2>
                <table class='w-full text-left table-auto border-collapse'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr>
                            <th class='py-3 px-4'>Solution ID</th>
                            <th class='py-3 px-4'>Model Type</th>
                            <th class='py-3 px-4'>Status</th>
                            <th class='py-3 px-4'>Log-Likelihood</th>
                            <th class='py-3 px-4'>N Data Points</th>
                            <th class='py-3 px-4'>Relative Probability</th>
                            <th class='py-3 px-4'>Notes Snippet</th>
                        </tr>
                    </thead>
                    <tbody class='text-rtd-text'>
                        {table_body}
                    </tbody>
                </table>
            </section>
            <!-- Event-Specific Data Visualizations (Evaluator-Only Placeholders) -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                    {visualization_title}
                </h2>
                <p class='text-sm text-gray-500 italic mb-4'>{visualization_note}</p>

                {lightcurve_viz}

                <div class='mb-6'>
                    <img src='{mass_dist_plot if mass_dist_plot else mass_placeholder}'
alt='Mass vs Distance Plot' class='w-full rounded-lg shadow-md'>
                    <p class='text-sm text-gray-600 mt-2'>{"Derived Lens Mass vs. Lens Distance for submitted solutions (Evaluator View)." if truth_available else "Lens mass vs. distance for submitted solutions."}</p>
                </div>
                <div class='mb-6'>
                    <img src='{proper_motion_plot if proper_motion_plot else proper_motion_placeholder}'
alt='Proper Motion Plot' class='w-full rounded-lg shadow-md'>
                    <p class='text-sm text-gray-600 mt-2'>{"Proper Motion North vs. East components for submitted solutions (Evaluator View)." if truth_available else "Proper Motion North vs. East components for submitted solutions."}</p>
                </div>
            </section>

            <!-- Footer -->
            <div class='text-sm text-gray-500 text-center pt-8 border-t border-gray-200 mt-10'>
                Generated by microlens-submit v{__version__} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>

            <!-- Regex Finish -->

        </div>
    </div>
</body>
</html>"""
    return html
