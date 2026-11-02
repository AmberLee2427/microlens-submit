"""Microlensing solution plotting module for microlens-submit.

This module provides tools to load lightcurve data, map solution parameters
to MulensModel format, dynamically fit fluxes to find the best parameterisation convention,
and render high-quality plots showing data fits and residuals.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap, Normalize

try:
    import MulensModel
except ImportError as exc:
    # Provide a clean, helpful error message if dependencies are missing
    raise ImportError(
        "The 'MulensModel' and 'matplotlib' packages are required for plotting. "
        "Please run 'pip install MulensModel matplotlib' to install them."
    ) from exc

def find_original_lightcurve_file(event_id: str, data_dir: Path) -> Optional[Path]:
    """Find the original lightcurve file corresponding to an event ID.

    Uses the tier-specific mapping or manifest to map event IDs to the
    lightcurve filename and constructs the appropriate filename pattern.

    Args:
        event_id: The event identifier (e.g., 'RMDC26_000001')
        data_dir: Directory containing 'Original Lightcurves' and mapping file

    Returns:
        Path to the original lightcurve file, or None if not found.
    """
    beginner_mapping = data_dir / "RMDC26_beginner_tier_w_id.txt"
    experienced_mapping = data_dir / "RMDC26_Experienced_Data_name_manifest.csv"
    if beginner_mapping.exists():
        mapping_df = pd.read_csv(beginner_mapping, sep=r"\s+")
        row = mapping_df[mapping_df["anon_id"] == event_id]
        lc_dir = data_dir / "Original Lightcurves"
        if row.empty or not lc_dir.exists():
            return None
        row = row.iloc[0]
        subrun = int(row["subrun"])
        field = int(row["field"])
        event = int(row["event"])
        patterns = [
            f"*_{subrun}_{field}_{event}.det.lc",
            f"*_{subrun}_{field}_{event}.all.lc",
            f"*_{subrun}_*_{event}.det.lc",
            f"*_{subrun}_*_{event}.all.lc",
        ]
    elif experienced_mapping.exists():
        mapping_df = pd.read_csv(experienced_mapping)
        row = mapping_df[mapping_df["name"] == event_id]
        lc_dir = data_dir / "selected_lc"
        if row.empty or not lc_dir.exists():
            return None
        row = row.iloc[0]
        lc_name = str(row.get("lc_name", ""))
        if lc_name:
            exact = list(lc_dir.rglob(lc_name))
            if exact:
                return exact[0]
            gz_exact = list(lc_dir.rglob(f"{lc_name}.gz"))
            if gz_exact:
                return gz_exact[0]
        subrun = int(row["subrun"])
        field = int(row["field"])
        event = int(row["event_id"])
        patterns = [
            f"*_{subrun}_{field}_{event}.det.lc",
            f"*_{subrun}_{field}_{event}.det.lc.gz",
        ]
    else:
        return None

    for pattern in patterns:
        files = list(lc_dir.rglob(pattern))
        if files:
            return files[0]
    return None

def load_truth_lightcurve(event_id: str, data_dir: Path) -> Optional[pd.DataFrame]:
    """Load truth lightcurve data from original file.

    Args:
        event_id: The event identifier
        data_dir: Directory containing 'Original Lightcurves' and mapping file

    Returns:
        DataFrame with columns: time (BJD), true_relative_flux, possibly other columns.
    """
    lc_file = find_original_lightcurve_file(event_id, data_dir)
    if not lc_file or not lc_file.exists():
        return None

    try:
        df = pd.read_csv(lc_file, sep=r"\s+", comment="#")
        # Keep only relevant columns
        required_cols = ['BJD', 'true_relative_flux']
        if not all(col in df.columns for col in required_cols):
            logging.warning(f"Missing required columns in {lc_file}")
            return None
        return df[['BJD', 'true_relative_flux']].copy()
    except Exception as e:
        logging.warning(f"Could not load truth lightcurve from {lc_file}: {e}")
        return None
def convert_to_sexagesimal(ra_deg: float, dec_deg: float) -> str:
    """Converts decimal degrees of RA and Dec to sexagesimal string HH:MM:SS +/-DD:MM:SS."""
    ra_hours = ra_deg / 15.0
    h = int(ra_hours)
    ra_rem = (ra_hours - h) * 60.0
    m = int(ra_rem)
    s = (ra_rem - m) * 60.0
    ra_str = f"{h:02d}:{m:02d}:{s:05.2f}"

    dec_sign = "-" if dec_deg < 0 else "+"
    dec_abs = abs(dec_deg)
    d = int(dec_abs)
    dec_rem = (dec_abs - d) * 60.0
    dm = int(dec_rem)
    ds = (dec_rem - dm) * 60.0
    dec_str = f"{dec_sign}{d:02d}:{dm:02d}:{ds:05.2f}"

    return f"{ra_str} {dec_str}"

def map_truth_parameters_to_com(
    truth_params: Dict[str, Any],
    t_ref: Optional[float] = None) -> Dict[str, Any]:
    """
    Shifts the GULLS truth parameters from a Primary-Centered origin to
    MulensModel's Center of Mass (CoM) origin for binary lenses.
    """
    import copy
    import math

    # First, run it through your existing mapping (this handles names, BJD/HJD offsets, etc.)
    mm_params = map_parameters_to_mulens(truth_params, t_ref=t_ref, alpha_in_degrees=False)

    # Check if this is a binary lens by looking for separation (s) and mass ratio (q)
    if "s" in truth_params and "q" in truth_params:
        s = float(truth_params["s"])
        q = float(truth_params["q"])
        tE = float(truth_params.get("tE", 1.0))

        # Calculate the X-offset of the Center of Mass relative to the primary lens
        x_com = (s * q) / (1.0 + q)

        # MulensModel alpha is in degrees, we need radians for the trig projection
        alpha_deg = mm_params.get("alpha", 0.0)
        alpha_rad = math.radians(alpha_deg)

        # Apply the coordinate transformation to shift the trajectory
        t0_key = "t_0_1" if "t_0_1" in mm_params else "t_0"
        if t0_key in mm_params:
            mm_params[t0_key] = mm_params[t0_key] + tE * x_com * math.cos(alpha_rad)

        u0_key = "u_0_1" if "u_0_1" in mm_params else "u_0"
        if u0_key in mm_params:
            mm_params[u0_key] = mm_params[u0_key] + x_com * math.sin(alpha_rad)

    return mm_params

def load_event_dataset(data_path: Path, bands: List[str], event_id: Optional[str] = None) -> List[MulensModel.MulensData]:
    """Loads a lightcurve dataset from a CSV/DAT/TXT or Parquet file.

    Robustly maps column names for Time (HJD), Magnitude/Flux, and Error,
    and supports splitting by band when a band column is present.

    Args:
        data_path: Path to the dataset file on disk.
        bands: List of band identifiers to load.
        event_id: Optional Event ID to filter when loading from a parquet file.

    Returns:
        List[MulensModel.MulensData]: List of MulensData objects.
    """
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {data_path}")

    # If it is a parquet file, load and filter in-memory directly
    if data_path.suffix == ".parquet":
        if not event_id:
            raise ValueError("event_id must be provided when loading from a parquet file")
        try:
            import pyarrow.parquet as pq

            available_columns = set(pq.ParquetFile(data_path).schema.names)
        except Exception:
            available_columns = set()

        preferred_columns = [
            "name",
            "ra_deg",
            "dec_deg",
            "bjd",
            "HJD",
            "filt",
            "band",
            "mag",
            "mag_err",
            "flux_uJy",
            "flux_err_uJy",
            "flux",
            "flux_err",
            "obs_x",
            "obs_y",
            "obs_z",
        ]
        columns = [column for column in preferred_columns if column in available_columns]
        read_kwargs = {"columns": columns} if columns else {}
        if "name" in available_columns:
            read_kwargs["filters"] = [("name", "==", event_id)]
        try:
            df = pd.read_parquet(data_path, **read_kwargs)
        except Exception:
            # Some parquet engines do not support filters; still restrict the
            # read to the small set of columns needed by the fit.
            read_kwargs.pop("filters", None)
            df = pd.read_parquet(data_path, **read_kwargs)
        if "name" in df.columns:
            df = df[df["name"] == event_id].copy()
        if df.empty:
            raise ValueError(f"Event {event_id} not found in parquet file {data_path}")

        # Map parquet columns to standard names
        if 'bjd' in df.columns:
            df = df.rename(columns={'bjd': 'HJD'})
        if 'filt' in df.columns:
            df = df.rename(columns={'filt': 'band'})
        if 'flux_uJy' in df.columns:
            df = df.rename(columns={'flux_uJy': 'flux'})
        if 'flux_err_uJy' in df.columns:
            df = df.rename(columns={'flux_err_uJy': 'flux_err'})
    else:
        # Try standard CSV/DAT delimiters
        df = None
        for sep in [",", "\t", r"\s+"]:
            try:
                temp_df = pd.read_csv(data_path, sep=sep, comment="#")
                if len(temp_df.columns) >= 3 and len(temp_df) > 0:
                    df = temp_df
                    break
            except Exception:
                continue

        if df is None:
            try:
                data = np.genfromtxt(data_path, names=True, dtype=None, encoding="utf-8")
                df = pd.DataFrame(data)
            except Exception as exc:
                raise ValueError(f"Could not parse dataset file {data_path}: {exc}") from exc

    # Clean up column names (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]

    # Map time/epoch column
    time_col = None
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ["hjd", "time", "t", "mjd", "jd", "epoch", "x"]:
            time_col = col
            break
    if not time_col:
        time_col = df.columns[0]

    # Map magnitude or flux column
    val_col = None
    phot_fmt = "mag"
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ["mag", "magnitude", "m", "y"]:
            val_col = col
            phot_fmt = "mag"
            break
        elif col_lower in ["flux", "f", "intensity", "flux_ujy", "flux_uJy".lower()]:
            val_col = col
            phot_fmt = "flux"
            break
    if not val_col:
        val_col = df.columns[1]

    # Map error column
    err_col = None
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ["mag_err", "err_mag", "error", "err", "flux_err", "flux_err_ujy", "e_mag", "e_flux", "sig", "sigma", "dy"]:
            err_col = col
            break
    if not err_col:
        err_col = df.columns[2]

    # Map band column
    band_col = None
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in ["band", "passband", "filter", "bandpass"]:
            band_col = col
            break

    # Dynamic coordinates and custom satellite ephemeris extraction
    ra_deg = float(df['ra_deg'].iloc[0]) if 'ra_deg' in df.columns else None
    dec_deg = float(df['dec_deg'].iloc[0]) if 'dec_deg' in df.columns else None
    coords_str = None
    if ra_deg is not None and dec_deg is not None:
        coords_str = convert_to_sexagesimal(ra_deg, dec_deg)

    ephemeris_path = None
    if 'obs_x' in df.columns and 'obs_y' in df.columns and 'obs_z' in df.columns and event_id:
        try:
            # Use the OS default temp directory instead of a hardcoded path
            temp_dir = Path(tempfile.gettempdir()) / "microlens_ephemerides"
            temp_dir.mkdir(exist_ok=True)

            ephemeris_path = temp_dir / f"ephemeris_{event_id}.dat"

            eph_df = df[[time_col, 'obs_x', 'obs_y', 'obs_z']].dropna().drop_duplicates(subset=[time_col])
            eph_data = eph_df.values.astype(float)
            np.savetxt(ephemeris_path, eph_data, fmt="%.7f %.10f %.10f %.10f")

        except Exception as exc:
            logging.warning("Could not write custom ephemeris file: %s", exc)

    datasets = []

    # If band column is present, split dataset by band
    if band_col is not None:
        grouped = df.groupby(band_col)
        for name, group in grouped:
            band_str = str(name).strip()

            # Optional: Log what we are loading vs what was requested
            if bands and band_str not in bands and str(band_str) not in [str(b) for b in bands]:
                logging.debug(f"Loading band '{band_str}' even though it wasn't in requested bands: {bands}")
                # REMOVED the 'continue' statement here so it stops skipping data

            # Create MulensData object
            try:
                kwargs = {
                    "data_list": [
                        group[time_col].values.astype(float),
                        group[val_col].values.astype(float),
                        group[err_col].values.astype(float),
                    ],
                    "phot_fmt": phot_fmt,
                    "bandpass": band_str,
                }
                if ephemeris_path and ephemeris_path.exists():
                    kwargs["ephemerides_file"] = str(ephemeris_path)
                mulens_data = MulensModel.MulensData(**kwargs)
                datasets.append(mulens_data)
            except Exception as exc:
                logging.warning("Could not parse band %s data: %s", band_str, exc)

    # If no datasets were parsed, load the entire file as a single dataset
    if not datasets:
        bandpass = str(bands[0]) if bands else "H"
        try:
            kwargs = {
                "data_list": [
                    df[time_col].values.astype(float),
                    df[val_col].values.astype(float),
                    df[err_col].values.astype(float),
                ],
                "phot_fmt": phot_fmt,
                "bandpass": bandpass,
            }
            if ephemeris_path and ephemeris_path.exists():
                kwargs["ephemerides_file"] = str(ephemeris_path)
            mulens_data = MulensModel.MulensData(**kwargs)
            datasets.append(mulens_data)
        except Exception as exc:
            raise ValueError(f"Failed to create MulensData from columns {time_col}, {val_col}, {err_col}: {exc}") from exc

    for d in datasets:
        if coords_str:
            d.coords_str = coords_str

    return datasets


def map_parameters_to_mulens(
    params: Dict[str, Any],
    t_ref: Optional[float] = None,
    alpha_in_degrees: bool = False,
    neg_u0: bool = False,
) -> Dict[str, Any]:
    """Map microlens-submit parameters to MulensModel native parameter names.

    Args:
        params: Dictionary of parameters from solution.
        t_ref: Reference time for time-dependent effects (Julian Date).
        alpha_in_degrees: If True, treat alpha as degrees as-is.
        neg_u0: If True, invert the sign of u0.

    Returns:
        Dict[str, Any]: Mapped parameters for MulensModel.
    """
    mm_params = {}

    # Core Parameters
    is_binary_source = "t0_source2" in params or "u0_source2" in params
    if "t0" in params:
        key = "t_0_1" if is_binary_source else "t_0"
        mm_params[key] = float(params["t0"])
    if "u0" in params:
        key = "u_0_1" if is_binary_source else "u_0"
        val = float(params["u0"])
        mm_params[key] = -val if neg_u0 else val
    if "tE" in params:
        mm_params["t_E"] = float(params["tE"])

    # Binary Lens Parameters
    if "s" in params:
        mm_params["s"] = float(params["s"])
    if "q" in params:
        mm_params["q"] = float(params["q"])
    if "alpha" in params:
        alpha_val = float(params["alpha"])
        if alpha_in_degrees:
            mm_params["alpha"] = alpha_val
        else:
            mm_params["alpha"] = np.degrees(alpha_val)
    if "Source2_alpha" in params:
        alpha_src_val = float(params["Source2_alpha"])
        if alpha_in_degrees:
            mm_params["Source2_alpha"] = alpha_src_val
        else:
            mm_params["Source2_alpha"] = np.degrees(alpha_src_val)

    # Finite Source Parameter
    if "rho" in params:
        mm_params["rho"] = float(params["rho"])

    # Parallax Parameters
    if "piEN" in params:
        mm_params["pi_E_N"] = float(params["piEN"])
    if "piEE" in params:
        mm_params["pi_E_E"] = float(params["piEE"])
    if t_ref is not None:
        mm_params["t_0_par"] = float(t_ref)

    # Lens Orbital Motion Parameters
    has_orbital_motion = "dsdt" in params or "dadt" in params
    if "dsdt" in params:
        mm_params["d_s_dt"] = float(params["dsdt"])
    if "dadt" in params:
        mm_params["d_alpha_dt"] = float(params["dadt"])
    if t_ref is not None and has_orbital_motion:
        mm_params["t_0_kep"] = float(t_ref)

    # Binary Source Parameters
    if "t0_source2" in params:
        mm_params["t_0_2"] = float(params["t0_source2"])
    if "u0_source2" in params:
        mm_params["u_0_2"] = float(params["u0_source2"])

    return mm_params


def get_fluxes_for_bandpass(params: Dict[str, Any], bandpass: str) -> Tuple[Optional[Any], Optional[float]]:
    """Tries to find source and blend fluxes for a given bandpass in parameters.

    Returns:
        Tuple[Optional[Any], Optional[float]]: (source_flux, blend_flux) if found, otherwise (None, None).
        source_flux can be a float or a list/tuple/numpy array of floats for multiple sources.
    """
    b = str(bandpass).strip()

    # Check binary source first
    s1_key = f"F{b}_S1"
    s2_key = f"F{b}_S2"
    b_key = f"F{b}_B"
    if s1_key in params and s2_key in params and b_key in params:
        return [float(params[s1_key]), float(params[s2_key])], float(params[b_key])

    # Check single source
    s_key = f"F{b}_S"
    if s_key in params and b_key in params:
        return float(params[s_key]), float(params[b_key])

    # Fallback to case insensitive search if not found
    for k in params.keys():
        k_upper = k.upper().strip()
        if k_upper == f"F{b.upper()}_B":
            # Found blend flux, let's find source flux
            for ks in params.keys():
                ks_upper = ks.upper().strip()
                if ks_upper == f"F{b.upper()}_S":
                    return float(params[ks]), float(params[k])
                elif ks_upper == f"F{b.upper()}_S1" and f"F{b.upper()}_S2" in [x.upper().strip() for x in params.keys()]:
                    ks2 = [x for x in params.keys() if x.upper().strip() == f"F{b.upper()}_S2"][0]
                    return [float(params[ks]), float(params[ks2])], float(params[k])

    return None, None


def fit_best_model(
    datasets: List[MulensModel.MulensData],
    solution_parameters: Dict[str, Any],
    model_type: str,
    t_ref: Optional[float] = None,
) -> Tuple[MulensModel.Event, float]:
    """Fits various conventions of parameterisation and chooses the one with the lowest chi2.

    Considers:
    - alpha in radians vs degrees
    - alpha with a 180 degree rotation/offset (common in Gulls vs MulensModel)
    - u0 positive vs negative

    Args:
        datasets: Loaded datasets.
        solution_parameters: Parameters dict.
        model_type: Model type string.
        t_ref: Optional reference time.

    Returns:
        Tuple[MulensModel.Event, float]: The best Event object and its chi2.
    """
    best_event = None
    best_chi2 = np.inf
    coords = datasets[0].coords_str if (datasets and getattr(datasets[0], "coords_str", None)) else "17:45:40.04 -29:00:28.1"

    # Try common variations:
    # 1. alpha options: standard, Gulls-style (180 deg shifted), reflected, and radian vs degree
    alpha_options = [0.0]
    if "alpha" in solution_parameters:
        alpha_val = float(solution_parameters["alpha"])
        is_radians = (abs(alpha_val) < 2.0 * np.pi)

        if is_radians:
            rad_deg = np.degrees(alpha_val)
            alpha_options = [
                # Radian-based conversions (assuming input in radians)
                rad_deg,
                rad_deg + 180.0,
                rad_deg - 180.0,
                -rad_deg,
                -rad_deg + 180.0,
                -rad_deg - 180.0,
                180.0 - rad_deg,
                360.0 - rad_deg,
            ]
        else:
            alpha_options = [
                # Degree-based values (assuming input is already in degrees)
                alpha_val,
                alpha_val + 180.0,
                alpha_val - 180.0,
                -alpha_val,
                -alpha_val + 180.0,
                -alpha_val - 180.0,
                180.0 - alpha_val,
                360.0 - alpha_val,
            ]

    # 2. u0 positive vs. negative
    u0_options = [False, True] if "u0" in solution_parameters else [False]

    for alpha_deg in alpha_options:
        for neg_u in u0_options:
            try:
                mm_params = map_parameters_to_mulens(
                    solution_parameters,
                    t_ref=t_ref,
                    alpha_in_degrees=True,  # alpha is overridden below
                    neg_u0=neg_u,
                )
                if "alpha" in solution_parameters:
                    mm_params["alpha"] = alpha_deg

                # Strip rho/t_star during convention search.
                # With rho set but no finite-source method specified, MulensModel
                # gives inaccurate magnification at caustic crossings, which inflates
                # chi2 for the CORRECT alpha (the one that crosses the caustic).
                # The WRONG alpha (no crossing) is unaffected, so it wins unfairly.
                # Using point-source chi2 purely for convention identification is correct.
                ps_params = {k: v for k, v in mm_params.items() if k not in ("rho", "t_star")}
                model = MulensModel.Model(ps_params, coords=coords)

                event = MulensModel.Event(datasets=datasets, model=model)

                # Fix fluxes from stored solution parameters — only alpha should vary.

                event.fit_fluxes()

                chi2 = event.get_chi2()
                if chi2 < best_chi2:
                    best_chi2 = chi2
                    # Store the FULL mm_params (including rho) for the winning convention
                    # Fluxes are rebuilt after the winning convention is known.
                    # The local flag belongs to that rebuild, not this search.
                    best_event = (mm_params, False)
            except Exception:
                continue

    # Rebuild the winning event with the full parameters (including rho) for plotting.
    def _build_final_event(mm_params, had_fixed_fluxes):
        model = MulensModel.Model(mm_params, coords=coords)
        if "rho" in mm_params or "t_star" in mm_params:
            try:
                t_data_min = min(d.time.min() for d in datasets) - 1.0
                t_data_max = max(d.time.max() for d in datasets) + 1.0
                method = "VBBL" if model.n_lenses == 2 else "finite_source_uniform_Gould94"
                model.set_magnification_methods(
                    [t_data_min, method, t_data_max]
                )
            except Exception as em:
                logging.debug("Could not set finite-source method: %s", em)
        ev = MulensModel.Event(datasets=datasets, model=model)
        has_fixed = False
        for d in datasets:
            fs_val, fb_val = get_fluxes_for_bandpass(solution_parameters, d.bandpass)
            if fs_val is not None and fb_val is not None:
                ev.fix_source_flux[d] = fs_val
                ev.fix_blend_flux[d] = fb_val
                has_fixed = True
        if not has_fixed:
            ev.fit_fluxes()
        return ev

    if isinstance(best_event, tuple):
        winning_mm_params, had_fixed = best_event
        try:
            best_event = _build_final_event(winning_mm_params, had_fixed)
            best_chi2 = best_event.get_chi2()
        except Exception as exc:
            logging.error("Failed to build final event from best convention: %s", exc)
            best_event = None

    if best_event is None:
        # Fallback to the absolute default mapping
        logging.warning("All conventions failed during optimization. Falling back to default mapping.")
        mm_params = map_parameters_to_mulens(solution_parameters, t_ref=t_ref)
        try:
            best_event = _build_final_event(mm_params, False)
            best_chi2 = best_event.get_chi2()
        except Exception as exc:
            logging.error("Fallback fitting failed: %s", exc)
            best_chi2 = 999999.9

    return best_event, best_chi2


def _generate_bokeh_lightcurve_plot(
    solution: Any,
    event: Any,
    datasets: List[Any],
    best_event: Any,
    chi2: float,
    output_html_path: Path,
    truth_df: Optional[pd.DataFrame] = None,
) -> None:
    """Generates an interactive premium two-panel Bokeh plot of lightcurve fit and residuals.

    Args:
        solution: Solution instance.
        event: Parent Event instance.
        datasets: List of MulensData objects.
        best_event: Best-fit MulensModel Event object.
        chi2: Best-fit chi2 value.
        output_html_path: Destination path for the HTML file.
    """
    try:
        from bokeh.plotting import figure
        from bokeh.models import ColumnDataSource, HoverTool, Span
        from bokeh.embed import file_html
        from bokeh.resources import CDN
        from bokeh.layouts import column
    except ImportError as exc:
        logging.warning("Bokeh is required for interactive plots. Skipping: %s", exc)
        return

    all_times = []
    for d in datasets:
        all_times.extend(d.time)

    t_min = min(all_times) if all_times else 0
    t_max = max(all_times) if all_times else 100
    t_span = t_max - t_min
    t_plot_min = t_min - 0.05 * t_span
    t_plot_max = t_max + 0.05 * t_span
    # Build a dense adaptive t_model grid.
    # For binary lens events the planetary perturbation can be very narrow (hours),
    # so we combine: (1) the actual data times so the model always passes through
    # observed epochs, and (2) a high-resolution uniform grid to fill gaps.
    # 10_000 uniform points over the span gives ~0.4 min resolution for a 72-day season.
    t_uniform = np.linspace(t_plot_min, t_plot_max, 10_000)
    t_model = np.unique(np.concatenate([t_uniform, np.array(all_times)]))

    is_mag = datasets[0].input_fmt == "mag"
    y_label = "Magnitude" if is_mag else "Flux"

    all_y = []
    for d in datasets:
        if is_mag:
            all_y.extend(d.mag)
        else:
            all_y.extend(d.flux)

    y_min = min(all_y) if all_y else 0.0
    y_max = max(all_y) if all_y else 25.0
    y_span = y_max - y_min if y_max != y_min else 1.0

    # Calculate y_range with padding
    if is_mag:
        y_range = (y_max + 0.05 * y_span + 0.1, y_min - 0.05 * y_span - 0.1)
    else:
        y_range = (y_min - 0.05 * y_span - 0.1, y_max + 0.05 * y_span + 0.1)

    alias_info = f" ({solution.alias})" if solution.alias else ""
    title = (
        f"Event: {event.event_id} | Solution: {solution.solution_id[:8]}...{alias_info}\n"
        f"Model: {solution.model_type} | Chi2: {chi2:.2f} (N={len(all_times)})"
    )

    p_lc = figure(
        title=title,
        x_axis_label="Time (HJD)",
        y_axis_label=y_label,
        height=320,
        width=850,
        y_range=y_range,
        tools="pan,box_zoom,wheel_zoom,reset,save",
        active_scroll="wheel_zoom",
        sizing_mode="stretch_width",
    )

    p_res = figure(
        x_axis_label="Time (HJD)",
        y_axis_label="Residuals",
        height=150,
        width=850,
        tools="pan,box_zoom,wheel_zoom,reset,save",
        active_scroll="wheel_zoom",
        x_range=p_lc.x_range,
        sizing_mode="stretch_width",
    )

    # Dynamic coordinates from dataset
    _coords = datasets[0].coords_str if (datasets and getattr(datasets[0], "coords_str", None)) else "17:45:40.04 -29:00:28.1"

    colors = ['#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE', '#AA3377', '#BBBBBB']

    for i, d in enumerate(datasets):
        color = colors[i % len(colors)]
        band_name = d.bandpass or f"Band {i}"

        # Use provided fluxes if available, otherwise get fitted ones from best_event
        fs_val, fb_val = get_fluxes_for_bandpass(solution.parameters, d.bandpass)
        if fs_val is not None and fb_val is not None:
            F_S_val = fs_val
            F_B = fb_val
        else:
            flux_res = best_event.get_flux_for_dataset(d)
            F_S_val = flux_res[0]
            F_B = flux_res[1]

        # Binary SOURCE models return a list of 2 magnification arrays; binary LENS returns 1 array
        is_binary_source_model = getattr(best_event.model, "n_sources", 1) == 2
        if is_binary_source_model and isinstance(F_S_val, (list, np.ndarray)) and len(F_S_val) > 1:
            magnifications = best_event.model.get_magnification(d.time)
            model_flux = F_S_val[0] * magnifications[0] + F_S_val[1] * magnifications[1] + F_B

            mags_t_model = best_event.model.get_magnification(t_model)
            model_flux_t_model = F_S_val[0] * mags_t_model[0] + F_S_val[1] * mags_t_model[1] + F_B
        else:
            F_S = F_S_val[0] if isinstance(F_S_val, (list, np.ndarray)) else F_S_val
            magnifications = best_event.model.get_magnification(d.time)
            model_flux = F_S * magnifications + F_B

            mags_t_model = best_event.model.get_magnification(t_model)
            model_flux_t_model = F_S * mags_t_model + F_B

        # Prep continuous model curve
        model_flux_t_model = np.clip(model_flux_t_model, 1e-10, None)
        if is_mag:
            y_model = 22.0 - 2.5 * np.log10(model_flux_t_model)
        else:
            y_model = model_flux_t_model

        model_source = ColumnDataSource(data={
            "time": t_model,
            "y": y_model,
        })

        # Render model line (top panel)
        p_lc.line(
            "time",
            "y",
            source=model_source,
            color=color,
            line_width=2.5,
            legend_label=f"Model ({band_name})",
        )

        # Prep data points & residuals
        model_flux = np.clip(model_flux, 1e-10, None)
        if is_mag:
            y_data = d.mag
            y_err = d.err_mag
            y_fit = 22.0 - 2.5 * np.log10(model_flux)
            residuals = d.mag - y_fit
        else:
            y_data = d.flux
            y_err = d.err_flux
            y_fit = model_flux
            residuals = d.flux - y_fit

        # Error bar segments
        lower = y_data - y_err
        upper = y_data + y_err

        res_lower = residuals - y_err
        res_upper = residuals + y_err

        data_source = ColumnDataSource(data={
            "time": d.time,
            "y": y_data,
            "err": y_err,
            "lower": lower,
            "upper": upper,
            "band": [band_name] * len(d.time),
        })

        res_source = ColumnDataSource(data={
            "time": d.time,
            "residual": residuals,
            "err": y_err,
            "lower": res_lower,
            "upper": res_upper,
            "band": [band_name] * len(d.time),
        })

        # Render error bars for data (top panel)
        p_lc.segment(
            x0="time",
            y0="lower",
            x1="time",
            y1="upper",
            source=data_source,
            line_color=color,
            line_alpha=0.3,
            line_width=1.5,
            legend_label=f"Data ({band_name})",
        )

        # Render data scatter points (top panel)
        p_lc.scatter(
            "time",
            "y",
            source=data_source,
            size=5.5,
            color=color,
            alpha=0.6,
            legend_label=f"Data ({band_name})",
        )

        # Render error bars for residuals (bottom panel)
        p_res.segment(
            x0="time",
            y0="lower",
            x1="time",
            y1="upper",
            source=res_source,
            line_color=color,
            line_alpha=0.3,
            line_width=1.5,
        )

        # Render residuals scatter points (bottom panel)
        p_res.scatter(
            "time",
            "residual",
            source=res_source,
            size=5,
            color=color,
            alpha=0.6,
        )

    # Residuals zero-line
    zero_span = Span(
        location=0.0,
        dimension="width",
        line_color="#333333",
        line_dash="solid",
        line_width=1.5,
        line_alpha=0.8,
    )
    p_res.add_layout(zero_span)

    # Style grids, borders, fonts
    for fig in [p_lc, p_res]:
        fig.background_fill_color = "#fdfbfd"
        fig.border_fill_color = "#ffffff"
        fig.grid.grid_line_color = "#cccccc"
        fig.grid.grid_line_alpha = 0.4
        fig.grid.grid_line_dash = [4, 4]
        fig.outline_line_color = "#e5e7eb"

        fig.xaxis.axis_label_text_font = "Inter, sans-serif"
        fig.xaxis.axis_label_text_font_style = "bold"
        fig.xaxis.axis_label_text_font_size = "11pt"

        fig.yaxis.axis_label_text_font = "Inter, sans-serif"
        fig.yaxis.axis_label_text_font_style = "bold"
        fig.yaxis.axis_label_text_font_size = "11pt"

        fig.xaxis.major_label_text_font = "Inter, sans-serif"
        fig.yaxis.major_label_text_font = "Inter, sans-serif"

    p_lc.title.text_font = "Inter, sans-serif"
    p_lc.title.text_font_style = "bold"
    p_lc.title.text_font_size = "12pt"
    p_lc.title.text_color = "#361d49"

    # Set up interactive legend
    p_lc.legend.click_policy = "hide"
    p_lc.legend.background_fill_alpha = 0.9
    p_lc.legend.label_text_font = "Inter, sans-serif"
    p_lc.legend.label_text_font_size = "9pt"
    p_lc.legend.location = "top_right"

    # Interactive hover tools
    hover_lc = HoverTool(
        tooltips=[
            ("HJD", "@time{0.0000}"),
            (y_label, "@y{0.000}"),
            ("Error", "@err{0.000}"),
            ("Band", "@band"),
        ],
        mode="mouse",
    )
    p_lc.add_tools(hover_lc)

    hover_res = HoverTool(
        tooltips=[
            ("HJD", "@time{0.0000}"),
            ("Residual", "@residual{0.000}"),
            ("Error", "@err{0.000}"),
            ("Band", "@band"),
        ],
        mode="mouse",
    )
    p_res.add_tools(hover_res)

    # Save to file
    layout = column(p_lc, p_res, sizing_mode="stretch_width")
    html_content = file_html(layout, CDN, f"Lightcurve Fit: {event.event_id}")

    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    with output_html_path.open("w", encoding="utf-8") as f:
        f.write(html_content)


def generate_mass_distance_comparison_plot(
    event: Any,
    output_path: Path,
) -> None:
    """Generates a scatter plot of Lens Mass vs Lens Distance for all active solutions.

    Args:
        event: The Event object containing solutions.
        output_path: Destination path for the image.
    """
    solutions = [s for s in event.solutions.values() if s.is_active]
    if not solutions:
        return

    masses = []
    distances = []
    probs = []

    for sol in solutions:
        phys = sol.physical_parameters or {}
        # Try 'lens_mass' first, then 'planet_mass' as fallback for mocks
        m = phys.get("lens_mass") or phys.get("planet_mass")
        d = phys.get("lens_distance")
        if m is not None and d is not None:
            masses.append(float(m))
            distances.append(float(d))
            probs.append(float(sol.relative_probability) if sol.relative_probability is not None else 0.0)

    if not masses:
        return

    plt.figure(figsize=(6, 4))
    plt.style.use('seaborn-v0_8-whitegrid')

    norm = Normalize(vmin=min(probs), vmax=max(probs) if len(probs) > 1 else 1.0)
    brand_cmap = LinearSegmentedColormap.from_list("brand_purple", ["#dfc5fa", "#a859e4", "#361d49"])
    sc = plt.scatter(distances, masses, c=probs, cmap=brand_cmap, s=60, edgecolors='k', alpha=0.8)

    plt.colorbar(sc, label='Relative Probability')
    plt.xlabel('Lens Distance [kpc]', fontsize=10, fontname='Inter')
    plt.ylabel(r'Lens Mass [$M_\odot$]', fontsize=10, fontname='Inter')
    plt.title(f'Degeneracy: Mass vs Distance ({event.event_id})', fontsize=12, fontname='Inter', fontweight='bold')

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def generate_proper_motion_comparison_plot(
    event: Any,
    output_path: Path,
) -> None:
    """Generates a scatter plot of Proper Motion North vs East for all active solutions.

    Args:
        event: The Event object containing solutions.
        output_path: Destination path for the image.
    """
    solutions = [s for s in event.solutions.values() if s.is_active]
    if not solutions:
        return

    pi_n = []
    pi_e = []
    probs = []

    for sol in solutions:
        phys = sol.physical_parameters or {}
        pn = phys.get("piE_N")
        pe = phys.get("piE_E")
        if pn is not None and pe is not None:
            pi_n.append(float(pn))
            pi_e.append(float(pe))
            probs.append(float(sol.relative_probability) if sol.relative_probability is not None else 0.0)

    if not pi_n:
        return

    plt.figure(figsize=(6, 4))
    plt.style.use('seaborn-v0_8-whitegrid')

    norm = Normalize(vmin=min(probs), vmax=max(probs) if len(probs) > 1 else 1.0)
    brand_cmap = LinearSegmentedColormap.from_list("brand_purple", ["#dfc5fa", "#a859e4", "#361d49"])
    sc = plt.scatter(pi_e, pi_n, c=probs, cmap=brand_cmap, s=60, edgecolors='k', alpha=0.8)

    plt.colorbar(sc, label='Relative Probability')
    plt.xlabel(r'$\pi_{E,East}$ [mas]', fontsize=10, fontname='Inter')
    plt.ylabel(r'$\pi_{E,North}$ [mas]', fontsize=10, fontname='Inter')
    plt.title(f'Degeneracy: Proper Motion Vector ({event.event_id})', fontsize=12, fontname='Inter', fontweight='bold')

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def generate_lens_plane_plot(
    solution: Any,
    event: Any,
    output_path: Path,
    coords: Optional[str] = None,
    data_dir: Optional[Path] = None,
) -> None:
    """Generates a premium SVG/PNG plot of the lens plane geometry (caustics & trajectory).
    If truth parameters are available, overlays the truth model.
    """
    _coords = coords or "17:45:40.04 -29:00:28.1"

    def prune_for_mulens_trajectory(mm_params_dict: dict, m_type: str) -> dict:
        allowed = {"t_0", "u_0", "t_E"}
        if "2L" in m_type:
            allowed.update({"s", "q", "alpha"})
        if "2S" in m_type:
            allowed.update({"t_0_1", "u_0_1", "t_0_2", "u_0_2", "flux_ratio"})
            if "t_0_1" not in mm_params_dict and "t_0" in mm_params_dict:
                mm_params_dict["t_0_1"] = mm_params_dict["t_0"]
            if "u_0_1" not in mm_params_dict and "u_0" in mm_params_dict:
                mm_params_dict["u_0_1"] = mm_params_dict["u_0"]
        return {k: v for k, v in mm_params_dict.items() if k in allowed}

    # Try to load original lightcurve file to overlay the true trajectory and plot marginals
    has_orig_traj = False
    x_orig = None
    y_orig = None
    dx = None
    dy = None
    limit = None

    # Default times grid
    t0_def = solution.parameters.get("t0", 2460000.0)
    tE_def = solution.parameters.get("tE", 30.0)
    times = np.linspace(t0_def - 3.0 * tE_def, t0_def + 3.0 * tE_def, 1000)

    # Compute ecliptic -> equatorial rotation angle (theta_rot) at the event's sky position.
    # This rotates from GULLS ecliptic frame into equatorial East-North for display.
    theta_rot = 0.0
    try:
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        _ra_str, _dec_str = _coords.split()
        _sc = SkyCoord(ra=_ra_str, dec=_dec_str, unit=(u.hourangle, u.deg))
        _ecl = _sc.geocentricmeanecliptic
        # Position angle of ecliptic North pole projected onto equatorial sky at this position
        _ecl_pole = SkyCoord(lon=_ecl.lon, lat=_ecl.lat + 1e-4 * u.deg, frame="geocentricmeanecliptic").icrs
        theta_rot = float(_sc.position_angle(_ecl_pole).rad)
    except Exception as _e:
        logging.debug("Could not compute theta_rot: %s", _e)

    def _rot(x, y, angle):
        """Rotate arrays (x, y) by angle (radians) anti-clockwise."""
        c, s = np.cos(angle), np.sin(angle)
        return x * c - y * s, x * s + y * c

    def _apply_alpha_rot(params_dict, angle):
        """Return a copy of params_dict with alpha rotated by angle (degrees)."""
        d = dict(params_dict)
        if "alpha" in d:
            d["alpha"] = float(d["alpha"]) + np.degrees(angle)
        return d

    theta_pm = 0.0  # kept for legacy fallback only

    if data_dir is not None:
        try:
            lc_file = find_original_lightcurve_file(event.event_id, data_dir)
            if lc_file and lc_file.exists():
                df = pd.read_csv(lc_file, sep=r"\s+", comment="#")
                df = df.sort_values('BJD').reset_index(drop=True)
                times = df['BJD'].values

                # Load GULLS source trajectory in ecliptic frame, then rotate to equatorial EN
                x_ecl = -df['source_x'].values
                y_ecl = -df['source_y'].values
                x_orig, y_orig = _rot(x_ecl, y_ecl, theta_rot)

                # Calculate fit trajectory at same times to get deviation
                mm_params = map_parameters_to_mulens(solution.parameters, t_ref=solution.t_ref)
                model_type = getattr(solution, "model_type", "1S1L")
                mm_params_dev = prune_for_mulens_trajectory(_apply_alpha_rot(mm_params, theta_rot), model_type)
                fit_model_for_dev = MulensModel.Model(mm_params_dev, coords=_coords)
                trajectory_fit = fit_model_for_dev.get_trajectory(times)
                if isinstance(trajectory_fit, list):
                    x_fit, y_fit = trajectory_fit[0].x, trajectory_fit[0].y
                else:
                    x_fit, y_fit = trajectory_fit.x, trajectory_fit.y

                # For single-lens model, MulensModel trajectory is horizontal; rotate to equatorial
                if fit_model_for_dev.n_lenses == 1:
                    x_fit, y_fit = _rot(x_fit, y_fit, theta_rot)

                # Calculate deviations
                dx = x_fit - x_orig
                dy = y_fit - y_orig

                # Compute zoom limits centered at (0, 0)
                s_val = solution.parameters.get("s")
                s_val = float(s_val) if s_val is not None else 1.0
                u0_val = solution.parameters.get("u0")
                u0_val = float(u0_val) if u0_val is not None else 0.5
                limit = max(2.0, 1.5 * s_val, 1.5 * abs(u0_val))
                has_orig_traj = True
        except Exception as e:
            logging.warning("Could not calculate trajectory deviation for lens plane: %s", e)

    # Initialize layout
    if has_orig_traj:
        # Create figure for locatable marginal plots
        fig, ax_main = plt.subplots(figsize=(6, 6))
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.sca(ax_main)
    else:
        plt.figure(figsize=(6, 6))
        plt.style.use('seaborn-v0_8-whitegrid')
        ax_main = plt.gca()

    has_fit = False
    try:
        mm_params = map_parameters_to_mulens(solution.parameters, t_ref=solution.t_ref)
        model_type = getattr(solution, "model_type", "1S1L")
        mm_params_rot = _apply_alpha_rot(mm_params, theta_rot)
        mm_params_rot = prune_for_mulens_trajectory(mm_params_rot, model_type)
        fit_model = MulensModel.Model(mm_params_rot, coords=_coords)

        # Plot caustics for binary lens, or Einstein ring + lens position for single lens.
        # All geometry is rotated to equatorial EN via theta_rot.
        if fit_model.n_lenses == 2:
            try:
                fit_model.update_caustics()
            except Exception:
                pass
            if fit_model.caustics is not None:
                x_c, y_c = fit_model.caustics.get_caustics(n_points=5000)
                x_c, y_c = _rot(np.array(x_c), np.array(y_c), theta_rot)
                ax_main.scatter(x_c, y_c, color="#a859e4", s=8, edgecolors="none", label="Fitted Caustic")
            # Draw binary lens positions rotated to equatorial EN
            _s_fit = float(mm_params_rot.get("s", 1.0))
            _q_fit = float(mm_params_rot.get("q", 0.1))
            _x1_fit = -_s_fit * _q_fit / (1.0 + _q_fit)
            _x2_fit = _s_fit / (1.0 + _q_fit)
            _x1e, _y1e = _rot(np.array([_x1_fit]), np.array([0.0]), theta_rot)
            _x2e, _y2e = _rot(np.array([_x2_fit]), np.array([0.0]), theta_rot)
            _r1 = max(60, 200 * (1.0 / (1.0 + _q_fit)))
            _r2 = max(20, 200 * (_q_fit / (1.0 + _q_fit)))
            ax_main.scatter(_x1e, _y1e, marker="*", s=_r1, color="#a859e4", zorder=6,
                            edgecolors="white", linewidths=0.5, label="Fitted Primary")
            ax_main.scatter(_x2e, _y2e, marker="o", s=_r2, color="#a859e4", zorder=6,
                            edgecolors="white", linewidths=0.5, label="Fitted Secondary")
        else:
            # Single lens: Einstein ring (invariant to rotation) and lens at origin
            theta_ring = np.linspace(0, 2 * np.pi, 300)
            ax_main.plot(np.cos(theta_ring), np.sin(theta_ring), color="#a859e4", lw=1.2,
                         linestyle="dotted", alpha=0.6, label="Fitted Einstein Ring")
            ax_main.scatter([0], [0], marker="*", s=120, color="#a859e4", zorder=5,
                            edgecolors="white", linewidths=0.5, label="Fitted Lens")

        # Plot source trajectories (MulensModel already has rotated alpha)
        traj_result = fit_model.get_trajectory(times)
        if isinstance(traj_result, list):
            trajs = traj_result
        else:
            trajs = [traj_result]

        for src_idx, traj in enumerate(trajs):
            x_fit_p, y_fit_p = traj.x, traj.y
            # Single lens: MulensModel trajectory is horizontal — rotate to equatorial
            if fit_model.n_lenses == 1:
                x_fit_p, y_fit_p = _rot(x_fit_p, y_fit_p, theta_rot)

            ax_main.plot(x_fit_p, y_fit_p, color="#a859e4", lw=3.0, label="Fitted Trajectory" if src_idx == 0 else "")
            mid = len(x_fit_p) // 2
            ax_main.annotate('', xy=(x_fit_p[mid+1], y_fit_p[mid+1]), xytext=(x_fit_p[mid], y_fit_p[mid]),
                             arrowprops=dict(arrowstyle="->", color="#a859e4", lw=3.0, mutation_scale=15))
        has_fit = True
    except Exception as e:
        logging.warning("Could not plot fitted model on lens plane: %s", e)

    has_truth = False
    if getattr(event, "truth_parameters", None) is not None:
        try:
            truth_params = event.truth_parameters
            truth_mm_params = map_parameters_to_mulens(truth_params, t_ref=solution.t_ref)
            truth_model_type = getattr(event, "truth_model", None) or ("1S2L" if "s" in truth_params else "1S1L")
            truth_mm_params_rot = _apply_alpha_rot(truth_mm_params, theta_rot)
            truth_mm_params_rot = prune_for_mulens_trajectory(truth_mm_params_rot, truth_model_type)
            truth_model = MulensModel.Model(truth_mm_params_rot, coords=_coords)

            # Plot true caustics for binary lens, or Einstein ring + lens position for single lens
            if truth_model.n_lenses == 2:
                try:
                    truth_model.update_caustics()
                except Exception:
                    pass
                if truth_model.caustics is not None:
                    x_c, y_c = truth_model.caustics.get_caustics(n_points=5000)
                    x_c, y_c = _rot(np.array(x_c), np.array(y_c), theta_rot)
                    ax_main.scatter(x_c, y_c, color="#22c55e", s=2, edgecolors="none", label="True Caustic")
                # Draw true binary lens positions rotated to equatorial EN
                _s_t = float(truth_mm_params_rot.get("s", 1.0))
                _q_t = float(truth_mm_params_rot.get("q", 0.1))
                _x1_t = -_s_t * _q_t / (1.0 + _q_t)
                _x2_t = _s_t / (1.0 + _q_t)
                _x1te, _y1te = _rot(np.array([_x1_t]), np.array([0.0]), theta_rot)
                _x2te, _y2te = _rot(np.array([_x2_t]), np.array([0.0]), theta_rot)
                _r1_t = max(60, 200 * (1.0 / (1.0 + _q_t)))
                _r2_t = max(20, 200 * (_q_t / (1.0 + _q_t)))
                ax_main.scatter(_x1te, _y1te, marker="*", s=_r1_t, color="#22c55e", zorder=6,
                                edgecolors="white", linewidths=0.5, label="True Primary")
                ax_main.scatter(_x2te, _y2te, marker="o", s=_r2_t, color="#22c55e", zorder=6,
                                edgecolors="white", linewidths=0.5, label="True Secondary")
            else:
                # Single lens: Einstein ring invariant to rotation, lens at origin
                theta_ring = np.linspace(0, 2 * np.pi, 300)
                ax_main.plot(np.cos(theta_ring), np.sin(theta_ring), color="#22c55e", lw=1.0,
                             linestyle="dotted", alpha=0.6, label="True Einstein Ring")
                ax_main.scatter([0], [0], marker="*", s=80, color="#22c55e", zorder=5,
                                edgecolors="white", linewidths=0.5, label="True Lens")

            if has_orig_traj:
                ax_main.plot(x_orig, y_orig, color="#22c55e", lw=1.2, linestyle="dashed", label="True Trajectory")
            else:
                traj_result = truth_model.get_trajectory(times)
                if isinstance(traj_result, list):
                    trajs = traj_result
                else:
                    trajs = [traj_result]
                for src_idx, traj in enumerate(trajs):
                    x_t_p, y_t_p = traj.x, traj.y
                    if truth_model.n_lenses == 1:
                        x_t_p, y_t_p = _rot(x_t_p, y_t_p, theta_rot)
                    ax_main.plot(x_t_p, y_t_p, color="#22c55e", lw=1.5, linestyle="dashed", label="True Trajectory" if src_idx == 0 else "")
            has_truth = True
        except Exception as e:
            logging.warning("Could not plot truth model on lens plane: %s", e)

    # Compass Indicator:
    # - For single lens: Ecliptic North is Up (+y), Ecliptic East is Right (+x).
    # - For binary lens: The axis points towards the secondary lens on the right (+x).
    if fit_model.n_lenses == 1:
        ax_main.annotate('N', xy=(0.92, 0.92), xycoords='axes fraction', xytext=(0.92, 0.96),
                         arrowprops=dict(arrowstyle="<-", color="#361d49", lw=1.5),
                         ha='center', va='bottom', fontsize=9, fontweight='bold')
        ax_main.annotate('E', xy=(0.92, 0.92), xycoords='axes fraction', xytext=(0.96, 0.92),
                         arrowprops=dict(arrowstyle="<-", color="#361d49", lw=1.5),
                         ha='left', va='center', fontsize=9, fontweight='bold')
    else:
        # Show direction of the secondary lens (to the right)
        ax_main.annotate('To Secondary', xy=(0.94, 0.92), xycoords='axes fraction', xytext=(0.80, 0.92),
                         arrowprops=dict(arrowstyle="->", color="#361d49", lw=1.5),
                         ha='right', va='center', fontsize=8, fontweight='bold')

    # Set up axes title and labels
    ax_main.set_title(f"Lens Plane Geometry - Event {event.event_id}" if not has_orig_traj else "", fontsize=11, fontweight="bold", color="#361d49", fontname="Inter")
    ax_main.set_xlabel(r"$\theta_x$ [Einstein radii]", fontsize=9, fontname="Inter")
    ax_main.set_ylabel(r"$\theta_y$ [Einstein radii]", fontsize=9, fontname="Inter")

    if has_orig_traj and limit is not None:
        ax_main.set_xlim(-limit, limit)
        ax_main.set_ylim(-limit, limit)
        ax_main.set_aspect('equal', adjustable='box')

        # Append marginal axes
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        divider = make_axes_locatable(ax_main)
        ax_top = divider.append_axes("top", size="20%", pad=0.15, sharex=ax_main)
        ax_right = divider.append_axes("right", size="20%", pad=0.15, sharey=ax_main)

        # Top Marginal Plot (dx vs x_orig)
        plt.sca(ax_top)
        mask_x = (x_orig >= -limit) & (x_orig <= limit)
        ax_top.plot(x_orig[mask_x], dx[mask_x], color="#3b82f6", lw=1.2, label=r"$\Delta x$")
        ax_top.axhline(0, color="gray", linestyle=":", lw=0.8)
        ax_top.set_ylabel(r"$\Delta x$ [ER]", fontsize=9, fontname="Inter")
        plt.setp(ax_top.get_xticklabels(), visible=False)
        ax_top.set_title(f"Lens Plane Geometry & Marginal Deviations - Event {event.event_id}", fontsize=11, fontweight="bold", color="#361d49", fontname="Inter", pad=15)

        # Right Marginal Plot (dy vs y_orig)
        plt.sca(ax_right)
        mask_y = (y_orig >= -limit) & (y_orig <= limit)
        ax_right.plot(dy[mask_y], y_orig[mask_y], color="#ec4899", lw=1.2, label=r"$\Delta y$")
        ax_right.axvline(0, color="gray", linestyle=":", lw=0.8)
        ax_right.set_xlabel(r"$\Delta y$ [ER]", fontsize=9, fontname="Inter")
        plt.setp(ax_right.get_yticklabels(), visible=False)

        # Set main active back to ax_main for legend/tight_layout
        plt.sca(ax_main)
    else:
        ax_main.axis("equal")

    if has_fit or has_truth:
        handles, labels = ax_main.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax_main.legend(by_label.values(), by_label.keys(), loc="best", framealpha=0.9, fontsize=8)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight" if has_orig_traj else None)
    plt.close()



def generate_lightcurve_plot(
    solution: Any,
    event: Any,
    data_path: Path,
    output_path: Path,
    data_dir: Optional[Path] = None,
    include_truth: bool = True,
) -> float:
    """Generates a premium interactive HTML plot of the lightcurve fit and residuals.

    Args:
        solution: Solution instance.
        event: Parent Event instance.
        data_path: Path to the observed lightcurve data file.
        output_path: Destination path for the generated plot.
        data_dir: Optional directory containing true simulation data.

    Returns:
        float: Best-fit chi2 value.
    """
    bands = getattr(solution, "bands", []) or []
    datasets = load_event_dataset(data_path, bands, event_id=event.event_id)

    best_event, chi2 = fit_best_model(
        datasets=datasets,
        solution_parameters=solution.parameters,
        model_type=solution.model_type,
        t_ref=solution.t_ref,
    )

    # Load truth lightcurve from original file only for tiers with trusted truth data.
    truth_df = None
    resolved_data_dir = data_dir or data_path.parent
    if include_truth:
        truth_df = load_truth_lightcurve(event.event_id, resolved_data_dir)

    # Force suffix to be .html
    html_path = output_path.with_suffix(".html")

    # Generate premium interactive Bokeh plot (saved as .html)
    _generate_bokeh_lightcurve_plot(
        solution=solution,
        event=event,
        datasets=datasets,
        best_event=best_event,
        chi2=chi2,
        output_html_path=html_path,
        truth_df=truth_df,
    )

    # Generate lens plane geometry plot (saved as lens_plane.png in the same directory)
    lens_plot_path = output_path.parent / "lens_plane.png"
    try:
        _dataset_coords = datasets[0].coords_str if (datasets and getattr(datasets[0], "coords_str", None)) else None
        generate_lens_plane_plot(
            solution,
            event,
            lens_plot_path,
            coords=_dataset_coords,
            data_dir=resolved_data_dir if include_truth else None,
        )
    except Exception as e:
        logging.warning("Could not generate lens plane geometry plot: %s", e)

    # Ensure backwards compatibility for tests/scripts checking output_path exists
    if output_path != html_path:
        try:
            import shutil
            shutil.copy2(html_path, output_path)
        except Exception as exc:
            logging.warning("Could not copy interactive plot to base output path: %s", exc)

    return chi2
