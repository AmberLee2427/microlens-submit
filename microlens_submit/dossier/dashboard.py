"""
Dashboard generation module for microlens-submit.

This module provides functionality to generate the main dashboard HTML page
for submission review and documentation. The dashboard provides an overview
of the submission including event summaries, solution statistics, and metadata.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import importlib.resources as importlib_resources
except ImportError:
    import importlib_resources

from ..models import Submission, Event, Solution
from .utils import format_hardware_info, extract_github_repo_name


def generate_dashboard_html(submission: Submission, output_dir: Path) -> None:
    """Generate a complete HTML dossier for the submission.

    Creates a comprehensive HTML dashboard that provides an overview of the submission,
    including event summaries, solution statistics, and metadata. The dossier includes:
    - Main dashboard (index.html) with submission overview
    - Individual event pages for each event
    - Individual solution pages for each solution
    - Full comprehensive dossier (full_dossier_report.html) for printing

    The function creates the output directory structure and copies necessary assets
    like logos and GitHub icons.

    Args:
        submission: The submission object containing events and solutions.
        output_dir: Directory where the HTML files will be saved. Will be created
            if it doesn't exist.

    Raises:
        OSError: If unable to create output directory or write files.
        ValueError: If submission data is invalid or missing required fields.

    Example:
        >>> from microlens_submit import load
        >>> from microlens_submit.dossier import generate_dashboard_html
        >>> from pathlib import Path
        >>>
        >>> # Load a submission project
        >>> submission = load("./my_project")
        >>>
        >>> # Generate the complete dossier
        >>> generate_dashboard_html(submission, Path("./dossier_output"))
        >>>
        >>> # Files created:
        >>> # - ./dossier_output/index.html (main dashboard)
        >>> # - ./dossier_output/EVENT001.html (event page)
        >>> # - ./dossier_output/solution_id.html (solution pages)
        >>> # - ./dossier_output/full_dossier_report.html (printable version)
        >>> # - ./dossier_output/assets/ (logos and icons)

    Note:
        This function generates all dossier components. For partial generation
        (e.g., only specific events), use the CLI command with --event-id or
        --solution-id flags instead.
    """
    # Create output directory structure
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "assets").mkdir(exist_ok=True)
    # (No events or solutions subfolders)

    # Check if full dossier report exists
    full_dossier_exists = (output_dir / "full_dossier_report.html").exists()
    # Generate the main dashboard HTML
    html_content = _generate_dashboard_content(
        submission, full_dossier_exists=full_dossier_exists
    )

    # Write the HTML file
    with (output_dir / "index.html").open("w", encoding="utf-8") as f:
        f.write(html_content)

    # Copy logos using importlib_resources for robust package data access
    def _get_asset_path(package, filename):
        try:
            # Python 3.9+ or importlib_resources >= 3.1
            return importlib_resources.files(package).joinpath(filename)
        except AttributeError:
            # Python 3.8 fallback
            with importlib_resources.path(package, filename) as p:
                return p

    try:
        logo_path = _get_asset_path('microlens_submit.assets', 'rges-pit_logo.png')
        shutil.copy2(logo_path, output_dir / "assets" / "rges-pit_logo.png")
    except (FileNotFoundError, ModuleNotFoundError, AttributeError):
        pass
    try:
        github_logo_path = _get_asset_path('microlens_submit.assets', 'github-desktop_logo.png')
        shutil.copy2(github_logo_path, output_dir / "assets" / "github-desktop_logo.png")
    except (FileNotFoundError, ModuleNotFoundError, AttributeError):
        pass

    # After generating index.html, generate event pages
    # Import here to avoid circular imports
    from .event_page import generate_event_page
    for event in submission.events.values():
        generate_event_page(event, submission, output_dir)


def _generate_dashboard_content(
    submission: Submission, full_dossier_exists: bool = False
) -> str:
    """Generate the HTML content for the submission dashboard.

    Creates the main dashboard HTML following the Dashboard_Design.md specification.
    The dashboard includes submission statistics, progress tracking, event tables,
    and aggregate parameter distributions.

    Args:
        submission: The submission object containing events and solutions.
        full_dossier_exists: Whether the full dossier report exists. Currently
            ignored but kept for future use.

    Returns:
        str: Complete HTML content as a string, ready to be written to index.html.

    Example:
        >>> from microlens_submit import load
        >>> from microlens_submit.dossier import _generate_dashboard_content
        >>>
        >>> submission = load("./my_project")
        >>> html_content = _generate_dashboard_content(submission)
        >>>
        >>> # Write to file
        >>> with open("dashboard.html", "w", encoding="utf-8") as f:
        ...     f.write(html_content)

    Note:
        This is an internal function. Use generate_dashboard_html() for the
        complete dossier generation workflow.
    """
    # Calculate statistics
    total_events = len(submission.events)
    total_active_solutions = sum(
        len(event.get_active_solutions()) for event in submission.events.values()
    )
    total_cpu_hours = 0
    total_wall_time_hours = 0

    # Calculate compute time
    for event in submission.events.values():
        for solution in event.solutions.values():
            if solution.compute_info:
                total_cpu_hours += solution.compute_info.get("cpu_hours", 0)
                total_wall_time_hours += solution.compute_info.get("wall_time_hours", 0)

    # Format hardware info
    hardware_info_str = format_hardware_info(submission.hardware_info)

    # Calculate progress (hardcoded total from design spec)
    TOTAL_CHALLENGE_EVENTS = 293
    progress_percentage = (
        (total_events / TOTAL_CHALLENGE_EVENTS) * 100
        if TOTAL_CHALLENGE_EVENTS > 0
        else 0
    )

    # Generate event table
    event_rows = []
    for event in sorted(submission.events.values(), key=lambda e: e.event_id):
        active_solutions = event.get_active_solutions()
        model_types = set(sol.model_type for sol in active_solutions)
        model_types_str = ", ".join(sorted(model_types)) if model_types else "None"

        event_rows.append(
            f"""
            <tr class="border-b border-gray-200 hover:bg-gray-50">
                <td class="py-3 px-4">
                    <a href="{event.event_id}.html" class="font-medium text-rtd-accent hover:underline">
                        {event.event_id}
                    </a>
                </td>
                <td class="py-3 px-4">{len(active_solutions)}</td>
                <td class="py-3 px-4">{model_types_str}</td>
            </tr>
        """
        )

    event_table = (
        "\n".join(event_rows)
        if event_rows
        else """
        <tr class="border-b border-gray-200">
            <td colspan="3" class="py-3 px-4 text-center text-gray-500">No events found</td>
        </tr>
    """
    )

    # Insert Print Full Dossier placeholder before the footer
    print_link_html = "<!--FULL_DOSSIER_LINK_PLACEHOLDER-->"

    # GitHub repo link (if present)
    github_html = ""
    repo_url = getattr(submission, "repo_url", None) or (
        submission.repo_url if hasattr(submission, "repo_url") else None
    )
    if repo_url:
        repo_name = extract_github_repo_name(repo_url)
        github_html = f"""
        <div class="flex items-center justify-center mb-4">
            <a href="{repo_url}" target="_blank" rel="noopener" class="flex items-center space-x-2 group">
                <img src="assets/github-desktop_logo.png" alt="GitHub" class="w-6 h-6 inline-block align-middle mr-2 group-hover:opacity-80" style="display:inline;vertical-align:middle;">
                <span class="text-base text-rtd-accent font-semibold group-hover:underline">{repo_name}</span>
            </a>
        </div>
        """

    # Generate the complete HTML following the design spec
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Microlensing Data Challenge Submission Dossier - {submission.team_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
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
<body class="font-inter bg-rtd-background">
    <div class="max-w-7xl mx-auto p-6 lg:p-8">
        <div class="bg-white shadow-xl rounded-lg">
            <!-- Header Section -->
            <div class="text-center py-8">
                <img src="./assets/rges-pit_logo.png" alt="RGES-PIT Logo" class="w-48 mx-auto mb-6">
                <h1 class="text-4xl font-bold text-rtd-secondary text-center mb-2">
                    Microlensing Data Challenge Submission Dossier
                </h1>
                <p class="text-xl text-rtd-accent text-center mb-8">
                    Team: {submission.team_name or 'Not specified'} | Tier: {submission.tier or 'Not specified'}
                </p>
                {github_html}
            </div>

            <hr class="border-t-4 border-rtd-accent my-8 mx-8">

            <!-- Regex Start -->
            
            <!-- Submission Summary Section -->
            <section class="mb-10 px-8">
                <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Submission Overview</h2>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center">
                        <p class="text-sm font-medium text-rtd-secondary">Total Events Submitted</p>
                        <p class="text-4xl font-bold text-rtd-accent mt-2">{total_events}</p>
                    </div>
                    <div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center">
                        <p class="text-sm font-medium text-rtd-secondary">Total Active Solutions</p>
                        <p class="text-4xl font-bold text-rtd-accent mt-2">{total_active_solutions}</p>
                    </div>
                    <div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center">
                        <p class="text-sm font-medium text-rtd-secondary">Hardware Information</p>
                        <p class="text-lg text-rtd-text mt-2">{hardware_info_str}</p>
                    </div>
                </div>
            </section>
            
            <!-- Overall Progress & Compute Time -->
            <section class="mb-10 px-8">
                <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Challenge Progress & Compute Summary</h2>
                
                <!-- Progress Bar -->
                <div class="w-full bg-gray-200 rounded-full h-4 mb-4">
                    <div class="bg-rtd-accent h-4 rounded-full" style="width: {progress_percentage}%"></div>
                </div>
                <p class="text-sm text-rtd-text text-center mb-6">
                    {total_events} / {TOTAL_CHALLENGE_EVENTS} Events Processed ({progress_percentage:.1f}%)
                </p>
                
                <!-- Compute Time Summary -->
                <div class="text-lg text-rtd-text mb-2">
                    <p><strong>Total CPU Hours:</strong> {total_cpu_hours:.2f}</p>
                    <p><strong>Total Wall Time Hours:</strong> {total_wall_time_hours:.2f}</p>
                </div>
                <p class="text-sm text-gray-500 italic">
                    Note: Comparison to other teams' compute times is available in the Evaluator Dossier.
                </p>
            </section>
            
            <!-- Event List -->
            <section class="mb-10 px-8">
                <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Submitted Events</h2>
                <table class="w-full text-left table-auto border-collapse">
                    <thead class="bg-rtd-primary text-rtd-secondary uppercase text-sm">
                        <tr>
                            <th class="py-3 px-4">Event ID</th>
                            <th class="py-3 px-4">Active Solutions</th>
                            <th class="py-3 px-4">Model Types Submitted</th>
                        </tr>
                    </thead>
                    <tbody class="text-rtd-text">
                        {event_table}
                    </tbody>
                </table>
            </section>
            
            <!-- Aggregate Parameter Distributions (Placeholders) -->
            <section class="mb-10 px-8">
                <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Aggregate Parameter Distributions</h2>
                <p class="text-sm text-gray-500 italic mb-4">
                    Note: These plots show distributions from <em>your</em> submitted solutions. Comparisons to simulation truths and other teams' results are available in the Evaluator Dossier.
                </p>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="text-center">
                        <img src="https://placehold.co/600x300/dfc5fa/361d49?text=tE+Distribution+from+Your+Solutions" 
                             alt="tE Distribution" class="w-full rounded-lg shadow-md">
                        <p class="text-sm text-gray-600 mt-2">Histogram of Einstein Crossing Times (tE) from your active solutions.</p>
                    </div>
                    <div class="text-center">
                        <img src="https://placehold.co/600x300/dfc5fa/361d49?text=u0+Distribution+from+Your+Solutions" 
                             alt="u0 Distribution" class="w-full rounded-lg shadow-md">
                        <p class="text-sm text-gray-600 mt-2">Histogram of Impact Parameters (u0) from your active solutions.</p>
                    </div>
                    <div class="text-center">
                        <img src="https://placehold.co/600x300/dfc5fa/361d49?text=Lens+Mass+Distribution+from+Your+Solutions" 
                             alt="M_L Distribution" class="w-full rounded-lg shadow-md">
                        <p class="text-sm text-gray-600 mt-2">Histogram of derived Lens Masses (M_L) from your active solutions.</p>
                    </div>
                    <div class="text-center">
                        <img src="https://placehold.co/600x300/dfc5fa/361d49?text=Lens+Distance+Distribution+from+Your+Solutions" 
                             alt="D_L Distribution" class="w-full rounded-lg shadow-md">
                        <p class="text-sm text-gray-600 mt-2">Histogram of derived Lens Distances (D_L) from your active solutions.</p>
                    </div>
                </div>
            </section>
            {print_link_html}

            <!-- Footer -->
            <div class="text-sm text-gray-500 text-center pt-8 pb-6">
                Generated by microlens-submit v0.14.0 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>

            <!-- Regex Finish -->

        </div>
    </div>
</body>
</html>"""

    return html 