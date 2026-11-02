"""
Dashboard generation module for microlens-submit.

This module provides functionality to generate the main dashboard HTML page
for submission review and documentation. The dashboard provides an overview
of the submission including event summaries, solution statistics, and metadata.
"""

import webbrowser
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .. import __version__
from ..models.submission import Submission
from ..tier_validation import get_tier_event_list
from .evaluation_data import evaluator_truth_available
from .utils import (
    copy_dossier_assets,
    extract_github_repo_name,
    format_hardware_info,
    get_tier_submissions_label,
    get_tier_submissions_url,
)


def generate_dashboard_html(
    submission: Submission,
    output_dir: Path,
    open: bool = False,
    evaluator_mode: bool = False,
) -> None:
    """Generate a complete HTML dossier for the submission."""
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    copy_dossier_assets(output_dir)
    full_dossier_exists = (output_dir / "full_dossier_report.html").exists()

    confusion_matrix_html = ""
    cohort_confusion_matrix_html = ""
    q_scatter_html = ""
    te_scatter_html = ""
    rho_scatter_html = ""
    u0_scatter_html = ""
    t0_scatter_html = ""
    classification_metrics_table_html = ""
    planet_metrics_table_html = ""
    modelling_metrics_table_html = ""
    efficiency_metrics_table_html = ""
    confidence_hist_html = ""
    parallax_hist_html = ""
    bl_s_scatter_html = ""
    bl_alpha_scatter_html = ""
    bs_s_scatter_html = ""
    bs_alpha_scatter_html = ""
    bs_flux_ratio_scatter_html = ""
    phys_mass_scatter_html = ""
    phys_dl_scatter_html = ""
    uncertainties_hist_html = ""
    precision_stats: Dict[str, Any] = {}

    cohort_num_teams = "N/A"
    cohort_mean_progress = None
    event_consensus = {}
    event_comparison_metrics = {}
    cohort_avg = {}
    cohort_teams = {}
    truth_available = evaluator_mode and evaluator_truth_available(submission.tier)

    if evaluator_mode:
        files_to_load = [
            ("confusion_matrix.html", "confusion_matrix_html"),
            ("q_scatter.html", "q_scatter_html"),
            ("te_scatter.html", "te_scatter_html"),
            ("rho_scatter.html", "rho_scatter_html"),
            ("u0_scatter.html", "u0_scatter_html"),
            ("t0_scatter.html", "t0_scatter_html"),
            ("classification_metrics_table.html", "classification_metrics_table_html"),
            ("planet_metrics_table.html", "planet_metrics_table_html"),
            ("modelling_metrics_table.html", "modelling_metrics_table_html"),
            ("efficiency_metrics_table.html", "efficiency_metrics_table_html"),
            ("confidence_hist.html", "confidence_hist_html"),
            ("parallax_hist.html", "parallax_hist_html"),
            ("bl_s_scatter.html", "bl_s_scatter_html"),
            ("bl_alpha_scatter.html", "bl_alpha_scatter_html"),
            ("bs_s_scatter.html", "bs_s_scatter_html"),
            ("bs_alpha_scatter.html", "bs_alpha_scatter_html"),
            ("bs_flux_ratio_scatter.html", "bs_flux_ratio_scatter_html"),
            ("phys_mass_scatter.html", "phys_mass_scatter_html"),
            ("phys_dl_scatter.html", "phys_dl_scatter_html"),
            ("uncertainties_hist.html", "uncertainties_hist_html"),
        ]
        local_content = {}
        for filename, key in files_to_load:
            filepath = assets_dir / filename
            if filepath.exists():
                with filepath.open("r", encoding="utf-8") as f:
                    local_content[key] = f.read()
            else:
                local_content[key] = ""

        confusion_matrix_html = local_content["confusion_matrix_html"]
        q_scatter_html = local_content["q_scatter_html"]
        te_scatter_html = local_content["te_scatter_html"]
        rho_scatter_html = local_content.get("rho_scatter_html", "")
        u0_scatter_html = local_content.get("u0_scatter_html", "")
        t0_scatter_html = local_content.get("t0_scatter_html", "")
        classification_metrics_table_html = local_content.get("classification_metrics_table_html", "")
        planet_metrics_table_html = local_content["planet_metrics_table_html"]
        modelling_metrics_table_html = local_content["modelling_metrics_table_html"]
        efficiency_metrics_table_html = local_content.get("efficiency_metrics_table_html", "")
        confidence_hist_html = local_content["confidence_hist_html"]
        parallax_hist_html = local_content["parallax_hist_html"]
        bl_s_scatter_html = local_content["bl_s_scatter_html"]
        bl_alpha_scatter_html = local_content["bl_alpha_scatter_html"]
        bs_s_scatter_html = local_content["bs_s_scatter_html"]
        bs_alpha_scatter_html = local_content["bs_alpha_scatter_html"]
        bs_flux_ratio_scatter_html = local_content["bs_flux_ratio_scatter_html"]
        phys_mass_scatter_html = local_content["phys_mass_scatter_html"]
        phys_dl_scatter_html = local_content["phys_dl_scatter_html"]
        if not truth_available:
            q_scatter_html = ""
            te_scatter_html = ""
            rho_scatter_html = ""
            u0_scatter_html = ""
            t0_scatter_html = ""
            classification_metrics_table_html = ""
            planet_metrics_table_html = ""
            modelling_metrics_table_html = ""
            efficiency_metrics_table_html = ""
            parallax_hist_html = ""
            bl_s_scatter_html = ""
            bl_alpha_scatter_html = ""
            bs_s_scatter_html = ""
            bs_alpha_scatter_html = ""
            bs_flux_ratio_scatter_html = ""
            phys_mass_scatter_html = ""
            phys_dl_scatter_html = ""
        # Dynamically load all uncertainties_*_hist.html plots
        uncert_plots = []
        for filepath in assets_dir.glob("uncertainties_*_hist.html"):
            param_name = filepath.name.replace("uncertainties_", "").replace("_hist.html", "")
            with filepath.open("r", encoding="utf-8") as f:
                plot_html = f.read()
            uncert_plots.append((param_name, plot_html))

        param_order = ["tE", "u0", "t0", "q", "s", "alpha", "t0_source2", "u0_source2", "flux_ratio", "planet_mass", "lens_distance", "piEN", "piEE"]
        uncert_plots.sort(key=lambda x: param_order.index(x[0]) if x[0] in param_order else 99)

        if uncert_plots:
            grid_html = "<div class='grid grid-cols-1 md:grid-cols-2 gap-6 mt-4'>"
            for param_name, plot_html in uncert_plots:
                grid_html += f"""
                <div class='bg-white p-4 rounded-lg shadow-sm border border-gray-100 mb-4'>
                    {plot_html}
                </div>
                """
            grid_html += "</div>"
            uncertainties_hist_html = grid_html
        else:
            uncertainties_hist_html = local_content.get("uncertainties_hist_html", "")

        prec_stats_file = assets_dir / "precision_stats.json"
        if prec_stats_file.exists():
            try:
                with prec_stats_file.open("r", encoding="utf-8") as f:
                    precision_stats = json.load(f)
            except Exception:
                pass

        comp_metrics_file = assets_dir / "event_comparison_metrics.json"
        if truth_available and comp_metrics_file.exists():
            with comp_metrics_file.open("r", encoding="utf-8") as f:
                event_comparison_metrics = json.load(f)

        # Search for cohort_analysis directory: try cohort-level parent dirs
        # output_dir = .../team_name/dossier/
        # cohort_analysis could be at: .../cohort_level/cohort_analysis/
        # where cohort_level = output_dir.parent.parent (sibling of team dir)
        shared_dir = None
        search_root = output_dir.resolve().parent.parent  # e.g., mock_submission/test_cohort/
        candidate = search_root / "cohort_analysis"
        if candidate.is_dir():
            shared_dir = candidate
        else:
            # Legacy fallback: project_root/rmdc26/cohort_analysis
            shared_dir = output_dir.resolve().parent.parent.parent / "rmdc26" / "cohort_analysis"

        cohort_matrix_file = shared_dir / "cohort_confusion_matrix.html"
        if cohort_matrix_file.exists():
            with cohort_matrix_file.open("r", encoding="utf-8") as f:
                cohort_confusion_matrix_html = f.read()

        cohort_metrics_file = shared_dir / "cohort_metrics.json"
        if cohort_metrics_file.exists():
            try:
                with cohort_metrics_file.open("r", encoding="utf-8") as f:
                    cdata = json.load(f)
                    summary = cdata.get("cohort_summary", {})
                    cohort_num_teams = str(summary.get("num_teams", "N/A"))
                    cohort_mean_progress = summary.get("mean_progress")
                    event_consensus = cdata.get("event_consensus", {})
                    cohort_avg = cdata.get("cohort_avg", {})
                    cohort_teams = cdata.get("teams", {})
            except Exception:
                pass


    # Load category ranks (written by generate_interactive_plots.py)
    classification_rank = "N/A"
    classification_sublabel = "Event F1: N/A | Planet F1: N/A"
    accuracy_rank = "N/A"
    precision_rank = "N/A"
    efficiency_rank = "N/A"
    if evaluator_mode and truth_available:
        cat_ranks_file = assets_dir / "category_ranks.json"
        if cat_ranks_file.exists():
            try:
                with cat_ranks_file.open("r", encoding="utf-8") as f:
                    cr = json.load(f)
                    classification_rank = cr.get("classification", "N/A")
                    classification_sublabel = cr.get(
                        "classification_sublabel",
                        "Event F1: N/A | Planet F1: N/A",
                    )
                    accuracy_rank = cr.get("accuracy", "N/A")
                    precision_rank = cr.get("precision", "N/A")
                    efficiency_rank = cr.get("efficiency", "N/A")
            except Exception:
                pass

    html_content = _generate_dashboard_content(
        submission,
        full_dossier_exists=full_dossier_exists,
        evaluator_mode=evaluator_mode,
        confusion_matrix_html=confusion_matrix_html,
        cohort_confusion_matrix_html=cohort_confusion_matrix_html,
        q_scatter_html=q_scatter_html,
        te_scatter_html=te_scatter_html,
        rho_scatter_html=rho_scatter_html,
        u0_scatter_html=u0_scatter_html,
        t0_scatter_html=t0_scatter_html,
        classification_metrics_table_html=classification_metrics_table_html,
        planet_metrics_table_html=planet_metrics_table_html,
        modelling_metrics_table_html=modelling_metrics_table_html,
        efficiency_metrics_table_html=efficiency_metrics_table_html,
        parallax_hist_html=parallax_hist_html,
        bl_s_scatter_html=bl_s_scatter_html,
        bl_alpha_scatter_html=bl_alpha_scatter_html,
        bs_s_scatter_html=bs_s_scatter_html,
        bs_alpha_scatter_html=bs_alpha_scatter_html,
        bs_flux_ratio_scatter_html=bs_flux_ratio_scatter_html,
        phys_mass_scatter_html=phys_mass_scatter_html,
        phys_dl_scatter_html=phys_dl_scatter_html,
        confidence_hist_html=confidence_hist_html,
        uncertainties_hist_html=uncertainties_hist_html,
        precision_stats=precision_stats,
        cohort_num_teams=cohort_num_teams,
        cohort_mean_progress=cohort_mean_progress,
        event_consensus=event_consensus,
        event_comparison_metrics=event_comparison_metrics,
        classification_rank=classification_rank,
        classification_sublabel=classification_sublabel,
        accuracy_rank=accuracy_rank,
        precision_rank=precision_rank,
        efficiency_rank=efficiency_rank,
        cohort_avg=cohort_avg,
        cohort_teams=cohort_teams,
    )

    index_path = output_dir / "index.html"
    with index_path.open("w", encoding="utf-8") as f:
        f.write(html_content)

    from .event_page import generate_event_page
    for event in submission.events.values():
        generate_event_page(event, submission, output_dir, evaluator_mode=evaluator_mode)

    if open:
        webbrowser.open(index_path.resolve().as_uri())


def _generate_dashboard_content(
    submission: Submission,
    full_dossier_exists: bool = False,
    evaluator_mode: bool = False,
    confusion_matrix_html: str = "",
    cohort_confusion_matrix_html: str = "",
    q_scatter_html: str = "",
    te_scatter_html: str = "",
    rho_scatter_html: str = "",
    u0_scatter_html: str = "",
    t0_scatter_html: str = "",
    classification_metrics_table_html: str = "",
    planet_metrics_table_html: str = "",
    modelling_metrics_table_html: str = "",
    efficiency_metrics_table_html: str = "",
    parallax_hist_html: str = "",
    bl_s_scatter_html: str = "",
    bl_alpha_scatter_html: str = "",
    bs_s_scatter_html: str = "",
    bs_alpha_scatter_html: str = "",
    bs_flux_ratio_scatter_html: str = "",
    phys_mass_scatter_html: str = "",
    phys_dl_scatter_html: str = "",
    confidence_hist_html: str = "",
    uncertainties_hist_html: str = "",
    precision_stats: Dict[str, Any] = None,
    cohort_num_teams: str = "N/A",
    cohort_mean_progress: Optional[float] = None,
    event_consensus: Dict[str, str] = None,
    event_comparison_metrics: Dict[str, Any] = None,
    classification_rank: str = "N/A",
    classification_sublabel: str = "Event F1: N/A | Planet F1: N/A",
    accuracy_rank: str = "N/A",
    precision_rank: str = "N/A",
    efficiency_rank: str = "N/A",
    cohort_avg: Dict[str, Any] = None,
    cohort_teams: Dict[str, Any] = None,
) -> str:
    """Generate the HTML content for the submission dashboard."""
    if event_comparison_metrics is None:
        event_comparison_metrics = {}
    if event_consensus is None:
        event_consensus = {}
    if precision_stats is None:
        precision_stats = {}
    if cohort_avg is None:
        cohort_avg = {}
    if cohort_teams is None:
        cohort_teams = {}

    is_experienced = str(submission.tier or "").lower() == "experienced"
    # Experienced reports have no trusted event-type labels, but their
    # physical/model comparison truth remains valid.
    show_truth_columns = (
        evaluator_mode
        and not is_experienced
        and evaluator_truth_available(submission.tier)
    )
    show_truth_comparison_columns = (
        evaluator_mode and evaluator_truth_available(submission.tier)
    )
    if is_experienced and evaluator_mode:
        classification_sublabel = "Submitted event distribution only"
    tier_submissions_url = get_tier_submissions_url(submission.tier)
    tier_submissions_link = (
        f"<a href='{tier_submissions_url}' class='text-rtd-accent hover:underline'>"
        f"{get_tier_submissions_label(submission.tier)}</a>"
        if tier_submissions_url
        else ""
    )

    # ── Compute precision stats from submission object (works in all modes) ──
    _conf_scores = []
    _n_sol_list = []
    _uncert_count = 0
    _posterior_count = 0
    _total_sol = 0
    _any_real_probs = precision_stats.get("any_real_probs", False)
    _per_param: Dict[str, list] = {}
    for _eid, _event in submission.events.items():
        _active = _event.get_active_solutions()
        if not _active:
            continue
        _probs_raw = [s.relative_probability for s in _active]
        _has_probs = all(p is not None for p in _probs_raw)
        _total_p = sum(p for p in _probs_raw if p is not None)
        if _has_probs and _total_p > 0:
            _probs = [p / _total_p for p in _probs_raw]
            _any_real_probs = True
        else:
            _probs = [1.0 / len(_active)] * len(_active)
        _conf_scores.append(max(_probs))
        _n_sol_list.append(len(_active))
        for _sol in _active:
            _total_sol += 1
            _unc = _sol.parameter_uncertainties or {}
            if _unc:
                _uncert_count += 1
            if _sol.posterior_path:
                _posterior_count += 1
    _sub_mean_conf = (
        sum(_conf_scores) / len(_conf_scores) * 100 if _conf_scores else None
    )
    _sub_deg_rate = (
        sum(1 for n in _n_sol_list if n > 1) / len(_n_sol_list) * 100
        if _n_sol_list else 0.0
    )
    _sub_mean_nsol = (
        sum(_n_sol_list) / len(_n_sol_list) if _n_sol_list else None
    )
    _sub_total_sol = sum(_n_sol_list)
    _sub_uncert_pct = (
        _uncert_count / _total_sol * 100 if _total_sol > 0 else 0.0
    )
    _sub_post_pct = (
        _posterior_count / _total_sol * 100 if _total_sol > 0 else 0.0
    )
    # Prefer script-computed values if available (more detailed)
    mean_confidence = precision_stats.get("mean_confidence", _sub_mean_conf)
    degeneracy_rate = precision_stats.get("degeneracy_rate", _sub_deg_rate)
    mean_n_solutions = precision_stats.get("mean_n_solutions", _sub_mean_nsol)
    total_solutions_prec = precision_stats.get("total_solutions", _sub_total_sol)
    uncertainty_coverage = precision_stats.get("uncertainty_coverage", _sub_uncert_pct)
    posterior_coverage = precision_stats.get("posterior_coverage", _sub_post_pct)
    median_frac_uncerts = precision_stats.get("median_frac_uncerts", {})
    most_common_method = precision_stats.get("most_common_method")
    most_common_cl = precision_stats.get("most_common_confidence_level")

    total_events = len(submission.events)
    total_active_solutions = sum(len(event.get_active_solutions()) for event in submission.events.values())
    total_cpu_hours = 0
    total_wall_time_hours = 0

    for event in submission.events.values():
        for solution in event.solutions.values():
            if solution.compute_info:
                total_cpu_hours += solution.compute_info.get("cpu_hours", 0)
                total_wall_time_hours += solution.compute_info.get("wall_time_hours", 0)

    hardware_info_str = format_hardware_info(submission.hardware_info)

    try:
        if submission.tier and submission.tier != "None":
            tier_events = get_tier_event_list(submission.tier)
            if tier_events:
                total_challenge_events = len(tier_events)
                progress_percentage = (total_events / total_challenge_events) * 100
                progress_display = f"{progress_percentage:.1f}%"
            else:
                total_challenge_events = "N/A"; progress_percentage = 0; progress_display = "N/A"
        else:
            total_challenge_events = "N/A"; progress_percentage = 0; progress_display = "N/A"
    except ValueError:
        total_challenge_events = "N/A"; progress_percentage = 0; progress_display = "N/A"

    event_rows = []
    dashboard_colspan = (
        3
        + (2 if show_truth_columns else 0)
        + (4 if show_truth_comparison_columns else 0)
    )
    for event in sorted(submission.events.values(), key=lambda e: e.event_id):
        active_solutions = event.get_active_solutions()
        model_types = sorted(set(sol.model_type for sol in active_solutions))
        model_types_str = ", ".join(model_types) if model_types else "None"

        comp = (
            event_comparison_metrics.get(event.event_id, {})
            if show_truth_comparison_columns
            else {}
        )
        truth_chi2 = comp.get("truth_chi2")
        pspl_dchi2 = comp.get("pspl_dchi2")
        flat_dchi2 = comp.get("flat_dchi2")
        truth_model = comp.get("truth_model", "N/A")
        consensus_model = event_consensus.get(event.event_id, "N/A") if show_truth_columns else "N/A"

        best_chi2_residual = None
        if active_solutions:
            best_sol = max(active_solutions, key=lambda s: s.relative_probability or 0.0)
            if best_sol.log_likelihood is not None and truth_chi2 is not None:
                team_chi2 = -2.0 * best_sol.log_likelihood
                best_chi2_residual = team_chi2 - truth_chi2

        truth_chi2_display = f"{truth_chi2:.1f}" if truth_chi2 is not None else "N/A"
        chi2_res_display = f"{best_chi2_residual:+.2f}" if best_chi2_residual is not None else "N/A"
        dchi2_p_display = f"{pspl_dchi2:.1f}" if pspl_dchi2 is not None else "N/A"
        dchi2_f_display = f"{flat_dchi2:.1f}" if flat_dchi2 is not None else "N/A"
        truth_row_cells = ""
        if show_truth_columns:
            truth_row_cells += f"""
                 <td class="py-3 px-4 text-xs font-bold text-center bg-gray-50/50">{truth_model}</td>
                 <td class="py-3 px-4 text-xs italic text-center">{consensus_model}</td>
            """
        if show_truth_comparison_columns:
            truth_row_cells += f"""
                 <td class="py-3 px-4 font-mono text-sm text-right">{truth_chi2_display}</td>
                 <td class="py-3 px-4 font-mono text-sm font-bold text-right {'text-green-600' if (best_chi2_residual or 0) < 0 else 'text-red-600'}">{chi2_res_display}</td>
                 <td class="py-3 px-4 font-mono text-sm text-right">{dchi2_p_display}</td>
                 <td class="py-3 px-4 font-mono text-sm text-right">{dchi2_f_display}</td>
            """
        event_rows.append(f"""
            <tr class="border-b border-gray-200 hover:bg-gray-50 cursor-pointer event-main-row"
                data-event-id="{event.event_id}"
                data-model-types="{model_types_str}"
                data-truth-chi2="{truth_chi2 if truth_chi2 is not None else 1e12}"
                data-best-chi2-res="{best_chi2_residual if best_chi2_residual is not None else 1e12}"
                data-pspl-dchi2="{pspl_dchi2 if pspl_dchi2 is not None else -1e12}"
                data-flat-dchi2="{flat_dchi2 if flat_dchi2 is not None else -1e12}"
                data-truth-model="{truth_model}"
                data-consensus-model="{consensus_model}">
                <td class="py-3 px-4 flex items-center gap-2">
                    <button class="toggle-btn focus:outline-none transition-transform duration-200">
                        <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                    </button>
                    <a href="{event.event_id}.html" class="font-bold text-rtd-accent hover:underline">{event.event_id}</a>
                 </td>
                 <td class="py-3 px-4 text-center">{len(active_solutions)}</td>
                 <td class="py-3 px-4 text-xs font-bold text-rtd-accent">{model_types_str}</td>
                 {truth_row_cells}

            </tr>
        """)

        sol_rows = []
        for sol in sorted(active_solutions, key=lambda s: s.relative_probability or 0.0, reverse=True):
            chi2_team = f"{-2.0 * sol.log_likelihood:.1f}" if sol.log_likelihood is not None else "N/A"
            chi2_res = "N/A"
            if truth_chi2 is not None and sol.log_likelihood is not None:
                dchi2 = (-2.0 * sol.log_likelihood) - truth_chi2
                color = "text-green-600" if dchi2 < 0 else "text-red-600"
                chi2_res = f"<span class='{color} font-bold'>{dchi2:+.2f}</span>"
            effects_str = ", ".join(sol.higher_order_effects) if sol.higher_order_effects else "None"

            sol_rows.append(f"""
                <tr class="border-b border-gray-100 last:border-0 hover:bg-gray-50/50">
                    <td class="py-2 px-4"><a href="{sol.solution_id}.html" class="text-sm font-mono text-rtd-accent hover:underline">{sol.alias or sol.solution_id[:8]}</a></td>
                    <td class="py-2 px-4 text-xs font-bold">{sol.model_type}</td>
                    <td class="py-2 px-4 text-xs">{chi2_team}</td>
                    <td class="py-2 px-4 text-xs">{chi2_res}</td>
                    <td class="py-2 px-4 text-xs italic text-gray-500">{effects_str}</td>
                    <td class="py-2 px-4 text-xs">{sol.compute_info.get('cpu_hours', 0.0):.2f} hr</td>
                    <td class="py-2 px-4 text-xs">{(sol.relative_probability or 1.0):.2f}</td>
                </tr>
            """)

        event_rows.append(f"""
            <tr class="hidden solution-sub-row bg-gray-50/50">
                <td colspan="{dashboard_colspan}" class="p-0">
                    <div class="px-8 py-4">
                        <table class="w-full text-left border-collapse bg-white rounded-lg shadow-inner border border-gray-200 overflow-hidden">
                            <thead class="bg-gray-50 text-gray-500 text-[10px] uppercase font-bold tracking-wider">
                                <tr>
                                    <th class="py-2 px-4">Solution ID / Alias</th>
                                    <th class="py-2 px-4">Model</th>
                                    <th class="py-2 px-4">Team -2 ln L</th>
                                    <th class="py-2 px-4">Δ -2 ln L</th>
                                    <th class="py-2 px-4">Effects</th>
                                    <th class="py-2 px-4">CPU</th>
                                    <th class="py-2 px-4">Prob</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join(sol_rows)}
                            </tbody>
                        </table>
                    </div>
                </td>
            </tr>
        """)
    event_table = "\n".join(event_rows) if event_rows else f"""<tr class=\"border-b border-gray-200\"><td colspan=\"{dashboard_colspan}\" class=\"py-3 px-4 text-center text-gray-500\">No events found</td></tr>"""

    github_html = ""
    repo_url = getattr(submission, "repo_url", None)
    if repo_url and not evaluator_mode:
        repo_name = extract_github_repo_name(repo_url)
        github_html = f"""<div class="flex items-center justify-center mb-4"><a href="{repo_url}" target="_blank" rel="noopener" class="flex items-center space-x-2 group"><img src="assets/github-desktop_logo.png" alt="GitHub" class="w-6 h-6 inline-block align-middle mr-2 group-hover:opacity-80" style="display:inline;vertical-align:middle;"><span class="text-base text-rtd-accent font-semibold group-hover:underline">{repo_name}</span></a></div>"""

    classification_section = ""
    if confusion_matrix_html or cohort_confusion_matrix_html or classification_metrics_table_html:
        classification_section = """<section class="mb-10 px-8">
            <h2 class="text-2xl font-semibold text-rtd-secondary mb-4 border-b border-gray-100 pb-2">Classification</h2>

            <!-- Score Explanation Callout -->
            <div class="bg-purple-50 border border-purple-200 rounded-xl p-5 mb-6 text-sm text-purple-950 shadow-sm">
                <h4 class="font-bold text-purple-900 mb-1">ℹ️ Classification Percentile Score Calculation</h4>
                <p class="mb-2">The Classification rank is calculated using the <strong>Classification Composite Score</strong>:</p>
                <div class="font-mono bg-white/70 px-4 py-2 rounded border border-purple-100 w-fit mb-3 font-semibold text-xs">
                    Classification Composite = 0.5 * Macro F1 + 0.5 * Planet F1
                </div>
                <ul class="list-disc list-inside space-y-1 text-purple-900/90 text-xs">
                    <li><strong>Macro F1</strong>: Probability-weighted harmonic mean of precision and recall across all four event model classes (1S1L, 1S2L, 2S1L, 2S2L).</li>
                    <li><strong>Planet F1</strong>: Harmonic mean of precision and recall focusing strictly on planetary events (where the mass ratio q &lt; 0.03).</li>
                    <li><strong>Event Detection Hardness / Recovery Rate</strong>: Measures how difficult a planetary event is to discover. Hardness is determined by the cohort-wide recovery rate (e.g., a planet recovered by only 10% of teams is extremely "hard" to find, whereas a 90% recovery rate is "easy"). The metrics report the hardest planetary event successfully detected and the easiest one missed.</li>
                </ul>
            </div>

            """ + classification_metrics_table_html + """

            <div class='flex flex-col xl:flex-row items-center justify-center gap-6 mt-6'>"""
        if confusion_matrix_html:
            classification_section += f"""<div class='flex flex-col items-center w-full xl:w-1/2'><h3 class="text-lg font-medium text-rtd-secondary mb-2">Team Submission</h3><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200 w-full flex justify-center overflow-x-auto'>{confusion_matrix_html}</div></div>"""
        if cohort_confusion_matrix_html:
            classification_section += f"""<div class='flex flex-col items-center w-full xl:w-1/2'><h3 class="text-lg font-medium text-rtd-secondary mb-2">Cohort Aggregate</h3><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200 w-full flex justify-center overflow-x-auto'>{cohort_confusion_matrix_html}</div></div>"""
        classification_section += """</div></section>"""
    else:
        classification_section = """<section class="mb-10 px-8">
            <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Classification</h2>
            <div class="bg-gray-50 p-6 rounded-lg border border-gray-200 text-gray-600">
                <p class="text-sm">Evaluates event model type classification across 1S1L, 1S2L, 2S1L, 2S2L categories.</p>
                <p class="text-sm mt-2 text-gray-500 italic">No classification confusion matrices are available yet for this submission. Confusion matrices are populated in cohort evaluator mode.</p>
            </div>
        </section>"""

    if is_experienced and evaluator_mode:
        classification_section = f"""<section class="mb-10 px-8">
            <h2 class="text-2xl font-semibold text-rtd-secondary mb-4 border-b border-gray-100 pb-2">Submitted Event Distribution</h2>
            <p class="text-sm text-gray-500 mb-6">Experienced-tier reports show submitted event models only. No hidden truth labels are used.</p>
            <div class='flex flex-col xl:flex-row items-center justify-center gap-6 mt-6'>
                {f"<div class='flex flex-col items-center w-full xl:w-1/2'><h3 class=\"text-lg font-medium text-rtd-secondary mb-2\">Team Submission</h3><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200 w-full flex justify-center overflow-x-auto'>{confusion_matrix_html}</div></div>" if confusion_matrix_html else ""}
                {f"<div class='flex flex-col items-center w-full xl:w-1/2'><h3 class=\"text-lg font-medium text-rtd-secondary mb-2\">Cohort Aggregate</h3><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200 w-full flex justify-center overflow-x-auto'>{cohort_confusion_matrix_html}</div></div>" if cohort_confusion_matrix_html else ""}
            </div>
        </section>"""

    cohort_marker_html = f"""<div class="absolute top-0 bottom-0 w-1 bg-indigo-600 shadow-[0_0_8px_rgba(79,70,229,0.5)] z-10" style="left: {cohort_mean_progress}%" title="Cohort Mean: {cohort_mean_progress:.1f}%"><div class="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-bold text-indigo-600 whitespace-nowrap bg-white px-1 rounded border border-indigo-200">Cohort Mean: {cohort_mean_progress:.1f}%</div></div>""" if cohort_mean_progress is not None else ""


    accuracy_section = ""
    has_accuracy_data = (
        q_scatter_html or te_scatter_html or rho_scatter_html or planet_metrics_table_html or modelling_metrics_table_html or parallax_hist_html or
        bl_s_scatter_html or bl_alpha_scatter_html or bs_s_scatter_html or bs_alpha_scatter_html or
        bs_flux_ratio_scatter_html or phys_mass_scatter_html or phys_dl_scatter_html
    )
    if has_accuracy_data:
        accuracy_section = """<section class="mb-10 px-8">
            <h2 class="text-2xl font-semibold text-rtd-secondary mb-6 border-b border-gray-100 pb-2">Accuracy</h2>

            <!-- Score Explanation Callout -->
            <div class="bg-purple-50 border border-purple-200 rounded-xl p-5 mb-6 text-sm text-purple-950 shadow-sm">
                <h4 class="font-bold text-purple-900 mb-1">ℹ️ Accuracy Percentile Score Calculation</h4>
            <p class="mb-2">The Accuracy rank evaluates the closeness of fit parameters to simulated truths. q, s, tE, and rho comparisons use log10 space; the displayed fractional differences are derived from absolute log10 residuals.</p>
                <div class="font-mono bg-white/70 px-4 py-2 rounded border border-purple-100 w-fit mb-3 font-semibold text-xs">
                    Accuracy Metric = (q_log10_error * tE_log10_error * mass_error * dl_error) ^ (1/4)
                </div>
                <p class="text-xs text-purple-900/90">A lower geometric mean indicates higher accuracy. The overall global rank is calculated by sorting cohort teams in ascending order (lowest errors receive the highest percentile rank).</p>
            <p class="text-xs text-purple-900/90 mt-2"><strong>Note on Planet Detection vs. Accuracy</strong>: Finding the presence of a planet (detection capability) and resolving its hardness is evaluated in the <em>Classification</em> score. The <em>Accuracy</em> score evaluates the closeness of the successfully fitted parameter values (including q and tE in log10 space) to their true simulated values.</p>
            </div>
            """

        # ── Subsection 1: Planet Parameters ──
        if planet_metrics_table_html or q_scatter_html or te_scatter_html or rho_scatter_html or u0_scatter_html or t0_scatter_html or parallax_hist_html:
            accuracy_section += f"""
            <div class="mb-8">
                <h3 class="text-xl font-medium text-rtd-secondary mb-3">Planet Detection &amp; Parameters</h3>
                {planet_metrics_table_html}
                <div class='flex flex-wrap items-center justify-center gap-6 mt-4'>"""
            if q_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{q_scatter_html}</div></div>"""
            if te_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{te_scatter_html}</div></div>"""
            if rho_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{rho_scatter_html}</div></div>"""
            if u0_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{u0_scatter_html}</div></div>"""
            if t0_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{t0_scatter_html}</div></div>"""
            if parallax_hist_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{parallax_hist_html}</div></div>"""
            accuracy_section += """
                </div>
            </div>"""

        # ── Subsection 2: Modelling Parameters (excluding 1S1L) ──
        has_modelling = bl_s_scatter_html or bl_alpha_scatter_html or bs_s_scatter_html or bs_alpha_scatter_html or bs_flux_ratio_scatter_html or modelling_metrics_table_html
        if has_modelling:
            accuracy_section += f"""
            <div class="mb-8 border-t border-gray-100 pt-6">
                <h3 class="text-xl font-medium text-rtd-secondary mb-2">Modelling Parameters</h3>
                <p class="text-xs text-gray-500 mb-4">Compares recovered trajectory and geometry parameters against simulated truths for binary lenses and binary sources (excluding simple 1S1L events).</p>
                {modelling_metrics_table_html}
                <div class='flex flex-wrap items-center justify-center gap-6'>"""
            if bl_s_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{bl_s_scatter_html}</div></div>"""
            if bl_alpha_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{bl_alpha_scatter_html}</div></div>"""
            if bs_s_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{bs_s_scatter_html}</div></div>"""
            if bs_alpha_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{bs_alpha_scatter_html}</div></div>"""
            if bs_flux_ratio_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{bs_flux_ratio_scatter_html}</div></div>"""
            accuracy_section += """
                </div>
            </div>"""

        # ── Subsection 3: Physical Parameters ──
        if True:
            # Count physical solutions in the current submission
            total_active_sols = 0
            sols_with_phys = 0
            for event in submission.events.values():
                for sol in event.solutions.values():
                    if sol.is_active:
                        total_active_sols += 1
                        phys = sol.physical_parameters or {}
                        if phys.get("planet_mass") is not None and phys.get("lens_distance") is not None:
                            sols_with_phys += 1

            phys_sol_pct = (sols_with_phys / total_active_sols * 100) if total_active_sols > 0 else 0.0

            # Load from cohort
            cohort_phys_sol_count_mean = cohort_avg.get("phys_sol_count")
            cohort_phys_sol_pct_mean = cohort_avg.get("phys_sol_pct")

            percentile_phys_sol_count = None
            if cohort_teams:
                all_counts = []
                for t in cohort_teams.values():
                    c = t.get("phys_sol_count")
                    if c is not None:
                        all_counts.append(c)
                if all_counts:
                    less_or_equal = sum(1 for c in all_counts if c <= sols_with_phys)
                    percentile_phys_sol_count = (less_or_equal / len(all_counts)) * 100

            _mean_count_str = f"{cohort_phys_sol_count_mean:.1f}" if cohort_phys_sol_count_mean is not None else "N/A"
            _mean_pct_str = f"{cohort_phys_sol_pct_mean:.1f}%" if cohort_phys_sol_pct_mean is not None else "N/A"
            _pct_rank_str = f"{percentile_phys_sol_count:.1f}%" if percentile_phys_sol_count is not None else "N/A"

            accuracy_section += f"""
            <div class="mb-8 border-t border-gray-100 pt-6">
                <h3 class="text-xl font-medium text-rtd-secondary mb-2">Physical Parameters</h3>
                <p class="text-xs text-gray-500 mb-4">Compares derived physical values (such as planetary companion mass and system distance) against simulating source/lens configurations.</p>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm text-center">
                        <p class="text-xs font-semibold text-rtd-secondary uppercase tracking-wide mb-1">Physical Solutions Submitted</p>
                        <p class="text-3xl font-bold text-rtd-accent mt-1">{sols_with_phys} <span class="text-lg text-gray-400">/ {total_active_sols}</span></p>
                        <p class="text-xs text-gray-400 mt-2">Cohort Mean: {_mean_count_str} | Cohort Percentile: {_pct_rank_str}</p>
                    </div>
                    <div class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm text-center">
                        <p class="text-xs font-semibold text-rtd-secondary uppercase tracking-wide mb-1">Physical Parameter Coverage</p>
                        <p class="text-3xl font-bold text-rtd-accent mt-1">{phys_sol_pct:.1f}%</p>
                        <p class="text-xs text-gray-400 mt-2">Cohort Mean: {_mean_pct_str} of active solutions</p>
                    </div>
                </div>

                <div class='flex flex-wrap items-center justify-center gap-6'>"""
            if phys_mass_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{phys_mass_scatter_html}</div></div>"""
            if phys_dl_scatter_html: accuracy_section += f"""<div class='flex flex-col items-center'><div class='bg-gray-50 p-4 rounded-lg shadow-inner border border-gray-200'>{phys_dl_scatter_html}</div></div>"""
            accuracy_section += """
                </div>
            </div>"""

        accuracy_section += """</section>"""
    else:
        accuracy_section = """<section class="mb-10 px-8">
            <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Accuracy</h2>
            <div class="bg-gray-50 p-6 rounded-lg border border-gray-200 text-gray-600">
                <p class="text-sm">Measures the closeness of fitted parameters (e.g., mass ratio $q$, Einstein time $t_E$, lens distance $d_L$, planet mass) to their true values.</p>
                <p class="text-sm mt-2 text-gray-500 italic">No scientific validation metrics are available yet for this submission. Accuracy metrics are populated in cohort evaluator mode.</p>
            </div>
        </section>"""

    # ── Precision stat cards ─────────────────────────────────────────────────
    _conf_display = f"{mean_confidence:.1f}%" if mean_confidence is not None else "N/A"
    _deg_display = f"{degeneracy_rate:.1f}%" if degeneracy_rate is not None else "N/A"
    _nsol_display = f"{mean_n_solutions:.2f}" if mean_n_solutions is not None else "N/A"
    _post_display = f"{posterior_coverage:.1f}%" if posterior_coverage is not None else "0.0%"
    _prob_note = (
        "Based on submitted relative probabilities"
        if _any_real_probs
        else "Based on equal-weight fallback (no probabilities submitted)"
    )

    _prec_stat_cards = f"""
        <div class='grid grid-cols-1 md:grid-cols-4 gap-4 mb-6'>
            <div class='bg-white border border-gray-200 rounded-xl p-5 shadow-sm text-center'>
                <p class='text-xs font-semibold text-rtd-secondary uppercase tracking-wide mb-1'>Mean Solution Confidence</p>
                <p class='text-3xl font-bold text-rtd-accent mt-1'>{_conf_display}</p>
                <p class='text-xs text-gray-400 mt-2'>{_prob_note}</p>
            </div>
            <div class='bg-white border border-gray-200 rounded-xl p-5 shadow-sm text-center'>
                <p class='text-xs font-semibold text-rtd-secondary uppercase tracking-wide mb-1'>Degeneracy Rate</p>
                <p class='text-3xl font-bold text-rtd-accent mt-1'>{_deg_display}</p>
                <p class='text-xs text-gray-400 mt-2'>Events with &gt;1 active solution</p>
            </div>
            <div class='bg-white border border-gray-200 rounded-xl p-5 shadow-sm text-center'>
                <p class='text-xs font-semibold text-rtd-secondary uppercase tracking-wide mb-1'>Mean Solutions / Event</p>
                <p class='text-3xl font-bold text-rtd-accent mt-1'>{_nsol_display}</p>
                <p class='text-xs text-gray-400 mt-2'>Total: {total_solutions_prec} active solutions</p>
            </div>
            <div class='bg-white border border-gray-200 rounded-xl p-5 shadow-sm text-center'>
                <p class='text-xs font-semibold text-rtd-secondary uppercase tracking-wide mb-1'>Posterior Coverage</p>
                <p class='text-3xl font-bold text-rtd-accent mt-1'>{_post_display}</p>
                <p class='text-xs text-gray-400 mt-2'>Solutions with posteriors attached</p>
            </div>
        </div>"""

    _conf_hist_block = (
        f"""<div class='mb-6'>
            <h3 class='text-xl font-medium text-rtd-secondary mb-2'>Confidence Distribution</h3>
            <p class='text-sm text-gray-500 mb-3'>
                Distribution of the highest-probability solution's weight across all submitted events.
                A peak near 1.0 indicates decisive single-solution fits; spread indicates degeneracy.
            </p>
            {confidence_hist_html}
        </div>"""
        if confidence_hist_html
        else ""
    )

    # ── Uncertainty subsection ────────────────────────────────────────────────
    _PARAM_LABELS = {
        "q": "Mass Ratio (q)",
        "tE": "Einstein Time (tE)",
        "s": "Binary Separation (s)",
        "alpha": "Trajectory Angle (α)",
        "u0": "Impact Parameter (u0)",
        "t0": "Peak Time (t0)",
        "piEN": "Parallax π_E,N",
        "piEE": "Parallax π_E,E",
    }
    if median_frac_uncerts:
        _method_note = ""
        if most_common_method:
            _method_note = f" &nbsp;·&nbsp; <span class='font-semibold'>Method:</span> {most_common_method}"
            if most_common_cl:
                _method_note += f" ({most_common_cl * 100:.0f}% CL)" if isinstance(most_common_cl, float) else f" ({most_common_cl} CL)"
        _uncert_rows = "".join(
            f"<tr class='border-b border-gray-200 hover:bg-gray-50'>"
            f"<td class='py-3 px-4 font-semibold'>{_PARAM_LABELS.get(p, p)}</td>"
            f"<td class='py-3 px-4 text-rtd-accent font-bold'>{v * 100:.2f}%</td>"
            f"<td class='py-3 px-4 text-gray-500'>{len(_per_param.get(p, [v])) if _per_param else '—'}</td>"
            f"</tr>"
            for p, v in median_frac_uncerts.items()
            if p in _PARAM_LABELS
        )
        _unc_plot_block = (
            f"""<div class='mb-6 mt-6'>
                <h4 class='text-lg font-medium text-rtd-secondary mb-2'>Fractional Uncertainty Distributions</h4>
                <p class='text-sm text-gray-500 mb-3'>
                    Distribution of log<sub>10</sub>( Fractional Uncertainty &sigma; / |x| ) across all submitted solutions.
                    A peak further to the left (e.g. -3 or -4) indicates extremely precise measurements (0.1% or 0.01%).
                </p>
                {uncertainties_hist_html}
            </div>"""
            if uncertainties_hist_html
            else ""
        )
        _uncert_block = f"""
        <div class='mb-4'>
            <h3 class='text-xl font-medium text-rtd-secondary mb-2'>Parameter Uncertainties</h3>
            <p class='text-sm text-gray-500 mb-1'>
                <span class='font-semibold'>Coverage:</span> {uncertainty_coverage:.1f}% of solutions have uncertainties submitted{_method_note}
            </p>
            <table class='w-full text-left table-auto border-collapse mt-4 mb-4'>
                <thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'>
                    <tr>
                        <th class='py-3 px-4'>Parameter</th>
                        <th class='py-3 px-4'>Median Fractional Uncertainty</th>
                        <th class='py-3 px-4'>Solutions with Data</th>
                    </tr>
                </thead>
                <tbody class='text-rtd-text'>{_uncert_rows}</tbody>
            </table>
            {_unc_plot_block}
        </div>"""
    else:
        _uncert_block = """
        <div class='mb-4'>
            <h3 class='text-xl font-medium text-rtd-secondary mb-2'>Parameter Uncertainties</h3>
            <div class='bg-blue-50 border border-blue-200 rounded-lg p-4 text-blue-800 text-sm'>
                <p class='font-semibold mb-1'>&#8505;&nbsp; No parameter uncertainties were submitted.</p>
                <p>Adding <code>parameter_uncertainties</code> to solutions allows the dossier to
                compute and display fractional uncertainties (e.g. &sigma;<sub>q</sub>/q, &sigma;<sub>t<sub>E</sub></sub>/t<sub>E</sub>).
                See the <a href='https://microlens-submit.readthedocs.io' target='_blank' class='underline text-blue-700'>submission manual</a>
                for instructions.</p>
            </div>
        </div>"""

    precision_section = f"""<section class="mb-10 px-8">
        <h2 class="text-2xl font-semibold text-rtd-secondary mb-4 border-b border-gray-100 pb-2">Precision</h2>
        <p class="text-sm text-gray-500 mb-6">Precision metrics measure a team's ability to constrain
        parameters and resolve degeneracies — evaluated via solution confidence, degeneracy rates, and
        parameter uncertainty sizes.</p>

        <!-- Score Explanation Callout -->
        <div class="bg-purple-50 border border-purple-200 rounded-xl p-5 mb-6 text-sm text-purple-950 shadow-sm">
            <h4 class="font-bold text-purple-900 mb-1">ℹ️ Precision Percentile Score Calculation</h4>
            <p class="mb-2">The Precision global rank is calculated based on the <strong>Precision Composite Score</strong>:</p>
            <div class="font-mono bg-white/70 px-4 py-2 rounded border border-purple-100 w-fit mb-3 font-semibold text-xs">
                Precision Composite = 0.5 * (Mean Confidence / 100) + 0.25 * (Uncertainty Coverage / 100) + 0.25 * (Posterior Coverage / 100)
            </div>
            <ul class="list-disc list-inside space-y-1 text-purple-900/90 text-xs">
                <li><strong>Mean Confidence</strong>: The average probability weight assigned to the team's primary (highest-probability) solutions across all events.</li>
                <li><strong>Uncertainty Coverage</strong>: The percentage of submitted solutions that successfully report detailed parameter uncertainties.</li>
                <li><strong>Posterior Coverage</strong>: The percentage of submitted solutions that successfully include posterior probability density files.</li>
            </ul>
        </div>

        <h3 class="text-xl font-medium text-rtd-secondary mb-3">Solution Confidence &amp; Degeneracy</h3>
        {_prec_stat_cards}
        {_conf_hist_block}
        {_uncert_block}
    </section>"""

    efficiency_section = f"""<section class="mb-10 px-8">
        <h2 class="text-2xl font-semibold text-rtd-secondary mb-4 border-b border-gray-100 pb-2">Efficiency</h2>

        <!-- Score Explanation Callout -->
        <div class="bg-purple-50 border border-purple-200 rounded-xl p-5 mb-6 text-sm text-purple-950 shadow-sm">
            <h4 class="font-bold text-purple-900 mb-1">ℹ️ Efficiency Percentile Score Calculation</h4>
            <p class="mb-2">The Efficiency rank represents the processing speed of planetary discoveries. It is calculated by dividing the planetary companion true positive rate by the total CPU time spent modeling:</p>
            <div class="font-mono bg-white/70 px-4 py-2 rounded border border-purple-100 w-fit mb-3 font-semibold text-xs">
                Efficiency = Planet True Positives / Total CPU Hours
            </div>
            <p class="text-xs text-purple-900/90">Teams in the cohort are ranked descendingly; those who discover the most planetary companion candidates per unit of computing power receive the highest global percentile rank.</p>
        </div>

        {efficiency_metrics_table_html}

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 bg-gray-50 p-6 rounded-lg border border-gray-100 mt-4">
            <div>
                <h3 class="text-sm font-bold text-rtd-secondary uppercase mb-2">Compute Stats</h3>
                <p><strong>Total CPU Hours:</strong> {total_cpu_hours:.2f}</p>
                <p class="text-sm text-gray-500 mt-1">Measures the total processing time used to fit and model all solutions across submitted events.</p>
            </div>
            <div>
                <h3 class="text-sm font-bold text-rtd-secondary uppercase mb-2">Hardware</h3>
                <p>{hardware_info_str}</p>
            </div>
        </div>
    </section>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Submission Dossier - {submission.team_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
      tailwind.config = {{ theme: {{ extend: {{ colors: {{ 'rtd-primary': '#dfc5fa', 'rtd-secondary': '#361d49', 'rtd-accent': '#a859e4', 'rtd-background': '#faf7fd', 'rtd-text': '#000' }}, fontFamily: {{ inter: ['Inter', 'sans-serif'] }} }} }} }};
    </script>
    <script src="https://cdn.bokeh.org/bokeh/release/bokeh-3.8.0.min.js"></script>
    <style> .toggle-btn.active {{ transform: rotate(90deg); }} </style>
</head>
<body class="font-inter bg-rtd-background">
    <div class="max-w-full mx-auto p-6">
        <div class="bg-white shadow-xl rounded-lg">
            <div class="text-center py-8">
                <img src="./assets/rges-pit_logo.png" class="w-48 mx-auto mb-6">
                <h1 class="text-4xl font-bold text-rtd-secondary mb-2">Microlensing Data Challenge Submission Dossier</h1>
                <p class="text-xl text-rtd-accent mb-8">Team: {submission.team_name} | Tier: {submission.tier}</p>
                {github_html}
                {tier_submissions_link}
            </div>
            <hr class="border-t-4 border-rtd-accent my-8 mx-8">
            <section class="mb-10 px-8">
                <!-- Regex Start -->
                <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Submission Overview</h2>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center">
                        <p class="text-sm font-medium text-rtd-secondary uppercase tracking-wide">Classification</p>
                        <p class="text-4xl font-bold text-rtd-accent mt-2">{classification_rank}</p>
                        <p class="text-xs text-rtd-secondary/60 mt-2">{classification_sublabel}</p>
                    </div>
                    <div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center">
                        <p class="text-sm font-medium text-rtd-secondary uppercase tracking-wide">Accuracy</p>
                        <p class="text-4xl font-bold text-rtd-accent mt-2">{accuracy_rank}</p>
                        <p class="text-xs text-rtd-secondary/60 mt-2">Global rank</p>
                    </div>
                    <div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center">
                        <p class="text-sm font-medium text-rtd-secondary uppercase tracking-wide">Precision</p>
                        <p class="text-4xl font-bold text-rtd-accent mt-2">{precision_rank}</p>
                        <p class="text-xs text-rtd-secondary/60 mt-2">Global rank</p>
                    </div>
                    <div class="bg-rtd-primary p-6 rounded-lg shadow-md text-center">
                        <p class="text-sm font-medium text-rtd-secondary uppercase tracking-wide">Efficiency</p>
                        <p class="text-4xl font-bold text-rtd-accent mt-2">{efficiency_rank}</p>
                        <p class="text-xs text-rtd-secondary/60 mt-2">Global rank</p>
                    </div>
                </div>
            </section>
            <section class="mb-10 px-8">
                <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Progress</h2>
                <div class="relative w-full bg-gray-200 rounded-full h-4 mb-4 mt-8">{cohort_marker_html}<div class="bg-rtd-accent h-4 rounded-full" style="width: {progress_percentage}%"></div></div>
                <p class="text-sm text-center mb-6">{total_events} / {total_challenge_events} Events ({progress_display})</p>
            </section>
            {classification_section}
            {accuracy_section}
            {precision_section}
            {efficiency_section}
            <section class="mb-10 px-8">
                <h2 class="text-2xl font-semibold text-rtd-secondary mb-4">Submitted Events</h2>
                <div class="mb-4 flex flex-col md:flex-row gap-4 items-center justify-between"><input type="text" id="eventSearch" placeholder="Search..." class="w-full md:w-96 px-4 py-2 border rounded-lg"><p class="text-sm text-gray-500 font-mono" id="tableStats"></p></div>
                <div class="overflow-x-auto rounded-lg border border-gray-200 shadow-lg">
                    <table class="w-full text-left table-auto border-collapse bg-white" id="eventTable">
                        <thead class="bg-rtd-primary text-rtd-secondary uppercase text-[10px] font-bold">
                            <tr>
                                <th class="py-4 px-4 cursor-pointer" data-sort="event">Event ID ↕</th>
                                <th class="py-4 px-4 cursor-pointer text-center" data-sort="num">Sols ↕</th>
                                <th class="py-4 px-4" data-sort="types">Team Models ↕</th>
                                {'''<th class="py-4 px-4 cursor-pointer text-center bg-rtd-secondary/10" data-sort="truth-model">Truth ↕</th>
                                 <th class="py-4 px-4 cursor-pointer text-center bg-rtd-secondary/5" data-sort="consensus">Consensus ↕</th>''' if show_truth_columns else ''}
                                {'''<th class="py-4 px-4 cursor-pointer text-right" data-sort="truth-chi2">Truth -2 ln L ↕</th>
                                 <th class="py-4 px-4 cursor-pointer text-right" data-sort="chi2-res">Best Δ -2 ln L ↕</th>
                                 <th class="py-4 px-4 cursor-pointer text-right" data-sort="dchi2-p">Δχ²_PSPL ↕</th>
                                 <th class="py-4 px-4 cursor-pointer text-right" data-sort="dchi2-f">Δχ²_Flat ↕</th>''' if show_truth_comparison_columns else ''}

                            </tr>
                        </thead>
                        <tbody>{event_table}</tbody>
                    </table>
                </div>
            </section>
            <!-- Regex Finish -->
            <div class="text-sm text-gray-500 text-center pt-8 pb-6">Generated by microlens-submit v{__version__} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
        </div>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const searchInput = document.getElementById('eventSearch');
            const table = document.getElementById('eventTable');
            const tbody = table.querySelector('tbody');
            const stats = document.getElementById('tableStats');
            const rowPairs = Array.from(tbody.querySelectorAll('.event-main-row')).map(m => ({{ main: m, sub: m.nextElementSibling }}));
            rowPairs.forEach(p => p.main.addEventListener('click', e => {{ if (!e.target.closest('a')) {{ const b = p.main.querySelector('.toggle-btn'); const h = p.sub.classList.toggle('hidden'); b.classList.toggle('active', !h); }} }}));
            searchInput.addEventListener('input', () => {{
                const q = searchInput.value.toLowerCase();
                let v = 0;
                rowPairs.forEach(p => {{
                    const t = (p.main.dataset.eventId + ' ' + p.main.dataset.modelTypes).toLowerCase();
                    if (t.includes(q)) {{ p.main.style.display = ''; v++; }} else {{ p.main.style.display = 'none'; p.sub.classList.add('hidden'); }}
                }});
                stats.textContent = 'Showing ' + v + ' / ' + rowPairs.length + ' events';
            }});
            const headers = table.querySelectorAll('th[data-sort]');
            let sortState = {{ col: null, dir: 1 }};
            headers.forEach(h => h.addEventListener('click', () => {{
                const c = h.dataset.sort;
                sortState.dir = (sortState.col === c) ? -sortState.dir : 1;
                sortState.col = c;
                rowPairs.sort((a, b) => {{
                    let vA, vB;
                    if (c === 'event') {{ vA = a.main.dataset.eventId; vB = b.main.dataset.eventId; }}
                    else if (c === 'num') {{ vA = parseInt(a.main.cells[1].textContent); vB = parseInt(b.main.cells[1].textContent); }}
                    else if (c === 'types') {{ vA = a.main.dataset.modelTypes; vB = b.main.dataset.modelTypes; }}
                    else if (c === 'truth-model') {{ vA = a.main.dataset.truthModel; vB = b.main.dataset.truthModel; }}
                    else if (c === 'consensus') {{ vA = a.main.dataset.consensusModel; vB = b.main.dataset.consensusModel; }}
                    else if (c === 'truth-chi2') {{ vA = parseFloat(a.main.dataset.truthChi2); vB = parseFloat(b.main.dataset.truthChi2); }}
                    else if (c === 'chi2-res') {{ vA = parseFloat(a.main.dataset.bestChi2Res); vB = parseFloat(b.main.dataset.bestChi2Res); }}
                    else if (c === 'dchi2-p') {{ vA = parseFloat(a.main.dataset.psplDchi2); vB = parseFloat(b.main.dataset.psplDchi2); }}
                    else {{ vA = parseFloat(a.main.dataset.flatDchi2); vB = parseFloat(b.main.dataset.flatDchi2); }}
                    return vA < vB ? -sortState.dir : (vA > vB ? sortState.dir : 0);
                }});
                rowPairs.forEach(p => {{ tbody.appendChild(p.main); tbody.appendChild(p.sub); }});
            }}));
            searchInput.dispatchEvent(new Event('input'));
        }});
    </script>
</body>
</html>"""
    return html
