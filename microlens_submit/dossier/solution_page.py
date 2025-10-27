"""
Solution page generation module for microlens-submit.

This module provides functionality to generate HTML pages for individual
microlensing solutions, including solution overview, parameter tables,
notes rendering, and evaluator-only sections.
"""

from datetime import datetime
from pathlib import Path

import markdown

from .. import __version__
from ..models.event import Event
from ..models.solution import Solution
from ..models.submission import Submission


def generate_solution_page(solution: Solution, event: Event, submission: Submission, output_dir: Path) -> None:
    """Generate an HTML dossier page for a single solution.

    Creates a detailed HTML page for a specific microlensing solution, following
    the Solution_Page_Design.md specification. The page includes solution overview,
    parameter tables, notes (with markdown rendering), and evaluator-only sections.

    Args:
        solution: The Solution object containing parameters, notes, and metadata.
        event: The parent Event object for context and navigation.
        submission: The grandparent Submission object for context and metadata.
        output_dir: The dossier directory where the HTML file will be saved.
            The file will be named {solution.solution_id}.html.

    Raises:
        OSError: If unable to write the HTML file or read notes file.
        ValueError: If solution data is invalid.

    Example:
        >>> from microlens_submit import load
        >>> from microlens_submit.dossier import generate_solution_page
        >>> from pathlib import Path
        >>>
        >>> submission = load("./my_project")
        >>> event = submission.get_event("EVENT001")
        >>> solution = event.get_solution("solution_uuid_here")
        >>>
        >>> # Generate solution page
        >>> generate_solution_page(solution, event, submission, Path("./dossier_output"))
        >>>
        >>> # Creates: ./dossier_output/solution_uuid_here.html

    Note:
        The solution page includes GitHub commit links if available, markdown
        rendering for notes, and navigation back to the event page and dashboard.
        Notes are rendered with syntax highlighting for code blocks.
    """
    # Prepare output directory (already created)
    html = _generate_solution_page_content(solution, event, submission)
    with (output_dir / f"{solution.solution_id}.html").open("w", encoding="utf-8") as f:
        f.write(html)


def _generate_solution_page_content(solution: Solution, event: Event, submission: Submission) -> str:
    """Generate the HTML content for a solution dossier page.

    Creates the complete HTML content for a single solution page, including
    parameter tables, markdown-rendered notes, plot placeholders, and
    evaluator-only sections.

    Args:
        solution: The Solution object containing parameters, notes, and metadata.
        event: The parent Event object for context and navigation.
        submission: The grandparent Submission object for context and metadata.

    Returns:
        str: Complete HTML content as a string for the solution page.

    Example:
        >>> from microlens_submit import load
        >>> from microlens_submit.dossier import _generate_solution_page_content
        >>>
        >>> submission = load("./my_project")
        >>> event = submission.get_event("EVENT001")
        >>> solution = event.get_solution("solution_uuid_here")
        >>> html_content = _generate_solution_page_content(solution, event, submission)
        >>>
        >>> # Write to file
        >>> with open("solution_page.html", "w", encoding="utf-8") as f:
        ...     f.write(html_content)

    Note:
        Parameter uncertainties are formatted as ±value or +upper/-lower
        depending on the uncertainty format. Notes are rendered from markdown
        with syntax highlighting for code blocks. GitHub commit links are
        included if git information is available in compute_info.
    """
    # Placeholder image URLs
    PARAM_COMPARISON_URL = "https://placehold.co/800x300/dfc5fa/361d49?text=Parameter+Comparison"
    PARAM_DIFFERENCE_URL = "https://placehold.co/800x400/dfc5fa/361d49?text=Parameter+Difference"
    PHYSICAL_PARAM_URL = "https://placehold.co/600x400/dfc5fa/361d49?text=Physical+Parameter"
    CMD_WITH_SOURCE_URL = "https://placehold.co/600x400/dfc5fa/361d49?text=CMD+with+Source"
    DATA_UTILIZATION_URL = "https://placehold.co/600x100/dfc5fa/361d49?text=Data+Utilization+Infographic"
    # Render notes as HTML from file
    notes_md = solution.get_notes(project_root=Path(submission.project_path))
    notes_html = markdown.markdown(notes_md or "", extensions=["extra", "tables", "fenced_code", "nl2br"])
    # Parameters table
    param_rows = []
    params = solution.parameters or {}
    uncertainties = solution.parameter_uncertainties or {}
    for k, v in params.items():
        unc = uncertainties.get(k)
        if unc is None:
            unc_str = "N/A"
        elif isinstance(unc, (list, tuple)) and len(unc) == 2:
            unc_str = f"+{unc[1]}/-{unc[0]}"
        else:
            unc_str = f"±{unc}"
        param_rows.append(
            f"""
            <tr class='border-b border-gray-200 hover:bg-gray-50'>
                <td class='py-3 px-4'>{k}</td>
                <td class='py-3 px-4'>{v}</td>
                <td class='py-3 px-4'>{unc_str}</td>
            </tr>
        """
        )
    param_table = (
        "\n".join(param_rows)
        if param_rows
        else """
        <tr class='border-b border-gray-200'>
            <td colspan='3' class='py-3 px-4 text-center text-gray-500'>
                No parameters found
            </td>
        </tr>
    """
    )
    # Higher-order effects
    hoe_str = ", ".join(solution.higher_order_effects) if solution.higher_order_effects else "None"
    # Plot paths (relative to solution page)
    lc_plot = solution.lightcurve_plot_path or ""
    lens_plot = solution.lens_plane_plot_path or ""
    posterior = solution.posterior_path or ""
    # Physical parameters table
    phys_rows = []
    phys = solution.physical_parameters or {}
    for k, v in phys.items():
        phys_rows.append(
            f"""
            <tr class='border-b border-gray-200 hover:bg-gray-50'>
                <td class='py-3 px-4'>{k}</td>
                <td class='py-3 px-4'>{v}</td>
            </tr>
        """
        )
    phys_table = (
        "\n".join(phys_rows)
        if phys_rows
        else """
        <tr class='border-b border-gray-200'>
            <td colspan='2' class='py-3 px-4 text-center text-gray-500'>
                No physical parameters found
            </td>
        </tr>
    """
    )
    # GitHub commit link (if present)
    repo_url = getattr(submission, "repo_url", None) or (
        submission.repo_url if hasattr(submission, "repo_url") else None
    )
    commit = None
    if solution.compute_info:
        git_info = solution.compute_info.get("git_info")
        if git_info:
            commit = git_info.get("commit")
    commit_html = ""
    if repo_url and commit:
        commit_short = commit[:8]
        commit_url = f"{repo_url.rstrip('/')}/commit/{commit}"
        commit_html = f"""<a href="{commit_url}" target="_blank" rel="noopener"
               title="View this commit on GitHub"
               class="inline-flex items-center space-x-1 ml-2 align-middle">
                <img src="assets/github-desktop_logo.png" alt="GitHub Commit"
                     class="w-4 h-4 inline-block align-middle"
                     style="display:inline;vertical-align:middle;">
                <span class="text-xs text-rtd-accent font-mono">{commit_short}</span>
            </a>"""
    # HTML content
    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>Solution Dossier: {solution.alias or solution.solution_id[:8] + '...'} - {submission.team_name}</title>
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
                    Solution Dossier:
                    {solution.alias or solution.solution_id[:8] + '...'}
                </h1>
                <p class='text-lg text-gray-600 text-center mb-2'>
                    Model Type:
                    <span class='font-mono bg-gray-100 px-2 py-1 rounded'>{solution.model_type}</span>
                </p>
                <p class='text-xl text-rtd-accent text-center mb-4'>Event: {event.event_id} | Team: (
                    {submission.team_name or 'Not specified'} |
                    Tier: {submission.tier or 'Not specified'}
                    {commit_html}
                )</p>
                {f"<p class='text-lg text-gray-600 text-center mb-2'>UUID: {solution.solution_id}</p>"
                 if solution.alias else ""}
                <nav class='flex justify-center space-x-4 mb-8'>
                    <a
                        href='{event.event_id}.html'
                        class='text-rtd-accent hover:underline'
                    >
                        &larr; Back to Event {event.event_id}
                    </a>
                    <a href='index.html' class='text-rtd-accent hover:underline'>&larr; Back to Dashboard</a>
                </nav>
            </div>

            <hr class="border-t-4 border-rtd-accent my-8 mx-8">

            <!-- Regex Start -->

            <!-- Solution Overview & Notes -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Solution Overview & Notes</h2>
                <table class='w-full text-left table-auto border-collapse mb-4'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr><th>Parameter</th><th>Value</th><th>Uncertainty</th></tr>
                    </thead>
                    <tbody class='text-rtd-text'>
                        {param_table}
                    </tbody>
                </table>
                <p class='text-rtd-text mt-4'>Higher-Order Effects: {hoe_str}</p>
                <h3 class='text-xl font-semibold text-rtd-secondary mt-6 mb-2'>Participant's Detailed Notes</h3>
                <div class='bg-gray-50 p-4 rounded-lg shadow-inner text-rtd-text prose max-w-none'>{notes_html}</div>
            </section>
            <!-- Lightcurve & Lens Plane Visuals -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Lightcurve & Lens Plane Visuals</h2>
                <div class='grid grid-cols-1 md:grid-cols-2 gap-6'>
                    <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md'>
                        <img
                            src='{lc_plot}'
                            alt='Lightcurve Plot'
                            class='w-full h-auto rounded-md mb-2'
                        >
                        <p class="text-sm text-rtd-secondary">
                            Caption: Lightcurve fit for Solution
                            {solution.alias or solution.solution_id[:8] + '...'}
                        </p>
                    </div>
                    <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md'>
                        <img src='{lens_plot}' alt='Lens Plane Plot' class='w-full h-auto rounded-md mb-2'>
                        <p class='text-sm text-rtd-secondary'>
                            Caption: Lens plane geometry for Solution
                            {solution.alias or solution.solution_id[:8] + '...'}
                        </p>
                    </div>
                </div>
                <p class='text-rtd-text mt-4 text-center'>
                    Posterior Samples:
                    {f"<a href='{posterior}' class='text-rtd-accent hover:underline'>"
                     f"Download Posterior Data</a>"
                     if posterior else ''}
                </p>
            </section>
            <!-- Fit Statistics & Data Utilization -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                    Fit Statistics & Data Utilization
                </h2>
                <div class='grid grid-cols-1 md:grid-cols-2 gap-6'>
                    <div class='bg-rtd-primary p-6 rounded-lg shadow-md text-center'>
                        <p class='text-sm font-medium text-rtd-secondary'>Log-Likelihood</p>
                        <p class='text-4xl font-bold text-rtd-accent mt-2'>
                            {solution.log_likelihood if solution.log_likelihood is not None else 'N/A'}
                        </p>
                    </div>
                    <div class='bg-rtd-primary p-6 rounded-lg shadow-md text-center'>
                        <p class='text-sm font-medium text-rtd-secondary'>N Data Points Used</p>
                        <p class='text-4xl font-bold text-rtd-accent mt-2'>
                            {solution.n_data_points if solution.n_data_points is not None else 'N/A'}
                        </p>
                    </div>
                </div>
                <h3 class='text-xl font-semibold text-rtd-secondary mt-6 mb-2'>
                    Data Utilization Ratio
                </h3>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md'>
                    <img
                        src='{DATA_UTILIZATION_URL}'
                        alt='Data Utilization'
                        class='w-full h-auto rounded-md mb-2'
                    >
                    <p class='text-sm text-rtd-secondary'>
                        Caption: Percentage of total event data points utilized in this solution's fit.
                    </p>
                </div>
            </section>
            <!-- Compute Performance -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Compute Performance</h2>
                <table class='w-full text-left table-auto border-collapse'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr>
                            <th>Metric</th>
                            <th>Your Solution</th>
                            <th>Same-Team Average</th>
                            <th>All-Submission Average</th>
                        </tr>
                    </thead>
                    <tbody class='text-rtd-text'>
                        <tr>
                            <td>CPU Hours</td>
                            <td>
                                {solution.compute_info.get('cpu_hours', 'N/A') if solution.compute_info else 'N/A'}
                            </td>
                            <td>N/A for Participants</td><td>N/A for Participants</td>
                        </tr>
                        <tr>
                            <td>Wall Time (Hrs)</td>
                            <td>
                                {solution.compute_info.get('wall_time_hours', 'N/A')
                                 if solution.compute_info else 'N/A'}
                            </td>
                            <td>N/A for Participants</td><td>N/A for Participants</td>
                        </tr>
                    </tbody>
                </table>
                <p class='text-sm text-gray-500 italic mt-4'>
                    Note: Comparison to other teams' compute times is available in the Evaluator Dossier.
                </p>
            </section>
            <!-- Parameter Accuracy vs. Truths (Evaluator-Only) -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                    Parameter Accuracy vs. Truths (Evaluator-Only)
                </h2>
                <p class='text-sm text-gray-500 italic mb-4'>
                    You haven't made a mistake. This just isn't for you.
                    Detailed comparisons of your fitted parameters against simulation truths
                    are available in the Evaluator Dossier.
                </p>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md'>
                    <img
                        src='{PARAM_COMPARISON_URL}'
                        alt='Parameter Comparison Table'
                        class='w-full h-auto rounded-md mb-2'
                    >
                    <p class='text-sm text-rtd-secondary'>
                        Caption: A table comparing fitted parameters to true values
                        (Evaluator View).
                    </p>
                </div>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6'>
                    <img
                        src='{PARAM_DIFFERENCE_URL}'
                        alt='Parameter Difference Distributions'
                        class='w-full h-auto rounded-md mb-2'
                    >
                    <p class='text-sm text-rtd-secondary'>
                        Caption: Distributions of (True - Fit) for key parameters across all
                        challenge submissions
                        (Evaluator View).
                    </p>
                </div>
            </section>
            <!-- Physical Parameter Context (Evaluator-Only) -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                    Physical Parameter Context (Evaluator-Only)
                </h2>
                <p class='text-sm text-gray-500 italic mb-4'>
                    You haven't made a mistake. This just isn't for you.
                    Contextual plots of derived physical parameters against population models
                    are available in the Evaluator Dossier.
                </p>
                <table class='w-full text-left table-auto border-collapse'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr><th>Parameter</th><th>Value</th></tr>
                    </thead>
                    <tbody class='text-rtd-text'>
                        {phys_table}
                    </tbody>
                </table>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6'>
                    <img
                        src='{PHYSICAL_PARAM_URL}'
                        alt='Physical Parameter Distribution'
                        class='w-full h-auto rounded-md mb-2'
                    >
                    <p class='text-sm text-rtd-secondary'>
                        Caption: Your solution's derived physical parameters plotted against a simulated
                        test set
                        (Evaluator View).
                    </p>
                </div>
            </section>
            <!-- Source Properties & CMD (Evaluator-Only) -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                    Source Properties & CMD (Evaluator-Only)
                </h2>
                <p class='text-sm text-gray-500 italic mb-4'>
                    You haven't made a mistake. This just isn't for you.
                    Source color and magnitude diagrams are available in the Evaluator Dossier.
                </p>
                <div class='text-rtd-text'>
                    <!-- Placeholder for source color/mag details -->
                </div>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6'>
                    <img
                        src='{CMD_WITH_SOURCE_URL}'
                        alt='Color-Magnitude Diagram'
                        class='w-full h-auto rounded-md mb-2'
                    >
                    <p class='text-sm text-rtd-secondary'>
                        Caption: Color-Magnitude Diagram for the event's field with source marked
                        (Evaluator View).
                    </p>
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
