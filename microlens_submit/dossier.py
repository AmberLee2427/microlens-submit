"""
Dossier generation module for microlens-submit.

This module provides functionality to generate HTML dossiers and dashboards
for submission review and documentation.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import markdown  # Add this import at the top

from .api import Submission, Event, Solution


def generate_dashboard_html(submission: Submission, output_dir: Path) -> None:
    """
    Generate an HTML dashboard for the submission.
    
    Args:
        submission: The submission object containing events and solutions
        output_dir: Directory where the HTML files will be saved
    """
    # Create output directory structure
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "assets").mkdir(exist_ok=True)
    (output_dir / "events").mkdir(exist_ok=True)
    
    # Generate the main dashboard HTML
    html_content = _generate_dashboard_content(submission)
    
    # Write the HTML file
    with (output_dir / "index.html").open("w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Copy logo if it exists in the project
    logo_source = Path(__file__).parent / "assets" / "rges-pit_logo.png"
    if logo_source.exists():
        import shutil
        shutil.copy2(logo_source, output_dir / "assets" / "rges-pit_logo.png")

    # After generating index.html, generate event pages
    for event in submission.events.values():
        generate_event_page(event, submission, output_dir / "events")


def _generate_dashboard_content(submission: Submission) -> str:
    """
    Generate the HTML content for the submission dashboard following Dashboard_Design.md.
    
    Args:
        submission: The submission object
        
    Returns:
        Complete HTML content as a string
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
                    <a href="events/{event.event_id}.html" class="font-medium text-rtd-accent hover:underline">
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
            </div>
            
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
            
            <!-- Footer -->
            <div class="text-sm text-gray-500 text-center pt-8 pb-6">
                Generated by microlens-submit v0.12.0-dev on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return html


def _format_hardware_info(hardware_info: Optional[Dict[str, Any]]) -> str:
    """Format hardware information for display."""
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
    """
    Generate an HTML dossier page for a single event, following Event_Page_Design.md.
    Args:
        event: The Event object
        submission: The parent Submission object
        output_dir: The 'events' subdirectory where the HTML file will be saved
    """
    # Prepare event output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    html = _generate_event_page_content(event, submission)
    with (output_dir / f"{event.event_id}.html").open("w", encoding="utf-8") as f:
        f.write(html)

    # After generating the event page, generate solution pages
    for sol in event.solutions.values():
        generate_solution_page(sol, event, submission, output_dir / event.event_id / "solutions")

def _generate_event_page_content(event: Event, submission: Submission) -> str:
    """
    Generate the HTML content for an event dossier page.
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
                    <a href=\"{event.event_id}/solutions/{sol.solution_id}.html\" class=\"font-medium text-rtd-accent hover:underline\">{sol.solution_id[:8]}...</a>
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
</head>
<body class='font-inter bg-rtd-background'>
    <div class='max-w-7xl mx-auto p-6 lg:p-8'>
        <div class='bg-white shadow-xl rounded-lg'>
            <!-- Header & Navigation -->
            <div class='text-center py-8'>
                <img src='../assets/rges-pit_logo.png' alt='RGES-PIT Logo' class='w-48 mx-auto mb-6'>
                <h1 class='text-4xl font-bold text-rtd-secondary text-center mb-2'>Event Dossier: {event.event_id}</h1>
                <p class='text-xl text-rtd-accent text-center mb-4'>Team: {submission.team_name or 'Not specified'} | Tier: {submission.tier or 'Not specified'}</p>
                <nav class='flex justify-center space-x-4 mb-8'>
                    <a href='../index.html' class='text-rtd-accent hover:underline'>&larr; Back to Dashboard</a>
                </nav>
            </div>
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
                Generated by microlens-submit v0.12.0-dev on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
        </div>
    </div>
</body>
</html>"""
    return html 

def generate_solution_page(solution: Solution, event: Event, submission: Submission, output_dir: Path) -> None:
    """
    Generate an HTML dossier page for a single solution, following Solution_Page_Design.md.
    Args:
        solution: The Solution object
        event: The parent Event object
        submission: The grandparent Submission object
        output_dir: The 'events/[event_id]/solutions' subdirectory where the HTML file will be saved
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    html = _generate_solution_page_content(solution, event, submission)
    with (output_dir / f"{solution.solution_id}.html").open("w", encoding="utf-8") as f:
        f.write(html)

def _generate_solution_page_content(solution: Solution, event: Event, submission: Submission) -> str:
    """
    Generate the HTML content for a solution dossier page.
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
    <style> .prose code {{ background: #f3f3f3; padding: 2px 4px; border-radius: 4px; }} </style>
</head>
<body class='font-inter bg-rtd-background'>
    <div class='max-w-7xl mx-auto p-6 lg:p-8'>
        <div class='bg-white shadow-xl rounded-lg'>
            <!-- Header & Navigation -->
            <div class='text-center py-8'>
                <img src='../../../assets/rges-pit_logo.png' alt='RGES-PIT Logo' class='w-48 mx-auto mb-6'>
                <h1 class='text-4xl font-bold text-rtd-secondary text-center mb-2'>Solution Dossier: {solution.solution_id[:8]}...</h1>
                <p class='text-xl text-rtd-accent text-center mb-4'>Event: {event.event_id} | Team: {submission.team_name or 'Not specified'} | Tier: {submission.tier or 'Not specified'}</p>
                <nav class='flex justify-center space-x-4 mb-8'>
                    <a href='../{event.event_id}.html' class='text-rtd-accent hover:underline'>&larr; Back to Event {event.event_id}</a>
                    <a href='../../index.html' class='text-rtd-accent hover:underline'>&larr; Back to Dashboard</a>
                </nav>
            </div>
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
                        <p class='text-sm text-rtd-secondary'>Caption: Lightcurve fit for Solution {solution.solution_id[:8]}...</p>
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
                Generated by microlens-submit v0.12.0-dev on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
        </div>
    </div>
</body>
</html>"""
    return html 