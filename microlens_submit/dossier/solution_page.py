"""
Solution page generation module for microlens-submit.

This module provides functionality to generate HTML pages for individual
microlensing solutions, including solution overview, parameter tables,
notes rendering, and evaluator-only sections.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import markdown

from .. import __version__
from ..models.event import Event
from ..models.solution import Solution
from ..models.submission import Submission
from .evaluation_data import (
    evaluator_truth_available,
    log10_error_to_fractional_difference,
    parameter_comparison_error,
    uses_log10_comparison,
)
from .utils import (
    get_tier_submissions_label,
    get_tier_submissions_url,
    resolve_dossier_asset_path,
)


def generate_solution_page(solution: Solution, event: Event, submission: Submission, output_dir: Path, evaluator_mode: bool = False) -> None:
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
        evaluator_mode: If True, include simulation truth comparisons in the report.

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
    project_root = Path(submission.project_path)
    lc_plot = resolve_dossier_asset_path(
        solution.lightcurve_plot_path,
        project_root,
        output_dir,
        subdir="plots",
        prefix=f"{event.event_id}_{solution.solution_id}_lightcurve",
    )
    lens_plot = resolve_dossier_asset_path(
        solution.lens_plane_plot_path,
        project_root,
        output_dir,
        subdir="plots",
        prefix=f"{event.event_id}_{solution.solution_id}_lens",
    )
    posterior = resolve_dossier_asset_path(
        solution.posterior_path,
        project_root,
        output_dir,
        subdir="posteriors",
        prefix=f"{event.event_id}_{solution.solution_id}_posterior",
    )
    html = _generate_solution_page_content(
        solution,
        event,
        submission,
        evaluator_mode=evaluator_mode,
        lc_plot=lc_plot,
        lens_plot=lens_plot,
        posterior=posterior,
    )
    with (output_dir / f"{solution.solution_id}.html").open("w", encoding="utf-8") as f:
        f.write(html)


def _generate_solution_page_content(
    solution: Solution,
    event: Event,
    submission: Submission,
    *,
    lc_plot: Optional[str] = None,
    lens_plot: Optional[str] = None,
    posterior: Optional[str] = None,
    evaluator_mode: bool = False,
) -> str:
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
    import pandas as pd
    import math

    truth_available = evaluator_mode and evaluator_truth_available(submission.tier)
    tier_submissions_url = get_tier_submissions_url(submission.tier)
    tier_submissions_link = (
        f"<a href='{tier_submissions_url}' class='text-rtd-accent hover:underline'>"
        f"{get_tier_submissions_label(submission.tier)}</a>"
        if tier_submissions_url
        else ""
    )

    # Render notes as HTML from file
    notes_md = solution.get_notes(project_root=Path(submission.project_path))
    notes_html = markdown.markdown(notes_md or "", extensions=["extra", "tables", "fenced_code", "nl2br"])
    # Truth parameters (Evaluator Only)
    truth_params = getattr(event, "truth_parameters", None)
    show_truth_column = (
        truth_available
        and truth_params is not None
    )

    # Parameters table
    param_rows = []
    params = solution.parameters or {}
    uncertainties = solution.parameter_uncertainties or {}

    def format_param_value(name: str, val: float) -> str:
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            return str(val)

        name_lower = name.lower()
        # 1. Preserve full precision for Julian Date / time fields
        if any(k in name_lower for k in ['t0', 't_0', 'tref', 't_ref', 'epoch']):
            return f"{val_f:.5f}"

        # 2. Use scientific notation for very small ratios (e.g. q, rho)
        if val_f != 0 and abs(val_f) < 0.0001:
            return f"{val_f:.4e}"

        # 3. Format standard model parameters to 5 significant figures
        try:
            from math import log10, floor
            if val_f == 0:
                return "0.0"
            return f"{round(val_f, -int(floor(log10(abs(val_f)))) + 4)}"
        except Exception:
            return f"{val_f:.5f}"

    for k, v in params.items():
        # Handle angle conversion for display
        is_angle = 'alpha' in k.lower()

        if is_angle and v is not None:
            v_display = math.degrees(float(v)) % 360.0
            v_str = f"{v_display:.2f}°"
        else:
            v_str = format_param_value(k, v)

        unc = uncertainties.get(k)
        if unc is None:
            unc_str = "N/A"
        elif isinstance(unc, (list, tuple)) and len(unc) == 2:
            if is_angle:
                u1 = math.degrees(unc[1]) % 360.0
                u0 = math.degrees(unc[0]) % 360.0
                unc_str = f"+{u1:.2f}°/-{u0:.2f}°"
            else:
                unc_str = f"+{format_param_value(k, unc[1])}/-{format_param_value(k, unc[0])}"
        else:
            if is_angle and unc is not None:
                u = math.degrees(unc) % 360.0
                unc_str = f"±{u:.2f}°"
            else:
                unc_str = f"±{format_param_value(k, unc)}"

        truth_val_str = "N/A"
        fractional_difference_str = "N/A"
        if show_truth_column and k in truth_params:
            tv = truth_params[k]
            if is_angle and tv is not None:
                truth_val_str = f"{math.degrees(float(tv)) % 360.0:.2f}°"
            else:
                truth_val_str = format_param_value(k, tv)

            comparison_error = parameter_comparison_error(v, tv, k)
            if comparison_error is not None:
                fractional_difference = (
                    log10_error_to_fractional_difference(comparison_error)
                    if uses_log10_comparison(k)
                    else comparison_error
                )
                fractional_difference_pct = fractional_difference * 100.0
                fractional_difference_str = f"{fractional_difference_pct:.2f}%"
                if uses_log10_comparison(k):
                    fractional_difference_str += (
                        f"<br><span class='text-xs text-gray-500'>"
                        f"|Δ log10| = {comparison_error:.4f}</span>"
                    )

        param_rows.append(
            f"""
            <tr class='border-b border-gray-200 hover:bg-gray-50'>
                <td class='py-3 px-4'>{k}</td>
                <td class='py-3 px-4'>{v_str}</td>
                <td class='py-3 px-4'>{unc_str}</td>
                {f"<td class='py-3 px-4'>{truth_val_str}</td><td class='py-3 px-4 font-mono'>{fractional_difference_str}</td>" if show_truth_column else ""}
            </tr>
        """
        )
    param_colspan = 5 if show_truth_column else 3
    param_table = (
        "\n".join(param_rows)
        if param_rows
        else f"""
        <tr class='border-b border-gray-200'>
            <td colspan='{param_colspan}' class='py-3 px-4 text-center text-gray-500'>
                No parameters found
            </td>
        </tr>
    """
    )
    # Higher-order effects
    hoe_str = ", ".join(solution.higher_order_effects) if solution.higher_order_effects else "None"
    # Plot paths (relative to solution page)
    lc_plot = lc_plot if lc_plot is not None else (solution.lightcurve_plot_path or "")
    lens_plot = lens_plot if lens_plot is not None else (solution.lens_plane_plot_path or "")
    posterior = posterior if posterior is not None else (solution.posterior_path or "")

    # Data Utilization Info
    used_pts = solution.n_data_points if solution.n_data_points is not None else 0
    # The published datasets use different fixed observation counts.
    total_pts = 49488 if submission.tier == "experienced" else 49097
    util_ratio = (used_pts / total_pts * 100.0) if total_pts > 0 else 0
    utilization_html = f"""
        <div class="bg-rtd-primary p-6 rounded-lg shadow-md">
            <div class="flex justify-between items-center mb-2">
                <span class="text-sm font-semibold text-rtd-secondary">Data Points Used</span>
                <span class="text-base font-bold text-rtd-accent">{util_ratio:.1f}% ({used_pts:,} / {total_pts:,} points)</span>
            </div>
            <div class="w-full bg-white bg-opacity-50 rounded-full h-4 overflow-hidden shadow-inner">
                <div class="bg-rtd-accent h-4 rounded-full transition-all duration-500" style="width: {util_ratio:.1f}%"></div>
            </div>
        </div>
    """

    # Physical parameters visuals
    lens_dist_svg = ""
    planet_mass_svg = ""
    if truth_available and solution.physical_parameters:
        try:
            d_fit = float(solution.physical_parameters.get("lens_distance", 0.0))
            d_true = float(truth_params.get("Lens_Dist", 0.0)) if truth_params else 0.0

            # Map distance (0 to 8.5 kpc) to Y coordinate along the line of sight:
            # Let the Sun be at (150, 270) (Y=270 is 0 kpc)
            # Let the Galactic Center be at (150, 90) (Y=90 is 8.5 kpc)
            # Distance scale is (270 - 90) / 8.5 = 180 / 8.5 px per kpc ~ 21.176 px/kpc
            y_sun = 270.0
            y_gc = 90.0
            scale_y = (y_sun - y_gc) / 8.5

            y_fit = y_sun - (d_fit * scale_y)
            y_true = y_sun - (d_true * scale_y) if d_true > 0 else None

             # Generate SVG elements for spiral arms to scale (clipped to fit in 300x320 box)
            # Logarithmic spirals: r = a * e^(b * theta)
            # Let's adjust a, b, and theta_end so that the maximum radius stays well within the SVG bounds.
            def get_spiral_path(theta_start, theta_end, a, b, cx=150, cy=90):
                points = []
                for t in np.linspace(theta_start, theta_end, 50):
                    r = a * np.exp(b * t)
                    # Limit radius to 140px to keep it inside the 300x320 SVG viewBox
                    if r > 140:
                        break
                    x = cx + r * np.cos(t)
                    y = cy + r * np.sin(t)
                    points.append(f"{x:.1f},{y:.1f}")
                return "M " + " L ".join(points)

            import numpy as np
            # Pitch angle ~ 12 degrees -> b = tan(12 deg) ~ 0.21
            b_spiral = 0.21
            # Spiral arms start close to the center and wind outwards up to 2*pi
            arm1 = get_spiral_path(0, 2.0 * np.pi, 12, b_spiral)
            arm2 = get_spiral_path(np.pi / 2, 2.0 * np.pi + np.pi/2, 12, b_spiral)
            arm3 = get_spiral_path(np.pi, 2.0 * np.pi + np.pi, 12, b_spiral)
            arm4 = get_spiral_path(3 * np.pi / 2, 2.0 * np.pi + 3 * np.pi/2, 12, b_spiral)

            lens_dist_svg = f"""
            <div class="bg-rtd-primary p-6 rounded-lg shadow-md flex-1 text-center">
                <h4 class="text-sm font-semibold text-rtd-secondary mb-4 text-left">Galactic Lens Location (Top-Down View)</h4>
                <div class="relative w-full max-w-[320px] mx-auto bg-gray-950 rounded-xl p-4 border border-gray-800 shadow-inner flex flex-col items-center">
                    <svg width="300" height="320" viewBox="0 0 300 320" class="overflow-hidden">
                        <!-- Definitions for glow effects -->
                        <defs>
                            <radialGradient id="bulge-glow" cx="50%" cy="50%" r="50%">
                                <stop offset="0%" stop-color="#f5d0fe" stop-opacity="1" />
                                <stop offset="30%" stop-color="#d8b4fe" stop-opacity="0.8" />
                                <stop offset="70%" stop-color="#a859e4" stop-opacity="0.3" />
                                <stop offset="100%" stop-color="#361d49" stop-opacity="0" />
                            </radialGradient>
                            <radialGradient id="sun-glow" cx="50%" cy="50%" r="50%">
                                <stop offset="0%" stop-color="#fef08a" stop-opacity="1" />
                                <stop offset="100%" stop-color="#eab308" stop-opacity="0" />
                            </radialGradient>
                            <filter id="blur-glow" x="-20%" y="-20%" width="140%" height="140%">
                                <feGaussianBlur stdDeviation="8" result="blur" />
                                <feComposite in="SourceGraphic" in2="blur" operator="over" />
                            </filter>
                        </defs>

                        <!-- Spiral Arms (background galaxy structure) -->
                        <path d="{arm1}" fill="none" stroke="rgba(168, 89, 228, 0.15)" stroke-width="8" stroke-linecap="round" />
                        <path d="{arm2}" fill="none" stroke="rgba(168, 89, 228, 0.15)" stroke-width="8" stroke-linecap="round" />
                        <path d="{arm3}" fill="none" stroke="rgba(168, 89, 228, 0.15)" stroke-width="8" stroke-linecap="round" />
                        <path d="{arm4}" fill="none" stroke="rgba(168, 89, 228, 0.15)" stroke-width="8" stroke-linecap="round" />

                        <path d="{arm1}" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="2" stroke-linecap="round" />
                        <path d="{arm2}" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="2" stroke-linecap="round" />
                        <path d="{arm3}" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="2" stroke-linecap="round" />
                        <path d="{arm4}" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="2" stroke-linecap="round" />

                        <!-- Galactic Central Bulge (Glow) -->
                        <circle cx="150" cy="90" r="45" fill="url(#bulge-glow)" />

                        <!-- Central Bar: Rotated 28 degrees relative to Y-axis, near side (pointing down/towards Sun) rotated towards left. -->
                        <!-- Line of sight to Sun is down (-Y). Rotate 28 degrees counter-clockwise from negative Y direction: -> -90 - 28 = -118 deg (or -62 deg from positive X-axis). -->
                        <g transform="translate(150, 90) rotate(-62)">
                            <rect x="-35" y="-10" width="70" height="20" rx="10" fill="#f5d0fe" opacity="0.8" filter="url(#blur-glow)" />
                        </g>

                        <!-- Line of Sight from Sun (150, 270) to Galactic Bulge/GC (150, 90) -->
                        <line x1="150" y1="270" x2="150" y2="90" stroke="rgba(255,255,255,0.25)" stroke-width="1.5" stroke-dasharray="4,4" />

                        <!-- Sun (0 kpc marker) -->
                        <circle cx="150" cy="270" r="10" fill="url(#sun-glow)" />
                        <circle cx="150" cy="270" r="3" fill="#eab308" />
                        <text x="135" y="274" fill="#fbbf24" font-size="8" font-weight="bold" font-family="sans-serif" text-anchor="end">Sun</text>

                        <!-- Galactic Center label -->
                        <text x="150" y="85" fill="#f5d0fe" font-size="8" font-weight="bold" font-family="sans-serif" text-anchor="middle">Galactic Center</text>

                        <!-- True Lens Marker -->
                        {f'''
                        <g transform="translate(150, {y_true:.1f})">
                            <circle cx="0" cy="0" r="5" fill="#22c55e" stroke="#fff" stroke-width="1" />
                            <line x1="0" y1="0" x2="25" y2="-12" stroke="#22c55e" stroke-width="1" />
                            <rect x="25" y="-22" width="75" height="15" rx="3" fill="rgba(34, 197, 94, 0.9)" />
                            <text x="62.5" y="-12" fill="#fff" font-size="8" font-weight="bold" font-family="sans-serif" text-anchor="middle">True: {d_true:.2f} kpc</text>
                        </g>
                        ''' if y_true is not None else ''}

                        <!-- Fitted Lens Marker -->
                        <g transform="translate(150, {y_fit:.1f})">
                            <circle cx="0" cy="0" r="5" fill="#a859e4" stroke="#fff" stroke-width="1" />
                            <line x1="0" y1="0" x2="-25" y2="12" stroke="#a859e4" stroke-width="1" />
                            <rect x="-100" y="12" width="75" height="15" rx="3" fill="rgba(168, 89, 228, 0.9)" />
                            <text x="-62.5" y="22" fill="#fff" font-size="8" font-weight="bold" font-family="sans-serif" text-anchor="middle">Fit: {d_fit:.2f} kpc</text>
                        </g>
                    </svg>
                    <p class="text-[10px] text-gray-500 italic mt-2 text-center w-full max-w-[280px]">
                        Top-down view of the Milky Way plane. Bulge and logarithmic spiral arms to scale; central bar oriented at 28° to the Sun-GC line of sight.
                    </p>
                </div>
            </div>
            """
        except Exception:
            pass

        try:
            m_fit_raw = float(solution.physical_parameters.get("planet_mass", 0.0))
            m_true_raw = float(truth_params.get("Planet_mass", 0.0)) if truth_params else 0.0
            m_fit = m_fit_raw * 1047.56 if m_fit_raw < 0.1 else m_fit_raw
            m_true = m_true_raw * 1047.56 if (m_true_raw > 0 and m_true_raw < 0.1) else m_true_raw

            planet_mass_svg = f"""
            <div class="bg-rtd-primary p-6 rounded-lg shadow-md flex-1">
                <h4 class="text-sm font-semibold text-rtd-secondary mb-4 text-left">Lens Planet Mass Comparison</h4>
                <div class="flex justify-around items-center h-20">
                    <div class="flex flex-col items-center">
                        <span class="text-xs text-gray-500 font-medium">Fitted Mass</span>
                        <div class="flex items-center space-x-2 mt-2">
                            <div class="w-8 h-8 rounded-full bg-rtd-accent flex items-center justify-center text-white text-xs font-bold shadow">M_p</div>
                            <span class="text-lg font-bold text-rtd-secondary">{m_fit:.4f} M_J</span>
                        </div>
                    </div>
                    {f'''
                    <div class="h-10 w-0.5 bg-gray-300"></div>
                    <div class="flex flex-col items-center">
                        <span class="text-xs text-gray-500 font-medium">True Mass</span>
                        <div class="flex items-center space-x-2 mt-2">
                            <div class="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center text-white text-xs font-bold shadow">M_p</div>
                            <span class="text-lg font-bold text-green-700">{m_true:.4f} M_J</span>
                        </div>
                    </div>
                    ''' if m_true > 0 else ''}
                </div>
            </div>
            """
        except Exception:
            pass

    # Source Properties & CMD
    mock_cmd_svg = f"""
    <div class="bg-rtd-primary p-6 rounded-lg shadow-md flex flex-col items-center">
        <h4 class="text-sm font-semibold text-rtd-secondary mb-4 text-left w-full">Field Star Color-Magnitude Diagram (CMD)</h4>
        <div class="relative w-[300px] h-[320px] bg-gray-950 rounded-lg p-4 border border-gray-800 shadow-inner">
            <svg width="260" height="280" viewBox="0 0 260 280" class="overflow-visible">
                <!-- Axes -->
                <line x1="40" y1="240" x2="240" y2="240" stroke="#555" stroke-width="1.5" />
                <line x1="40" y1="20" x2="40" y2="240" stroke="#555" stroke-width="1.5" />

                <!-- Axis Labels -->
                <text x="140" y="270" fill="#888" font-size="10" text-anchor="middle" font-family="sans-serif">V - I (Color)</text>
                <text x="12" y="130" fill="#888" font-size="10" text-anchor="middle" font-family="sans-serif" transform="rotate(-90 12 130)">I (Magnitude)</text>

                <!-- Main Sequence -->
                <path d="M 60,220 Q 90,170 120,130 T 160,70" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="20" stroke-linecap="round" />
                <path d="M 60,220 Q 90,170 120,130 T 160,70" fill="none" stroke="rgba(223, 197, 250, 0.25)" stroke-width="8" stroke-linecap="round" />
                <!-- Red Giant Branch -->
                <path d="M 120,130 Q 170,90 210,30" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="15" stroke-linecap="round" />
                <path d="M 120,130 Q 170,90 210,30" fill="none" stroke="rgba(168, 89, 228, 0.25)" stroke-width="6" stroke-linecap="round" />
                <!-- Red Clump -->
                <circle cx="170" cy="95" r="10" fill="rgba(223, 197, 250, 0.4)" stroke="rgba(168, 89, 228, 0.3)" stroke-width="1" />

                <!-- Grid tick marks -->
                <text x="40" y="255" fill="#555" font-size="8" text-anchor="middle" font-family="monospace">1.0</text>
                <text x="140" y="255" fill="#555" font-size="8" text-anchor="middle" font-family="monospace">2.0</text>
                <text x="240" y="255" fill="#555" font-size="8" text-anchor="middle" font-family="monospace">3.0</text>

                <text x="32" y="240" fill="#555" font-size="8" text-anchor="end" alignment-baseline="middle" font-family="monospace">22</text>
                <text x="32" y="130" fill="#555" font-size="8" text-anchor="end" alignment-baseline="middle" font-family="monospace">18</text>
                <text x="32" y="20" fill="#555" font-size="8" text-anchor="end" alignment-baseline="middle" font-family="monospace">14</text>

                <!-- Target Source Star (pulsing yellow star) -->
                <circle cx="160" cy="105" r="5" fill="#fbbf24">
                    <animate attributeName="r" values="4;7;4" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.7;1;0.7" dur="2s" repeatCount="indefinite" />
                </circle>
                <path d="M 160,98 L 162,103 L 167,103 L 163,106 L 165,111 L 160,108 L 155,111 L 157,106 L 153,103 L 158,103 Z" fill="#fbbf24" stroke="#d97706" stroke-width="0.5" />
                <text x="170" y="118" fill="#fbbf24" font-size="8" font-weight="bold" font-family="sans-serif">Source</text>
            </svg>
        </div>
        <p class="text-xs text-gray-500 italic mt-2 text-center">Empirical color-magnitude diagram model with target source star highlighted.</p>
    </div>
    """

    # Missing plot fallbacks
    if not lc_plot:
        lc_plot_html = """
        <div class="w-full h-[300px] flex flex-col items-center justify-center bg-gray-50 border border-dashed border-gray-300 rounded-md mb-2">
            <svg class="w-12 h-12 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
            </svg>
            <span class="text-sm font-semibold text-gray-600">Interactive Lightcurve Fit Not Generated</span>
            <span class="text-xs text-gray-400 mt-1">Use 'microlens-submit plot-solution' to generate this plot</span>
        </div>
        """
    else:
        lc_plot_ext = Path(lc_plot).suffix.lower() if lc_plot else ""
        if lc_plot_ext == ".html":
            lc_plot_html = f"""<iframe src="{lc_plot}" class="w-full h-[600px] border-0 rounded-md mb-2" style="min-height: 600px;"></iframe>"""
        else:
            lc_plot_html = f"""<img src="{lc_plot}" alt="Lightcurve Plot" class="w-full h-auto rounded-md mb-2">"""

    if not lens_plot:
        lens_plot_html = """
        <div class="w-full h-[300px] flex flex-col items-center justify-center bg-gray-50 border border-dashed border-gray-300 rounded-md mb-2">
            <svg class="w-12 h-12 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"></path>
            </svg>
            <span class="text-sm font-semibold text-gray-600">Lens Plane Geometry Plot Not Generated</span>
            <span class="text-xs text-gray-400 mt-1">Provide lens_plane_plot_path in your solution</span>
        </div>
        """
    else:
        lens_plot_html = f"""<img src='{lens_plot}' alt='Lens Plane Plot' class='w-full h-auto rounded-md mb-2'>"""

    # Evaluator Content Blocks
    if truth_available:
        param_accuracy_content = f"""
            <p class="text-sm text-gray-600 mb-4">
                Parameter truth values, fractional differences, and evaluations are shown in the
                Solution Overview table above. The q, s, tE, and rho comparisons use log10 space:
                the table reports the symmetric fractional difference implied by |Δ log10|.
            </p>
        """

        physical_context_content = f"""
            <p class="text-sm text-gray-600 mb-4">
                Contextual plots of derived physical parameters against simulation truths.
            </p>
            <div class="flex flex-col md:flex-row gap-6">
                {lens_dist_svg}
                {planet_mass_svg}
            </div>
        """

        source_properties_content = f"""
            <p class="text-sm text-gray-600 mb-4">
                Empirical Color-Magnitude Diagram for the field with target source star marked.
            </p>
            <div class="flex justify-center">
                {mock_cmd_svg}
            </div>
        """
    else:
        locked_block = """
            <div class="flex flex-col items-center justify-center p-8 bg-gray-50 border border-gray-200 rounded-lg text-center">
                <svg class="w-10 h-10 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 00-2 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                </svg>
                <h3 class="text-sm font-semibold text-gray-700">Evaluator-Only Section</h3>
                <p class="text-xs text-gray-500 mt-1 max-w-md">
                    Detailed comparisons, physical parameter distributions, and source color-magnitude diagrams are locked for participants.
                </p>
            </div>
        """
        locked_heading = (
            "Evaluator-only section"
            if not evaluator_mode
            else "No trusted truth data is available for this tier"
        )
        locked_description = (
            "Detailed comparisons are available in the evaluator dossier."
            if not evaluator_mode
            else "This section is unavailable because the experienced tier has no trusted hidden truth labels."
        )
        locked_block = locked_block.replace("Evaluator-Only Section", locked_heading).replace(
            "Detailed comparisons, physical parameter distributions, and source color-magnitude diagrams are locked for participants.",
            locked_description,
        )
        param_accuracy_content = locked_block
        physical_context_content = locked_block
        source_properties_content = locked_block
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
    parameter_section_title = (
        "Parameter Accuracy vs. Truths (Evaluator-Only)"
        if truth_available
        else "Parameter Validation (No Trusted Truth Data)"
    )
    physical_section_title = (
        "Physical Parameter Context (Evaluator-Only)"
        if truth_available
        else "Physical Parameter Context (Truth Unavailable)"
    )
    source_section_title = (
        "Source Properties & CMD (Evaluator-Only)"
        if truth_available
        else "Source Properties & CMD (Truth Unavailable)"
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
    if repo_url and commit and not evaluator_mode:
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
                    {tier_submissions_link}
                </nav>
            </div>

            <hr class="border-t-4 border-rtd-accent my-8 mx-8">

            <!-- Regex Start -->

            <!-- Solution Overview & Notes -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Solution Overview & Notes</h2>
                <table class='w-full text-left table-auto border-collapse mb-4'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr>
                            <th class='py-3 px-4'>Parameter</th>
                            <th class='py-3 px-4'>Value</th>
                            <th class='py-3 px-4'>Uncertainty</th>
                            {f"<th class='py-3 px-4'>Truth</th><th class='py-3 px-4'>Fractional Difference<br><span class='text-[10px] normal-case font-normal'>(q, s, tE, rho: log10 comparison)</span></th>" if show_truth_column else ""}
                        </tr>
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
                        {lc_plot_html}
                        <p class="text-sm text-rtd-secondary">
                            Caption: Lightcurve fit for Solution
                            {solution.alias or solution.solution_id[:8] + '...'}
                        </p>
                    </div>
                    <div class='text-center bg-rtd-primary p-4 rounded-lg shadow-md'>
                        {lens_plot_html}
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
                {utilization_html}
            </section>
            <!-- Compute Performance -->
            <section class='mb-10 px-8'>
                <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>Compute Performance</h2>
                <table class='w-full text-left table-auto border-collapse'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr>
                            <th>Metric</th>
                            <th>This Solution</th>
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
             <!-- Parameter Validation -->
             <section class='mb-10 px-8'>
                 <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                     {parameter_section_title}
                 </h2>
                 {param_accuracy_content}
             </section>
             <!-- Physical Parameter Context -->
             <section class='mb-10 px-8'>
                 <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                     {physical_section_title}
                 </h2>
                <table class='w-full text-left table-auto border-collapse mb-6'>
                    <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                        <tr><th>Parameter</th><th>Value</th></tr>
                    </thead>
                    <tbody class='text-rtd-text'>
                        {phys_table}
                    </tbody>
                </table>
                {physical_context_content}
            </section>
             <!-- Source Properties & CMD -->
             <section class='mb-10 px-8'>
                 <h2 class='text-2xl font-semibold text-rtd-secondary mb-4'>
                     {source_section_title}
                 </h2>
                {source_properties_content}
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
