import os
import json
import math
import pandas as pd
import numpy as np
import argparse
from collections import Counter
from pathlib import Path
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, FactorRange, HoverTool, LinearColorMapper, CheckboxGroup, CustomJS
from bokeh.embed import components
from bokeh.transform import transform
from bokeh.layouts import row as bokeh_row, column

from microlens_submit.dossier.evaluation_data import (
    build_truth_parameters,
    default_evaluation_data_dir,
    find_lightcurve_file,
    evaluator_truth_available,
    is_lens_model,
    is_planet_model,
    is_source_model,
    load_truth_mapping,
    load_truth_records,
    log10_error_to_fractional_difference,
    match_truth_lens_component,
    model_types_for_tier,
    parameter_comparison_error,
    resolve_evaluation_data,
)

# Scientific color palette (Paul Tol's "Bright" Palette in optimized order)
MY_PALETTE = ['#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE', '#AA3377', '#BBBBBB']

def calculate_dchi2(file_path):
    """Calculate Delta Chi2 from original lightcurve file."""
    try:
        df = pd.read_csv(file_path, sep=r"\s+", comment="#")
        flux = df["measured_relative_flux"].values
        err = df["measured_relative_flux_error"].values
        pspl = df["best_single_lens_fit"].values
        true_f = df["true_relative_flux"].values
        chi2_1l = np.sum(((flux - pspl) / err) ** 2)
        chi2_2l = np.sum(((flux - true_f) / err) ** 2)
        return chi2_1l - chi2_2l
    except Exception:
        return None

def find_lc_file(lc_dir, event_id, subrun):
    """Find the original lightcurve file for a given event and subrun."""
    pattern = f"*_{subrun}_*_{event_id}.det.lc"
    matches = list(lc_dir.glob(pattern))
    if not matches:
        pattern = f"*_{subrun}_*_{event_id}.all.lc"
        matches = list(lc_dir.glob(pattern))
    return matches[0] if matches else None


def _lightcurve_y_range(event_df, value_column):
    """Return an inverted range for magnitudes and an ascending range for flux."""
    upper = event_df["upper"]
    lower = event_df["lower"]
    if value_column == "mag":
        return upper.max() + 0.1, lower.min() - 0.1
    return lower.min() - 0.1, upper.max() + 0.1


def generate_lightcurve_plots(project_path, data_path, shared_output_dir, force=False, event_ids=None):
    """Generate interactive Bokeh lightcurves for all events in the project."""
    print(f"Loading data from {data_path}...")
    events_dir = project_path / "events"
    if not events_dir.exists(): return
    available_event_ids = [d.name for d in events_dir.iterdir() if d.is_dir()]
    event_ids = available_event_ids if event_ids is None else event_ids

    shared_output_dir.mkdir(parents=True, exist_ok=True)
    event_ids_to_render = [
        event_id
        for event_id in event_ids
        if event_id in available_event_ids
        if force or not (shared_output_dir / f"{event_id}_lc.html").exists()
    ]
    if not event_ids_to_render:
        return

    # Read only the selected events and the columns used by the plot.  This is
    # essential for the experienced parquet, which contains over 100 million
    # rows and is shared by every team in the cohort.
    try:
        df = pd.read_parquet(
            data_path,
            columns=["name", "bjd", "filt", "mag", "mag_err"],
            filters=[("name", "in", event_ids_to_render)],
        )
    except Exception:
        df = pd.read_parquet(
            data_path,
            columns=["name", "bjd", "filt", "flux_uJy", "flux_err_uJy"],
            filters=[("name", "in", event_ids_to_render)],
        )

    for event_id in event_ids_to_render:
        out_file = shared_output_dir / f"{event_id}_lc.html"
        #if out_file.exists():
            #continue

        print(f"Generating interactive lightcurve for {event_id}...")
        event_df = df[df['name'] == event_id].copy()
        event_df['bjd_offset'] = event_df['bjd'] - 2460000.0
        if event_df.empty: continue

        event_df = event_df.sort_values('bjd')
        if {'mag', 'mag_err'}.issubset(event_df.columns):
            value_column = 'mag'
            error_column = 'mag_err'
            value_label = 'Magnitude'
        elif {'flux_uJy', 'flux_err_uJy'}.issubset(event_df.columns):
            value_column = 'flux_uJy'
            error_column = 'flux_err_uJy'
            value_label = 'Flux (uJy)'
        else:
            print(f"Skipping {event_id}: no supported magnitude or flux columns")
            continue

        event_df['upper'] = event_df[value_column] + event_df[error_column]
        event_df['lower'] = event_df[value_column] - event_df[error_column]

        y_range = _lightcurve_y_range(event_df, value_column)

        p = figure(title=f"Lightcurve: {event_id}",
                   x_axis_label='BJD - 2460000', y_axis_label=value_label,
                   height=450, width=850,
                   y_range=y_range,
                   tools="pan,box_zoom,wheel_zoom,reset,save",
                   active_scroll="wheel_zoom",
                   output_backend="webgl")

        filters = sorted(event_df['filt'].unique())
        if not filters:
            continue

        for i, filt in enumerate(filters):
            filt_df = event_df[event_df['filt'] == filt]
            source = ColumnDataSource(filt_df)
            color = MY_PALETTE[i % len(MY_PALETTE)]

            # Check if this is the default filter
            is_default = (filt == "F146")

            # Pass visible=is_default to both glyphs
            p.segment(x0='bjd_offset', y0='lower', x1='bjd_offset', y1='upper',
                      source=source, line_color=color, line_alpha=0.3,
                      legend_label=filt, visible=is_default)

            p.scatter('bjd_offset', value_column, source=source, size=4,
                      color=color, alpha=0.6,
                      legend_label=filt, visible=is_default)

        # This makes the legend act as your checkboxes
        p.legend.click_policy = "hide"

        # Add hover tool
        p.add_tools(HoverTool(tooltips=[
            ("BJD", "@bjd{0.0000}"),
            (value_label, f"@{value_column}{{0.000}}"),
            ("Error", f"@{error_column}{{0.000}}"),
            ("Filter", "@filt"),
        ]))

        # Since we ditched the widgets, just pass the plot 'p' directly to components
        script, div = components(p)
        with open(out_file, "w") as f:
            f.write(f"{script}\n{div}")

def get_team_predictions(events_dir, true_params=None):
    preds = {}
    if not events_dir.exists(): return preds
    for event_dir in events_dir.iterdir():
        if not event_dir.is_dir(): continue
        event_id = event_dir.name
        sols = []
        for sol_file in (event_dir / "solutions").glob("*.json"):
            with open(sol_file, "r") as f:
                sol = json.load(f)
                if sol.get("is_active", True):
                    sols.append(sol)
        if not sols: continue

        total_prob = sum(s.get("relative_probability") or 0.0 for s in sols)
        has_probs = all(s.get("relative_probability") is not None for s in sols)

        parsed_sols = []
        for s in sols:
            if has_probs and total_prob > 0:
                rp = s["relative_probability"] / total_prob
            else:
                rp = 1.0 / len(sols)

            model_type = s["model_type"]
            params = s.get("parameters", {})
            q = params.get("q")
            te = params.get("tE")
            rho = params.get("rho")
            t0 = params.get("t0")
            u0 = params.get("u0")
            s_model = params.get("s")
            alpha = params.get("alpha")
            t0_source2 = params.get("t0_source2")
            u0_source2 = params.get("u0_source2")
            flux_ratio = params.get("flux_ratio")
            piEN = params.get("piEN")
            piEE = params.get("piEE")

            # --- Source Matching & Swap Check ---
            if true_params and event_id in true_params and is_source_model(model_type):
                t_p = true_params[event_id]
                t0_truth_1 = t_p.get("t0")
                u0_truth_1 = t_p.get("u0")
                t0_truth_2 = t_p.get("t0_source2")
                u0_truth_2 = t_p.get("u0_source2")
                te_truth = t_p.get("te")

                q_truth = t_p.get("Obs_0_fs2ofs1")
                fs_total_truth = t_p.get("Obs_0_fs")
                if fs_total_truth is None or pd.isna(fs_total_truth):
                    fs_total_truth = 1.0

                if q_truth is not None and pd.notna(q_truth) and te_truth is not None and pd.notna(te_truth):
                    fs_truth_1 = fs_total_truth / (1.0 + q_truth)
                    fs_truth_2 = fs_total_truth * q_truth / (1.0 + q_truth)

                    all_params = s.get("parameters") or {}
                    fs_model_1 = all_params.get("F0_S1")
                    fs_model_2 = all_params.get("F0_S2")
                    if fs_model_1 is None or fs_model_2 is None:
                        fs_model_1 = 1.0
                        fs_model_2 = flux_ratio if flux_ratio is not None else 0.0
                    else:
                        fs_model_1 = float(fs_model_1)
                        fs_model_2 = float(fs_model_2)

                    denom_1 = fs_truth_1 if fs_truth_1 > 0 else 1.0
                    denom_2 = fs_truth_2 if fs_truth_2 > 0 else 1.0

                    dist_unswapped = 0.0
                    if t0 is not None and t0_truth_1 is not None:
                        dist_unswapped += ((t0 - t0_truth_1) / te_truth) ** 2
                    if t0_source2 is not None and t0_truth_2 is not None:
                        dist_unswapped += ((t0_source2 - t0_truth_2) / te_truth) ** 2
                    dist_unswapped += ((fs_model_1 - fs_truth_1) / denom_1) ** 2
                    dist_unswapped += ((fs_model_2 - fs_truth_2) / denom_2) ** 2

                    dist_swapped = 0.0
                    if t0 is not None and t0_truth_2 is not None:
                        dist_swapped += ((t0 - t0_truth_2) / te_truth) ** 2
                    if t0_source2 is not None and t0_truth_1 is not None:
                        dist_swapped += ((t0_source2 - t0_truth_1) / te_truth) ** 2
                    dist_swapped += ((fs_model_1 - fs_truth_2) / denom_2) ** 2
                    dist_swapped += ((fs_model_2 - fs_truth_1) / denom_1) ** 2

                    if dist_swapped < dist_unswapped:
                        t0, t0_source2 = t0_source2, t0
                        u0, u0_source2 = u0_source2, u0
                        if flux_ratio is not None and flux_ratio > 0:
                            flux_ratio = 1.0 / flux_ratio

            phys = s.get("physical_parameters") or {}
            mass = phys.get("planet_mass")
            dl = phys.get("lens_distance")
            piE_N = phys.get("piE_N")
            piE_E = phys.get("piE_E")
            cpu = s.get("compute_info", {}).get("cpu_hours", 0)

            all_params = {**(s.get("parameters") or {}), **(s.get("physical_parameters") or {})}
            all_uncerts = {**(s.get("parameter_uncertainties") or {}), **(s.get("physical_parameter_uncertainties") or {})}
            uncertainty_method = s.get("uncertainty_method") or None
            confidence_level = s.get("confidence_level") or None
            posterior_path = s.get("posterior_path") or None

            is_planet = is_planet_model(model_type, q)

            parsed_sols.append({
                "model_type": model_type,
                "prob": rp,
                "has_equal_weight": not (has_probs and total_prob > 0),
                "is_planet": is_planet,
                "q": q,
                "te": te,
                "rho": rho,
                "t0": t0,
                "u0": u0,
                "s": s_model,
                "alpha": alpha,
                "t0_source2": t0_source2,
                "u0_source2": u0_source2,
                "flux_ratio": flux_ratio,
                "piEN": piEN,
                "piEE": piEE,
                "mass": mass,
                "dl": dl,
                "piE_N": piE_N,
                "piE_E": piE_E,
                "cpu": cpu,
                "param_uncerts": all_uncerts,
                "uncertainty_method": uncertainty_method,
                "confidence_level": confidence_level,
                "posterior_path": posterior_path,
                "params": all_params,
            })
        preds[event_id] = parsed_sols
    return preds

def _submitted_event_model_counts(preds):
    """Count one primary submitted model per event, without truth labels."""
    counts = Counter()
    for solutions in preds.values():
        if solutions:
            primary = max(solutions, key=lambda solution: solution["prob"])
            counts[primary["model_type"]] += 1
    return counts


def _write_submitted_event_histogram(counts, output_path, title):
    """Write a bar chart showing the submitted primary model per event."""
    labels = sorted(counts) or ["No submitted events"]
    values = [counts[label] for label in labels] if counts else [0]
    source = ColumnDataSource({"model": labels, "count": values})
    plot = figure(
        title=title,
        x_range=labels,
        x_axis_label="Submitted primary model",
        y_axis_label="Submitted events",
        height=450,
        width=700,
        tools="pan,wheel_zoom,reset,save,hover",
    )
    plot.vbar(x="model", top="count", width=0.7, source=source, color=MY_PALETTE[0])
    plot.hover.tooltips = [("Model", "@model"), ("Events", "@count")]
    plot.xaxis.major_label_orientation = math.pi / 4
    script, div = components(plot)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as handle:
        handle.write(f"{script}\n{div}")


def generate_confusion_matrix(project_path, data_dir, local_assets_dir, tier="beginner"):
    """Generate a confusion matrix and save it to the SUBMISSION assets folder."""
    print("Generating submission confusion matrix...")
    if str(tier).lower() == "experienced":
        preds = get_team_predictions(project_path / "events")
        counts = _submitted_event_model_counts(preds)
        _write_submitted_event_histogram(
            counts,
            local_assets_dir / "confusion_matrix.html",
            "Submitted Event Model Distribution",
        )
        return

    try:
        evaluation_data = resolve_evaluation_data(data_dir, tier)
        records = load_truth_records(evaluation_data)
        truth_map = load_truth_mapping(evaluation_data, records)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Truth data unavailable. Skipping confusion matrix: {exc}")
        return
    if not truth_map:
        print("No truth classifications found. Skipping confusion matrix.")
        return

    # 2. Get Submission Data
    events_dir = project_path / "events"
    preds = get_team_predictions(events_dir)

    # 3. Create Matrix Data
    submitted_model_types = {
        solution["model_type"]
        for solutions in preds.values()
        for solution in solutions
    }
    truth_types = model_types_for_tier(tier, truth_map.values())
    submitted_types = model_types_for_tier(tier, submitted_model_types) + ["No Submission"]

    data = []
    for t in truth_types:
        for s in submitted_types:
            count = 0.0
            for event_id, t_type in truth_map.items():
                if t_type == t:
                    if event_id in preds:
                        count += sum(sol["prob"] for sol in preds[event_id] if sol["model_type"] == s)
                    else:
                        if s == "No Submission": count += 1.0
            data.append({"truth": t, "submitted": s, "count": count})

    df_matrix = pd.DataFrame(data)

    # Calculate column percentages
    df_matrix['col_total'] = df_matrix.groupby('truth')['count'].transform('sum')
    df_matrix['perc'] = (df_matrix['count'] / df_matrix['col_total'].replace(0, 1)) * 100
    df_matrix['text'] = df_matrix.apply(lambda r: f"{r['count']:.1f}\n({r['perc']:.1f}%)" if r['col_total'] > 0 else "0", axis=1)

    source = ColumnDataSource(df_matrix)

    # 4. Plot Heatmap (Using Blues256 reversed for light to dark)
    from bokeh.palettes import Blues256
    mapper = LinearColorMapper(palette=Blues256[::-1], low=0, high=100)

    p = figure(title="Model Type Confusion Matrix",
               x_range=truth_types, y_range=submitted_types[::-1],
               x_axis_label="Ground Truth",
               y_axis_label="Submitted Model",
               height=450, width=600, toolbar_location=None, tools="")

    p.rect(x="truth", y="submitted", width=1, height=1, source=source,
           line_color="white", fill_color=transform('perc', mapper))

    p.text(x="truth", y="submitted", text="text", source=source,
           text_align="center", text_baseline="middle",
           text_color="black", text_font_style="bold")

    p.add_tools(HoverTool(tooltips=[("Truth", "@truth"), ("Submitted", "@submitted"), ("Count", "@count"), ("Percentage", "@perc{0.1f}%")]))

    script, div = components(p)
    local_assets_dir.mkdir(parents=True, exist_ok=True)
    with open(local_assets_dir / "confusion_matrix.html", "w") as f:
        f.write(f"{script}\n{div}")


def generate_planet_metrics(
    project_path,
    data_dir,
    local_assets_dir,
    tier="beginner",
    cohort_analysis_dir=None,
):
    """Generate planet parameter scatter plots and efficiency metrics."""
    print("Generating planet detection metrics...")
    if not evaluator_truth_available(tier):
        print("Trusted truth data is unavailable for this tier. Skipping planet metrics.")
        return
    try:
        evaluation_data = resolve_evaluation_data(data_dir, tier)
        truth_records = load_truth_records(evaluation_data)
        truth_map = load_truth_mapping(evaluation_data, truth_records)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Truth data unavailable. Skipping planet metrics: {exc}")
        return
    if not truth_map:
        return
    cohort_metrics_path = (
        Path(cohort_analysis_dir) if cohort_analysis_dir is not None
        else data_dir.parent / "cohort_analysis"
    ) / "cohort_metrics.json"

    def get_best_transform_idx(pairs):
        """Find the single trajectory transformation option that minimizes the total aggregate angular difference across all events."""
        if not pairs:
            return 0, "Standard"
        options = [
            ("Standard", lambda t: t),
            ("Direction Flipped (α + 180°)", lambda t: (t + 180.0) % 360.0),
            ("Reflected (u0 sign flip)", lambda t: (360.0 - t) % 360.0),
            ("Reflected & Flipped", lambda t: (180.0 - t) % 360.0)
        ]
        best_idx = 0
        best_label = "Standard"
        min_total_err = float("inf")
        for idx, (label, func) in enumerate(options):
            total_err = 0.0
            for m, t in pairs:
                transformed_t = func(t)
                diff = abs(m - transformed_t)
                diff = min(diff, 360.0 - diff)
                total_err += diff
            if total_err < min_total_err:
                min_total_err = total_err
                best_idx = idx
                best_label = label
        return best_idx, best_label

    true_planets = set()
    true_params = {}
    for _, row in truth_records.iterrows():
        eid = row["anon_id"]
        t_type = truth_map.get(eid)
        t_p = build_truth_parameters(row)
        if bool(row.get("is_planet")) or is_planet_model(t_type, t_p.get("q")):
            true_planets.add(eid)
        true_params[eid] = t_p

    events_dir = project_path / "events"
    preds = get_team_predictions(events_dir, true_params=true_params)

    # ── Pass 1: Determine the single best global coordinate transformation across all events ──
    bl_alpha_pairs = []
    bs_alpha_pairs = []
    for eid, sols in preds.items():
        t_p = true_params.get(eid)
        t_type = truth_map.get(eid)
        if t_p:
            for s in sols:
                if is_lens_model(t_type) and is_lens_model(s["model_type"]):
                    if s["alpha"] is not None and pd.notna(t_p["alpha"]):
                        bl_alpha_pairs.append((math.degrees(s["alpha"]) % 360.0, t_p["alpha"] % 360.0))
                if is_source_model(t_type) and is_source_model(s["model_type"]):
                    if s["t0_source2"] is not None and s["u0_source2"] is not None and s["t0"] is not None and s["u0"] is not None and s["te"] is not None:
                        is_swapped = False
                        if t_p.get("t0_source2") is not None and t_p.get("t0") is not None:
                            diff_unswapped = abs(s["t0"] - t_p["t0"]) + abs(s["t0_source2"] - t_p["t0_source2"])
                            diff_swapped = abs(s["t0"] - t_p["t0_source2"]) + abs(s["t0_source2"] - t_p["t0"])
                            if diff_swapped < diff_unswapped:
                                is_swapped = True

                        dx = (s["t0_source2"] - s["t0"]) / s["te"]
                        dy = s["u0_source2"] - s["u0"]
                        if is_lens_model(s["model_type"]) and s.get("alpha") is not None:
                            alpha_offset = math.degrees(s["alpha"])
                        else:
                            alpha_offset = t_p.get("alpha") if (t_p and t_p.get("alpha") is not None) else 0.0
                        modeled_alpha = (math.degrees(math.atan2(dy, -dx)) + alpha_offset) % 360.0
                        if pd.notna(t_p.get("Source2_alpha")):
                            t_val = (t_p["Source2_alpha"] + 180.0) % 360.0 if is_swapped else t_p["Source2_alpha"] % 360.0
                            bs_alpha_pairs.append((modeled_alpha, t_val))

    bl_best_idx, bl_best_label = get_best_transform_idx(bl_alpha_pairs)
    bs_best_idx, bs_best_label = get_best_transform_idx(bs_alpha_pairs)

    q_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": [], "truth_component": []}
    te_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": []}
    rho_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": []}
    u0_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": []}
    t0_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": []}

    # Modelling Parameters (split by event type)
    # 1. Binary Lens (1S2L, 2S2L): separation (s), orientation (alpha)
    bl_s_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": [], "truth_component": []}
    bl_alpha_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": [], "transform": []}

    # 2. Binary Source (2S1L, 2S2L): separation (s_source), orientation (alpha_source), flux_ratio
    bs_s_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": []}
    bs_alpha_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": [], "transform": []}
    bs_flux_ratio_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": []}

    # Physical Parameters (all events)
    phys_mass_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": [], "truth_component": []}
    phys_dl_data = {"true": [], "model": [], "model_low": [], "model_high": [], "event": [], "prob": [], "truth_component": []}

    parallax_N_residuals = []
    parallax_E_residuals = []

    tp = 0.0
    fp = 0.0
    fn = 0.0
    team_cpu = 0.0

    q_log10_fractional_error_sum, q_weight = 0.0, 0.0
    te_log10_fractional_error_sum, te_weight = 0.0, 0.0
    rho_log10_fractional_error_sum, rho_weight = 0.0, 0.0
    u0_err_sum, u0_weight = 0.0, 0.0
    t0_err_sum, t0_weight = 0.0, 0.0
    mass_err_sum, mass_weight = 0.0, 0.0
    dl_err_sum, dl_weight = 0.0, 0.0

    bl_s_log10_fractional_error_sum, bl_s_weight = 0.0, 0.0
    bl_alpha_err_sum, bl_alpha_weight = 0.0, 0.0
    bs_s_log10_fractional_error_sum, bs_s_weight = 0.0, 0.0
    bs_alpha_err_sum, bs_alpha_weight = 0.0, 0.0
    bs_flux_err_sum, bs_flux_weight = 0.0, 0.0

    phys_planets = 0.0
    phys_sol_count = 0       # distinct active solutions that include physical params (mass + dl)
    total_active_sol_count = 0  # all active solutions across all events

    cohort_data = {}
    if cohort_metrics_path.exists():
        with open(cohort_metrics_path, "r") as f:
            cohort_data = json.load(f)

    event_recovery = cohort_data.get("event_recovery", {})

    hardest_det_eid = None
    hardest_det_rec = 1.0
    easiest_miss_eid = None
    easiest_miss_rec = 0.0

    for eid, sols in preds.items():
        planet_prob = sum(s["prob"] for s in sols if s["is_planet"])
        is_true_planet = eid in true_planets
        team_cpu += sum(s["prob"] * s["cpu"] for s in sols)

        if is_true_planet:
            tp += planet_prob
            fn += (1.0 - planet_prob)
            if planet_prob >= 0.5:
                rec = event_recovery.get(eid, 1.0)
                if rec < hardest_det_rec:
                    hardest_det_rec = rec
                    hardest_det_eid = eid
            else:
                rec = event_recovery.get(eid, 0.0)
                if rec > easiest_miss_rec:
                    easiest_miss_rec = rec
                    easiest_miss_eid = eid
        else:
            fp += planet_prob

        t_p = true_params.get(eid)
        t_type = truth_map.get(eid)
        if t_p:
            for s in sols:
                prob = s["prob"]
                lens_component = (
                    match_truth_lens_component(t_p, s.get("s"), s.get("q"))
                    if is_lens_model(s["model_type"])
                    else None
                )
                is_swapped = False
                if is_source_model(t_type) and is_source_model(s["model_type"]):
                    if (s["t0_source2"] is not None and t_p.get("t0_source2") is not None and
                        s["t0"] is not None and t_p.get("t0") is not None):
                        diff_unswapped = abs(s["t0"] - t_p["t0"]) + abs(s["t0_source2"] - t_p["t0_source2"])
                        diff_swapped = abs(s["t0"] - t_p["t0_source2"]) + abs(s["t0_source2"] - t_p["t0"])
                        if diff_swapped < diff_unswapped:
                            is_swapped = True

                def get_bounds(param_key, val, is_angle=False, log_scale=False):
                    uncerts = s.get("param_uncerts") or {}
                    sigma = uncerts.get(param_key)
                    if sigma is None:
                        return val, val

                    if isinstance(sigma, (list, tuple)):
                        low_sig, high_sig = sigma
                    else:
                        low_sig, high_sig = sigma, sigma

                    if is_angle:
                        return val - math.degrees(low_sig), val + math.degrees(high_sig)

                    low_bound = val - low_sig
                    high_bound = val + high_sig
                    if log_scale and low_bound <= 0:
                        # Log axes cannot render <= 0. Clip to 1e-10 so the bar
                        # extends to the bottom of the plot, visually communicating
                        # that the lower bound is unconstrained.
                        low_bound = 1e-10
                    return low_bound, high_bound

                # Parallax residuals
                if s["piEN"] is not None and pd.notna(t_p["piEN"]):
                    parallax_N_residuals.append(s["piEN"] - t_p["piEN"])
                if s["piEE"] is not None and pd.notna(t_p["piEE"]):
                    parallax_E_residuals.append(s["piEE"] - t_p["piEE"])

                # te, rho, u0, t0 are general parameter comparisons computed for all events
                if pd.notna(t_p["te"]) and s["te"] is not None:
                    te_error = parameter_comparison_error(s["te"], t_p["te"], "tE")
                    if te_error is not None:
                        te_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(te_error)
                        te_weight += prob
                    low_b, high_b = get_bounds("tE", s["te"], log_scale=True)
                    te_data["true"].append(t_p["te"])
                    te_data["model"].append(s["te"])
                    te_data["model_low"].append(low_b)
                    te_data["model_high"].append(high_b)
                    te_data["event"].append(eid)
                    te_data["prob"].append(prob)

                if pd.notna(t_p.get("rho")) and s["rho"] is not None:
                    rho_error = parameter_comparison_error(s["rho"], t_p.get("rho"), "rho")
                    if rho_error is not None:
                        rho_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(rho_error)
                        rho_weight += prob
                        low_b, high_b = get_bounds("rho", s["rho"], log_scale=True)
                        rho_data["true"].append(t_p.get("rho"))
                        rho_data["model"].append(s["rho"])
                        rho_data["model_low"].append(low_b)
                        rho_data["model_high"].append(high_b)
                        rho_data["event"].append(eid)
                        rho_data["prob"].append(prob)

                u0_truth = t_p["u0_source2"] if is_swapped else t_p["u0"]
                t0_truth = t_p["t0_source2"] if is_swapped else t_p["t0"]

                if pd.notna(u0_truth) and s["u0"] is not None:
                    u0_err_sum += prob * abs(abs(u0_truth) - abs(s["u0"]))
                    u0_weight += prob
                    val_abs = abs(s["u0"])
                    low_b, high_b = get_bounds("u0", val_abs, log_scale=True)
                    u0_data["true"].append(abs(u0_truth))
                    u0_data["model"].append(val_abs)
                    u0_data["model_low"].append(low_b)
                    u0_data["model_high"].append(high_b)
                    u0_data["event"].append(eid)
                    u0_data["prob"].append(prob)
                if pd.notna(t0_truth) and s["t0"] is not None:
                    t0_err_sum += prob * abs(t0_truth - s["t0"])
                    t0_weight += prob
                    low_b, high_b = get_bounds("t0", s["t0"], log_scale=False)
                    t0_data["true"].append(t0_truth)
                    t0_data["model"].append(s["t0"])
                    t0_data["model_low"].append(low_b)
                    t0_data["model_high"].append(high_b)
                    t0_data["event"].append(eid)
                    t0_data["prob"].append(prob)

                compare_lens_component = lens_component is not None and (
                    tier == "experienced" or (is_true_planet and s["is_planet"])
                )
                if compare_lens_component:
                    if s["q"] is not None and pd.notna(lens_component["q"]):
                        q_error = parameter_comparison_error(s["q"], lens_component["q"], "q")
                        if q_error is not None:
                            q_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(q_error)
                            q_weight += prob
                        low_b, high_b = get_bounds("q", s["q"], log_scale=True)
                        q_data["true"].append(lens_component["q"])
                        q_data["model"].append(s["q"])
                        q_data["model_low"].append(low_b)
                        q_data["model_high"].append(high_b)
                        q_data["event"].append(eid)
                        q_data["prob"].append(prob)
                        q_data["truth_component"].append(lens_component["label"])
                    if is_true_planet and s["is_planet"] and s["mass"] is not None and s["dl"] is not None:
                        phys_planets += prob
                        phys_sol_count += 1
                        truth_mass = lens_component.get("mass")
                        truth_dl = lens_component.get("dl")
                        if truth_mass is not None and pd.notna(truth_mass):
                            mass_err_sum += prob * abs(truth_mass - s["mass"]) / truth_mass
                            mass_weight += prob
                        if truth_dl is not None and pd.notna(truth_dl):
                            dl_err_sum += prob * abs(truth_dl - s["dl"]) / truth_dl
                            dl_weight += prob
                total_active_sol_count += 1

                # ── Modelling Parameters (excl. 1S1L) ──
                # Binary Lens (1S2L, 2S2L)
                if is_lens_model(t_type) and is_lens_model(s["model_type"]):
                    if lens_component is not None and s["s"] is not None:
                        low_b, high_b = get_bounds("s", s["s"], log_scale=True)
                        bl_s_data["true"].append(lens_component["s"])
                        bl_s_data["model"].append(s["s"])
                        bl_s_data["model_low"].append(low_b)
                        bl_s_data["model_high"].append(high_b)
                        bl_s_data["event"].append(eid)
                        bl_s_data["prob"].append(prob)
                        bl_s_data["truth_component"].append(lens_component["label"])
                        bl_s_error = parameter_comparison_error(s["s"], lens_component["s"], "s")
                        if bl_s_error is not None:
                            bl_s_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(bl_s_error)
                            bl_s_weight += prob
                    if s["alpha"] is not None and pd.notna(t_p["alpha"]):
                        m_val = math.degrees(s["alpha"]) % 360.0
                        t_val = t_p["alpha"] % 360.0
                        if bl_best_idx == 0:
                            t_equiv = t_val
                        elif bl_best_idx == 1:
                            t_equiv = (t_val + 180.0) % 360.0
                        elif bl_best_idx == 2:
                            t_equiv = (360.0 - t_val) % 360.0
                        else:
                            t_equiv = (180.0 - t_val) % 360.0

                        low_b, high_b = get_bounds("alpha", m_val, is_angle=True)
                        bl_alpha_data["true"].append(t_equiv)
                        bl_alpha_data["model"].append(m_val)
                        bl_alpha_data["model_low"].append(low_b)
                        bl_alpha_data["model_high"].append(high_b)
                        bl_alpha_data["event"].append(eid)
                        bl_alpha_data["prob"].append(prob)
                        bl_alpha_data["transform"].append(bl_best_label)
                        diff = abs(m_val - t_equiv)
                        diff = min(diff, 360.0 - diff)
                        bl_alpha_err_sum += prob * diff
                        bl_alpha_weight += prob

                if is_source_model(t_type) and is_source_model(s["model_type"]):
                    if s["t0_source2"] is not None and s["u0_source2"] is not None and s["t0"] is not None and s["u0"] is not None and s["te"] is not None:
                        dx = (s["t0_source2"] - s["t0"]) / s["te"]
                        dy = s["u0_source2"] - s["u0"]
                        modeled_s = math.sqrt(dx**2 + dy**2)

                        if is_lens_model(s["model_type"]) and s.get("alpha") is not None:
                            alpha_offset = math.degrees(s["alpha"])
                        else:
                            alpha_offset = t_p.get("alpha") if (t_p and t_p.get("alpha") is not None) else 0.0

                        modeled_alpha = (math.degrees(math.atan2(dy, -dx)) + alpha_offset) % 360.0

                        if pd.notna(t_p["Source2_s"]):
                            bs_s_data["true"].append(t_p["Source2_s"])
                            bs_s_data["model"].append(modeled_s)
                            bs_s_data["model_low"].append(modeled_s)
                            bs_s_data["model_high"].append(modeled_s)
                            bs_s_data["event"].append(eid)
                            bs_s_data["prob"].append(prob)
                            bs_s_error = parameter_comparison_error(modeled_s, t_p["Source2_s"], "s_source")
                            if bs_s_error is not None:
                                bs_s_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(bs_s_error)
                                bs_s_weight += prob
                        if pd.notna(t_p["Source2_alpha"]):
                            m_val = modeled_alpha % 360.0
                            t_val = (t_p["Source2_alpha"] + 180.0) % 360.0 if is_swapped else t_p["Source2_alpha"] % 360.0
                            if bs_best_idx == 0:
                                t_equiv = t_val
                            elif bs_best_idx == 1:
                                t_equiv = (t_val + 180.0) % 360.0
                            elif bs_best_idx == 2:
                                t_equiv = (360.0 - t_val) % 360.0
                            else:
                                t_equiv = (180.0 - t_val) % 360.0
                            bs_alpha_data["true"].append(t_equiv)
                            bs_alpha_data["model"].append(m_val)
                            bs_alpha_data["model_low"].append(m_val)
                            bs_alpha_data["model_high"].append(m_val)
                            bs_alpha_data["event"].append(eid)
                            bs_alpha_data["prob"].append(prob)
                            bs_alpha_data["transform"].append(bs_best_label)
                            diff = abs(m_val - t_equiv)
                            diff = min(diff, 360.0 - diff)
                            bs_alpha_err_sum += prob * diff
                            bs_alpha_weight += prob

                    if s["flux_ratio"] is not None and s["flux_ratio"] > 0 and pd.notna(t_p["Obs_0_fs2ofs1"]) and t_p["Obs_0_fs2ofs1"] > 0:
                        raw_fr = s["flux_ratio"]
                        truth_fr = t_p["Obs_0_fs2ofs1"]
                        # GULLS always has fs_1 > fs_2 so the truth ratio (fs2_of_fs1) is <= 1.
                        # The submitted solution can be whatever, so invert it if it is > 1.
                        s_flux = (1.0 / raw_fr) if raw_fr > 1.0 else raw_fr
                        truth_fr_norm = (1.0 / truth_fr) if truth_fr > 1.0 else truth_fr
                        low_b, high_b = get_bounds("flux_ratio", s_flux, log_scale=True)
                        bs_flux_ratio_data["true"].append(truth_fr_norm)
                        bs_flux_ratio_data["model"].append(s_flux)
                        bs_flux_ratio_data["model_low"].append(low_b)
                        bs_flux_ratio_data["model_high"].append(high_b)
                        bs_flux_ratio_data["event"].append(eid)
                        bs_flux_ratio_data["prob"].append(prob)
                        bs_flux_err_sum += prob * abs(truth_fr_norm - s_flux) / truth_fr_norm
                        bs_flux_weight += prob

                # ── Physical Parameters ──
                physical_component = lens_component or {
                    "label": "canonical",
                    "mass": t_p.get("mass"),
                    "dl": t_p.get("dl"),
                }
                if s["mass"] is not None and physical_component.get("mass") is not None and pd.notna(physical_component["mass"]):
                    low_b, high_b = get_bounds("planet_mass", s["mass"], log_scale=True)
                    phys_mass_data["true"].append(physical_component["mass"])
                    phys_mass_data["model"].append(s["mass"])
                    phys_mass_data["model_low"].append(low_b)
                    phys_mass_data["model_high"].append(high_b)
                    phys_mass_data["event"].append(eid)
                    phys_mass_data["prob"].append(prob)
                    phys_mass_data["truth_component"].append(physical_component["label"])
                if s["dl"] is not None and physical_component.get("dl") is not None and pd.notna(physical_component["dl"]):
                    low_b, high_b = get_bounds("lens_distance", s["dl"], log_scale=False)
                    phys_dl_data["true"].append(physical_component["dl"])
                    phys_dl_data["model"].append(s["dl"])
                    phys_dl_data["model_low"].append(low_b)
                    phys_dl_data["model_high"].append(high_b)
                    phys_dl_data["event"].append(eid)
                    phys_dl_data["prob"].append(prob)
                    phys_dl_data["truth_component"].append(physical_component["label"])

    # Helper function to plot and save Bokeh scatter plots
    def save_scatter_plot(data, title, x_label, y_label, filename, log_scale=True, tooltip_x_format="0.00", tooltip_y_format="0.00", color_idx=0, is_angle=False):
        if not data["true"]:
            return False

        # Calculate plot range limits
        if log_scale:
            min_val = min(min(data["true"]), min(data["model"]))
            max_val = max(max(data["true"]), max(data["model"]))
            min_val *= 0.8
            max_val *= 1.2

            p = figure(title=title, x_axis_type="log", y_axis_type="log",
                       x_axis_label=x_label, y_axis_label=y_label,
                       height=350, width=400, tools="pan,wheel_zoom,reset,hover")
        else:
            true_min = min(data["true"])
            true_max = max(data["true"])
            span = true_max - true_min
            if span == 0:
                span = abs(true_min) * 0.05 if true_min != 0 else 1.0
            min_val = true_min - span * 0.15
            max_val = true_max + span * 0.15

            p = figure(title=title, x_axis_type="linear", y_axis_type="linear",
                       x_axis_label=x_label, y_axis_label=y_label,
                       x_range=(min_val, max_val), y_range=(min_val, max_val),
                       height=350, width=400, tools="pan,wheel_zoom,reset,hover")

        source = ColumnDataSource(data)
        if "model_low" in data and "model_high" in data:
            p.segment(x0="true", y0="model_low", x1="true", y1="model_high",
                      source=source, color="gray", line_width=1.2, alpha=0.5)
        p.scatter("true", "model", source=source, size=8, color=MY_PALETTE[color_idx % len(MY_PALETTE)], alpha="prob")

        p.line([min_val, max_val], [min_val, max_val], color="black", line_dash="dashed")
        tooltips = [
            ("Event", "@event"),
            ("True", f"@true{{{tooltip_x_format}}}"),
            ("Modelled", f"@model{{{tooltip_y_format}}}"),
            ("Prob", "@prob{0.2f}")
        ]
        if "transform" in data:
            tooltips.append(("Transformation", "@transform"))
        if "truth_component" in data:
            tooltips.append(("Truth component", "@truth_component"))
        p.hover.tooltips = tooltips

        # 2. Right Panel: Probability-weighted residual histogram
        model_arr = np.array(data["model"])
        true_arr = np.array(data["true"])
        prob_arr = np.array(data["prob"])

        if log_scale:
            residuals = np.log10(model_arr) - np.log10(true_arr)
            parameter_label = x_label.replace("True ", "").replace(" (log scale)", "")
            hist_x_label = f"Residual Δ log10({parameter_label})"
        elif is_angle:
            diff = model_arr - true_arr
            residuals = (diff + 180.0) % 360.0 - 180.0
            hist_x_label = f"Residual Δ {x_label.replace('True ', '')} (deg)"
        else:
            residuals = model_arr - true_arr
            hist_x_label = f"Residual Δ {x_label.replace('True ', '')}"

        # Compute weighted histogram
        if log_scale or is_angle:
            r_min, r_max = np.min(residuals), np.max(residuals)
        else:
            if len(residuals) > 1:
                q_low, q_high = np.percentile(residuals, [2.5, 97.5])
                if q_low == q_high:
                    r_min, r_max = q_low - 0.5, q_high + 0.5
                else:
                    pad = (q_high - q_low) * 0.1
                    r_min, r_max = q_low - pad, q_high + pad
            else:
                r_min, r_max = np.min(residuals), np.max(residuals)

        if r_min == r_max:
            edges = np.linspace(r_min - 0.1, r_max + 0.1, 16)
        else:
            edges = np.linspace(r_min, r_max, 16)
        hist, edges = np.histogram(residuals, bins=edges, weights=prob_arr)

        p_hist = figure(title=f"{title.split(' Recovery')[0]} Residuals",
                        x_axis_label=hist_x_label, y_axis_label="Weighted Count",
                        height=350, width=400, tools="pan,wheel_zoom,reset,hover,save")

        # Render quad bars
        hist_color = MY_PALETTE[color_idx % len(MY_PALETTE)]
        p_hist.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
                    fill_color=hist_color, line_color="white", alpha=0.8)

        # Draw dashed vertical line at x = 0.0
        hist_max = max(hist) if len(hist) > 0 else 0.0
        line_max = hist_max * 1.1 if hist_max > 0 else 1.0
        p_hist.line([0, 0], [0, line_max], color="black", line_dash="dashed", line_width=1.5)

        p_hist.hover.tooltips = [
            ("Residual Range", "@left{0.000} to @right{0.000}"),
            ("Weighted Count", "@top{0.00}")
        ]

        # Combine side-by-side using row layout
        layout = bokeh_row(p, p_hist)

        script, div = components(layout)
        with open(local_assets_dir / filename, "w") as f:
            f.write(f"{script}\n{div}")
        return True

    # Positive scale parameters use logarithmic axes and log10 residuals.
    save_scatter_plot(q_data, "Mass Ratio (q) Recovery (log10-space comparison)", "True q (log scale)", "Modelled q (log scale)", "q_scatter.html", log_scale=True, tooltip_x_format="0.00000", tooltip_y_format="0.00000", color_idx=0)
    save_scatter_plot(te_data, "Einstein Crossing Time (tE) Recovery (log10-space comparison)", "True tE (days, log scale)", "Modelled tE (days, log scale)", "te_scatter.html", log_scale=True, tooltip_x_format="0.00", tooltip_y_format="0.00", color_idx=1)
    save_scatter_plot(rho_data, "Finite-Source Radius (rho) Recovery (log10-space comparison)", "True rho (log scale)", "Modelled rho (log scale)", "rho_scatter.html", log_scale=True, tooltip_x_format="0.00000", tooltip_y_format="0.00000", color_idx=4)
    save_scatter_plot(u0_data, "Impact Parameter (u0) Recovery", "True u0", "Modelled u0", "u0_scatter.html", log_scale=True, tooltip_x_format="0.0000", tooltip_y_format="0.0000", color_idx=2)
    save_scatter_plot(t0_data, "Time of Peak Magnification (t0) Recovery", "True t0 (HJD)", "Modelled t0 (HJD)", "t0_scatter.html", log_scale=False, tooltip_x_format="0.000", tooltip_y_format="0.000", color_idx=3)

    # Plot Binary Lens Modelling Parameters
    save_scatter_plot(bl_s_data, "Binary Lens Separation (s) (log10-space comparison)", "True s (log scale)", "Modelled s (log scale)", "bl_s_scatter.html", log_scale=True, tooltip_x_format="0.00", tooltip_y_format="0.00", color_idx=2)
    save_scatter_plot(bl_alpha_data, "Binary Lens Trajectory Angle (α)", "True α (deg)", "Modelled α (deg)", "bl_alpha_scatter.html", log_scale=False, tooltip_x_format="0.0", tooltip_y_format="0.0", color_idx=3, is_angle=True)

    # Plot Binary Source Modelling Parameters
    save_scatter_plot(bs_s_data, "Binary Source Separation (s_source) (log10-space comparison)", "True s_source (log scale)", "Modelled s_source (log scale)", "bs_s_scatter.html", log_scale=True, tooltip_x_format="0.00", tooltip_y_format="0.00", color_idx=4)
    save_scatter_plot(bs_alpha_data, "Binary Source Angle (α_source)", "True α_source (deg)", "Modelled α_source (deg)", "bs_alpha_scatter.html", log_scale=False, tooltip_x_format="0.0", tooltip_y_format="0.0", color_idx=5, is_angle=True)
    save_scatter_plot(bs_flux_ratio_data, "Binary Source Flux Ratio (Band 0)", "True F_S2/F_S1 (Band 0)", "Modelled F_S2/F_S1 (Band 0)", "bs_flux_ratio_scatter.html", log_scale=True, tooltip_x_format="0.000", tooltip_y_format="0.000", color_idx=0)

    # Plot Physical Parameters
    save_scatter_plot(phys_mass_data, "Companion Mass (M_planet)", "True Mass (M_earth)", "Modelled Mass (M_earth)", "phys_mass_scatter.html", log_scale=True, tooltip_x_format="0.00", tooltip_y_format="0.00", color_idx=1)
    save_scatter_plot(phys_dl_data, "Lens Distance (D_L)", "True D_L (kpc)", "Modelled D_L (kpc)", "phys_dl_scatter.html", log_scale=False, tooltip_x_format="0.00", tooltip_y_format="0.00", color_idx=2)

    # Plot Parallax Residuals Histogram
    if parallax_N_residuals or parallax_E_residuals:
        # Combine both to get unified bin edges
        combined_res = parallax_N_residuals + parallax_E_residuals
        if combined_res:
            min_val = min(combined_res)
            max_val = max(combined_res)
            # Add some padding
            padding = (max_val - min_val) * 0.05 if max_val != min_val else 0.1
            bins = np.linspace(min_val - padding, max_val + padding, 20)

            p_hist = figure(title="Parallax Component Residuals (πE,N, πE,E)",
                            x_axis_label="Residual (Model - Truth) [θE]", y_axis_label="Count",
                            height=350, width=400, tools="pan,wheel_zoom,reset,save")

            if parallax_N_residuals:
                hist_N, _ = np.histogram(parallax_N_residuals, bins=bins)
                p_hist.quad(top=hist_N, bottom=0, left=bins[:-1], right=bins[1:],
                            fill_color=MY_PALETTE[0], line_color="white", alpha=0.6, legend_label="πE,N (North)")
            if parallax_E_residuals:
                hist_E, _ = np.histogram(parallax_E_residuals, bins=bins)
                p_hist.quad(top=hist_E, bottom=0, left=bins[:-1], right=bins[1:],
                            fill_color=MY_PALETTE[1], line_color="white", alpha=0.6, legend_label="πE,E (East)")

            p_hist.legend.click_policy = "hide"
            p_hist.legend.background_fill_alpha = 0.7

            script, div = components(p_hist)
            with open(local_assets_dir / "parallax_hist.html", "w") as f: f.write(f"{script}\n{div}")

    # Calculate precision metrics for this team
    _confidence_scores = []
    _total_sol_count = 0
    _uncert_sol_count = 0
    _posterior_sol_count = 0

    for _eid, _sols in preds.items():
        if not _sols:
            continue
        _confidence_scores.append(max(_s["prob"] for _s in _sols))
        for _s in _sols:
            _total_sol_count += 1
            _uncerts = _s.get("param_uncerts") or {}
            if _s.get("posterior_path"):
                _posterior_sol_count += 1
            if _uncerts:
                _uncert_sol_count += 1

    _mean_confidence = float(np.mean(_confidence_scores)) * 100 if _confidence_scores else 0.0
    _uncertainty_coverage = (
        _uncert_sol_count / _total_sol_count * 100 if _total_sol_count > 0 else 0.0
    )
    _posterior_coverage = (
        _posterior_sol_count / _total_sol_count * 100 if _total_sol_count > 0 else 0.0
    )
    _precision_composite = 0.5 * (_mean_confidence / 100.0) + 0.25 * (_uncertainty_coverage / 100.0) + 0.25 * (_posterior_coverage / 100.0)

    # Calculate Current Team Metrics
    team_metrics = {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "planets_per_cpu": tp / team_cpu if team_cpu > 0 else 0,
        "q_log10_fractional_error": float((q_log10_fractional_error_sum / q_weight) * 100) if q_weight > 0 else None,
        "te_log10_fractional_error": float((te_log10_fractional_error_sum / te_weight) * 100) if te_weight > 0 else None,
        "rho_log10_fractional_error": float((rho_log10_fractional_error_sum / rho_weight) * 100) if rho_weight > 0 else None,
        "u0_mae": float(u0_err_sum / u0_weight) if u0_weight > 0 else None,
        "t0_mae": float(t0_err_sum / t0_weight) if t0_weight > 0 else None,
        "phys_planets": phys_planets,
        "phys_sol_count": phys_sol_count,
        "phys_sol_pct": float(phys_sol_count / total_active_sol_count * 100) if total_active_sol_count > 0 else 0.0,
        "mass_mape": float((mass_err_sum / mass_weight) * 100) if mass_weight > 0 else None,
        "dl_mape": float((dl_err_sum / dl_weight) * 100) if dl_weight > 0 else None,
        "bl_s_log10_fractional_error": float((bl_s_log10_fractional_error_sum / bl_s_weight) * 100) if bl_s_weight > 0 else None,
        "bl_alpha_mae": float(bl_alpha_err_sum / bl_alpha_weight) if bl_alpha_weight > 0 else None,
        "bs_s_log10_fractional_error": float((bs_s_log10_fractional_error_sum / bs_s_weight) * 100) if bs_s_weight > 0 else None,
        "bs_alpha_mae": float(bs_alpha_err_sum / bs_alpha_weight) if bs_alpha_weight > 0 else None,
        "bs_flux_ratio_mape": float((bs_flux_err_sum / bs_flux_weight) * 100) if bs_flux_weight > 0 else None,
        "mean_confidence": _mean_confidence,
        "uncertainty_coverage": _uncertainty_coverage,
        "posterior_coverage": _posterior_coverage,
        "precision_composite": _precision_composite,
    }

    # Compute F1 scores for this team (same logic as generate_cohort_stats.py)
    _truth_types = model_types_for_tier(tier, truth_map.values())
    _class_tp = {c: 0.0 for c in _truth_types}
    _class_fp = {c: 0.0 for c in _truth_types}
    _class_fn = {c: 0.0 for c in _truth_types}
    for _eid, _tc in truth_map.items():
        if _tc not in _truth_types:
            continue
        if _eid in preds:
            for _s in preds[_eid]:
                _sc = _s["model_type"]
                _p = _s["prob"]
                if _sc not in _truth_types:
                    continue
                if _sc == _tc:
                    _class_tp[_tc] += _p
                else:
                    _class_fp[_sc] += _p
                    _class_fn[_tc] += _p
        else:
            _class_fn[_tc] += 1.0
    _f1s = []
    for _c in _truth_types:
        _pr = _class_tp[_c] / (_class_tp[_c] + _class_fp[_c]) if (_class_tp[_c] + _class_fp[_c]) > 0 else 0.0
        _rc = _class_tp[_c] / (_class_tp[_c] + _class_fn[_c]) if (_class_tp[_c] + _class_fn[_c]) > 0 else 0.0
        _f1s.append(2 * _pr * _rc / (_pr + _rc) if (_pr + _rc) > 0 else 0.0)
    _macro_f1 = float(np.mean(_f1s))
    _tp_p = tp
    _fp_p = fp
    _fn_p = fn
    _pf1_denom = 2 * _tp_p + _fp_p + _fn_p
    _planet_f1 = float(2 * _tp_p / _pf1_denom) if _pf1_denom > 0 else 0.0
    _composite = (_macro_f1 + _planet_f1) / 2.0
    team_metrics["macro_f1"] = _macro_f1
    team_metrics["planet_f1"] = _planet_f1
    team_metrics["classification_composite"] = _composite
    if tier == "experienced":
        # Experienced reports have parameter truth, but no trusted event-type
        # classification labels for scoring.
        team_metrics["macro_f1"] = None
        team_metrics["planet_f1"] = None
        team_metrics["classification_composite"] = None

    cohort_avg = cohort_data.get("cohort_avg", {})
    all_teams = cohort_data.get("teams", {})
    all_event_recoveries = list(event_recovery.values())
    num_planets_in_cohort = len(all_event_recoveries)

    def compute_category_ranks():
        """Compute cohort percentiles for the four summary categories.

        Returns a dict with display strings for each category box.
        """
        def _percentile(metric, val, higher_is_better):
            """Compute percentile score for this team vs. all teams in cohort_metrics.json."""
            if val is None:
                return "N/A"
            vals = [
                tm.get(metric)
                for tm in all_teams.values()
                if tm.get(metric) is not None
            ]
            if val not in vals:
                vals.append(val)
            vals = sorted(vals, reverse=higher_is_better)
            rank = vals.index(val) + 1
            n = len(vals)
            if n <= 1:
                return "100"
            pct = round(100 * (n - rank) / (n - 1))
            return str(pct)

        # ── Classification ───────────────────────────────────────────────────
        composite_rank = _percentile(
            "classification_composite",
            team_metrics.get("classification_composite"),
            True,
        )
        macro_rank = _percentile("macro_f1", team_metrics.get("macro_f1"), True)
        planet_rank = _percentile("planet_f1", team_metrics.get("planet_f1"), True)
        classification_sublabel = (
            "Submitted event distribution only"
            if tier == "experienced"
            else f"Event F1: {macro_rank} | Planet F1: {planet_rank}"
        )

        # ── Accuracy (geometric mean of parameter errors, lower = better) ─────
        mape_keys = [
            "q_log10_fractional_error",
            "te_log10_fractional_error",
            "mass_mape",
            "dl_mape",
        ]
        this_mapes = [team_metrics.get(k) for k in mape_keys if team_metrics.get(k) is not None]

        if this_mapes:
            this_geomean = math.exp(sum(math.log(m) for m in this_mapes) / len(this_mapes))
            # Build cohort geomeans
            cohort_geomeans = []
            for tm in all_teams.values():
                team_mapes = [tm.get(k) for k in mape_keys if tm.get(k) is not None]
                if team_mapes:
                    cohort_geomeans.append(
                        math.exp(sum(math.log(m) for m in team_mapes) / len(team_mapes))
                    )
            if this_geomean not in cohort_geomeans:
                cohort_geomeans.append(this_geomean)
            cohort_geomeans_sorted = sorted(cohort_geomeans)  # ascending = best first
            rank = cohort_geomeans_sorted.index(this_geomean) + 1
            n = len(cohort_geomeans_sorted)
            if n <= 1:
                accuracy_rank = "100"
            else:
                pct = round(100 * (n - rank) / (n - 1))
                accuracy_rank = str(pct)
        else:
            accuracy_rank = "N/A"

        # ── Precision ─────────────────────────────────────────────────────────
        precision_rank = _percentile(
            "precision_composite",
            team_metrics.get("precision_composite"),
            True,
        )

        # ── Efficiency ────────────────────────────────────────────────────────
        efficiency_rank = _percentile(
            "planets_per_cpu",
            team_metrics.get("planets_per_cpu"),
            True,
        )
        return {
            "classification": composite_rank,
            "classification_sublabel": classification_sublabel,
            "accuracy": accuracy_rank,
            "precision": precision_rank,
            "efficiency": efficiency_rank,
        }

    category_ranks = compute_category_ranks()
    with open(local_assets_dir / "category_ranks.json", "w") as f:
        json.dump(category_ranks, f, indent=2)

    def get_percentile(metric, val, higher_is_better=True):
        if val is None: return "N/A"
        vals = [tm.get(metric) for tm in all_teams.values() if tm.get(metric) is not None]
        if val not in vals: vals.append(val)
        vals = sorted(vals, reverse=higher_is_better)
        rank = vals.index(val) + 1
        n = len(vals)
        if n <= 1:
            pct = 100
        else:
            pct = round(100 * (n - rank) / (n - 1))
        # Add ordinal suffix
        if 11 <= (pct % 100) <= 13:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(pct % 10, 'th')
        return f"{pct}{suffix} percentile"

    def get_event_hardness_rank(rec, easiest=False):
        if rec is None or not all_event_recoveries: return "N/A"
        vals = sorted(all_event_recoveries, reverse=easiest)
        try:
            rank = vals.index(rec) + 1
            return f"#{rank} / {num_planets_in_cohort}"
        except ValueError:
            return "N/A"

    def fmt_val(val, is_pct=False, is_int=False, is_deg=False):
        if val is None: return "N/A"
        if is_int: return f"{val:.1f}"
        if is_deg: return f"{val:.2f}°"
        return f"{val:.2f}%" if is_pct else f"{val:.4f}"

    hardest_link = f"<a href='{hardest_det_eid}.html' class='text-rtd-accent hover:underline font-mono'>{hardest_det_eid}</a>" if hardest_det_eid else "None"
    easiest_link = f"<a href='{easiest_miss_eid}.html' class='text-rtd-accent hover:underline font-mono'>{easiest_miss_eid}</a>" if easiest_miss_eid else "None"

    hardest_rec_str = f"{hardest_det_rec*100:.1f}% Recovery" if hardest_det_eid else "N/A"
    easiest_rec_str = f"{easiest_miss_rec*100:.1f}% Recovery" if easiest_miss_eid else "N/A"

    hardest_rank = get_event_hardness_rank(hardest_det_rec, easiest=False)
    easiest_rank = get_event_hardness_rank(easiest_miss_rec, easiest=True)

    # ── 1. Build Classification Metrics Table ──
    class_rows = [
        {"label": "True Positives (Planets)", "val": fmt_val(team_metrics["true_positives"], is_int=True), "avg": fmt_val(cohort_avg.get("true_positives"), is_int=True), "pct": get_percentile("true_positives", team_metrics["true_positives"], True)},
        {"label": "False Positives (Planets)", "val": fmt_val(team_metrics["false_positives"], is_int=True), "avg": fmt_val(cohort_avg.get("false_positives"), is_int=True), "pct": get_percentile("false_positives", team_metrics["false_positives"], False)},
        {"label": "False Negatives (Missed)", "val": fmt_val(team_metrics["false_negatives"], is_int=True), "avg": fmt_val(cohort_avg.get("false_negatives"), is_int=True), "pct": get_percentile("false_negatives", team_metrics["false_negatives"], False)},
        {"label": "Macro F1 (Event Classification)", "val": fmt_val(team_metrics["macro_f1"]), "avg": fmt_val(cohort_avg.get("macro_f1")), "pct": get_percentile("macro_f1", team_metrics["macro_f1"], True)},
        {"label": "Planet F1 Score (Planet Detection)", "val": fmt_val(team_metrics["planet_f1"]), "avg": fmt_val(cohort_avg.get("planet_f1")), "pct": get_percentile("planet_f1", team_metrics["planet_f1"], True)},
    ]
    class_html = "<table class='w-full text-left table-auto border-collapse mt-4 mb-4'>"
    class_html += "<thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'><tr><th class='py-3 px-4'>Metric</th><th class='py-3 px-4'>Team Submission</th><th class='py-3 px-4'>Cohort Mean</th><th class='py-3 px-4'>Cohort Percentile / Hardness</th></tr></thead>"
    class_html += "<tbody class='text-rtd-text'>"
    for row in class_rows:
        class_html += f"<tr class='border-b border-gray-200 hover:bg-gray-50'><td class='py-3 px-4 font-semibold'>{row['label']}</td><td class='py-3 px-4 text-rtd-accent font-bold'>{row['val']}</td><td class='py-3 px-4'>{row['avg']}</td><td class='py-3 px-4 text-gray-500 font-bold'>{row['pct']}</td></tr>"
    class_html += f"<tr class='border-b border-gray-200 hover:bg-gray-50'><td class='py-3 px-4 font-semibold text-rtd-secondary'>Hardest Planet Detected</td><td class='py-3 px-4 font-bold'>{hardest_link}</td><td class='py-3 px-4 text-sm'>{hardest_rec_str}</td><td class='py-3 px-4 text-gray-500 font-bold'>{hardest_rank} Hardest</td></tr>"
    class_html += f"<tr class='border-b border-gray-200 hover:bg-gray-50'><td class='py-3 px-4 font-semibold text-rtd-secondary'>Easiest Planet Missed</td><td class='py-3 px-4 font-bold'>{easiest_link}</td><td class='py-3 px-4 text-sm'>{easiest_rec_str}</td><td class='py-3 px-4 text-gray-500 font-bold'>{easiest_rank} Easiest</td></tr>"
    class_html += "</tbody></table>"
    with open(local_assets_dir / "classification_metrics_table.html", "w") as f:
        f.write(class_html)

    # ── 2. Build Planet Accuracy Metrics Table ──
    accuracy_rows = [
        {"label": "Mass Ratio (q) Mean Symmetric Fractional Difference (log10)", "val": fmt_val(team_metrics["q_log10_fractional_error"], is_pct=True), "avg": fmt_val(cohort_avg.get("q_log10_fractional_error"), is_pct=True), "pct": get_percentile("q_log10_fractional_error", team_metrics["q_log10_fractional_error"], False)},
        {"label": "Einstein Time (tE) Mean Symmetric Fractional Difference (log10)", "val": fmt_val(team_metrics["te_log10_fractional_error"], is_pct=True), "avg": fmt_val(cohort_avg.get("te_log10_fractional_error"), is_pct=True), "pct": get_percentile("te_log10_fractional_error", team_metrics["te_log10_fractional_error"], False)},
        {"label": "Finite-Source Radius (rho) Mean Symmetric Fractional Difference (log10)", "val": fmt_val(team_metrics["rho_log10_fractional_error"], is_pct=True), "avg": fmt_val(cohort_avg.get("rho_log10_fractional_error"), is_pct=True), "pct": get_percentile("rho_log10_fractional_error", team_metrics["rho_log10_fractional_error"], False)},
        {"label": "Impact Parameter (u0) Mean Abs Error (MAE)", "val": fmt_val(team_metrics.get("u0_mae")), "avg": fmt_val(cohort_avg.get("u0_mae")), "pct": get_percentile("u0_mae", team_metrics.get("u0_mae"), False)},
        {"label": "Time of Peak (t0) Mean Abs Error (MAE)", "val": fmt_val(team_metrics.get("t0_mae")), "avg": fmt_val(cohort_avg.get("t0_mae")), "pct": get_percentile("t0_mae", team_metrics.get("t0_mae"), False)},
        {"label": "Physical Planets Modeled", "val": fmt_val(team_metrics["phys_planets"], is_int=True), "avg": fmt_val(cohort_avg.get("phys_planets"), is_int=True), "pct": get_percentile("phys_planets", team_metrics["phys_planets"], True)},
        {"label": "Solutions with Physical Params (mass+dist)", "val": fmt_val(team_metrics.get("phys_sol_count"), is_int=True), "avg": fmt_val(cohort_avg.get("phys_sol_count"), is_int=True), "pct": get_percentile("phys_sol_count", team_metrics.get("phys_sol_count"), True)},
        {"label": "Physical Parameter Coverage", "val": fmt_val(team_metrics.get("phys_sol_pct"), is_pct=True), "avg": fmt_val(cohort_avg.get("phys_sol_pct"), is_pct=True), "pct": get_percentile("phys_sol_pct", team_metrics.get("phys_sol_pct"), True)},
        {"label": "Planet Mass Mean Error (MAPE)", "val": fmt_val(team_metrics["mass_mape"], is_pct=True), "avg": fmt_val(cohort_avg.get("mass_mape"), is_pct=True), "pct": get_percentile("mass_mape", team_metrics["mass_mape"], False)},
        {"label": "Lens Distance Mean Error (MAPE)", "val": fmt_val(team_metrics["dl_mape"], is_pct=True), "avg": fmt_val(cohort_avg.get("dl_mape"), is_pct=True), "pct": get_percentile("dl_mape", team_metrics["dl_mape"], False)},
    ]
    accuracy_html = "<table class='w-full text-left table-auto border-collapse mt-4 mb-4'>"
    accuracy_html += "<thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'><tr><th class='py-3 px-4'>Metric</th><th class='py-3 px-4'>Team Submission</th><th class='py-3 px-4'>Cohort Mean</th><th class='py-3 px-4'>Cohort Percentile</th></tr></thead>"
    accuracy_html += "<tbody class='text-rtd-text'>"
    for row in accuracy_rows:
        accuracy_html += f"<tr class='border-b border-gray-200 hover:bg-gray-50'><td class='py-3 px-4 font-semibold'>{row['label']}</td><td class='py-3 px-4 text-rtd-accent font-bold'>{row['val']}</td><td class='py-3 px-4'>{row['avg']}</td><td class='py-3 px-4 text-gray-500 font-bold'>{row['pct']}</td></tr>"
    accuracy_html += "</tbody></table>"
    with open(local_assets_dir / "planet_metrics_table.html", "w") as f:
        f.write(accuracy_html)

    # ── 3. Build Modelling Accuracy Metrics Table ──
    modelling_rows = [
        {"label": "Binary Lens Separation (s) Symmetric Fractional Difference (log10)", "val": fmt_val(team_metrics.get("bl_s_log10_fractional_error"), is_pct=True), "avg": fmt_val(cohort_avg.get("bl_s_log10_fractional_error"), is_pct=True), "pct": get_percentile("bl_s_log10_fractional_error", team_metrics.get("bl_s_log10_fractional_error"), False)},
        {"label": "Binary Lens Trajectory Angle (α) Error", "val": fmt_val(team_metrics.get("bl_alpha_mae"), is_deg=True), "avg": fmt_val(cohort_avg.get("bl_alpha_mae"), is_deg=True), "pct": get_percentile("bl_alpha_mae", team_metrics.get("bl_alpha_mae"), False)},
        {"label": "Binary Source Separation (s_source) Symmetric Fractional Difference (log10)", "val": fmt_val(team_metrics.get("bs_s_log10_fractional_error"), is_pct=True), "avg": fmt_val(cohort_avg.get("bs_s_log10_fractional_error"), is_pct=True), "pct": get_percentile("bs_s_log10_fractional_error", team_metrics.get("bs_s_log10_fractional_error"), False)},
        {"label": "Binary Source Angle (α_source) Error", "val": fmt_val(team_metrics.get("bs_alpha_mae"), is_deg=True), "avg": fmt_val(cohort_avg.get("bs_alpha_mae"), is_deg=True), "pct": get_percentile("bs_alpha_mae", team_metrics.get("bs_alpha_mae"), False)},
        {"label": "Binary Source Flux Ratio Error", "val": fmt_val(team_metrics.get("bs_flux_ratio_mape"), is_pct=True), "avg": fmt_val(cohort_avg.get("bs_flux_ratio_mape"), is_pct=True), "pct": get_percentile("bs_flux_ratio_mape", team_metrics.get("bs_flux_ratio_mape"), False)},
    ]
    m_html = "<table class='w-full text-left table-auto border-collapse mt-4 mb-4'>"
    m_html += "<thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'><tr><th class='py-3 px-4'>Metric</th><th class='py-3 px-4'>Team Submission</th><th class='py-3 px-4'>Cohort Mean</th><th class='py-3 px-4'>Cohort Percentile</th></tr></thead>"
    m_html += "<tbody class='text-rtd-text'>"
    for row in modelling_rows:
        m_html += f"<tr class='border-b border-gray-200 hover:bg-gray-50'><td class='py-3 px-4 font-semibold'>{row['label']}</td><td class='py-3 px-4 text-rtd-accent font-bold'>{row['val']}</td><td class='py-3 px-4'>{row['avg']}</td><td class='py-3 px-4 text-gray-500 font-bold'>{row['pct']}</td></tr>"
    m_html += "</tbody></table>"
    with open(local_assets_dir / "modelling_metrics_table.html", "w") as f:
        f.write(m_html)

    # ── 4. Build Efficiency Metrics Table ──
    eff_rows = [
        {"label": "Planets Reclaimed / CPU Hr", "val": fmt_val(team_metrics.get("planets_per_cpu")), "avg": fmt_val(cohort_avg.get("planets_per_cpu")), "pct": get_percentile("planets_per_cpu", team_metrics.get("planets_per_cpu"), True)},
        {"label": "Total CPU Cost", "val": fmt_val(team_cpu, is_int=True) + " CPU Hours", "avg": fmt_val(cohort_avg.get("cpu_hours"), is_int=True) + " CPU Hours" if cohort_avg.get("cpu_hours") is not None else "N/A", "pct": "N/A"},
    ]
    eff_html = "<table class='w-full text-left table-auto border-collapse mt-4 mb-4'>"
    eff_html += "<thead class='bg-rtd-primary text-rtd-secondary uppercase text-sm'><tr><th class='py-3 px-4'>Metric</th><th class='py-3 px-4'>Team Submission</th><th class='py-3 px-4'>Cohort Mean</th><th class='py-3 px-4'>Cohort Percentile</th></tr></thead>"
    eff_html += "<tbody class='text-rtd-text'>"
    for row in eff_rows:
        eff_html += f"<tr class='border-b border-gray-200 hover:bg-gray-50'><td class='py-3 px-4 font-semibold'>{row['label']}</td><td class='py-3 px-4 text-rtd-accent font-bold'>{row['val']}</td><td class='py-3 px-4'>{row['avg']}</td><td class='py-3 px-4 text-gray-500 font-bold'>{row['pct']}</td></tr>"
    eff_html += "</tbody></table>"
    with open(local_assets_dir / "efficiency_metrics_table.html", "w") as f:
        f.write(eff_html)

def get_flux_ratio(lc_file):
    """Parse source fluxes from light curve header and return flux ratio (F_S2 / F_S1)."""
    fs1 = None
    fs2 = None
    try:
        with open(lc_file, "r") as f:
            for line in f:
                if line.startswith("#fs:"):
                    fs1 = [float(x) for x in line.split()[1:]]
                elif line.startswith("#fs2:"):
                    fs2 = [float(x) for x in line.split()[1:]]
                if fs1 is not None and fs2 is not None:
                    break
        if fs1 and fs2 and len(fs1) > 0 and len(fs2) > 0 and fs1[0] > 0:
            return fs2[0] / fs1[0]
    except Exception:
        pass
    return 0.0

def generate_comparison_metrics(project_path, data_dir, local_assets_dir, tier="beginner", force=False):
    """Pre-calculate intrinsic event signal strength and truth classifications."""
    print("Generating event comparison metrics...")
    if not evaluator_truth_available(tier):
        print("Trusted truth data is unavailable for this tier. Skipping event comparison metrics.")
        return
    metrics_path = local_assets_dir / "event_comparison_metrics.json"
    if metrics_path.exists() and not force:
        print(f"  Reusing cached event comparison metrics: {metrics_path}")
        return
    try:
        evaluation_data = resolve_evaluation_data(data_dir, tier)
        truth_records = load_truth_records(evaluation_data)
        truth_map = load_truth_mapping(evaluation_data, truth_records)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Truth data unavailable. Skipping event comparison metrics: {exc}")
        return

    metrics = {}
    for _, row in truth_records.iterrows():
        eid = row["anon_id"]
        pspl_dchi2 = None
        flat_dchi2 = None
        truth_chi2 = None

        lc_file = find_lightcurve_file(evaluation_data, row)
        if lc_file:
            try:
                df_lc = pd.read_csv(lc_file, sep=r"\s+", comment="#")
                flux = df_lc["measured_relative_flux"].values
                err = df_lc["measured_relative_flux_error"].values
                pspl_fit = df_lc["best_single_lens_fit"].values
                true_f = df_lc["true_relative_flux"].values
                chi2_truth = np.sum(((flux - true_f) / err) ** 2)
                chi2_pspl = np.sum(((flux - pspl_fit) / err) ** 2)
                median_flux = np.median(flux)
                chi2_flat = np.sum(((flux - median_flux) / err) ** 2)
                truth_chi2 = float(chi2_truth)
                pspl_dchi2 = float(chi2_pspl - chi2_truth)
                flat_dchi2 = float(chi2_flat - chi2_truth)
            except Exception:
                pass

        t_type = truth_map.get(eid, row.get("truth_model") or "1S1L")
        if tier == "beginner" and pspl_dchi2 is not None and pspl_dchi2 >= 160.0:
            if t_type == "1S1L":
                t_type = "1S2L"
            elif t_type == "2S1L":
                t_type = "2S2L"

        truth = build_truth_parameters(row)
        t_params = None
        if all(truth.get(key) is not None and not pd.isna(truth.get(key)) for key in ("t0", "u0", "te")):
            t_params = {
                "t0": float(truth["t0"]),
                "u0": float(truth["u0"]),
                "tE": float(truth["te"]),
            }
            for key in ("ra", "dec"):
                value = row.get(f"{key}_deg")
                if value is not None and not pd.isna(value):
                    t_params[key] = float(value)
            if truth.get("alpha") is not None and not pd.isna(truth["alpha"]):
                t_params["alpha"] = np.radians(float(truth["alpha"]))
            for key in ("rho", "piEN", "piEE"):
                value = truth.get(key)
                if value is not None and not pd.isna(value) and (key == "rho" or float(value) != 0):
                    t_params[key] = float(value)
            if is_lens_model(t_type):
                for output_key, truth_key in (("s", "Planet_s"), ("q", "q")):
                    value = truth.get(truth_key)
                    if value is not None and not pd.isna(value):
                        t_params[output_key] = float(value)
                t_params["lens_candidates"] = truth.get("lens_candidates", [])
            if is_source_model(t_type):
                for output_key in ("t0_source2", "u0_source2"):
                    value = truth.get(output_key)
                    if value is not None and not pd.isna(value):
                        t_params[output_key] = float(value)
                value = truth.get("Source2_s")
                if value is not None and not pd.isna(value):
                    t_params["s_source"] = float(value)
                value = truth.get("Source2_alpha")
                if value is not None and not pd.isna(value):
                    t_params["alpha_source"] = np.radians(float(value))
                value = truth.get("Obs_0_fs2ofs1")
                if value is not None and not pd.isna(value):
                    t_params["flux_ratio"] = float(value)

        metrics[eid] = {
            "truth_chi2": truth_chi2,
            "pspl_dchi2": pspl_dchi2,
            "flat_dchi2": flat_dchi2,
            "truth_model": t_type,
            "truth_parameters": t_params,
            "lens_candidates": truth.get("lens_candidates", []),
            "Planet_s": truth.get("Planet_s"),
            "Planet_q": truth.get("q"),
            "alpha": np.radians(float(truth["alpha"])) if truth.get("alpha") is not None and not pd.isna(truth["alpha"]) else None,
            "Source2_s": truth.get("Source2_s"),
            "Source2_alpha": truth.get("Source2_alpha"),
            "Obs_0_fs2ofs1": truth.get("Obs_0_fs2ofs1"),
            "mass": truth.get("mass"),
            "dl": truth.get("dl"),
        }

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

def generate_precision_metrics(project_path, local_assets_dir):
    """Generate precision metrics: solution confidence, degeneracy, and parameter uncertainties."""
    print("Generating precision metrics...")
    events_dir = project_path / "events"
    preds = get_team_predictions(events_dir)
    if not preds:
        return

    # ── Subsection 1: Solution Confidence & Degeneracy ──────────────────────
    confidence_scores = []
    n_solutions_list = []
    any_real_probs = False

    for eid, sols in preds.items():
        if not sols:
            continue
        confidence_scores.append(max(s["prob"] for s in sols))
        n_solutions_list.append(len(sols))
        if not sols[0].get("has_equal_weight", True):
            any_real_probs = True

    n_events = len(confidence_scores)
    mean_confidence = float(np.mean(confidence_scores)) * 100 if confidence_scores else None
    degeneracy_rate = (
        sum(1 for n in n_solutions_list if n > 1) / len(n_solutions_list) * 100
        if n_solutions_list else 0.0
    )
    mean_n_solutions = float(np.mean(n_solutions_list)) if n_solutions_list else None
    total_solutions = int(sum(n_solutions_list))

    # Confidence histogram (Bokeh)
    if confidence_scores:
        bins = np.linspace(0.0, 1.0, 21)
        hist, edges = np.histogram(confidence_scores, bins=bins)
        p_conf = figure(
            title="Solution Confidence Distribution",
            x_axis_label="Max Solution Probability per Event",
            y_axis_label="Number of Events",
            height=300, width=520,
            tools="pan,wheel_zoom,reset,save",
        )
        p_conf.quad(
            top=hist, bottom=0, left=edges[:-1], right=edges[1:],
            fill_color=MY_PALETTE[0], line_color="white", alpha=0.85,
        )
        p_conf.add_tools(HoverTool(tooltips=[
            ("Confidence Range", "@left{0.00} – @right{0.00}"),
            ("Events", "@top"),
        ]))
        p_conf.xaxis.axis_label_text_font_size = "11px"
        p_conf.yaxis.axis_label_text_font_size = "11px"
        script, div = components(p_conf)
        with open(local_assets_dir / "confidence_hist.html", "w") as f:
            f.write(f"{script}\n{div}")

    # ── Subsection 2: Parameter Uncertainties ────────────────────────────────
    total_sol_count = 0
    uncert_sol_count = 0
    posterior_sol_count = 0
    uncertainty_methods = []
    confidence_levels = []
    per_param_frac_uncerts = {}   # param -> [fractional uncertainty values]

    KEY_PARAMS = [
        "tE", "u0", "t0", "q", "s", "alpha",
        "t0_source2", "u0_source2", "flux_ratio",
        "planet_mass", "lens_distance", "piEN", "piEE"
    ]

    for eid, sols in preds.items():
        for s in sols:
            total_sol_count += 1
            uncerts = s.get("param_uncerts") or {}
            if s.get("posterior_path"):
                posterior_sol_count += 1
            if uncerts:
                uncert_sol_count += 1
                if s.get("uncertainty_method"):
                    uncertainty_methods.append(s["uncertainty_method"])
                if s.get("confidence_level"):
                    confidence_levels.append(s["confidence_level"])
                params = s.get("params") or {}
                for param in KEY_PARAMS:
                    val = params.get(param)
                    sigma = uncerts.get(param)
                    if val is not None and sigma is not None and abs(val) > 0:
                        if isinstance(sigma, (list, tuple)):
                            sigma_val = sum(sigma) / len(sigma)
                        else:
                            sigma_val = sigma
                        per_param_frac_uncerts.setdefault(param, []).append(
                            abs(sigma_val / val)
                        )

    uncertainty_coverage = (
        uncert_sol_count / total_sol_count * 100 if total_sol_count > 0 else 0.0
    )

    # Median fractional uncertainties per parameter
    median_frac_uncerts = {}
    for param, vals in per_param_frac_uncerts.items():
        if vals:
            sorted_vals = sorted(vals)
            mid = len(sorted_vals) // 2
            if len(sorted_vals) % 2 == 0:
                median_frac_uncerts[param] = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
            else:
                median_frac_uncerts[param] = sorted_vals[mid]

    # Most common uncertainty method
    most_common_method = None
    if uncertainty_methods:
        method_counts = {}
        for m in uncertainty_methods:
            method_counts[m] = method_counts.get(m, 0) + 1
        most_common_method = max(method_counts, key=method_counts.get)

    most_common_cl = None
    if confidence_levels:
        cl_counts = {}
        for cl in confidence_levels:
            cl_counts[cl] = cl_counts.get(cl, 0) + 1
        most_common_cl = max(cl_counts, key=cl_counts.get)

    posterior_coverage = (
        posterior_sol_count / total_sol_count * 100 if total_sol_count > 0 else 0.0
    )

    # ── Parameter-specific Fractional Uncertainty Distribution Plots ─────────────────────────────
    colors = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#AA3377", "#44AA99", "#88CCEE", "#BBBBBB"]
    param_labels = {
        "tE": "Einstein Time (tE)",
        "u0": "Impact Parameter (u0)",
        "t0": "Peak Time (t0)",
        "q": "Mass Ratio (q)",
        "s": "Separation (s)",
        "alpha": "Trajectory Angle (α)",
        "t0_source2": "Binary Source Peak Time (t0_source2)",
        "u0_source2": "Binary Source Impact Parameter (u0_source2)",
        "flux_ratio": "Binary Source Flux Ratio",
        "planet_mass": "Planet Mass (M_earth)",
        "lens_distance": "Lens Distance (D_L)",
        "piEN": "Parallax Component North (piEN)",
        "piEE": "Parallax Component East (piEE)",
    }

    # Delete the old combined uncertainties file if it exists to clean up
    old_file = local_assets_dir / "uncertainties_hist.html"
    if old_file.exists():
        try:
            old_file.unlink()
        except Exception:
            pass

    for idx, param in enumerate(KEY_PARAMS):
        vals = per_param_frac_uncerts.get(param, [])
        if not vals:
            continue
        log_vals = [np.log10(v) for v in vals if v > 0]
        if not log_vals:
            continue

        p_unc = figure(
            title=f"{param_labels.get(param, param)} Uncertainty Distribution",
            x_axis_label="log10( σ / |x| )",
            y_axis_label="Number of Solutions",
            height=260,
            sizing_mode="stretch_width",
            tools="pan,wheel_zoom,reset,save",
        )
        bins = np.linspace(min(log_vals) - 0.1, max(log_vals) + 0.1, 26)
        hist, edges = np.histogram(log_vals, bins=bins)
        p_unc.quad(
            top=hist, bottom=0, left=edges[:-1], right=edges[1:],
            fill_color=colors[idx % len(colors)], line_color="white", alpha=0.7
        )
        p_unc.xaxis.axis_label_text_font_size = "10px"
        p_unc.yaxis.axis_label_text_font_size = "10px"
        p_unc.title.text_font_size = "11px"

        script_unc, div_unc = components(p_unc)
        with open(local_assets_dir / f"uncertainties_{param}_hist.html", "w") as f:
            f.write(f"{script_unc}\n{div_unc}")


    phys_sol_count = 0
    total_active_sol_count = 0
    for eid, sols in preds.items():
        for s in sols:
            total_active_sol_count += 1
            if s.get("mass") is not None and s.get("dl") is not None:
                phys_sol_count += 1
    phys_sol_pct = float(phys_sol_count / total_active_sol_count * 100) if total_active_sol_count > 0 else 0.0

    stats = {
        "n_events": n_events,
        "total_solutions": total_solutions,
        "mean_confidence": mean_confidence,
        "degeneracy_rate": degeneracy_rate,
        "mean_n_solutions": mean_n_solutions,
        "any_real_probs": any_real_probs,
        "uncertainty_coverage": uncertainty_coverage,
        "uncert_sol_count": uncert_sol_count,
        "posterior_coverage": posterior_coverage,
        "posterior_sol_count": posterior_sol_count,
        "total_sol_count": total_sol_count,
        "most_common_method": most_common_method,
        "most_common_confidence_level": most_common_cl,
        "median_frac_uncerts": median_frac_uncerts,
        "phys_sol_count": phys_sol_count,
        "phys_sol_pct": phys_sol_pct,
    }
    with open(local_assets_dir / "precision_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  Precision stats: confidence={mean_confidence:.1f}%, degeneracy={degeneracy_rate:.1f}%, uncertainty_coverage={uncertainty_coverage:.1f}%, posterior_coverage={posterior_coverage:.1f}%")
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate interactive plots for a submission.")
    parser.add_argument("project_path", type=str, help="Path to the submission project folder.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to ground truth data directory (defaults to the cohort's shared evaluator_data directory).",
    )
    parser.add_argument("--tier", choices=["beginner", "experienced"], default="beginner")
    args = parser.parse_args()

    proj = Path(args.project_path).resolve()
    data = (
        Path(args.data_dir).resolve()
        if args.data_dir
        else default_evaluation_data_dir(proj.parent, args.tier)
    )
    evaluation_data = resolve_evaluation_data(data, args.tier)

    # Shared lightcurves
    shared_out = (proj.parent.parent / f"interactive_plots_{args.tier}").resolve()
    shared_out.mkdir(parents=True, exist_ok=True)

    # Local assets folder (unique to THIS submission)
    local_assets = proj / "dossier" / "assets"
    local_assets.mkdir(parents=True, exist_ok=True)

    generate_lightcurve_plots(proj, evaluation_data.parquet_path, shared_out)
    generate_confusion_matrix(proj, data, local_assets, tier=args.tier)
    generate_planet_metrics(proj, data, local_assets, tier=args.tier)
    generate_comparison_metrics(proj, data, local_assets, tier=args.tier)
    generate_precision_metrics(proj, local_assets)

    print(f"\nDone!")
    print(f"  Shared lightcurves in: {shared_out}")
    print(f"  Submission-specific confusion matrix and metrics in: {local_assets}")
