"""Tier-specific external data handling for evaluator reports.

The beginner and experienced RMDC26 datasets do not share file names or truth
schemas.  This module presents both datasets through the small canonical schema
used by the evaluator scripts.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import numpy as np
import pandas as pd


SUPPORTED_EVALUATION_TIERS = ("beginner", "experienced")
TRUTH_EVALUATION_TIERS = ("beginner", "experienced")
EVALUATOR_DATA_DIRECTORY_NAME = "evaluator_data"
BASE_MODEL_TYPES = ("1S1L", "1S2L", "2S1L", "2S2L")
EXPERIENCED_MODEL_TYPES = (
    "1S1L",
    "1S2L",
    "1S3L",
    "1S4L",
    "2S1L",
    "2S2L",
    "2S3L",
    "2S4L",
)
LOG10_COMPARISON_PARAMETERS = frozenset({"q", "s", "te", "rho", "s_source"})


def uses_log10_comparison(parameter_name: str) -> bool:
    """Return whether a parameter is compared using absolute log10 residuals."""
    return str(parameter_name or "").lower() in LOG10_COMPARISON_PARAMETERS


def parameter_comparison_error(
    fitted: Any,
    truth: Any,
    parameter_name: str,
) -> Optional[float]:
    """Return a parameter error using the parameter's comparison convention.

    The returned value is ``|log10(fitted) - log10(truth)|`` for positive
    scale parameters (q, s, tE, rho), and the absolute fractional difference
    for other parameters.
    """
    try:
        fitted_value = float(fitted)
        truth_value = float(truth)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(fitted_value) or not math.isfinite(truth_value):
        return None
    if uses_log10_comparison(parameter_name):
        if fitted_value <= 0 or truth_value <= 0:
            return None
        return abs(math.log10(fitted_value) - math.log10(truth_value))
    if truth_value == 0:
        return None
    return abs(fitted_value - truth_value) / abs(truth_value)


def log10_error_to_fractional_difference(log10_error: float) -> float:
    """Convert a symmetric absolute log10 error to a fractional difference."""
    return math.pow(10.0, abs(float(log10_error))) - 1.0


def evaluator_truth_available(tier: str) -> bool:
    """Return whether evaluator reports may use hidden truth data for a tier."""
    return str(tier or "").lower() in TRUTH_EVALUATION_TIERS


def default_evaluation_data_dir(cohort_dir: Path, tier: str) -> Path:
    """Return the standard evaluator-data directory for a cohort.

    Cohorts are expected to live beside the shared ``evaluator_data`` directory::

        rmdc26_submissions/
        |-- beginner/
        |-- experienced/
        `-- evaluator_data/
            |-- beginner/
            `-- experienced/
    """
    tier = str(tier or "").strip().lower()
    if tier not in SUPPORTED_EVALUATION_TIERS:
        raise ValueError(
            f"Unsupported evaluator tier {tier!r}; expected one of "
            f"{', '.join(SUPPORTED_EVALUATION_TIERS)}"
        )
    return Path(cohort_dir).resolve().parent / EVALUATOR_DATA_DIRECTORY_NAME / tier


@dataclass(frozen=True)
class EvaluationData:
    """Resolved external files for one evaluator tier."""

    tier: str
    data_dir: Path
    parquet_path: Path
    mapping_path: Optional[Path]
    truth_path: Optional[Path]
    lightcurve_dir: Optional[Path]
    predictions_path: Optional[Path] = None


def _first_existing(candidates: Iterable[Path]) -> Optional[Path]:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_evaluation_data(
    data_dir: Path,
    tier: str,
    *,
    require_truth: bool = True,
) -> EvaluationData:
    """Resolve tier-specific evaluator inputs below ``data_dir``.

    The experienced distribution currently uses a manifest and nested
    ``selected_lc`` directories, while the beginner distribution uses the
    original mapping file and ``Original Lightcurves``.
    """
    tier = str(tier).lower()
    if tier not in SUPPORTED_EVALUATION_TIERS:
        raise ValueError(
            f"Unsupported evaluator tier {tier!r}; expected one of "
            f"{', '.join(SUPPORTED_EVALUATION_TIERS)}"
        )

    data_dir = Path(data_dir).resolve()
    if tier == "beginner":
        parquet_candidates = [data_dir / "RMDC26_Beginner_Tier.parquet"]
        mapping_candidates = [data_dir / "RMDC26_beginner_tier_w_id.txt"]
        truth_candidates = [data_dir / "RMDC26_Events.out.hdf5"]
        lightcurve_candidates = [data_dir / "Original Lightcurves"]
        prediction_candidates = [
            data_dir / "beginner_tier_predictions.csv",
            data_dir.parent / "beginner_tier_predictions.csv",
        ]
    else:
        parquet_candidates = [
            data_dir / "RMDC26_Experienced_Data.parquet",
            data_dir / "RMDC26_Experienced_Tier.parquet",
        ]
        mapping_candidates = [
            data_dir / "RMDC26_Experienced_Data_name_manifest.csv",
            data_dir / "RMDC26_Experienced_event_list.txt",
        ]
        truth_candidates = [
            data_dir / "RMDC26_Experienced_Data_out.hdf5",
            data_dir / "RMDC26_Experienced_Data_out.hdf",
        ]
        lightcurve_candidates = [
            data_dir / "selected_lc",
            data_dir / "Original Lightcurves",
        ]
        prediction_candidates = [
            data_dir / "experienced_tier_predictions.csv",
            data_dir / "experienced_predictions.csv",
            data_dir.parent / "experienced_tier_predictions.csv",
            data_dir.parent / "experienced_predictions.csv",
        ]

    parquet_path = _first_existing(parquet_candidates)
    mapping_path = _first_existing(mapping_candidates)
    truth_path = _first_existing(truth_candidates)
    lightcurve_dir = _first_existing(lightcurve_candidates)
    predictions_path = _first_existing(prediction_candidates)

    required_files = [("light-curve parquet", parquet_path)]
    if require_truth:
        required_files.extend(
            [
                ("event mapping/manifest", mapping_path),
                ("truth HDF5", truth_path),
            ]
        )
        if tier == "beginner":
            required_files.append(("light-curve directory", lightcurve_dir))
    missing = []
    for label, path in required_files:
        if path is None:
            missing.append(label)
    if missing:
        raise FileNotFoundError(
            f"Missing {tier} evaluator data in {data_dir}: {', '.join(missing)}"
        )

    return EvaluationData(
        tier=tier,
        data_dir=data_dir,
        parquet_path=parquet_path,
        mapping_path=mapping_path,
        truth_path=truth_path,
        lightcurve_dir=lightcurve_dir,
        predictions_path=predictions_path,
    )


def _series_from_columns(frame: pd.DataFrame, *names: str) -> pd.Series:
    for name in names:
        if name in frame.columns:
            return frame[name]
    return pd.Series(np.nan, index=frame.index)


def _normalise_event_name(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value)


def _read_beginner_truth(data: EvaluationData) -> pd.DataFrame:
    mapping = pd.read_csv(data.mapping_path, sep=r"\s+")
    frames = [pd.read_hdf(data.truth_path, key=key) for key in ("beginner", "rerun")]
    truth = pd.concat(frames, ignore_index=True)
    return pd.merge(
        mapping,
        truth,
        left_on=["runname", "event", "subrun"],
        right_on=["runname", "EventID", "SubRun"],
        how="inner",
    )


def _read_experienced_truth(data: EvaluationData) -> pd.DataFrame:
    manifest = pd.read_csv(data.mapping_path)
    with pd.HDFStore(data.truth_path, mode="r") as store:
        keys = store.keys()
        if not keys:
            raise ValueError(f"No datasets found in experienced truth file {data.truth_path}")
        truth = store.get("/selected_events" if "/selected_events" in keys else keys[0])

    # The experienced HDF already contains the anonymous event name.  The
    # manifest supplies the original run/subrun/field values used by the LC
    # filenames.
    truth["event_name"] = truth["event_name"].map(_normalise_event_name)
    manifest["name"] = manifest["name"].map(_normalise_event_name)
    return pd.merge(
        truth,
        manifest,
        left_on="event_name",
        right_on="name",
        how="left",
        suffixes=("", "_manifest"),
    )


def _experienced_model_type(row: pd.Series) -> Optional[str]:
    try:
        nsource = int(row.get("nsource"))
        nlens = int(row.get("nlens"))
    except (TypeError, ValueError):
        return None
    if nsource not in (1, 2) or nlens not in (1, 2, 3, 4):
        return None
    return f"{nsource}S{nlens}L"


def _first_number(row: pd.Series, names: Iterable[str]) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and not pd.isna(value):
            return value
    return None


def _experienced_planet_values(row: pd.Series, suffix: str) -> list[Any]:
    values = []
    for index in range(4):
        value = row.get(f"planet_{index}_{suffix}")
        if value is not None and not pd.isna(value):
            values.append(value)
    return values


def _has_planet(row: pd.Series) -> bool:
    q_values = _experienced_planet_values(row, "q")
    if not q_values:
        q_values = [_first_number(row, ("Planet_q",))]
    return any(value is not None and float(value) < 0.03 for value in q_values)


def load_truth_records(data: EvaluationData) -> pd.DataFrame:
    """Load truth rows using canonical column names expected by evaluators."""
    raw = _read_beginner_truth(data) if data.tier == "beginner" else _read_experienced_truth(data)

    if data.tier == "beginner":
        event_names = _series_from_columns(raw, "anon_id", "event_name")
        model_types: pd.Series = pd.Series([None] * len(raw), index=raw.index)
    else:
        event_names = _series_from_columns(raw, "event_name", "name")
        model_types = raw.apply(_experienced_model_type, axis=1)

    records = pd.DataFrame(index=raw.index)
    records["anon_id"] = event_names.map(_normalise_event_name)
    records["runname"] = _series_from_columns(raw, "runname", "runname_manifest")
    records["event"] = _series_from_columns(
        raw, "event", "event_x", "event_id", "event_id_manifest", "event_y"
    )
    records["subrun"] = _series_from_columns(raw, "subrun", "subrun_x", "SubRun", "subrun_y")
    records["field"] = _series_from_columns(raw, "field", "field_x", "Field", "field_y")
    records["truth_model"] = model_types
    records["nlens"] = _series_from_columns(raw, "nlens")
    records["nplanets"] = _series_from_columns(raw, "nplanets")
    records["lenscompanions"] = _series_from_columns(raw, "lenscompanions")

    # Experienced events can contain more than one non-primary lens.  Keep
    # every indexed pair available instead of reducing the truth to planet_0.
    for index in range(4):
        records[f"planet_{index}_q"] = _series_from_columns(
            raw, f"planet_{index}_q", f"Planet_{index}_q"
        )
        records[f"planet_{index}_s"] = _series_from_columns(
            raw, f"planet_{index}_s0", f"Planet_{index}_s0"
        )
        records[f"planet_{index}_mass"] = _series_from_columns(
            raw, f"planet_{index}_mass", f"Planet_{index}_mass"
        )
        records[f"planet_{index}_dl"] = _series_from_columns(
            raw, f"planet_{index}_dl", f"Planet_{index}_dl"
        )

    aliases = {
        "t0lens1": ("t0lens1",),
        "u0lens1": ("u0lens1",),
        "tE_helio": ("tE_helio", "te_helio"),
        "ra_deg": ("ra_deg",),
        "dec_deg": ("dec_deg",),
        "alpha": ("alpha",),
        "rho": ("rho",),
        "piEN": ("piEN", "pien"),
        "piEE": ("piEE", "piee"),
        "Planet_s": ("Planet_s", "planet_0_s0"),
        "Planet_q": ("Planet_q", "planet_0_q"),
        "Planet_mass": ("Planet_mass", "planet_0_mass"),
        "Lens_Dist": ("Lens_Dist", "planet_0_dl"),
        "Source2_s": ("Source2_s", "source2_s"),
        "Source2_alpha": ("Source2_alpha", "source2_alpha"),
        "Obs_0_fs": ("Obs_0_fs", "obs_0_fs"),
        "Obs_0_fs2ofs1": ("Obs_0_fs2ofs1",),
    }
    for canonical, names in aliases.items():
        records[canonical] = _series_from_columns(raw, *names)

    if data.tier == "experienced":
        source_flux = _series_from_columns(raw, "obs_0_fs")
        source2_flux = _series_from_columns(raw, "obs_0_fs2")
        ratio = source2_flux / source_flux.replace(0, np.nan)
        records["Obs_0_fs2ofs1"] = records["Obs_0_fs2ofs1"].where(
            records["Obs_0_fs2ofs1"].notna(), ratio
        )
        records["is_planet"] = raw.apply(_has_planet, axis=1)
    else:
        records["is_planet"] = False

    records["lc_name"] = _series_from_columns(raw, "lc_name")
    records["raw_index"] = raw.index
    return records.reset_index(drop=True)


def load_truth_mapping(data: EvaluationData, records: pd.DataFrame) -> Dict[str, str]:
    """Return event-to-model truth labels, deriving experienced labels if needed."""
    if data.predictions_path is not None:
        predictions = pd.read_csv(data.predictions_path)
        return {
            _normalise_event_name(event_id): str(model)
            for event_id, model in zip(predictions["anon_id"], predictions["predicted_class"])
        }

    return {
        str(row.anon_id): str(row.truth_model)
        for row in records.itertuples()
        if row.anon_id and row.truth_model and row.truth_model != "None"
    }


def build_truth_parameters(row: pd.Series | Dict[str, Any]) -> Dict[str, Any]:
    """Convert a canonical truth row into submission-style parameters."""
    getter = row.get
    t0_raw = getter("t0lens1")
    u0 = getter("u0lens1")
    t_e = getter("tE_helio")
    t0 = float(t0_raw) + 2461406.5 if t0_raw is not None and not pd.isna(t0_raw) else None
    result: Dict[str, Any] = {
        "q": getter("Planet_q"),
        "te": t_e,
        "mass": getter("Planet_mass"),
        "dl": getter("Lens_Dist"),
        "t0": t0,
        "u0": u0,
        "ra": getter("ra_deg"),
        "dec": getter("dec_deg"),
        "rho": getter("rho"),
        "piEN": getter("piEN"),
        "piEE": getter("piEE"),
        "Planet_s": getter("Planet_s"),
        "alpha": getter("alpha"),
        "Source2_s": getter("Source2_s"),
        "Source2_alpha": getter("Source2_alpha"),
        "Obs_0_fs2ofs1": getter("Obs_0_fs2ofs1"),
        "Obs_0_fs": getter("Obs_0_fs"),
        "t0_source2": None,
        "u0_source2": None,
        "lens_candidates": [],
    }

    try:
        nplanets = int(getter("nplanets"))
    except (TypeError, ValueError):
        nplanets = 0
    try:
        lenscompanions = int(getter("lenscompanions"))
    except (TypeError, ValueError):
        lenscompanions = 0

    # The experienced export also uses planet_2_* for a non-primary stellar
    # companion in some 4L rows.  Include every populated indexed component;
    # empty columns are ignored below.
    candidate_indices = range(4)
    for index in candidate_indices:
        q = getter(f"planet_{index}_q")
        separation = getter(f"planet_{index}_s")
        if q is None or separation is None or pd.isna(q) or pd.isna(separation):
            continue
        try:
            q = float(q)
            separation = float(separation)
        except (TypeError, ValueError):
            continue
        if q <= 0 or separation <= 0:
            continue
        candidate = {
            "index": index,
            "label": (
                "lens_companion"
                if lenscompanions > 0 and index >= nplanets
                else f"planet_{index}"
            ),
            "q": q,
            "s": separation,
        }
        for output_key, row_key in (("mass", f"planet_{index}_mass"), ("dl", f"planet_{index}_dl")):
            value = getter(row_key)
            if value is not None and not pd.isna(value):
                try:
                    candidate[output_key] = float(value)
                except (TypeError, ValueError):
                    pass
        result["lens_candidates"].append(candidate)

    # Beginner truth has one canonical Planet_q/Planet_s pair rather than
    # indexed experienced-tier columns.
    if not result["lens_candidates"]:
        q = result.get("q")
        separation = result.get("Planet_s")
        if q is not None and separation is not None and not pd.isna(q) and not pd.isna(separation):
            try:
                if float(q) > 0 and float(separation) > 0:
                    result["lens_candidates"].append(
                        {
                            "index": 0,
                            "label": "planet_0",
                            "q": float(q),
                            "s": float(separation),
                            "mass": result.get("mass"),
                            "dl": result.get("dl"),
                        }
                    )
            except (TypeError, ValueError):
                pass

    source_s = result["Source2_s"]
    source_alpha = result["Source2_alpha"]
    lens_alpha = result["alpha"]
    if all(value is not None and not pd.isna(value) for value in (t0_raw, t_e, source_s, source_alpha, lens_alpha)):
        source_alpha_rad = math.radians(float(source_alpha))
        lens_alpha_rad = math.radians(float(lens_alpha))
        result["t0_source2"] = (
            float(t0_raw)
            - float(t_e) * float(source_s) * math.cos(source_alpha_rad - lens_alpha_rad)
            + 2461406.5
        )
    if all(value is not None and not pd.isna(value) for value in (u0, source_s, source_alpha, lens_alpha)):
        source_alpha_rad = math.radians(float(source_alpha))
        lens_alpha_rad = math.radians(float(lens_alpha))
        result["u0_source2"] = float(u0) + float(source_s) * math.sin(source_alpha_rad - lens_alpha_rad)
    return result


def match_truth_lens_component(
    truth_parameters: Dict[str, Any],
    model_s: Any = None,
    model_q: Any = None,
) -> Optional[Dict[str, Any]]:
    """Match a submitted binary lens to the closest truth lens component.

    Separations and mass ratios span orders of magnitude, so a Euclidean
    distance in log-space treats multiplicative errors consistently.  The
    returned component identifies which non-primary lens was used.
    """
    candidates = truth_parameters.get("lens_candidates") or []
    try:
        model_s = float(model_s)
        model_q = float(model_q)
    except (TypeError, ValueError):
        model_s = None
        model_q = None

    if model_s is not None and (not math.isfinite(model_s) or model_s <= 0):
        model_s = None
    if model_q is not None and (not math.isfinite(model_q) or model_q <= 0):
        model_q = None

    if model_s is None or model_q is None:
        return None

    matches = []
    for candidate in candidates:
        terms = []
        if model_s is not None and candidate.get("s"):
            terms.append(math.log(model_s / float(candidate["s"])))
        if model_q is not None and candidate.get("q"):
            terms.append(math.log(model_q / float(candidate["q"])))
        if terms:
            matches.append((math.hypot(*terms), candidate))

    if not matches:
        return None
    score, candidate = min(matches, key=lambda item: item[0])
    return {**candidate, "match_score": score}


def model_type_parts(model_type: str) -> tuple[Optional[int], Optional[int]]:
    match = re.fullmatch(r"([12])S([1-4])L", str(model_type))
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def is_lens_model(model_type: str, minimum_lenses: int = 2) -> bool:
    _, n_lenses = model_type_parts(model_type)
    return n_lenses is not None and n_lenses >= minimum_lenses


def is_source_model(model_type: str) -> bool:
    n_sources, _ = model_type_parts(model_type)
    return n_sources == 2


def is_planet_model(model_type: str, q: Any) -> bool:
    if not is_lens_model(model_type) or q is None:
        return False
    try:
        return float(q) < 0.03
    except (TypeError, ValueError):
        return False


def model_types_for_tier(tier: str, extra: Iterable[str] = ()) -> list[str]:
    base = list(EXPERIENCED_MODEL_TYPES if tier == "experienced" else BASE_MODEL_TYPES)
    for model_type in extra:
        if model_type and model_type not in base:
            base.append(model_type)
    return base


def find_lightcurve_file(data: EvaluationData, row: pd.Series | Dict[str, Any]) -> Optional[Path]:
    """Locate a truth light curve from a canonical truth row."""
    if data.lightcurve_dir is None:
        return None
    getter = row.get
    lc_name = getter("lc_name")
    if lc_name is not None and not pd.isna(lc_name):
        for candidate in data.lightcurve_dir.rglob(str(lc_name)):
            return candidate
        for candidate in data.lightcurve_dir.rglob(f"{lc_name}.gz"):
            return candidate

    runname = getter("runname")
    subrun = getter("subrun")
    event = getter("event")
    field = getter("field")
    if runname is None or pd.isna(runname) or subrun is None or pd.isna(subrun) or event is None or pd.isna(event):
        return None

    subrun_text = str(int(subrun)) if isinstance(subrun, (int, float, np.integer, np.floating)) else str(subrun)
    event_text = str(int(event)) if isinstance(event, (int, float, np.integer, np.floating)) else str(event)
    field_text = str(int(field)) if isinstance(field, (int, float, np.integer, np.floating)) else str(field)
    patterns = [
        f"*_{subrun_text}_*_{event_text}.det.lc",
        f"*_{subrun_text}_*_{event_text}.all.lc",
        f"*_{subrun_text}_{field_text}_{event_text}.det.lc",
        f"*_{subrun_text}_{field_text}_{event_text}.all.lc",
    ]
    for pattern in patterns:
        matches = list(data.lightcurve_dir.rglob(pattern))
        if matches:
            return matches[0]
        gz_matches = list(data.lightcurve_dir.rglob(f"{pattern}.gz"))
        if gz_matches:
            return gz_matches[0]
    return None
