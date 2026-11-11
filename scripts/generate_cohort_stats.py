import os
import json
import math
import pandas as pd
import numpy as np
import argparse
from collections import Counter
from pathlib import Path
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, FactorRange, HoverTool, LinearColorMapper
from bokeh.embed import components
from bokeh.transform import transform

from microlens_submit.dossier.evaluation_data import (
    build_truth_parameters,
    default_evaluation_data_dir,
    is_lens_model,
    is_planet_model,
    is_source_model,
    log10_error_to_fractional_difference,
    load_truth_mapping,
    load_truth_records,
    match_truth_lens_component,
    model_types_for_tier,
    parameter_comparison_error,
    resolve_evaluation_data,
)
from microlens_submit.dossier.anonymization import (
    anonymized_team_name,
    load_team_name_lookup,
)

MY_PALETTE = ['#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE', '#AA3377', '#BBBBBB']

def calculate_dchi2(file_path):
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
    pattern = f"*_{subrun}_*_{event_id}.det.lc"
    matches = list(lc_dir.glob(pattern))
    if not matches:
        pattern = f"*_{subrun}_*_{event_id}.all.lc"
        matches = list(lc_dir.glob(pattern))
    return matches[0] if matches else None

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

            param_uncerts = s.get("parameter_uncertainties") or {}
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
                "param_uncerts": param_uncerts,
                "uncertainty_method": uncertainty_method,
                "confidence_level": confidence_level,
                "posterior_path": posterior_path,
                "params": params,
            })
        preds[event_id] = parsed_sols
    return preds

def compute_team_f1_scores(preds, truth_map, true_planets, truth_types=None):
    """Compute 4-class macro-F1 and planet-binary F1 for a single team's predictions.

    Returns a dict with keys: 'macro_f1', 'planet_f1', 'classification_composite'.
    """
    # --- 4-class macro-F1 (probability-weighted confusion matrix) ---
    truth_types = truth_types or model_types_for_tier("beginner", truth_map.values())
    # TP_c, FP_c, FN_c per class
    class_tp = {c: 0.0 for c in truth_types}
    class_fp = {c: 0.0 for c in truth_types}
    class_fn = {c: 0.0 for c in truth_types}

    for event_id, truth_class in truth_map.items():
        if truth_class not in truth_types:
            continue
        if event_id in preds:
            for sol in preds[event_id]:
                s_class = sol["model_type"]
                p = sol["prob"]
                if s_class not in truth_types:
                    continue
                if s_class == truth_class:
                    class_tp[truth_class] += p
                else:
                    class_fp[s_class] += p
                    class_fn[truth_class] += p
        else:
            # No submission counts as a miss (FN) for the true class
            class_fn[truth_class] += 1.0

    f1_scores = []
    for c in truth_types:
        tp_c = class_tp[c]
        fp_c = class_fp[c]
        fn_c = class_fn[c]
        prec = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0.0
        rec = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        f1_scores.append(f1)
    macro_f1 = float(np.mean(f1_scores))

    # --- Planet-binary F1 ---
    # Use the already-computed TP/FP/FN planet counts from the submission
    # We compute them here from preds so this is self-contained.
    tp_p = 0.0
    fp_p = 0.0
    fn_p = 0.0
    for event_id, sols in preds.items():
        planet_prob = sum(s["prob"] for s in sols if s["is_planet"])
        if event_id in true_planets:
            tp_p += planet_prob
            fn_p += (1.0 - planet_prob)
        else:
            fp_p += planet_prob

    planet_f1_denom = 2 * tp_p + fp_p + fn_p
    planet_f1 = float(2 * tp_p / planet_f1_denom) if planet_f1_denom > 0 else 0.0

    composite = (macro_f1 + planet_f1) / 2.0

    return {
        "macro_f1": macro_f1,
        "planet_f1": planet_f1,
        "classification_composite": composite,
    }


def _generate_experienced_submitted_event_report(cohort_dir, output_dir, team_name_lookup):
    """Generate experienced-tier submission counts without hidden truths."""
    all_counts = Counter()
    team_metrics = {}

    for team_dir in cohort_dir.iterdir():
        if not team_dir.is_dir() or not (team_dir / "submission.json").exists():
            continue
        preds = get_team_predictions(team_dir / "events")
        counts = Counter()
        for solutions in preds.values():
            if solutions:
                primary = max(solutions, key=lambda solution: solution["prob"])
                counts[primary["model_type"]] += 1
        all_counts.update(counts)
        team_name = anonymized_team_name(team_dir, team_name_lookup)
        team_metrics[team_name] = {
            "submitted_events": sum(counts.values()),
            "model_counts": dict(sorted(counts.items())),
        }

    labels = sorted(all_counts) or ["No submitted events"]
    values = [all_counts[label] for label in labels] if all_counts else [0]
    source = ColumnDataSource({"model": labels, "count": values})
    plot = figure(
        title="Cohort Submitted Event Model Distribution",
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

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "cohort_confusion_matrix.html", "w") as handle:
        handle.write(f"{script}\n{div}")
    with open(output_dir / "cohort_metrics.json", "w") as handle:
        json.dump(
            {
                "teams": team_metrics,
                "cohort_avg": {},
                "cohort_summary": {
                    "num_teams": len(team_metrics),
                    "mean_progress": None,
                },
                "submitted_event_counts": dict(sorted(all_counts.items())),
                "event_recovery": {},
                "event_consensus": {},
            },
            handle,
            indent=2,
        )
    print(f"Cohort submitted-event histogram saved to {output_dir / 'cohort_confusion_matrix.html'}")
    print(f"Cohort submission counts saved to {output_dir / 'cohort_metrics.json'}")


def generate_cohort_confusion_matrix(cohort_dir, data_dir, output_dir, tier="beginner"):
    cohort_dir = Path(cohort_dir)
    team_name_lookup = load_team_name_lookup(cohort_dir)
    experienced_tier = str(tier).lower() == "experienced"
    print(f"Generating aggregate confusion matrix for cohort in {cohort_dir.name}...")
    if experienced_tier:
        _generate_experienced_submitted_event_report(cohort_dir, output_dir, team_name_lookup)

    try:
        evaluation_data = resolve_evaluation_data(data_dir, tier)
        truth_records = load_truth_records(evaluation_data)
        truth_map = load_truth_mapping(evaluation_data, truth_records)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Truth data unavailable. Skipping cohort statistics: {exc}")
        return
    if not truth_map:
        return

    def get_best_transform_idx(pairs):
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
        t_params = build_truth_parameters(row)
        if bool(row.get("is_planet")) or is_planet_model(t_type, t_params.get("q")):
            true_planets.add(eid)
        true_params[eid] = t_params

    all_team_preds = {}
    cohort_submissions = {}; completion_rates = []; total_possible_events = len(truth_map)
    completion_rates = []

    # Get total number of possible events to calculate completion rate
    total_possible_events = len(truth_map)

    for team_dir in cohort_dir.iterdir():
        if not team_dir.is_dir() or not (team_dir / "submission.json").exists(): continue
        team_name = anonymized_team_name(team_dir, team_name_lookup)
        events_dir = team_dir / "events"
        if not events_dir.exists(): continue

        preds = get_team_predictions(events_dir, true_params=true_params)
        all_team_preds[team_name] = preds

        # Calculate completion rate for this team
        if total_possible_events > 0:
            completion_rates.append(len(preds) / total_possible_events)

        cohort_submissions[team_name] = {}
        for eid, sols in preds.items():
            for s in sols:
                m = s["model_type"]
                cohort_submissions[team_name].setdefault(eid, {})
                cohort_submissions[team_name][eid][m] = cohort_submissions[team_name][eid].get(m, 0.0) + s["prob"]

    if not cohort_submissions: return

    event_recovery = {}
    for eid in true_planets:
        probs = []
        for team_name, preds in all_team_preds.items():
            if eid in preds:
                planet_prob = sum(s["prob"] for s in preds[eid] if s["is_planet"])
                probs.append(planet_prob)
            else:
                probs.append(0.0)
        event_recovery[eid] = float(np.mean(probs))

    team_metrics = {}
    for team_name, preds in all_team_preds.items():
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

        phys_planets = 0.0
        phys_sol_count = 0
        total_active_sol_count = 0

        hardest_det_eid = None
        hardest_det_rec = 1.0
        easiest_miss_eid = None
        easiest_miss_rec = 0.0

        # Pass 1: Find best global transformations for trajectory angles
        bl_alpha_pairs = []
        bs_alpha_pairs = []
        for eid, sols in preds.items():
            t_p = true_params.get(eid)
            t_type = truth_map.get(eid)
            if t_p:
                for s in sols:
                    if is_lens_model(t_type) and is_lens_model(s["model_type"]):
                        if s["alpha"] is not None and pd.notna(t_p["alpha"]):
                            # s["alpha"] is submitted (stored in radians) -> convert to degrees
                            # t_p["alpha"] is truth from GULLS HDF5 -> already in degrees
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

        # Accumulate modelling parameter errors
        bl_s_log10_fractional_error_sum, bl_s_weight = 0.0, 0.0
        bl_alpha_err_sum, bl_alpha_weight = 0.0, 0.0
        bs_s_log10_fractional_error_sum, bs_s_weight = 0.0, 0.0
        bs_alpha_err_sum, bs_alpha_weight = 0.0, 0.0
        bs_flux_err_sum, bs_flux_weight = 0.0, 0.0

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

                    # Accumulate modelling parameter errors
                    if is_lens_model(t_type) and is_lens_model(s["model_type"]):
                        if lens_component is not None and s["s"] is not None:
                            bl_s_error = parameter_comparison_error(s["s"], lens_component["s"], "s")
                            if bl_s_error is not None:
                                bl_s_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(bl_s_error)
                                bl_s_weight += prob
                        if s["alpha"] is not None and pd.notna(t_p["alpha"]):
                            m_val = math.degrees(s["alpha"]) % 360.0
                            # t_p["alpha"] from GULLS HDF5 is in degrees already
                            t_val = t_p["alpha"] % 360.0
                            if bl_best_idx == 0:
                                t_equiv = t_val
                            elif bl_best_idx == 1:
                                t_equiv = (t_val + 180.0) % 360.0
                            elif bl_best_idx == 2:
                                t_equiv = (360.0 - t_val) % 360.0
                            else:
                                t_equiv = (180.0 - t_val) % 360.0
                            diff = abs(m_val - t_equiv)
                            diff = min(diff, 360.0 - diff)
                            bl_alpha_err_sum += prob * diff
                            bl_alpha_weight += prob

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
                            modeled_s = math.sqrt(dx**2 + dy**2)
                            if is_lens_model(s["model_type"]) and s.get("alpha") is not None:
                                alpha_offset = math.degrees(s["alpha"])
                            else:
                                alpha_offset = t_p.get("alpha") if (t_p and t_p.get("alpha") is not None) else 0.0
                            modeled_alpha = (math.degrees(math.atan2(dy, -dx)) + alpha_offset) % 360.0

                            if pd.notna(t_p["Source2_s"]):
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
                                diff = abs(m_val - t_equiv)
                                diff = min(diff, 360.0 - diff)
                                bs_alpha_err_sum += prob * diff
                                bs_alpha_weight += prob

                        if s["flux_ratio"] is not None and s["flux_ratio"] > 0 and pd.notna(t_p["Obs_0_fs2ofs1"]):
                            raw_fr = s["flux_ratio"]
                            s_flux = (1.0 / raw_fr) if raw_fr > 1.0 else raw_fr
                            truth_fr = t_p["Obs_0_fs2ofs1"]
                            truth_fr_norm = (1.0 / truth_fr) if truth_fr > 1.0 else truth_fr
                            bs_flux_err_sum += prob * abs(truth_fr_norm - s_flux) / truth_fr_norm
                            bs_flux_weight += prob

            if t_p:
                for s in sols:
                    prob = s["prob"]
                    is_swapped = False
                    if is_source_model(t_type) and is_source_model(s["model_type"]):
                        if (s["t0_source2"] is not None and t_p.get("t0_source2") is not None and
                            s["t0"] is not None and t_p.get("t0") is not None):
                            diff_unswapped = abs(s["t0"] - t_p["t0"]) + abs(s["t0_source2"] - t_p["t0_source2"])
                            diff_swapped = abs(s["t0"] - t_p["t0_source2"]) + abs(s["t0_source2"] - t_p["t0"])
                            if diff_swapped < diff_unswapped:
                                is_swapped = True

                    u0_truth = t_p["u0_source2"] if is_swapped else t_p["u0"]
                    t0_truth = t_p["t0_source2"] if is_swapped else t_p["t0"]

                    # te, rho, u0, t0 are general parameter comparisons computed for all events
                    if pd.notna(t_p["te"]) and s["te"] is not None:
                        te_error = parameter_comparison_error(s["te"], t_p["te"], "tE")
                        if te_error is not None:
                            te_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(te_error)
                            te_weight += prob
                    if pd.notna(t_p.get("rho")) and s["rho"] is not None:
                        rho_error = parameter_comparison_error(s["rho"], t_p.get("rho"), "rho")
                        if rho_error is not None:
                            rho_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(rho_error)
                            rho_weight += prob
                    if pd.notna(u0_truth) and s["u0"] is not None:
                        u0_err_sum += prob * abs(abs(u0_truth) - abs(s["u0"]))
                        u0_weight += prob
                    if pd.notna(t0_truth) and s["t0"] is not None:
                        t0_err_sum += prob * abs(t0_truth - s["t0"])
                        t0_weight += prob

                    compare_lens_component = lens_component is not None and (
                        tier == "experienced" or (is_true_planet and s["is_planet"])
                    )
                    if compare_lens_component:
                        if s["q"] is not None and pd.notna(lens_component["q"]):
                            q_error = parameter_comparison_error(s["q"], lens_component["q"], "q")
                            if q_error is not None:
                                q_log10_fractional_error_sum += prob * log10_error_to_fractional_difference(q_error)
                                q_weight += prob
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

        eff = tp / team_cpu if team_cpu > 0 else 0

        f1_scores = compute_team_f1_scores(
            preds,
            truth_map,
            true_planets,
            truth_types=model_types_for_tier(tier, truth_map.values()),
        )

        # Calculate precision metrics for this team
        confidence_scores = []
        n_solutions_list = []
        total_sol_count = 0
        uncert_sol_count = 0
        posterior_sol_count = 0

        for eid, sols in preds.items():
            if not sols:
                continue
            confidence_scores.append(max(s["prob"] for s in sols))
            n_solutions_list.append(len(sols))
            for s in sols:
                total_sol_count += 1
                uncerts = s.get("param_uncerts") or {}
                if s.get("posterior_path"):
                    posterior_sol_count += 1
                if uncerts:
                    uncert_sol_count += 1

        mean_confidence = float(np.mean(confidence_scores)) * 100 if confidence_scores else 0.0
        uncertainty_coverage = (
            uncert_sol_count / total_sol_count * 100 if total_sol_count > 0 else 0.0
        )
        posterior_coverage = (
            posterior_sol_count / total_sol_count * 100 if total_sol_count > 0 else 0.0
        )

        precision_composite = 0.5 * (mean_confidence / 100.0) + 0.25 * (uncertainty_coverage / 100.0) + 0.25 * (posterior_coverage / 100.0)

        team_metrics[team_name] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "planets_per_cpu": eff,
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
            "hardest_detected": f"{hardest_det_eid} ({hardest_det_rec*100:.1f}%)" if hardest_det_eid else "None",
            "easiest_missed": f"{easiest_miss_eid} ({easiest_miss_rec*100:.1f}%)" if easiest_miss_eid else "None",
            "hardest_det_rec": hardest_det_rec if hardest_det_eid else None,
            "easiest_miss_rec": easiest_miss_rec if easiest_miss_eid else None,
            "macro_f1": f1_scores["macro_f1"],
            "planet_f1": f1_scores["planet_f1"],
            "classification_composite": f1_scores["classification_composite"],
            "mean_confidence": mean_confidence,
            "uncertainty_coverage": uncertainty_coverage,
            "posterior_coverage": posterior_coverage,
            "precision_composite": precision_composite,
        }
        if experienced_tier:
            for key in ("macro_f1", "planet_f1", "classification_composite"):
                team_metrics[team_name][key] = None

    cohort_avg = {}
    avg_keys = [
        "true_positives", "false_positives", "false_negatives",
        "planets_per_cpu", "q_log10_fractional_error", "te_log10_fractional_error", "rho_log10_fractional_error", "u0_mae", "t0_mae", "phys_planets", "phys_sol_count", "phys_sol_pct",
        "mass_mape", "dl_mape",
        "bl_s_log10_fractional_error", "bl_alpha_mae", "bs_s_log10_fractional_error", "bs_alpha_mae", "bs_flux_ratio_mape",
        "macro_f1", "planet_f1", "classification_composite",
        "mean_confidence", "uncertainty_coverage", "posterior_coverage", "precision_composite",
    ]
    for key in avg_keys:
        vals = [tm[key] for tm in team_metrics.values() if tm.get(key) is not None]
        cohort_avg[key] = float(np.mean(vals)) if vals else None

    # Calculate event-level cohort consensus (most common model)
    event_consensus = {}
    all_events = set()
    for team_subs in cohort_submissions.values():
        all_events.update(team_subs.keys())

    for eid in all_events:
        model_counts = {}
        for team_name, team_subs in cohort_submissions.items():
            if eid in team_subs:
                for m, prob in team_subs[eid].items():
                    model_counts[m] = model_counts.get(m, 0.0) + prob
        if model_counts:
            # Most common model is the one with the highest total probability sum across teams
            most_common = max(model_counts.items(), key=lambda x: x[1])[0]
            event_consensus[eid] = most_common

    output_data = {
        "teams": team_metrics,
        "cohort_avg": cohort_avg,
        "cohort_summary": {
            "num_teams": len(cohort_submissions),
            "mean_progress": float(np.mean(completion_rates) * 100) if completion_rates else 0.0
        },
        "event_recovery": {} if experienced_tier else event_recovery,
        "event_consensus": {} if experienced_tier else event_consensus,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "cohort_metrics.json", "w") as f:
        json.dump(output_data, f, indent=2)

    if experienced_tier:
        print(f"Experienced cohort parameter metrics saved to {output_dir / 'cohort_metrics.json'}")
        return

    truth_types = model_types_for_tier(tier, truth_map.values())
    submitted_types = model_types_for_tier(tier) + ["No Submission"]

    data = []
    for t in truth_types:
        for s in submitted_types:
            count = 0.0
            for event_id, t_type in truth_map.items():
                if t_type == t:
                    for team_name, team_subs in cohort_submissions.items():
                        if event_id in team_subs:
                            count += team_subs[event_id].get(s, 0.0)
                        else:
                            if s == "No Submission": count += 1.0
            data.append({"truth": t, "submitted": s, "count": count})

    df_matrix = pd.DataFrame(data)
    num_teams = len(cohort_submissions)
    df_matrix['col_total'] = df_matrix.groupby('truth')['count'].transform('sum')
    df_matrix['perc'] = (df_matrix['count'] / df_matrix['col_total'].replace(0, 1)) * 100
    df_matrix['mean_count'] = df_matrix['count'] / num_teams
    df_matrix['text'] = df_matrix.apply(lambda r: f"{r['mean_count']:.1f}\n({r['perc']:.1f}%)" if r['col_total'] > 0 else "0", axis=1)

    source = ColumnDataSource(df_matrix)
    from bokeh.palettes import Blues256
    mapper = LinearColorMapper(palette=Blues256[::-1], low=0, high=100)

    p = figure(title=f"Aggregate Cohort Confusion Matrix ({num_teams} Teams)",
               x_range=truth_types, y_range=submitted_types[::-1],
               x_axis_label="Ground Truth",
               y_axis_label="Submitted Model",
               height=450, width=600, toolbar_location=None, tools="")

    p.rect(x="truth", y="submitted", width=1, height=1, source=source,
           line_color="white", fill_color=transform('perc', mapper))

    p.text(x="truth", y="submitted", text="text", source=source,
           text_align="center", text_baseline="middle",
           text_color="black", text_font_style="bold")

    p.add_tools(HoverTool(tooltips=[("Truth", "@truth"), ("Submitted", "@submitted"), ("Mean Count", "@mean_count{0.1f}"), ("Percentage", "@perc{0.1f}%")]))

    script, div = components(p)
    with open(output_dir / "cohort_confusion_matrix.html", "w") as f:
        f.write(f"{script}\n{div}")

    print(f"Cohort confusion matrix saved to {output_dir / 'cohort_confusion_matrix.html'}")
    print(f"Cohort metrics saved to {output_dir / 'cohort_metrics.json'}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate aggregate statistics for a cohort of submissions.")
    parser.add_argument("--cohort-dir", type=str, required=True, help="Directory containing multiple submission folders.")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to ground truth data directory (defaults to the cohort's shared evaluator_data directory).",
    )
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save generated plots (defaults to <cohort-dir>/cohort_analysis).")
    parser.add_argument("--tier", choices=["beginner", "experienced"], default="beginner")
    args = parser.parse_args()

    cohort = Path(args.cohort_dir).resolve()
    data = (
        Path(args.data_dir).resolve()
        if args.data_dir
        else default_evaluation_data_dir(cohort, args.tier)
    )
    out = Path(args.output_dir).resolve() if args.output_dir else cohort / "cohort_analysis"
    generate_cohort_confusion_matrix(cohort, data, out, tier=args.tier)
