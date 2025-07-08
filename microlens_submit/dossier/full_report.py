"""
Full dossier report generation module for microlens-submit.

This module provides functionality to generate comprehensive printable HTML
dossier reports that combine all dashboard, event, and solution content
into a single document.
"""

import json
from datetime import datetime
from pathlib import Path

from ..models import Submission
from ..models.solution import Solution
from .dashboard import _generate_dashboard_content
from .event_page import _generate_event_page_content
from .solution_page import _generate_solution_page_content


def generate_full_dossier_report_html(submission: Submission, output_dir: Path) -> None:
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
        >>> from microlens_submit.dossier import generate_full_dossier_report_html
        >>> from pathlib import Path
        >>>
        >>> submission = load("./my_project")
        >>>
        >>> # Generate comprehensive dossier
        >>> generate_full_dossier_report_html(submission, Path("./dossier_output"))
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
    dash_body = extract_main_content_body(dash_html)
    all_html_sections.append(dash_body)
    all_html_sections.append('<hr class="my-8 border-t-2 border-rtd-accent">')  # Divider after dashboard

    # Events and solutions
    for event in submission.events.values():
        event_html = _generate_event_page_content(event, submission)
        event_body = extract_main_content_body(event_html, section_type="event", section_id=event.event_id)
        all_html_sections.append(event_body)
        all_html_sections.append('<hr class="my-8 border-t-2 border-rtd-accent">')  # Divider after event

        for sol in event.get_active_solutions():
            sol_html = _generate_solution_page_content(sol, event, submission)
            sol_body = extract_main_content_body(
                sol_html,
                section_type="solution",
                section_id=sol.solution_id,
                project_root=Path(submission.project_path),
                solution=sol,
            )
            all_html_sections.append(sol_body)
            all_html_sections.append('<hr class="my-8 border-t-2 border-rtd-accent">')  # Divider after solution

    # Compose the full HTML
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    header = f"""
    <div class="text-center py-8 bg-rtd-primary text-rtd-secondary">
        <img src='assets/rges-pit_logo.png' alt='RGES-PIT Logo' class='w-48 mx-auto mb-6'>
        <h1 class="text-3xl font-bold mb-2">Comprehensive Submission Dossier</h1>
        <p class="text-lg">Generated on: {now}</p>
        <p class="text-md">
            Team: {submission.team_name} | Tier: {submission.tier}
        </p>
    </div>
    <hr class="border-t-4 border-rtd-accent my-8">
    """
    html = f"""<!DOCTYPE html>
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
    <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"
        rel="stylesheet"
    >
    <!-- Highlight.js for code syntax highlighting -->
    <link
        rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css"
    >
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js">
    </script>
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
</html>"""
    with (output_dir / "full_dossier_report.html").open("w", encoding="utf-8") as f:
        f.write(html)


def extract_main_content_body(
    html: str,
    section_type: str = None,
    section_id: str = None,
    project_root: Path = None,
    solution: Solution = None,
) -> str:
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
        project_root: Path to the project root directory. Used to access aliases.json
            for solution alias lookups.
        solution: Solution object (required when section_type is 'solution'). Used
            to get model_type and other solution metadata for the heading.

    Returns:
        str: Extracted and formatted HTML content ready for inclusion in
            the full dossier report.

    Raises:
        ValueError: If required regex markers are not found in the HTML.

    Example:
        >>> # Extract dashboard content
        >>> dashboard_html = _generate_dashboard_content(submission)
        >>> dashboard_body = extract_main_content_body(dashboard_html)
        >>>
        >>> # Extract event content
        >>> event_html = _generate_event_page_content(event, submission)
        >>> event_body = extract_main_content_body(event_html, 'event', 'EVENT001')
        >>>
        >>> # Extract solution content
        >>> solution_html = _generate_solution_page_content(solution, event, submission)
        >>> solution_body = extract_main_content_body(solution_html, 'solution', 'sol_uuid', project_root, solution)

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
        content = html[start_pos : finish_pos + len(finish_marker)]

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
        content = html[start_pos : finish_pos + len(finish_marker)]

        # Remove the markers
        content = content.replace(start_marker, "").replace(finish_marker, "")

        # Optionally add a heading
        heading = ""
        section_class = ""
        if section_type == "event" and section_id:
            heading = f'<h2 class="text-3xl font-bold text-rtd-accent my-8">Event: {section_id}</h2>'
            section_class = "dossier-event-section"
        elif section_type == "solution" and section_id:
            # Look up alias from aliases.json if project_root is provided
            alias_key = None
            if project_root:
                aliases_file = project_root / "aliases.json"
                if aliases_file.exists():
                    try:
                        with aliases_file.open("r", encoding="utf-8") as f:
                            aliases = json.load(f)
                        # Look up the solution_id in the aliases
                        for key, uuid in aliases.items():
                            if uuid == section_id:
                                alias_key = key
                                break
                    except (json.JSONDecodeError, KeyError):
                        pass

            # Get model type from solution object
            model_type = solution.model_type if solution else "Unknown"

            if alias_key:
                heading = f"""<h2 class="text-3xl font-bold text-rtd-accent my-6">Solution: {alias_key}</h2>
                <h3 class="text-lg text-gray-600 mb-4">Model Type: {model_type} | UUID: {section_id}</h3>"""
            else:
                heading = f"""<h2 class="text-3xl font-bold text-rtd-accent my-6">Solution: {section_id}</h2>
                <h3 class="text-lg text-gray-600 mb-4">Model Type: {model_type}</h3>"""
            section_class = "dossier-solution-section"

        # Wrap in a section for clarity
        return f'<section class="{section_class}">\n{heading}\n{content.strip()}\n</section>'
