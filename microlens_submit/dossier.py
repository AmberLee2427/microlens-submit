"""
Dossier generation module for microlens-submit.

This module provides functionality to generate HTML dossiers and dashboards
for submission review and documentation. It creates comprehensive, printable
HTML reports that showcase microlensing challenge submissions with detailed
statistics, visualizations, and participant notes.

The module generates three types of HTML pages:
1. Dashboard (index.html) - Overview of all events and solutions
2. Event pages - Detailed view of each event with its solutions
3. Solution pages - Individual solution details with parameters and notes

All pages use Tailwind CSS for styling and include syntax highlighting for
code blocks in participant notes.

Example:
    >>> from microlens_submit import load
    >>> from microlens_submit.dossier import generate_dashboard_html
    >>> 
    >>> # Load a submission
    >>> submission = load("./my_project")
    >>> 
    >>> # Generate the complete dossier
    >>> generate_dashboard_html(submission, Path("./dossier_output"))
    >>> 
    >>> # The dossier will be created at ./dossier_output/index.html
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import markdown  # Add this import at the top
import re
import os
import sys

from .api import Submission, Event, Solution


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
    html_content = _generate_dashboard_content(submission, full_dossier_exists=full_dossier_exists)
    
    # Write the HTML file
    with (output_dir / "index.html").open("w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Copy logos if they exist in the project
    logo_source = Path(__file__).parent / "assets" / "rges-pit_logo.png"
    if logo_source.exists():
        import shutil
        shutil.copy2(logo_source, output_dir / "assets" / "rges-pit_logo.png")
    
    # Copy GitHub logo if it exists in the project
    github_logo_source = Path(__file__).parent / "assets" / "github-desktop_logo.png"
    if github_logo_source.exists():
        import shutil
        shutil.copy2(github_logo_source, output_dir / "assets" / "github-desktop_logo.png")

    # After generating index.html, generate event pages
    for event in submission.events.values():
        generate_event_page(event, submission, output_dir)


def _generate_dashboard_content(submission: Submission, full_dossier_exists: bool = False) -> str:
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
        >>> with open("dashboard.html", "w") as f:
        ...     f.write(html_content)
    
    Note:
        This is an internal function. Use generate_dashboard_html() for the
        complete dossier generation workflow.
    """
    # Calculate statistics
    total_events = len(submission.events)
    total_active_solutions = sum(len(event.get_active_solutions()) for event in submission.events.values())
    total_cpu_hours = 0
    total_wall_time_hours = 0
    
    # Calculate compute time
    for event in submission.events.values():
        for solution in event.solutions.values():
            if solution.compute_info:
                total_cpu_hours += solution.compute_info.get('cpu_hours', 0)
                total_wall_time_hours += solution.compute_info.get('wall_time_hours', 0)
    
    # Format hardware info
    hardware_info_str = _format_hardware_info(submission.hardware_info)
    
    # Calculate progress (hardcoded total from design spec)
    TOTAL_CHALLENGE_EVENTS = 293
    progress_percentage = (total_events / TOTAL_CHALLENGE_EVENTS) * 100 if TOTAL_CHALLENGE_EVENTS > 0 else 0
    
    # Generate event table
    event_rows = []
    for event in sorted(submission.events.values(), key=lambda e: e.event_id):
        active_solutions = event.get_active_solutions()
        model_types = set(sol.model_type for sol in active_solutions)
        model_types_str = ", ".join(sorted(model_types)) if model_types else "None"
        
        event_rows.append(f"""
            <tr class="border-b border-gray-200 hover:bg-gray-50">
                <td class="py-3 px-4">
                    <a href="{event.event_id}.html" class="font-medium text-rtd-accent hover:underline">
                        {event.event_id}
                    </a>
                </td>
                <td class="py-3 px-4">{len(active_solutions)}</td>
                <td class="py-3 px-4">{model_types_str}</td>
            </tr>
        """)
    
    event_table = "\n".join(event_rows) if event_rows else """
        <tr class="border-b border-gray-200">
            <td colspan="3" class="py-3 px-4 text-center text-gray-500">No events found</td>
        </tr>
    """
    
    # Insert Print Full Dossier placeholder before the footer
    print_link_html = "<!--FULL_DOSSIER_LINK_PLACEHOLDER-->"
    
    # GitHub repo link (if present)
    github_html = ""
    repo_url = getattr(submission, 'repo_url', None) or (submission.repo_url if hasattr(submission, 'repo_url') else None)
    if repo_url:
        repo_name = _extract_github_repo_name(repo_url)
        github_html = f'''
        <div class="flex items-center justify-center mb-4">
            <a href="{repo_url}" target="_blank" rel="noopener" class="flex items-center space-x-2 group">
                <img src="assets/github-desktop_logo.png" alt="GitHub" class="w-6 h-6 inline-block align-middle mr-2 group-hover:opacity-80" style="display:inline;vertical-align:middle;">
                <span class="text-base text-rtd-accent font-semibold group-hover:underline">{repo_name}</span>
            </a>
        </div>
        '''
    
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
                Generated by microlens-submit v0.12.1 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>

            <!-- Regex Finish -->

        </div>
    </div>
</body>
</html>"""
    
    return html


def _format_hardware_info(hardware_info: Optional[Dict[str, Any]]) -> str:
    """Format hardware information for display in the dashboard.
    
    Converts hardware information dictionary into a human-readable string
    suitable for display in the dashboard. Handles various hardware info
    formats and provides fallbacks for missing information.
    
    Args:
        hardware_info: Dictionary containing hardware information. Can include
            keys like 'cpu_details', 'cpu', 'memory_gb', 'ram_gb', 'nexus_image'.
            If None or empty, returns "Not specified".
    
    Returns:
        str: Formatted hardware information string for display.
    
    Example:
        >>> hardware_info = {
        ...     'cpu_details': 'Intel Xeon E5-2680 v4',
        ...     'memory_gb': 64,
        ...     'nexus_image': 'roman-science-platform:latest'
        ... }
        >>> _format_hardware_info(hardware_info)
        'CPU: Intel Xeon E5-2680 v4, RAM: 64GB, Platform: Roman Nexus'
        
        >>> _format_hardware_info(None)
        'Not specified'
        
        >>> _format_hardware_info({'custom_field': 'custom_value'})
        'custom_field: custom_value'
    
    Note:
        This function handles multiple hardware info formats for compatibility
        with different submission sources. It prioritizes detailed CPU info
        over basic CPU info and provides fallbacks for missing data.
    """
    if not hardware_info:
        return "Not specified"
    
    parts = []
    
    # Common hardware fields
    if 'cpu_details' in hardware_info:
        parts.append(f"CPU: {hardware_info['cpu_details']}")
    elif 'cpu' in hardware_info:
        parts.append(f"CPU: {hardware_info['cpu']}")
    
    if 'memory_gb' in hardware_info:
        parts.append(f"RAM: {hardware_info['memory_gb']}GB")
    elif 'ram_gb' in hardware_info:
        parts.append(f"RAM: {hardware_info['ram_gb']}GB")
    
    if 'nexus_image' in hardware_info:
        parts.append(f"Platform: Roman Nexus")
    
    if parts:
        return ", ".join(parts)
    else:
        # Fallback: show any available info
        return ", ".join(f"{k}: {v}" for k, v in hardware_info.items() if v is not None) 


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
        >>> with open("event_page.html", "w") as f:
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
            -(sol.relative_probability if sol.relative_probability is not None else float('-inf')),
            sol.solution_id
        )
    solutions = sorted(event.solutions.values(), key=sort_key)
    # Table rows
    rows = []
    for sol in solutions:
        status = '<span class="text-green-600">Active</span>' if sol.is_active else '<span class="text-red-600">Inactive</span>'
        logl = f"{sol.log_likelihood:.2f}" if sol.log_likelihood is not None else "N/A"
        ndp = str(sol.n_data_points) if sol.n_data_points is not None else "N/A"
        relprob = f"{sol.relative_probability:.3f}" if sol.relative_probability is not None else "N/A"
        # Read notes snippet from file
        notes_snip = (sol.get_notes(project_root=Path(submission.project_path))[:50] + ("..." if len(sol.get_notes(project_root=Path(submission.project_path))) > 50 else "")) if sol.notes_path else ""
        rows.append(f"""
            <tr class='border-b border-gray-200 hover:bg-gray-50'>
                <td class='py-3 px-4'>
                    <a href="{sol.solution_id}.html" class="font-medium text-rtd-accent hover:underline">{sol.solution_id[:8]}...</a>
                </td>
                <td class='py-3 px-4'>{sol.model_type}</td>
                <td class='py-3 px-4'>{status}</td>
                <td class='py-3 px-4'>{logl}</td>
                <td class='py-3 px-4'>{ndp}</td>
                <td class='py-3 px-4'>{relprob}</td>
                <td class='py-3 px-4 text-gray-600 italic'>{notes_snip}</td>
            </tr>
        """)
    table_body = "\n".join(rows) if rows else """
        <tr class='border-b border-gray-200'><td colspan='7' class='py-3 px-4 text-center text-gray-500'>No solutions found</td></tr>
    """
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
                Generated by microlens-submit v0.12.1 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>

            <!-- Regex Finish -->

        </div>
    </div>
</body>
</html>"""
    return html 

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
        >>> with open("solution_page.html", "w") as f:
        ...     f.write(html_content)
    
    Note:
        Parameter uncertainties are formatted as ±value or +upper/-lower
        depending on the uncertainty format. Notes are rendered from markdown
        with syntax highlighting for code blocks. GitHub commit links are
        included if git information is available in compute_info.
    """
    # Render notes as HTML from file
    notes_md = solution.get_notes(project_root=Path(submission.project_path))
    notes_html = markdown.markdown(notes_md or "", extensions=["extra", "tables", "fenced_code"])
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
        param_rows.append(f"""
            <tr class='border-b border-gray-200 hover:bg-gray-50'>
                <td class='py-3 px-4'>{k}</td>
                <td class='py-3 px-4'>{v}</td>
                <td class='py-3 px-4'>{unc_str}</td>
            </tr>
        """)
    param_table = "\n".join(param_rows) if param_rows else """
        <tr class='border-b border-gray-200'><td colspan='3' class='py-3 px-4 text-center text-gray-500'>No parameters found</td></tr>
    """
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
        phys_rows.append(f"""
            <tr class='border-b border-gray-200 hover:bg-gray-50'>
                <td class='py-3 px-4'>{k}</td>
                <td class='py-3 px-4'>{v}</td>
            </tr>
        """)
    phys_table = "\n".join(phys_rows) if phys_rows else """
        <tr class='border-b border-gray-200'><td colspan='2' class='py-3 px-4 text-center text-gray-500'>No physical parameters found</td></tr>
    """
    # GitHub commit link (if present)
    repo_url = getattr(submission, 'repo_url', None) or (submission.repo_url if hasattr(submission, 'repo_url') else None)
    commit = None
    if solution.compute_info:
        git_info = solution.compute_info.get('git_info')
        if git_info:
            commit = git_info.get('commit')
    commit_html = ""
    if repo_url and commit:
        commit_short = commit[:8]
        commit_url = f"{repo_url.rstrip('/')}/commit/{commit}"
        commit_html = f'''<a href="{commit_url}" target="_blank" rel="noopener" title="View this commit on GitHub" class="inline-flex items-center space-x-1 ml-2 align-middle">
            <img src="assets/github-desktop_logo.png" alt="GitHub Commit" class="w-4 h-4 inline-block align-middle" style="display:inline;vertical-align:middle;">
            <span class="text-xs text-rtd-accent font-mono">{commit_short}</span>
        </a>'''
    # HTML content
    html = f"""<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>Solution Dossier: {solution.solution_id[:8]}... - {submission.team_name}</title>
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
                <h1 class='text-4xl font-bold text-rtd-secondary text-center mb-2'>Solution Dossier: {solution.solution_id[:8]}...</h1>
                <p class='text-xl text-rtd-accent text-center mb-4'>Event: {event.event_id} | Team: {submission.team_name or 'Not specified'} | Tier: {submission.tier or 'Not specified'} {commit_html}</p>
                <nav class='flex justify-center space-x-4 mb-8'>
                    <a href='{event.event_id}.html' class='text-rtd-accent hover:underline'>&larr; Back to Event {event.event_id}</a>
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
                        <img src='{lc_plot}' alt='Lightcurve Plot' class='w-full h-auto rounded-md mb-2'>
                        <p class="text-sm text-rtd-secondary">Caption: Lightcurve fit for Solution {solution.solution_id[:8]}...</p>
                    </div>
                    <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md'>
                        <img src='{lens_plot}' alt='Lens Plane Plot' class='w-full h-auto rounded-md mb-2'>
                        <p class='text-sm text-rtd-secondary'>Caption: Lens plane geometry for Solution {solution.solution_id[:8]}...</p>
                    </div>
                </div>
                {f"<p class='text-rtd-text mt-4 text-center'>Posterior Samples: <a href='{posterior}' class='text-rtd-accent hover:underline'>Download Posterior Data</a></p>" if posterior else ''}
            </section>
            <!-- Fit Statistics & Data Utilization -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Fit Statistics & Data Utilization</h2>
                <div class='grid grid-cols-1 md:grid-cols-2 gap-6'>
                    <div class='bg-rtd-primary p-6 rounded-lg shadow-md text-center'>
                        <p class='text-sm font-medium text-rtd-secondary'>Log-Likelihood</p>
                        <p class='text-4xl font-bold text-rtd-accent mt-2'>{solution.log_likelihood if solution.log_likelihood is not None else 'N/A'}</p>
                    </div>
                    <div class='bg-rtd-primary p-6 rounded-lg shadow-md text-center'>
                        <p class='text-sm font-medium text-rtd-secondary'>N Data Points Used</p>
                        <p class='text-4xl font-bold text-rtd-accent mt-2'>{solution.n_data_points if solution.n_data_points is not None else 'N/A'}</p>
                    </div>
                </div>
                <h3 class='text-xl font-semibold text-rtd-secondary mt-6 mb-2'>Data Utilization Ratio</h3>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md'>
                    <img src='https://placehold.co/600x100/dfc5fa/361d49?text=Data+Utilization+Infographic' alt='Data Utilization' class='w-full h-auto rounded-md mb-2'>
                    <p class='text-sm text-rtd-secondary'>Caption: Percentage of total event data points utilized in this solution's fit.</p>
                </div>
            </section>
            <!-- Compute Performance -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Compute Performance</h2>
                <table class='w-full text-left table-auto border-collapse'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr><th>Metric</th><th>Your Solution</th><th>Same-Team Average</th><th>All-Submission Average</th></tr>
                    </thead>
                    <tbody class='text-rtd-text'>
                        <tr><td>CPU Hours</td><td>{solution.compute_info.get('cpu_hours', 'N/A') if solution.compute_info else 'N/A'}</td><td>N/A for Participants</td><td>N/A for Participants</td></tr>
                        <tr><td>Wall Time (Hrs)</td><td>{solution.compute_info.get('wall_time_hours', 'N/A') if solution.compute_info else 'N/A'}</td><td>N/A for Participants</td><td>N/A for Participants</td></tr>
                    </tbody>
                </table>
                <p class='text-sm text-gray-500 italic mt-4'>Note: Comparison to other teams' compute times is available in the Evaluator Dossier.</p>
            </section>
            <!-- Parameter Accuracy vs. Truths (Evaluator-Only) -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Parameter Accuracy vs. Truths (Evaluator-Only)</h2>
                <p class='text-sm text-gray-500 italic mb-4'>You haven't fucked up. This just isn't for you. Detailed comparisons of your fitted parameters against simulation truths are available in the Evaluator Dossier.</p>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md'>
                    <img src='https://placehold.co/800x300/dfc5fa/361d49?text=Parameter+Comparison+Table+(Evaluator+Only)' alt='Parameter Comparison Table' class='w-full h-auto rounded-md mb-2'>
                    <p class='text-sm text-rtd-secondary'>Caption: A table comparing fitted parameters to true values (Evaluator View).</p>
                </div>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6'>
                    <img src='https://placehold.co/800x400/dfc5fa/361d49?text=Parameter+Difference+Distributions+(Evaluator+Only)' alt='Parameter Difference Distributions' class='w-full h-auto rounded-md mb-2'>
                    <p class='text-sm text-rtd-secondary'>Caption: Distributions of (True - Fit) for key parameters across all challenge submissions (Evaluator View).</p>
                </div>
            </section>
            <!-- Physical Parameter Context (Evaluator-Only) -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Physical Parameter Context (Evaluator-Only)</h2>
                <p class='text-sm text-gray-500 italic mb-4'>You haven't fucked up. This just isn't for you. Contextual plots of derived physical parameters against population models are available in the Evaluator Dossier.</p>
                <table class='w-full text-left table-auto border-collapse'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr><th>Parameter</th><th>Value</th></tr>
                    </thead>
                    <tbody class='text-rtd-text'>
                        {phys_table}
                    </tbody>
                </table>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6'>
                    <img src='https://placehold.co/600x400/dfc5fa/361d49?text=Physical+Parameter+Distribution+(Evaluator+Only)' alt='Physical Parameter Distribution' class='w-full h-auto rounded-md mb-2'>
                    <p class='text-sm text-rtd-secondary'>Caption: Your solution's derived physical parameters plotted against a simulated test set (Evaluator View).</p>
                </div>
            </section>
            <!-- Source Properties & CMD (Evaluator-Only) -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Source Properties & CMD (Evaluator-Only)</h2>
                <p class='text-sm text-gray-500 italic mb-4'>You haven't fucked up. This just isn't for you. Source color and magnitude diagrams are available in the Evaluator Dossier.</p>
                <div class='text-rtd-text'>
                    <!-- Placeholder for source color/mag details -->
                </div>
                <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md mt-6'>
                    <img src='https://placehold.co/600x400/dfc5fa/361d49?text=Color-Magnitude+Diagram+with+Source+(Evaluator+Only)' alt='Color-Magnitude Diagram' class='w-full h-auto rounded-md mb-2'>
                    <p class='text-sm text-rtd-secondary'>Caption: Color-Magnitude Diagram for the event's field with source marked (Evaluator View).</p>
                </div>
            </section>

            <!-- Footer -->
            <div class='text-sm text-gray-500 text-center pt-8 border-t border-gray-200 mt-10'>
                Generated by microlens-submit v0.12.1 on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>

            <!-- Regex Finish -->
            
        </div>
    </div>
</body>
</html>"""
    return html 

def _extract_main_content_body(html: str, section_type: str = None, section_id: str = None) -> str:
    """Extract main content for the full dossier using explicit markers.
    
    Extracts the main content from HTML pages using explicit marker comments.
    This function is used to create the comprehensive full dossier report by
    extracting content from individual pages and combining them.
    
    Args:
        html: The complete HTML content to extract from.
        section_type: Type of section being extracted. If None, extracts dashboard
            content. If 'event' or 'solution', extracts and formats accordingly.
        section_id: Identifier for the section (event_id or solution_id). Used
            to create section headings in the full dossier.
    
    Returns:
        str: Extracted and formatted HTML content ready for inclusion in
            the full dossier report.
    
    Raises:
        ValueError: If required regex markers are not found in the HTML.
    
    Example:
        >>> # Extract dashboard content
        >>> dashboard_html = _generate_dashboard_content(submission)
        >>> dashboard_body = _extract_main_content_body(dashboard_html)
        >>> 
        >>> # Extract event content
        >>> event_html = _generate_event_page_content(event, submission)
        >>> event_body = _extract_main_content_body(event_html, 'event', 'EVENT001')
        >>> 
        >>> # Extract solution content
        >>> solution_html = _generate_solution_page_content(solution, event, submission)
        >>> solution_body = _extract_main_content_body(solution_html, 'solution', 'sol_uuid')
    
    Note:
        This function relies on HTML comments <!-- Regex Start --> and
        <!-- Regex Finish --> to identify content boundaries. These markers
        must be present in the source HTML for extraction to work.
    """
    if section_type is None:  # dashboard
        # Extract everything between the markers
        start_marker = "<!-- Regex Start -->"
        finish_marker = "<!-- Regex Finish -->"
        
        start_pos = html.find(start_marker)
        finish_pos = html.find(finish_marker)
        
        if start_pos == -1 or finish_pos == -1:
            raise ValueError("Could not find regex markers in dashboard HTML")
        
        # Extract content between markers (including the markers themselves)
        content = html[start_pos:finish_pos + len(finish_marker)]
        
        # Remove the markers
        content = content.replace(start_marker, "").replace(finish_marker, "")
        
        return content.strip()
    else:
        # For event/solution: extract content between markers, remove header/nav/logo, add heading, wrap in <section>
        start_marker = "<!-- Regex Start -->"
        finish_marker = "<!-- Regex Finish -->"
        
        start_pos = html.find(start_marker)
        finish_pos = html.find(finish_marker)
        
        if start_pos == -1 or finish_pos == -1:
            raise ValueError("Could not find regex markers in HTML")
        
        # Extract content between markers
        content = html[start_pos:finish_pos + len(finish_marker)]
        
        # Remove the markers
        content = content.replace(start_marker, "").replace(finish_marker, "")
        
        # Optionally add a heading
        heading = ''
        section_class = ''
        if section_type == 'event' and section_id:
            heading = f'<h2 class="text-3xl font-bold text-rtd-accent my-8">Event: {section_id}</h2>'
            section_class = 'dossier-event-section'
        elif section_type == 'solution' and section_id:
            heading = f'<h2 class="text-3xl font-bold text-rtd-accent my-6">Solution: {section_id}</h2>'
            section_class = 'dossier-solution-section'
        
        # Wrap in a section for clarity
        return f'<section class="{section_class}">\n{heading}\n{content.strip()}\n</section>'


def _generate_full_dossier_report_html(submission, output_dir):
    """Generate a comprehensive printable HTML dossier report.
    
    Creates a single HTML file that concatenates all dossier sections (dashboard,
    events, and solutions) into one comprehensive, printable document. This is
    useful for creating a complete submission overview that can be printed or
    shared as a single file.
    
    Args:
        submission: The submission object containing all events and solutions.
        output_dir: Directory where the full dossier report will be saved.
            The file will be named full_dossier_report.html.
    
    Raises:
        OSError: If unable to write the HTML file.
        ValueError: If submission data is invalid or extraction fails.
    
    Example:
        >>> from microlens_submit import load
        >>> from microlens_submit.dossier import _generate_full_dossier_report_html
        >>> from pathlib import Path
        >>> 
        >>> submission = load("./my_project")
        >>> 
        >>> # Generate comprehensive dossier
        >>> _generate_full_dossier_report_html(submission, Path("./dossier_output"))
        >>> 
        >>> # Creates: ./dossier_output/full_dossier_report.html
        >>> # This file contains all dashboard, event, and solution content
        >>> # in a single, printable HTML document
    
    Note:
        This function creates a comprehensive report by extracting content from
        individual pages and combining them with section dividers. The report
        includes all active solutions and maintains the same styling as
        individual pages. This is typically called automatically by
        generate_dashboard_html() when creating a full dossier.
    """
    all_html_sections = []
    # Dashboard (extract only main content, skip header/logo)
    dash_html = _generate_dashboard_content(submission, full_dossier_exists=True)
    dash_body = _extract_main_content_body(dash_html)
    all_html_sections.append(dash_body)
    all_html_sections.append('<hr class="my-8 border-t-2 border-rtd-accent">')  # Divider after dashboard
    
    # Events and solutions
    for event in submission.events.values():
        event_html = _generate_event_page_content(event, submission)
        event_body = _extract_main_content_body(event_html, section_type='event', section_id=event.event_id)
        all_html_sections.append(event_body)
        all_html_sections.append('<hr class="my-8 border-t-2 border-rtd-accent">')  # Divider after event
        
        for sol in event.get_active_solutions():
            sol_html = _generate_solution_page_content(sol, event, submission)
            sol_body = _extract_main_content_body(sol_html, section_type='solution', section_id=sol.solution_id)
            all_html_sections.append(sol_body)
            all_html_sections.append('<hr class="my-8 border-t-2 border-rtd-accent">')  # Divider after solution
    
    # Compose the full HTML
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    header = f'''
    <div class="text-center py-8 bg-rtd-primary text-rtd-secondary">
        <img src='assets/rges-pit_logo.png' alt='RGES-PIT Logo' class='w-48 mx-auto mb-6'>
        <h1 class="text-3xl font-bold mb-2">Comprehensive Submission Dossier</h1>
        <p class="text-lg">Generated on: {now}</p>
        <p class="text-md">Team: {submission.team_name} | Tier: {submission.tier}</p>
    </div>
    <hr class="border-t-4 border-rtd-accent my-8">
    '''
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Dossier Report - {submission.team_name}</title>
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
        {header}
        {''.join(all_html_sections)}
    </div>
</body>
</html>'''
    with (output_dir / "full_dossier_report.html").open("w", encoding="utf-8") as f:
        f.write(html) 

def _extract_github_repo_name(repo_url: str) -> str:
    """Extract owner/repo name from a GitHub URL.
    
    Parses GitHub repository URLs to extract the owner and repository name
    in a display-friendly format. Handles various GitHub URL formats including
    HTTPS, SSH, and URLs with .git extension.
    
    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/owner/repo,
            git@github.com:owner/repo.git, etc.)
    
    Returns:
        str: Repository name in "owner/repo" format, or the original URL
            if parsing fails.
    
    Example:
        >>> _extract_github_repo_name("https://github.com/username/microlens-submit")
        'username/microlens-submit'
        
        >>> _extract_github_repo_name("git@github.com:username/microlens-submit.git")
        'username/microlens-submit'
        
        >>> _extract_github_repo_name("https://github.com/org/repo-name")
        'org/repo-name'
        
        >>> _extract_github_repo_name("invalid-url")
        'invalid-url'
    
    Note:
        This function uses regex to parse GitHub URLs and handles common
        variations. If the URL doesn't match expected patterns, it returns
        the original URL unchanged.
    """
    import re
    match = re.search(r'github\.com[:/]+([\w.-]+)/([\w.-]+)', repo_url)
    if match:
        return f"{match.group(1)}/{match.group(2).replace('.git','')}"
    return repo_url 