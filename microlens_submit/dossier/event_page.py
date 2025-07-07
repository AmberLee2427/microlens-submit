"""
Event page generation module for microlens-submit.

This module provides functionality to generate HTML pages for individual
microlensing events, including event overview, solutions tables, and
evaluator-only visualizations.
"""

from datetime import datetime
from pathlib import Path

from ..models import Event, Submission
from .solution_page import generate_solution_page


def generate_event_page(event: Event, submission: Submission, output_dir: Path) -> None:
    """Generate an HTML dossier page for a single event.

    Creates a detailed HTML page for a specific microlensing event, following
    the Event_Page_Design.md specification. The page includes event overview,
    solutions table, and evaluator-only visualizations.

    Args:
        event: The Event object containing solutions and metadata.
        submission: The parent Submission object for context and metadata.
        output_dir: The dossier directory where the HTML file will be saved.
            The file will be named {event.event_id}.html.

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
    html = _generate_event_page_content(event, submission)
    with (output_dir / f"{event.event_id}.html").open("w", encoding="utf-8") as f:
        f.write(html)

    # After generating the event page, generate solution pages
    for sol in event.solutions.values():
        generate_solution_page(sol, event, submission, output_dir)


def _generate_event_page_content(event: Event, submission: Submission) -> str:
    """Generate the HTML content for an event dossier page.

    Creates the complete HTML content for a single event page, including
    event overview, solutions table with sorting, and evaluator-only
    visualization placeholders.

    Args:
        event: The Event object containing solutions and metadata.
        submission: The parent Submission object for context and metadata.

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
            -(
                sol.relative_probability
                if sol.relative_probability is not None
                else float("-inf")
            ),
            sol.solution_id,
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
        relprob = (
            f"{sol.relative_probability:.3f}"
            if sol.relative_probability is not None
            else "N/A"
        )
        # Read notes snippet from file
        notes_snip = (
            (
                sol.get_notes(project_root=Path(submission.project_path))[:50]
                + (
                    "..."
                    if len(sol.get_notes(project_root=Path(submission.project_path)))
                    > 50
                    else ""
                )
            )
            if sol.notes_path
            else ""
        )

        # Display alias as primary identifier, UUID as secondary
        if sol.alias:
            solution_display = f"""
                <div>
                    <a href="{sol.solution_id}.html" class="font-medium text-rtd-accent hover:underline">{sol.alias}</a>
                    <div class="text-xs text-gray-500 font-mono">{sol.solution_id[:8]}...</div>
                </div>
            """
        else:
            solution_display = f'<a href="{sol.solution_id}.html" class="font-medium text-rtd-accent hover:underline">{sol.solution_id[:8]}...</a>'

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
        <tr class='border-b border-gray-200'><td colspan='7' class='py-3 px-4 text-center text-gray-500'>No solutions found</td></tr>
    """
    )
    # Optional raw data link
    raw_data_html = ""
    if hasattr(event, "event_data_path") and event.event_data_path:
        raw_data_html = f'<p class="text-rtd-text">Raw Event Data: <a href="{event.event_data_path}" class="text-rtd-accent hover:underline">Download Data</a></p>'
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
                <h1 class='text-4xl font-bold text-rtd-secondary text-center mb-2'>Event Dossier: {event.event_id}</h1>
                <p class='text-xl text-rtd-accent text-center mb-4'>Team: {submission.team_name or 'Not specified'} | Tier: {submission.tier or 'Not specified'}</p>
                <nav class='flex justify-center space-x-4 mb-8'>
                    <a href='index.html' class='text-rtd-accent hover:underline'>&larr; Back to Dashboard</a>
                </nav>
            </div>

            <hr class="border-t-4 border-rtd-accent my-8 mx-8">

            <!-- Regex Start -->

            <!-- Event Summary -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Event Overview</h2>
                <p class='text-rtd-text'>This page provides details for microlensing event {event.event_id}.</p>
                {raw_data_html}
            </section>
            <!-- Solutions Table -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Solutions for Event {event.event_id}</h2>
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
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Event Data Visualizations (Evaluator-Only)</h2>
                <p class='text-sm text-gray-500 italic mb-4'>Note: These advanced plots, including comparisons to simulation truths and other teams' results, are available in the Evaluator Dossier.</p>
                <div class='mb-6'>
                    <img src='https://placehold.co/800x450/dfc5fa/361d49?text=Raw+Lightcurve+and+Astrometry+Data+(Evaluator+Only)' alt='Raw Data Plot' class='w-full rounded-lg shadow-md'>
                    <p class='text-sm text-gray-600 mt-2'>Raw lightcurve and astrometry data for Event {event.event_id}, with true model overlaid (Evaluator View).</p>
                </div>
                <div class='mb-6'>
                    <img src='https://placehold.co/600x400/dfc5fa/361d49?text=Mass+vs+Distance+Scatter+Plot+(Evaluator+Only)' alt='Mass vs Distance Plot' class='w-full rounded-lg shadow-md'>
                    <p class='text-sm text-gray-600 mt-2'>Derived Lens Mass vs. Lens Distance for solutions of Event {event.event_id}. Points colored by Relative Probability (Evaluator View).</p>
                </div>
                <div class='mb-6'>
                    <img src='https://placehold.co/600x400/dfc5fa/361d49?text=Proper+Motion+N+vs+E+Plot+(Evaluator+Only)' alt='Proper Motion Plot' class='w-full rounded-lg shadow-md'>
                    <p class='text-sm text-gray-600 mt-2'>Proper Motion North vs. East components for solutions of Event {event.event_id}. Points colored by Relative Probability (Evaluator View).</p>
                </div>
            </section>

            <!-- Footer -->
            <div class='text-sm text-gray-500 text-center pt-8 border-t border-gray-200 mt-10'>
                Generated by microlens-submit v0.13.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>

            <!-- Regex Finish -->

        </div>
    </div>
</body>
</html>"""
    return html 