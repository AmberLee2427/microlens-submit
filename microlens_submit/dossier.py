"""
Dossier generation module for microlens-submit.

This module provides functionality to generate HTML dossiers and dashboards
for submission review and documentation.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

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
    logo_source = Path(__file__).parent.parent / "assets" / "rges-pit_logo.png"
    if logo_source.exists():
        import shutil
        shutil.copy2(logo_source, output_dir / "assets" / "rges-pit_logo.png")


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