"""
Parameter validation module for microlens-submit.

This module provides centralized validation logic for checking solution completeness
and parameter consistency against model definitions. It validates microlensing
solutions against predefined model types, higher-order effects, and parameter
constraints to ensure submissions are complete and physically reasonable.

The module defines:
- Model definitions with required parameters for each model type
- Higher-order effect definitions with associated parameters
- Parameter properties including types, units, and descriptions
- Validation functions for completeness, types, uncertainties, and consistency

**Supported Model Types:**
- 1S1L: Point Source, Single Point Lens (standard microlensing)
- 1S2L: Point Source, Binary Point Lens
- 2S1L: Binary Source, Single Point Lens
- 2S2L: Binary Source, Binary Point Lens (commented)
- 1S3L: Point Source, Triple Point Lens (commented)
- 2S3L: Binary Source, Triple Point Lens (commented)

**Supported Higher-Order Effects:**
- parallax: Microlens parallax effect
- finite-source: Finite source size effect
- lens-orbital-motion: Orbital motion of lens components
- xallarap: Source orbital motion
- gaussian-process: Gaussian process noise modeling
- stellar-rotation: Stellar rotation effects
- fitted-limb-darkening: Fitted limb darkening coefficients

Example:
    >>> from microlens_submit.validate_parameters import check_solution_completeness
    >>>
    >>> # Validate a simple 1S1L solution
    >>> parameters = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}
    >>> messages = check_solution_completeness("1S1L", parameters)
    >>> if not messages:
    ...     print("Solution is complete!")
    >>> else:
    ...     print("Issues found:", messages)

    >>> # Validate a binary lens with parallax
    >>> parameters = {
    ...     "t0": 2459123.5, "u0": 0.1, "tE": 20.0,
    ...     "s": 1.2, "q": 0.5, "alpha": 45.0,
    ...     "piEN": 0.1, "piEE": 0.05
    ... }
    >>> effects = ["parallax"]
    >>> messages = check_solution_completeness("1S2L", parameters, effects, t_ref=2459123.0)
    >>> print("Validation messages:", messages)

Note:
    All validation functions return lists of human-readable messages instead
    of raising exceptions, allowing for comprehensive validation reporting.
    Unknown parameters generate warnings rather than errors to accommodate
    custom parameters and future model types.
"""

import re
from typing import Any, Dict, List, Optional

# --- BEGIN AUTO-GENERATED: MODEL_DEFINITIONS ---
MODEL_DEFINITIONS = {
    "1S1L": {
        "description": "Point Source, Single Point Lens (standard microlensing)",
        "required_params_core": ["t0", "u0", "tE"],
    },
    "1S2L": {
        "description": "Point Source, Binary Point Lens",
        "required_params_core": ["t0", "u0", "tE", "s", "q", "alpha"],
    },
    "2S1L": {
        "description": "Binary Source, Single Point Lens",
        "required_params_core": ["t0", "u0", "tE", "t0_source2", "u0_source2", "flux_ratio"],
    },
    # '2S2L': {
    #     "description": 'Binary Source, Binary Point Lens',
    #     "required_params_core": ['t0', 'u0', 'tE', 's', 'q', 'alpha', 't0_source2', 'u0_source2', 'flux_ratio'],
    # },
    # '1S3L': {
    #     "description": 'Point Source, Triple Point Lens',
    #     "required_params_core": ['t0', 'u0', 'tE'],
    # },
    # '2S3L': {
    #     "description": 'Binary Source, Triple Point Lens',
    #     "required_params_core": ['t0', 'u0', 'tE', 't0_source2', 'u0_source2', 'flux_ratio'],
    # },
    # '1S4L': {
    #     "description": 'Point Source, Quadruple Point Lens',
    #     "required_params_core": ['t0', 'u0', 'tE'],
    # },
    # '2S4L': {
    #     "description": 'Binary Source, Quadruple Point Lens',
    #     "required_params_core": ['t0', 'u0', 'tE', 't0_source2', 'u0_source2', 'flux_ratio'],
    # },
    "other": {
        "description": "Other or unknown model type",
        "required_params_core": [],
    },
}
# --- END AUTO-GENERATED: MODEL_DEFINITIONS ---

_FLUX_PARAM_RE = re.compile(r"^F(?P<band>\d+)_S(?:[12])?$|^F(?P<band_b>\d+)_B$")
_LD_PARAM_RE = re.compile(r"^u_(?P<band>\d+)$")


def _find_flux_params(parameters: Dict[str, Any]) -> List[str]:
    """Return a list of parameters that look like band-specific flux terms."""
    return [param for param in parameters.keys() if isinstance(param, str) and _FLUX_PARAM_RE.match(param)]


def _find_ld_params(parameters: Dict[str, Any]) -> List[str]:
    """Return a list of parameters that look like band-specific limb darkening terms."""
    return [param for param in parameters.keys() if isinstance(param, str) and _LD_PARAM_RE.match(param)]


def _infer_bands_from_flux_params(flux_params: List[str]) -> List[str]:
    """Infer band identifiers from flux parameter names."""
    bands = set()
    for param in flux_params:
        match = _FLUX_PARAM_RE.match(param)
        if not match:
            continue
        band = match.group("band") or match.group("band_b")
        if band is not None:
            bands.add(band)
    return sorted(bands)


# Metadata parameters that should NOT be counted in BIC calculations
# These are solution-level metadata, not model parameters
METADATA_PARAMETERS = {
    "t_ref",  # Reference time (metadata for time-dependent effects)
    "limb_darkening_coeffs",  # Fixed LD coefficients (not fitted)
    "limb_darkening_model",  # Name of LD model (not a parameter)
    "bands",  # List of photometric bands (not a parameter)
    "used_astrometry",  # Boolean flag (not a parameter)
    "used_postage_stamps",  # Boolean flag (not a parameter)
}

# Physical parameters (derived, not fitted in the microlensing model)
PHYSICAL_PARAMETERS = {
    "Mtot",
    "M1",
    "M2",
    "M3",
    "M4",  # Masses
    "D_L",
    "D_S",  # Distances
    "thetaE",  # Einstein radius
    "piE",
    "piE_N",
    "piE_E",
    "piE_parallel",
    "piE_perpendicular",
    "piE_l",
    "piE_b",  # Parallax
    "mu_rel",
    "mu_rel_N",
    "mu_rel_E",
    "mu_rel_l",
    "mu_rel_b",  # Proper motion
    "phi",  # Position angle
}


def count_model_parameters(parameters: Dict[str, Any]) -> int:
    """
    Count the number of actual model parameters for BIC calculation.

    Excludes:
    - Metadata parameters (t_ref, limb_darkening_coeffs, etc.)
    - Physical parameters (Mtot, D_L, etc.) - these are derived, not fitted

    Includes:
    - Core model parameters (t0, u0, tE, s, q, alpha, etc.)
    - Higher-order effect parameters (piEN, piEE, rho, etc.)
    - Flux parameters (F0_S, F0_B, etc.)
    - Fitted limb darkening parameters (u_0, u_1, etc.)

    Args:
        parameters: Dictionary of solution parameters

    Returns:
        Number of model parameters for BIC calculation

    Example:
        >>> params = {
        ...     't0': 2459123.5, 'u0': 0.1, 'tE': 20.0,
        ...     'piEN': 0.1, 'piEE': 0.05,
        ...     'F0_S': 1000.0, 'F0_B': 500.0,
        ...     't_ref': 2459123.0,  # metadata, not counted
        ...     'Mtot': 0.45,  # physical parameter, not counted
        ... }
        >>> count_model_parameters(params)
        6
    """
    count = 0
    for param in parameters.keys():
        # Skip metadata parameters
        if param in METADATA_PARAMETERS:
            continue
        # Skip physical parameters (derived, not fitted)
        if param in PHYSICAL_PARAMETERS:
            continue
        # Count everything else (core params, higher-order params, flux params, LD params)
        count += 1
    return count


# --- BEGIN AUTO-GENERATED: HIGHER_ORDER_EFFECT_DEFINITIONS ---
HIGHER_ORDER_EFFECT_DEFINITIONS = {
    "parallax": {
        "description": "Microlens parallax effect (annual parallax from Earth's orbital motion)",
        "requires_t_ref": True,
        "required_higher_order_params": ["piEN", "piEE"],
        "optional_higher_order_params": ["t_ref"],
    },
    "finite-source": {
        "description": "Finite source size effect",
        "requires_t_ref": False,
        "required_higher_order_params": ["rho"],
    },
    "lens-orbital-motion": {
        "description": "Orbital motion of lens components",
        "requires_t_ref": True,
        "required_higher_order_params": ["dsdt", "dadt"],
        "optional_higher_order_params": ["dzdt", "t_ref", "d2sdt2", "d2adt2"],
    },
    "xallarap": {
        "description": "Source orbital motion (xallarap is 'parallax' spelled backwards)",
        "requires_t_ref": True,
        "required_higher_order_params": ["xiEN", "xiEE", "P_xi"],
        "optional_higher_order_params": ["e_xi", "omega_xi", "i_xi"],
    },
    "gaussian-process": {
        "description": "Gaussian process model for time-correlated noise",
        "requires_t_ref": False,
        "required_higher_order_params": [],
        "optional_higher_order_params": ["ln_K", "ln_lambda", "ln_period", "ln_gamma", "ln_a", "ln_c"],
    },
    "stellar-rotation": {
        "description": "Effect of stellar rotation on the light curve (e.g., spots)",
        "requires_t_ref": False,
        "required_higher_order_params": [],
        "optional_higher_order_params": ["v_rot_sin_i", "epsilon"],
    },
    "fitted-limb-darkening": {
        "description": "Limb darkening coefficients fitted as parameters",
        "requires_t_ref": False,
        "required_higher_order_params": [],
    },
    "other": {
        "description": "Custom higher-order effect",
        "requires_t_ref": False,
        "required_higher_order_params": [],
    },
}
# --- END AUTO-GENERATED: HIGHER_ORDER_EFFECT_DEFINITIONS ---

# This dictionary defines properties/constraints for each known parameter
# (e.g., expected type, units, a more detailed description, corresponding
# uncertainty field name)
# --- BEGIN AUTO-GENERATED: PARAMETER_PROPERTIES ---
PARAMETER_PROPERTIES = {
    # Core Microlensing Parameters
    "t0": {
        "type": "float",
        "units": "HJD",
        "description": "Time of closest approach",
    },
    "u0": {
        "type": "float",
        "units": "θE",
        "description": "Minimum impact parameter",
    },
    "tE": {
        "type": "float",
        "units": "days",
        "description": "Einstein radius crossing time",
    },
    # Binary Lens Parameters
    "s": {
        "type": "float",
        "units": "θE",
        "description": "Binary separation scaled by Einstein radius",
    },
    "q": {
        "type": "float",
        "units": "dimensionless",
        "description": "Mass ratio M2/M1",
    },
    "alpha": {
        "type": "float",
        "units": "rad",
        "description": "Angle of source trajectory relative to binary axis",
    },
    # Binary_Source
    "t0_source2": {
        "type": "float",
        "units": "BJD",
        "description": "Time of closest approach for second source",
    },
    "u0_source2": {
        "type": "float",
        "units": "θE",
        "description": "Minimum impact parameter for second source",
    },
    "flux_ratio": {
        "type": "float",
        "units": "dimensionless",
        "description": "Flux ratio of second source to first source",
    },
    # Finite Source Parameters
    "rho": {
        "type": "float",
        "units": "θE",
        "description": "Source radius scaled by Einstein radius",
    },
    # Parallax Parameters
    "piEN": {
        "type": "float",
        "units": "θE",
        "description": "Parallax vector component (North)",
    },
    "piEE": {
        "type": "float",
        "units": "θE",
        "description": "Parallax vector component (East)",
    },
    # Lens Orbital Motion Parameters
    "dsdt": {
        "type": "float",
        "units": "θE/year",
        "description": "Rate of change of binary separation",
    },
    "dadt": {
        "type": "float",
        "units": "rad/year",
        "description": "Rate of change of binary orientation",
    },
    "dzdt": {
        "type": "float",
        "units": "au/year",
        "description": "Relative radial rate of change of lenses",
    },
    # Xallarap
    "xiEN": {
        "type": "float",
        "units": "θE",
        "description": "Xallarap vector component (North)",
    },
    "xiEE": {
        "type": "float",
        "units": "θE",
        "description": "Xallarap vector component (East)",
    },
    "P_xi": {
        "type": "float",
        "units": "days",
        "description": "Orbital period of the source companion",
    },
    "e_xi": {
        "type": "float",
        "units": "dimensionless",
        "description": "Eccentricity of source orbit",
    },
    "omega_xi": {
        "type": "float",
        "units": "rad",
        "description": "Argument of periapsis for source orbit",
    },
    "i_xi": {
        "type": "float",
        "units": "deg",
        "description": "Inclination of source orbit",
    },
    # Gaussian Process Parameters
    "ln_K": {
        "type": "float",
        "units": "mag²",
        "description": "Log-amplitude of the GP kernel",
    },
    "ln_lambda": {
        "type": "float",
        "units": "days",
        "description": "Log-lengthscale of the GP kernel",
    },
    "ln_period": {
        "type": "float",
        "units": "days",
        "description": "Log-period of the GP kernel",
    },
    "ln_gamma": {
        "type": "float",
        "units": "dimensionless",
        "description": "Log-smoothing parameter of the GP kernel",
    },
    # Stellar Rotation Parameters
    "v_rot_sin_i": {
        "type": "float",
        "units": "km/s",
        "description": "Rotational velocity times sin(inclination)",
    },
    "epsilon": {
        "type": "float",
        "units": "dimensionless",
        "description": "Spot coverage/brightness parameter",
    },
    # Other
    "flux_parameters": {
        "type": "float",
        "units": "",
        "description": "",
    },
    # Derived Physical Parameters
    "Mtot": {
        "type": "float",
        "units": "M_sun",
        "description": "Total lens mass",
    },
    "M1": {
        "type": "float",
        "units": "M_sun",
        "description": "Primary lens mass",
    },
    "M2": {
        "type": "float",
        "units": "M_sun",
        "description": "Secondary lens mass",
    },
    "M3": {
        "type": "float",
        "units": "M_sun",
        "description": "Tertiary lens mass",
    },
    "M4": {
        "type": "float",
        "units": "M_sun",
        "description": "Quaternary lens mass",
    },
    "D_L": {
        "type": "float",
        "units": "kpc",
        "description": "Lens distance from observer",
    },
    "D_S": {
        "type": "float",
        "units": "kpc",
        "description": "Source distance from observer",
    },
    "thetaE": {
        "type": "float",
        "units": "mas",
        "description": "Angular Einstein radius",
    },
    "piE": {
        "type": "float",
        "units": "dimensionless",
        "description": "Microlens parallax magnitude",
    },
    "piE_N": {
        "type": "float",
        "units": "dimensionless",
        "description": "North component of microlens parallax vector",
    },
    "piE_E": {
        "type": "float",
        "units": "dimensionless",
        "description": "East component of microlens parallax vector",
    },
    "piE_parallel": {
        "type": "float",
        "units": "dimensionless",
        "description": "Component of parallax vector parallel to lens-source relative motion",
    },
    "piE_perpendicular": {
        "type": "float",
        "units": "dimensionless",
        "description": "Component of parallax vector perpendicular to lens-source relative motion",
    },
    "piE_l": {
        "type": "float",
        "units": "dimensionless",
        "description": "Galactic longitude component of microlens parallax vector",
    },
    "piE_b": {
        "type": "float",
        "units": "dimensionless",
        "description": "Galactic latitude component of microlens parallax vector",
    },
    "mu_rel": {
        "type": "float",
        "units": "mas/yr",
        "description": "Magnitude of the relative proper motion between lens and source",
    },
    "mu_rel_N": {
        "type": "float",
        "units": "mas/yr",
        "description": "North component of the relative proper motion between lens and source",
    },
    "mu_rel_E": {
        "type": "float",
        "units": "mas/yr",
        "description": "East component of the relative proper motion between lens and source",
    },
    "mu_rel_l": {
        "type": "float",
        "units": "mas/yr",
        "description": "Galactic longitude component of the relative proper motion between lens and source",
    },
    "mu_rel_b": {
        "type": "float",
        "units": "mas/yr",
        "description": "Galactic latitude component of the relative proper motion between lens and source",
    },
    "phi": {
        "type": "float",
        "units": "rad",
        "description": "Angle of lens-source relative proper motion relative to ecliptic",
    },
}
# --- END AUTO-GENERATED: PARAMETER_PROPERTIES ---


def get_required_flux_params(model_type: str, bands: List[str]) -> List[str]:
    """Get the required flux parameters for a given model type and bands.

    Determines which flux parameters are required based on the model type
    (single vs binary source) and the photometric bands used. For single
    source models, each band requires source and blend flux parameters.
    For binary source models, each band requires two source fluxes and
    a common blend flux.

    Args:
        model_type: The type of microlensing model (e.g., "1S1L", "2S1L").
        bands: List of band IDs as strings (e.g., ["0", "1", "2"]).

    Returns:
        List of required flux parameter names (e.g., ["F0_S", "F0_B", "F1_S", "F1_B"]).

    Example:
        >>> get_required_flux_params("1S1L", ["0", "1"])
        ['F0_S', 'F0_B', 'F1_S', 'F1_B']

        >>> get_required_flux_params("2S1L", ["0", "1"])
        ['F0_S1', 'F0_S2', 'F0_B', 'F1_S1', 'F1_S2', 'F1_B']

        >>> get_required_flux_params("1S1L", [])
        []

    Note:
        This function handles the most common model types (1S and 2S).
        For models with more than 2 sources, additional logic would be needed.
        The function returns an empty list if no bands are specified.
    """
    flux_params = []
    if not bands:
        return flux_params  # No bands, no flux parameters

    for band in bands:
        if model_type.startswith("1S"):  # Single source models
            flux_params.append(f"F{band}_S")  # Source flux for this band
            flux_params.append(f"F{band}_B")  # Blend flux for this band
        elif model_type.startswith("2S"):  # Binary source models
            flux_params.append(f"F{band}_S1")  # First source flux for this band
            flux_params.append(f"F{band}_S2")  # Second source flux for this band
            flux_params.append(f"F{band}_B")  # Blend flux for this band
            # (common for binary sources)
        # Add more source types (e.g., 3S) if necessary in the future
    return flux_params


def check_solution_completeness(
    model_type: str,
    parameters: Dict[str, Any],
    higher_order_effects: Optional[List[str]] = None,
    bands: Optional[List[str]] = None,
    t_ref: Optional[float] = None,
    **kwargs,
) -> List[str]:
    """Check if a solution has all required parameters based on its model type and effects.

    This function validates that all required parameters are present for the given
    model type and any higher-order effects. It returns a list of human-readable
    warning or error messages instead of raising exceptions immediately.

    The validation checks:
    - Required core parameters for the model type
    - Required parameters for each higher-order effect
    - Flux parameters for specified photometric bands
    - Reference time requirements for time-dependent effects
    - Recognition of unknown parameters (warnings only)

    Args:
        model_type: The type of microlensing model (e.g., '1S1L', '1S2L').
        parameters: Dictionary of model parameters with parameter names as keys.
        higher_order_effects: List of higher-order effects (e.g., ['parallax', 'finite-source']).
            If None, no higher-order effects are assumed.
        bands: List of photometric bands used (e.g., ["0", "1", "2"]).
            If None, no band-specific parameters are required.
        t_ref: Reference time for time-dependent effects (Julian Date).
            Required for effects that specify requires_t_ref=True.
        **kwargs: Additional solution attributes to validate (currently unused).

    Returns:
        List of validation messages. Empty list if all validations pass.
        Messages indicate missing required parameters, unknown effects,
        missing reference times, or unrecognized parameters.

    Example:
        >>> # Simple 1S1L solution - should pass
        >>> params = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}
        >>> messages = check_solution_completeness("1S1L", params)
        >>> print(messages)
        []

        >>> # Missing required parameter
        >>> params = {"t0": 2459123.5, "u0": 0.1}  # Missing tE
        >>> messages = check_solution_completeness("1S1L", params)
        >>> print(messages)
        ["Missing required core parameter 'tE' for model type '1S1L'"]

        >>> # Binary lens with parallax
        >>> params = {
        ...     "t0": 2459123.5, "u0": 0.1, "tE": 20.0,
        ...     "s": 1.2, "q": 0.5, "alpha": 45.0,
        ...     "piEN": 0.1, "piEE": 0.05
        ... }
        >>> messages = check_solution_completeness(
        ...     "1S2L",
        ...     params,
        ...     ["parallax"],
        ...     t_ref=2459123.0
        ... )
        >>> print(messages)
        []

        >>> # Missing reference time for parallax
        >>> messages = check_solution_completeness("1S2L", params, ["parallax"])
        >>> print(messages)
        ["Reference time (t_ref) required for effect 'parallax'"]

    Note:
        This function is designed to be comprehensive but not overly strict.
        Unknown parameters generate warnings rather than errors to accommodate
        custom parameters and future model types. The function validates against
        the predefined MODEL_DEFINITIONS and HIGHER_ORDER_EFFECT_DEFINITIONS.
    """
    messages = []

    # Validate model type
    if model_type not in MODEL_DEFINITIONS:
        messages.append(f"Unknown model type: '{model_type}'. " f"Valid types: {list(MODEL_DEFINITIONS.keys())}")
        return messages

    model_def = MODEL_DEFINITIONS[model_type]

    # Check required core parameters
    required_core_params = model_def.get("required_params_core", [])
    for param in required_core_params:
        if param not in parameters:
            messages.append(f"Missing required core parameter '{param}' for model type " f"'{model_type}'")

    # Validate higher-order effects
    if higher_order_effects:
        for effect in higher_order_effects:
            if effect not in HIGHER_ORDER_EFFECT_DEFINITIONS:
                messages.append(
                    f"Unknown higher-order effect: '{effect}'. "
                    f"Valid effects: {list(HIGHER_ORDER_EFFECT_DEFINITIONS.keys())}"
                )
                continue

            effect_def = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]

            # Check required parameters for this effect
            effect_required = effect_def.get("required_higher_order_params", [])
            for param in effect_required:
                if param not in parameters:
                    messages.append(f"Missing required parameter '{param}' for effect " f"'{effect}'")

            # Check optional parameters for this effect
            effect_optional = effect_def.get("optional_higher_order_params", [])
            for param in effect_optional:
                if param not in parameters:
                    messages.append(f"Warning: Optional parameter '{param}' not provided " f"for effect '{effect}'")

            # Check if t_ref is required for this effect
            if effect_def.get("requires_t_ref", False) and t_ref is None:
                messages.append(f"Reference time (t_ref) required for effect '{effect}'")

    # Validate band-specific parameters
    flux_params = _find_flux_params(parameters)
    if flux_params and not bands:
        inferred_bands = _infer_bands_from_flux_params(flux_params)
        example_bands = inferred_bands or ["0"]
        messages.append(
            "Flux parameters were provided but bands is empty. "
            "Set bands to match your flux terms (Python API: solution.bands = "
            f"{example_bands!r})."
        )

    ld_params = _find_ld_params(parameters)
    if ld_params and not bands:
        messages.append("Limb darkening parameters (u_{band}) provided but bands is empty.")

    if bands:
        required_flux_params = get_required_flux_params(model_type, bands)
        for param in required_flux_params:
            if param not in parameters:
                messages.append(f"Missing required flux parameter '{param}' for bands " f"{bands}")

        # If fitted-limb-darkening is active, check for LD params
        if higher_order_effects and "fitted-limb-darkening" in higher_order_effects:
            for band in bands:
                expected_ld = f"u_{band}"
                if expected_ld not in parameters:
                    messages.append(f"Missing required limb darkening parameter '{expected_ld}' for band '{band}'")

    # Check for invalid parameters (not in any definition)
    all_valid_params = set()

    # Add core model parameters
    all_valid_params.update(required_core_params)

    # Add higher-order effect parameters
    if higher_order_effects:
        for effect in higher_order_effects:
            if effect in HIGHER_ORDER_EFFECT_DEFINITIONS:
                effect_def = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]
                all_valid_params.update(effect_def.get("required_higher_order_params", []))
                all_valid_params.update(effect_def.get("optional_higher_order_params", []))

    # Add band-specific parameters if bands are specified
    if bands:
        all_valid_params.update(get_required_flux_params(model_type, bands))

        # Add allowed LD params if effect is active
        if higher_order_effects and "fitted-limb-darkening" in higher_order_effects:
            for band in bands:
                all_valid_params.add(f"u_{band}")

    # Check for invalid parameters
    invalid_params = set(parameters.keys()) - all_valid_params
    if flux_params and not bands:
        invalid_params -= set(flux_params)

    # Allow LD params if fitted-limb-darkening is active
    # (even if not strictly in all_valid_params above if bands missing)
    if higher_order_effects and "fitted-limb-darkening" in higher_order_effects:
        invalid_params -= set(ld_params)

    for param in invalid_params:
        messages.append(f"Warning: Parameter '{param}' not recognized for model type '{model_type}'")

    return messages


def validate_parameter_types(
    parameters: Dict[str, Any],
    model_type: str,
) -> List[str]:
    """Validate parameter types and value ranges against expected types.

    ... (omitted docstring for brevity) ...
    """
    messages = []

    if model_type not in MODEL_DEFINITIONS:
        return [f"Unknown model type: '{model_type}'"]

    for param, value in parameters.items():
        if param in PARAMETER_PROPERTIES:
            prop = PARAMETER_PROPERTIES[param]
            # Check type
            expected_type = prop.get("type")
            if expected_type == "float" and not isinstance(value, (int, float)):
                messages.append(f"Parameter '{param}' should be numeric, got {type(value).__name__}")
            elif expected_type == "int" and not isinstance(value, int):
                messages.append(f"Parameter '{param}' should be integer, got {type(value).__name__}")
            elif expected_type == "str" and not isinstance(value, str):
                messages.append(f"Parameter '{param}' should be string, got {type(value).__name__}")
        elif _LD_PARAM_RE.match(param):
            if not isinstance(value, (int, float)):
                messages.append(f"Parameter '{param}' should be numeric, got {type(value).__name__}")

    return messages


def validate_parameter_uncertainties(
    parameters: Dict[str, Any],
    uncertainties: Optional[Dict[str, Any]] = None,
    physical_parameters: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Validate parameter uncertainties for reasonableness and consistency.

    Performs comprehensive validation of parameter uncertainties, including:
    - Format validation (single value or [lower, upper] pairs)
    - Sign validation (uncertainties must be positive)
    - Consistency checks (lower ≤ upper for asymmetric uncertainties)
    - Reasonableness checks (relative uncertainty between 0.1% and 50%)

    Args:
        parameters: Dictionary of model parameters with parameter names as keys.
        uncertainties: Dictionary of parameter uncertainties. Can be None if
            no uncertainties are provided. Supports two formats:
            - Single value: {"param": 0.1} (symmetric uncertainty)
            - Asymmetric bounds: {"param": [0.05, 0.15]} (lower, upper)

    Returns:
        List of validation messages. Empty list if all validations pass.
        Messages indicate format errors, sign issues, consistency problems,
        or warnings about very large/small relative uncertainties.

    Example:
        >>> # Valid symmetric uncertainties
        >>> params = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}
        >>> unc = {"t0": 0.1, "u0": 0.01, "tE": 0.5}
        >>> messages = validate_parameter_uncertainties(params, unc)
        >>> print(messages)
        []

        >>> # Valid asymmetric uncertainties
        >>> unc = {"t0": [0.05, 0.15], "u0": [0.005, 0.015]}
        >>> messages = validate_parameter_uncertainties(params, unc)
        >>> print(messages)
        []

        >>> # Invalid format
        >>> unc = {"t0": [0.1, 0.2, 0.3]}  # Too many values
        >>> messages = validate_parameter_uncertainties(params, unc)
        >>> print(messages)
        ["Uncertainty for 't0' should be [lower, upper] or single value"]

        >>> # Inconsistent bounds
        >>> unc = {"t0": [0.2, 0.1]}  # Lower > upper
        >>> messages = validate_parameter_uncertainties(params, unc)
        >>> print(messages)
        ["Lower uncertainty for 't0' (0.2) > upper uncertainty (0.1)"]

        >>> # Very large relative uncertainty
        >>> unc = {"t0": 1000.0}  # Very large uncertainty
        >>> messages = validate_parameter_uncertainties(params, unc)
        >>> print(messages)
        ["Warning: Uncertainty for 't0' is very large (40.8% of parameter value)"]

    Note:
        This function provides warnings rather than errors for very large
        or very small relative uncertainties, as these might be legitimate
        in some cases. The 0.1% to 50% range is a guideline based on
        typical microlensing parameter uncertainties.
    """
    messages = []

    if not uncertainties:
        return messages

    for param_name, uncertainty in uncertainties.items():
        if param_name not in parameters:
            # Check if it's a physical parameter
            if physical_parameters and param_name in physical_parameters:
                messages.append(
                    f"Physical parameter '{param_name}' found in parameter_uncertainties. "
                    "Move it to physical_parameter_uncertainties."
                )
            else:
                messages.append(f"Uncertainty provided for unknown parameter '{param_name}'")
            continue

        param_value = parameters[param_name]

        # Handle different uncertainty formats
        if isinstance(uncertainty, (list, tuple)):
            # [lower, upper] format
            if len(uncertainty) != 2:
                messages.append(f"Uncertainty for '{param_name}' should be [lower, upper] " f"or single value")
                continue
            lower, upper = uncertainty
            if not (isinstance(lower, (int, float)) and isinstance(upper, (int, float))):
                messages.append(f"Uncertainty bounds for '{param_name}' must be numeric")
                continue
            if lower < 0 or upper < 0:
                messages.append(f"Uncertainty bounds for '{param_name}' must be positive")
                continue
            if lower > upper:
                messages.append(f"Lower uncertainty for '{param_name}' ({lower}) > " f"upper uncertainty ({upper})")
                continue
        else:
            # Single value format
            if not isinstance(uncertainty, (int, float)):
                messages.append(f"Uncertainty for '{param_name}' must be numeric")
                continue
            if uncertainty < 0:
                messages.append(f"Uncertainty for '{param_name}' must be positive")
                continue
            lower = upper = uncertainty

        # Check if uncertainty is reasonable relative to parameter value
        if isinstance(param_value, (int, float)) and param_value != 0:
            # Calculate relative uncertainty
            if isinstance(uncertainty, (list, tuple)):
                rel_uncertainty = max(
                    abs(lower / param_value),
                    abs(upper / param_value),
                )
            else:
                rel_uncertainty = abs(uncertainty / param_value)

            # Warn if uncertainty is very large (>50%) or very small (<0.1%)
            if rel_uncertainty > 0.5:
                messages.append(
                    f"Warning: Uncertainty for '{param_name}' is very large "
                    f"({rel_uncertainty:.1%} of parameter value)"
                )
            elif rel_uncertainty < 0.001:
                messages.append(
                    f"Warning: Uncertainty for '{param_name}' is very small "
                    f"({rel_uncertainty:.1%} of parameter value)"
                )

    return messages


def validate_solution_consistency(
    model_type: str,
    parameters: Dict[str, Any],
    **kwargs: Any,
) -> List[str]:
    """Validate internal consistency of solution parameters.

    Performs physical consistency checks on microlensing parameters to
    identify potentially problematic values. This includes range validation,
    physical constraints, and model-specific consistency checks.

    Args:
        model_type: The type of microlensing model (e.g., '1S1L', '1S2L').
        parameters: Dictionary of model parameters with parameter names as keys.
        **kwargs: Additional solution attributes. Currently supports:
            relative_probability: Probability value for range checking (0-1).

    Returns:
        List of validation messages. Empty list if all validations pass.
        Messages indicate physical inconsistencies, range violations,
        or warnings about unusual parameter combinations.

    Example:
        >>> # Valid parameters
        >>> params = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}
        >>> messages = validate_solution_consistency("1S1L", params)
        >>> print(messages)
        []

        >>> # Invalid tE (must be positive)
        >>> params = {"t0": 2459123.5, "u0": 0.1, "tE": -5.0}
        >>> messages = validate_solution_consistency("1S1L", params)
        >>> print(messages)
        ["Einstein crossing time (tE) must be positive"]

        >>> # Invalid mass ratio
        >>> params = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "q": 1.5}
        >>> messages = validate_solution_consistency("1S2L", params)
        >>> print(messages)
        ["Mass ratio (q) should be between 0 and 1"]

        >>> # Invalid relative probability
        >>> messages = validate_solution_consistency("1S1L", params, relative_probability=1.5)
        >>> print(messages)
        ["Relative probability should be between 0 and 1"]

        >>> # Binary lens with unusual separation
        >>> params = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "s": 0.1, "q": 0.5}
        >>> messages = validate_solution_consistency("1S2L", params)
        >>> print(messages)
        ["Warning: Separation (s) outside typical caustic crossing range (0.5-2.0)"]

    Note:
        This function focuses on physical consistency rather than statistical
        validation. Warnings are provided for unusual but not impossible
        parameter combinations. The caustic crossing range check for binary
        lenses is a guideline based on typical microlensing events.
    """
    messages = []

    # Check for physically impossible values
    if "tE" in parameters and parameters["tE"] <= 0:
        messages.append("Einstein crossing time (tE) must be positive")

    if "q" in parameters and (parameters["q"] <= 0 or parameters["q"] > 1):
        messages.append("Mass ratio (q) should be between 0 and 1")

    if "s" in parameters and parameters["s"] <= 0:
        messages.append("Separation (s) must be positive")

    rel_prob = kwargs.get("relative_probability")
    if rel_prob is not None and not 0 <= rel_prob <= 1:
        messages.append("Relative probability should be between 0 and 1")

    # Check for binary lens specific consistency (1S2L, 2S2L models)
    if model_type in ["1S2L", "2S2L"]:
        if "q" in parameters and "s" in parameters:
            # Check for caustic crossing conditions
            s = parameters["s"]

            # Simple caustic crossing check
            if s < 0.5 or s > 2.0:
                messages.append("Warning: " "Separation (s) outside typical caustic crossing range " "(0.5-2.0)")

    # Run physical parameter validation
    messages.extend(validate_physical_parameters(parameters))

    return messages


def validate_uncertainty_metadata(
    parameter_uncertainties: Optional[Dict[str, Any]],
    physical_parameter_uncertainties: Optional[Dict[str, Any]],
    uncertainty_method: Optional[str],
    confidence_level: Optional[float],
) -> List[str]:
    """Validate uncertainty metadata for completeness and consistency.

    Provides recommendations (not requirements) for uncertainty reporting.
    """
    warnings = []

    # Check if uncertainties are provided without metadata
    has_param_unc = parameter_uncertainties is not None and len(parameter_uncertainties) > 0
    has_phys_unc = physical_parameter_uncertainties is not None and len(physical_parameter_uncertainties) > 0

    if (has_param_unc or has_phys_unc) and not uncertainty_method:
        warnings.append(
            "Recommendation: Uncertainties provided without uncertainty_method. "
            "Consider adding --uncertainty-method to improve evaluation "
            "(options: mcmc_posterior, fisher_matrix, bootstrap, propagation, inference, literature, other)"
        )

    # Validate confidence level if provided
    if confidence_level is not None:
        if not 0 < confidence_level < 1:
            warnings.append(f"Confidence level ({confidence_level}) should be between 0 and 1")
        elif confidence_level not in [0.68, 0.95, 0.997]:
            warnings.append(
                f"Unusual confidence_level: {confidence_level}. " "Standard values are 0.68 (1σ), 0.95 (2σ), 0.997 (3σ)"
            )

    # Validate uncertainty method if provided
    valid_methods = ["mcmc_posterior", "fisher_matrix", "bootstrap", "propagation", "inference", "literature", "other"]
    if uncertainty_method and uncertainty_method not in valid_methods:
        warnings.append(
            f"Unknown uncertainty_method: '{uncertainty_method}'. " f"Valid options: {', '.join(valid_methods)}"
        )

    # Recommend physical parameter uncertainties if physical parameters exist
    # (This is handled in validate_physical_parameters now)

    return warnings


def validate_physical_parameters(parameters: Dict[str, Any]) -> List[str]:
    """Validate physical parameters for consistency and range.

    Checks:
    - Mass consistency (Mtot vs sum of components)
    - Vector magnitude consistency
    - Distance limits and ordering (D_L < D_S)
    - Reasonable mass ranges (warn on unit confusion)
    """
    messages = []

    # 1. Mass Consistency
    # Check if Mtot matches sum of components (M1, M2, M3, M4)
    mass_components = []
    for k in ["M1", "M2", "M3", "M4"]:
        if k in parameters:
            mass_components.append(parameters[k])

    if "Mtot" in parameters and mass_components:
        total_comp = sum(mass_components)
        # Allow 1% error or 1e-6 absolute
        if abs(parameters["Mtot"] - total_comp) > max(parameters["Mtot"] * 0.01, 1e-6):
            messages.append(f"Total mass Mtot ({parameters['Mtot']}) does not match sum of components ({total_comp})")

    # 2. Vector Consistency
    # piE magnitude vs components (piE_N, piE_E)
    if "piE" in parameters and "piE_N" in parameters and "piE_E" in parameters:
        mag = (parameters["piE_N"] ** 2 + parameters["piE_E"] ** 2) ** 0.5
        if abs(parameters["piE"] - mag) > max(parameters["piE"] * 0.01, 1e-6):
            messages.append(
                f"piE magnitude ({parameters['piE']}) inconsistent with N/E components (calculated {mag:.4f})"
            )

    # mu_rel magnitude vs components (mu_rel_N, mu_rel_E)
    if "mu_rel" in parameters and "mu_rel_N" in parameters and "mu_rel_E" in parameters:
        mag = (parameters["mu_rel_N"] ** 2 + parameters["mu_rel_E"] ** 2) ** 0.5
        if abs(parameters["mu_rel"] - mag) > max(parameters["mu_rel"] * 0.01, 1e-6):
            messages.append(
                f"mu_rel magnitude ({parameters['mu_rel']}) inconsistent with N/E components (calculated {mag:.4f})"
            )

    # 3. Distance Checks
    if "D_L" in parameters and parameters["D_L"] > 25.0:
        messages.append(f"Warning: Lens distance D_L ({parameters['D_L']} kpc) is unusually large (> 25 kpc)")

    if "D_S" in parameters and parameters["D_S"] > 25.0:
        messages.append(f"Warning: Source distance D_S ({parameters['D_S']} kpc) is unusually large (> 25 kpc)")

    if "D_L" in parameters and "D_S" in parameters:
        if parameters["D_L"] >= parameters["D_S"]:
            messages.append(
                f"Lens distance D_L ({parameters['D_L']}) must be smaller "
                f"than source distance D_S ({parameters['D_S']})"
            )

    # 4. Mass Magnitude Warnings
    # Warn if any mass component is > 20 M_sun (possible unit confusion with Jupiter masses or unreasonable value)
    # Jupiter mass is ~0.001 Solar Mass (so 1 M_J ~ 0.001 M_S).
    # If they enter '1' meaning M_J, they get 1 M_S (reasonable).
    # If they enter '1000' meaning M_J (approx 1 M_S), they get 1000 M_S (unreasonable).
    for m_key in ["Mtot", "M1", "M2", "M3", "M4"]:
        if m_key in parameters and parameters[m_key] > 20.0:
            messages.append(
                f"Warning: {m_key} ({parameters[m_key]} M_sun) is very large. Check units (should be Solar masses)."
            )

    return messages


def validate_solution_rigorously(
    model_type: str,
    parameters: Dict[str, Any],
    higher_order_effects: Optional[List[str]] = None,
    bands: Optional[List[str]] = None,
    t_ref: Optional[float] = None,
    limb_darkening_coeffs: Optional[Dict[str, List[float]]] = None,
) -> List[str]:
    """Extremely rigorous validation of solution parameters.

    This function performs comprehensive validation that catches ALL parameter errors:
    - Parameter types must be correct (t_ref must be float, etc.)
    - No invalid parameters for model type (e.g., 's' parameter for 1S1L)
    - t_ref only allowed when required by higher-order effects
    - bands must be a list of strings
    - All required flux parameters must be present for each band
    - Only "other" model types or effects can have unknown parameters
    - If limb_darkening_coeffs is provided, it must match bands

    Args:
        model_type: The type of microlensing model
        parameters: Dictionary of model parameters
        higher_order_effects: List of higher-order effects
        bands: List of photometric bands
        t_ref: Reference time for time-dependent effects
        limb_darkening_coeffs: Dictionary of fixed limb darkening coefficients

    Returns:
        List of validation error messages. Empty list if all validations pass.
    """
    messages = []
    higher_order_effects = higher_order_effects or []
    bands = bands or []

    # 1. Validate t_ref type
    if t_ref is not None and not isinstance(t_ref, (int, float)):
        messages.append(f"t_ref must be numeric, got {type(t_ref).__name__}")

    # 2. Validate bands format
    if not isinstance(bands, list):
        messages.append(f"bands must be a list, got {type(bands).__name__}")
    else:
        for i, band in enumerate(bands):
            if not isinstance(band, str):
                messages.append(f"band {i} must be a string, got {type(band).__name__}")

    # Validate limb_darkening_coeffs if provided
    if limb_darkening_coeffs:
        if not isinstance(limb_darkening_coeffs, dict):
            messages.append(f"limb_darkening_coeffs must be a dict, got {type(limb_darkening_coeffs).__name__}")
        elif bands:
            # Check coverage of bands if bands are specified
            missing_ld_bands = [b for b in bands if b not in limb_darkening_coeffs]
            if missing_ld_bands:
                messages.append(f"limb_darkening_coeffs missing bands: {missing_ld_bands}")

            # Check for extra bands (warning)
            extra_ld_bands = [b for b in limb_darkening_coeffs if b not in bands]
            if extra_ld_bands:
                messages.append(f"limb_darkening_coeffs contains bands not in solution.bands: {extra_ld_bands}")

            # Validate structure
            for band, coeffs in limb_darkening_coeffs.items():
                if not isinstance(coeffs, list):
                    messages.append(f"limb_darkening_coeffs[{band!r}] must be a list of floats")
                elif not all(isinstance(c, (int, float)) for c in coeffs):
                    messages.append(f"limb_darkening_coeffs[{band!r}] must contain only numeric values")

    flux_params = _find_flux_params(parameters)
    if flux_params and not bands:
        inferred_bands = _infer_bands_from_flux_params(flux_params)
        example_bands = inferred_bands or ["0"]
        messages.append(
            "Flux parameters were provided but bands is empty. "
            "Set bands to match your flux terms (Python API: solution.bands = "
            f"{example_bands!r})."
        )

    # 3. Check if t_ref is provided when not needed
    t_ref_required = False
    for effect in higher_order_effects:
        if effect in HIGHER_ORDER_EFFECT_DEFINITIONS:
            if HIGHER_ORDER_EFFECT_DEFINITIONS[effect].get("requires_t_ref", False):
                t_ref_required = True
                break

    if not t_ref_required and t_ref is not None:
        messages.append("t_ref provided but not required by any higher-order effects")

    # 4. Get all valid parameters for this model and effects
    valid_params = set()

    # Add core model parameters
    if model_type in MODEL_DEFINITIONS:
        valid_params.update(MODEL_DEFINITIONS[model_type]["required_params_core"])
    elif model_type != "other":
        messages.append(f"Unknown model type: '{model_type}'")

    # Add higher-order effect parameters
    for effect in higher_order_effects:
        if effect in HIGHER_ORDER_EFFECT_DEFINITIONS:
            effect_def = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]
            valid_params.update(effect_def.get("required_higher_order_params", []))
            valid_params.update(effect_def.get("optional_higher_order_params", []))
        elif effect != "other":
            messages.append(f"Unknown higher-order effect: '{effect}'")

    # Add band-specific parameters
    if bands:
        valid_params.update(get_required_flux_params(model_type, bands))

    # 5. Check for invalid parameters (unless model_type or effects are "other")
    if model_type != "other" and "other" not in higher_order_effects:
        invalid_params = set(parameters.keys()) - valid_params
        if flux_params and not bands:
            invalid_params -= set(flux_params)
        for param in invalid_params:
            messages.append(f"Invalid parameter '{param}' for model type '{model_type}'")

    # 6. Validate parameter types for all parameters
    for param, value in parameters.items():
        if param in PARAMETER_PROPERTIES:
            prop = PARAMETER_PROPERTIES[param]
            expected_type = prop.get("type")

            if expected_type == "float" and not isinstance(value, (int, float)):
                messages.append(f"Parameter '{param}' must be numeric, got {type(value).__name__}")
            elif expected_type == "int" and not isinstance(value, int):
                messages.append(f"Parameter '{param}' must be integer, got {type(value).__name__}")
            elif expected_type == "str" and not isinstance(value, str):
                messages.append(f"Parameter '{param}' must be string, got {type(value).__name__}")

    # 7. Check for missing required parameters
    missing_core = []
    if model_type in MODEL_DEFINITIONS:
        for param in MODEL_DEFINITIONS[model_type]["required_params_core"]:
            if param not in parameters:
                missing_core.append(param)

    if missing_core:
        messages.append(f"Missing required parameters for {model_type}: {missing_core}")

    # 8. Check for missing higher-order effect parameters
    for effect in higher_order_effects:
        if effect in HIGHER_ORDER_EFFECT_DEFINITIONS:
            effect_def = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]
            required_params = effect_def.get("required_higher_order_params", [])
            missing_params = [param for param in required_params if param not in parameters]
            if missing_params:
                messages.append(f"Missing required parameters for effect '{effect}': {missing_params}")

    # 9. Check for missing flux parameters
    if bands:
        required_flux = get_required_flux_params(model_type, bands)
        missing_flux = [param for param in required_flux if param not in parameters]
        if missing_flux:
            messages.append(f"Missing required flux parameters for bands {bands}: {missing_flux}")

    # 10. Validate physical parameters
    physical_messages = validate_physical_parameters(parameters)
    messages.extend(physical_messages)

    return messages


def validate_solution_metadata(
    parameter_uncertainties: Optional[Dict[str, Any]] = None,
    physical_parameters: Optional[Dict[str, Any]] = None,
    physical_parameter_uncertainties: Optional[Dict[str, Any]] = None,
    uncertainty_method: Optional[str] = None,
    confidence_level: Optional[float] = None,
) -> List[str]:
    """Validate solution metadata including uncertainties.

    This is a convenience wrapper that calls all metadata validators.
    """
    messages = []

    # Validate uncertainty metadata
    unc_messages = validate_uncertainty_metadata(
        parameter_uncertainties,
        physical_parameter_uncertainties,
        uncertainty_method,
        confidence_level,
    )
    messages.extend(unc_messages)

    # Recommend physical parameter uncertainties if physical parameters provided
    if physical_parameters and not physical_parameter_uncertainties:
        messages.append(
            "Recommendation: Physical parameters provided without uncertainties. "
            "Consider adding --physical-param-uncertainty for better evaluation."
        )

    return messages
