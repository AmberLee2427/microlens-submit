"""
Dossier generation package for microlens-submit.

This package provides functionality to generate HTML dossiers and dashboards
for submission review and documentation. It creates comprehensive, printable
HTML reports that showcase microlensing challenge submissions with detailed
statistics, visualizations, and participant notes.

The package generates three types of HTML pages:
1. Dashboard (index.html) - Overview of all events and solutions
2. Event pages - Detailed view of each event with its solutions
3. Solution pages - Individual solution details with parameters and notes

All pages use Tailwind CSS for styling and include syntax highlighting for
code blocks in participant notes.

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
    This package is designed to be used primarily through the CLI command
    `microlens-submit generate-dossier`, but can also be used programmatically
    for custom dossier generation workflows.
"""

from .dashboard import generate_dashboard_html
from .event_page import generate_event_page
from .full_report import generate_full_dossier_report_html
from .solution_page import generate_solution_page

__all__ = [
    "generate_dashboard_html",
    "generate_event_page",
    "generate_solution_page",
    "generate_full_dossier_report_html",
]
