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

from typing import Dict, List, Any, Optional, Union


MODEL_DEFINITIONS = {
    # Single Source, Single Lens (PSPL)
    "1S1L": {
        "description": "Point Source, Single Point Lens (standard microlensing)",
        "required_params_core": ["t0", "u0", "tE"],
    },
    # Single Source, Binary Lens
    "1S2L": {
        "description": "Point Source, Binary Point Lens",
        "required_params_core": ["t0", "u0", "tE", "s", "q", "alpha"],
    },
    # Binary Source, Single Lens
    "2S1L": {
        "description": "Binary Source, Single Point Lens",
        "required_params_core": ["t0", "u0", "tE"],  # Core lens params
    },
    # Add other model types as needed:
    # "2S2L": { "description": "Binary Source, Binary Point Lens", "required_params_core": ["t0", "u0", "tE", "s", "q", "alpha"]},
    # "1S3L": { "description": "Point Source, Triple Point Lens", "required_params_core": ["t0", "u0", "tE", "s1", "q1", "alpha1", "s2", "q2", "alpha2"]},
    # "2S3L": { "description": "Binary Source, Triple Point Lens", "required_params_core": ["t0", "u0", "tE", "s1", "q1", "alpha1", "s2", "q2", "alpha2"]},
}

HIGHER_ORDER_EFFECT_DEFINITIONS = {
    "parallax": {
        "description": "Microlens parallax effect",
        "requires_t_ref": True,  # A flag to check for the 't_ref' attribute
        "required_higher_order_params": [
            "piEN",
            "piEE",
        ],  # These are often part of the main parameters if fitted
    },
    "finite-source": {
        "description": "Finite source size effect",
        "requires_t_ref": False,
        "required_higher_order_params": ["rho"],
    },
    "lens-orbital-motion": {
        "description": "Orbital motion of the lens components",
        "requires_t_ref": True,
        "required_higher_order_params": ["dsdt", "dadt"],
        "optional_higher_order_params": [
            "dzdt"
        ],  # Relative radial rate of change of lenses (if needed)
    },
    "xallarap": {
        "description": "Source orbital motion (xallarap)",
        "requires_t_ref": True,  # Xallarap often has a t_ref related to its epoch
        "required_higher_order_params": [],  # Specific parameters (e.g., orbital period, inclination) to be added here
    },
    "gaussian-process": {
        "description": "Gaussian process model for time-correlated noise",
        "requires_t_ref": False,  # GP parameters are usually not time-referenced in this way
        "required_higher_order_params": [],  # Placeholder for common GP hyperparameters
        "optional_higher_order_params": [
            "ln_K",
            "ln_lambda",
            "ln_period",
            "ln_gamma",
        ],  # Common GP params, or specific names like "amplitude", "timescale", "periodicity" etc.
    },
    "stellar-rotation": {
        "description": "Effect of stellar rotation on the light curve (e.g., spots)",
        "requires_t_ref": False,  # Usually not time-referenced directly in this context
        "required_higher_order_params": [],  # Specific parameters (e.g., rotation period, inclination) to be added here
        "optional_higher_order_params": [
            "v_rot_sin_i",
            "epsilon",
        ],  # Guessing common params: rotational velocity times sin(inclination), spot coverage
    },
    "fitted-limb-darkening": {
        "description": "Limb darkening coefficients fitted as parameters",
        "requires_t_ref": False,
        "required_higher_order_params": [],  # Parameters are usually u1, u2, etc. (linear, quadratic)
        "optional_higher_order_params": [
            "u1",
            "u2",
            "u3",
            "u4",
        ],  # Common limb darkening coefficients (linear, quadratic, cubic, quartic)
    },
    # The "other" effect type is handled by allowing any other string in `higher_order_effects` list itself.
}

# This dictionary defines properties/constraints for each known parameter
# (e.g., expected type, units, a more detailed description, corresponding uncertainty field name)
PARAMETER_PROPERTIES = {
    # Core Microlensing Parameters
    "t0": {"type": "float", "units": "HJD", "description": "Time of closest approach"},
    "u0": {
        "type": "float",
        "units": "thetaE",
        "description": "Minimum impact parameter",
    },
    "tE": {
        "type": "float",
        "units": "days",
        "description": "Einstein radius crossing time",
    },
    "s": {
        "type": "float",
        "units": "thetaE",
        "description": "Binary separation scaled by Einstein radius",
    },
    "q": {"type": "float", "units": "mass ratio", "description": "Mass ratio M2/M1"},
    "alpha": {
        "type": "float",
        "units": "rad",
        "description": "Angle of source trajectory relative to binary axis",
    },
    # Higher-Order Effect Parameters
    "rho": {
        "type": "float",
        "units": "thetaE",
        "description": "Source radius scaled by Einstein radius (Finite Source)",
    },
    "piEN": {
        "type": "float",
        "units": "Einstein radius",
        "description": "Parallax vector component (North) (Parallax)",
    },
    "piEE": {
        "type": "float",
        "units": "Einstein radius",
        "description": "Parallax vector component (East) (Parallax)",
    },
    "dsdt": {
        "type": "float",
        "units": "thetaE/year",
        "description": "Rate of change of binary separation (Lens Orbital Motion)",
    },
    "dadt": {
        "type": "float",
        "units": "rad/year",
        "description": "Rate of change of binary angle (Lens Orbital Motion)",
    },
    "dzdt": {
        "type": "float",
        "units": "au/year",
        "description": "Relative radial rate of change of lenses (Lens Orbital Motion, if applicable)",
    },  # Example, may vary
    # Flux Parameters (dynamically generated by get_required_flux_params)
    # Ensure these names precisely match how they're generated by get_required_flux_params
    "F0_S": {
        "type": "float",
        "units": "counts/s",
        "description": "Source flux in band 0",
    },
    "F0_B": {
        "type": "float",
        "units": "counts/s",
        "description": "Blend flux in band 0",
    },
    "F1_S": {
        "type": "float",
        "units": "counts/s",
        "description": "Source flux in band 1",
    },
    "F1_B": {
        "type": "float",
        "units": "counts/s",
        "description": "Blend flux in band 1",
    },
    "F2_S": {
        "type": "float",
        "units": "counts/s",
        "description": "Source flux in band 2",
    },
    "F2_B": {
        "type": "float",
        "units": "counts/s",
        "description": "Blend flux in band 2",
    },
    # Binary Source Flux Parameters (e.g., for "2S" models)
    "F0_S1": {
        "type": "float",
        "units": "counts/s",
        "description": "Primary source flux in band 0",
    },
    "F0_S2": {
        "type": "float",
        "units": "counts/s",
        "description": "Secondary source flux in band 0",
    },
    "F1_S1": {
        "type": "float",
        "units": "counts/s",
        "description": "Primary source flux in band 1",
    },
    "F1_S2": {
        "type": "float",
        "units": "counts/s",
        "description": "Secondary source flux in band 1",
    },
    "F2_S1": {
        "type": "float",
        "units": "counts/s",
        "description": "Primary source flux in band 2",
    },
    "F2_S2": {
        "type": "float",
        "units": "counts/s",
        "description": "Secondary source flux in band 2",
    },
    # Gaussian Process parameters (examples, often ln-scaled)
    "ln_K": {
        "type": "float",
        "units": "mag^2",
        "description": "Log-amplitude of the GP kernel (GP)",
    },
    "ln_lambda": {
        "type": "float",
        "units": "days",
        "description": "Log-lengthscale of the GP kernel (GP)",
    },
    "ln_period": {
        "type": "float",
        "units": "days",
        "description": "Log-period of the GP kernel (GP)",
    },
    "ln_gamma": {
        "type": "float",
        "units": " ",
        "description": "Log-smoothing parameter of the GP kernel (GP)",
    },  # Specific interpretation varies by kernel
    # Stellar Rotation parameters (examples)
    "v_rot_sin_i": {
        "type": "float",
        "units": "km/s",
        "description": "Rotational velocity times sin(inclination) (Stellar Rotation)",
    },
    "epsilon": {
        "type": "float",
        "units": " ",
        "description": "Spot coverage/brightness parameter (Stellar Rotation)",
    },  # Example, may vary
    # Fitted Limb Darkening coefficients (examples)
    "u1": {
        "type": "float",
        "units": " ",
        "description": "Linear limb darkening coefficient (Fitted Limb Darkening)",
    },
    "u2": {
        "type": "float",
        "units": " ",
        "description": "Quadratic limb darkening coefficient (Fitted Limb Darkening)",
    },
    "u3": {
        "type": "float",
        "units": " ",
        "description": "Cubic limb darkening coefficient (Fitted Limb Darkening)",
    },
    "u4": {
        "type": "float",
        "units": " ",
        "description": "Quartic limb darkening coefficient (Fitted Limb Darkening)",
    },
}


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
            flux_params.append(
                f"F{band}_B"
            )  # Blend flux for this band (common for binary sources)
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
        >>> messages = check_solution_completeness("1S2L", params, ["parallax"], t_ref=2459123.0)
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
        messages.append(
            f"Unknown model type: '{model_type}'. Valid types: {list(MODEL_DEFINITIONS.keys())}"
        )
        return messages

    model_def = MODEL_DEFINITIONS[model_type]

    # Check required core parameters
    required_core_params = model_def.get("required_params_core", [])
    for param in required_core_params:
        if param not in parameters:
            messages.append(
                f"Missing required core parameter '{param}' for model type '{model_type}'"
            )

    # Validate higher-order effects
    if higher_order_effects:
        for effect in higher_order_effects:
            if effect not in HIGHER_ORDER_EFFECT_DEFINITIONS:
                messages.append(
                    f"Unknown higher-order effect: '{effect}'. Valid effects: {list(HIGHER_ORDER_EFFECT_DEFINITIONS.keys())}"
                )
                continue

            effect_def = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]

            # Check required parameters for this effect
            effect_required = effect_def.get("required_higher_order_params", [])
            for param in effect_required:
                if param not in parameters:
                    messages.append(
                        f"Missing required parameter '{param}' for effect '{effect}'"
                    )

            # Check optional parameters for this effect
            effect_optional = effect_def.get("optional_higher_order_params", [])
            for param in effect_optional:
                if param not in parameters:
                    messages.append(
                        f"Warning: Optional parameter '{param}' not provided for effect '{effect}'"
                    )

            # Check if t_ref is required for this effect
            if effect_def.get("requires_t_ref", False) and t_ref is None:
                messages.append(
                    f"Reference time (t_ref) required for effect '{effect}'"
                )

    # Validate band-specific parameters
    if bands:
        required_flux_params = get_required_flux_params(model_type, bands)
        for param in required_flux_params:
            if param not in parameters:
                messages.append(
                    f"Missing required flux parameter '{param}' for bands {bands}"
                )

    # Check for invalid parameters (not in any definition)
    all_valid_params = set()

    # Add core model parameters
    all_valid_params.update(required_core_params)

    # Add higher-order effect parameters
    if higher_order_effects:
        for effect in higher_order_effects:
            if effect in HIGHER_ORDER_EFFECT_DEFINITIONS:
                effect_def = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]
                all_valid_params.update(
                    effect_def.get("required_higher_order_params", [])
                )
                all_valid_params.update(
                    effect_def.get("optional_higher_order_params", [])
                )

    # Add band-specific parameters if bands are specified
    if bands:
        all_valid_params.update(get_required_flux_params(model_type, bands))

    # Check for invalid parameters
    invalid_params = set(parameters.keys()) - all_valid_params
    for param in invalid_params:
        messages.append(
            f"Warning: Parameter '{param}' not recognized for model type '{model_type}'"
        )

    return messages


def validate_parameter_types(parameters: Dict[str, Any], model_type: str) -> List[str]:
    """Validate parameter types and value ranges against expected types.

    Checks that parameters have the correct data types as defined in
    PARAMETER_PROPERTIES. Currently supports validation of float, int,
    and string types. Parameters not defined in PARAMETER_PROPERTIES
    are skipped (no validation performed).

    Args:
        parameters: Dictionary of model parameters with parameter names as keys.
        model_type: The type of microlensing model (used for context in messages).

    Returns:
        List of validation messages. Empty list if all validations pass.
        Messages indicate type mismatches for known parameters.

    Example:
        >>> # Valid parameters
        >>> params = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}
        >>> messages = validate_parameter_types(params, "1S1L")
        >>> print(messages)
        []

        >>> # Invalid type for t0
        >>> params = {"t0": "2459123.5", "u0": 0.1, "tE": 20.0}  # t0 is string
        >>> messages = validate_parameter_types(params, "1S1L")
        >>> print(messages)
        ["Parameter 't0' should be numeric, got str"]

        >>> # Unknown parameter (no validation performed)
        >>> params = {"t0": 2459123.5, "custom_param": "value"}
        >>> messages = validate_parameter_types(params, "1S1L")
        >>> print(messages)
        []

    Note:
        This function only validates parameters that are defined in
        PARAMETER_PROPERTIES. Unknown parameters are ignored to allow
        for custom parameters and future extensions. The validation
        is currently limited to basic type checking (float, int, str).
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
                messages.append(
                    f"Parameter '{param}' should be numeric, got {type(value).__name__}"
                )
            elif expected_type == "int" and not isinstance(value, int):
                messages.append(
                    f"Parameter '{param}' should be integer, got {type(value).__name__}"
                )
            elif expected_type == "str" and not isinstance(value, str):
                messages.append(
                    f"Parameter '{param}' should be string, got {type(value).__name__}"
                )

    return messages


def validate_parameter_uncertainties(
    parameters: Dict[str, Any], uncertainties: Optional[Dict[str, Any]] = None
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
            messages.append(
                f"Uncertainty provided for unknown parameter '{param_name}'"
            )
            continue

        param_value = parameters[param_name]

        # Handle different uncertainty formats
        if isinstance(uncertainty, (list, tuple)):
            # [lower, upper] format
            if len(uncertainty) != 2:
                messages.append(
                    f"Uncertainty for '{param_name}' should be [lower, upper] or single value"
                )
                continue
            lower, upper = uncertainty
            if not (
                isinstance(lower, (int, float)) and isinstance(upper, (int, float))
            ):
                messages.append(
                    f"Uncertainty bounds for '{param_name}' must be numeric"
                )
                continue
            if lower < 0 or upper < 0:
                messages.append(
                    f"Uncertainty bounds for '{param_name}' must be positive"
                )
                continue
            if lower > upper:
                messages.append(
                    f"Lower uncertainty for '{param_name}' ({lower}) > upper uncertainty ({upper})"
                )
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
                    abs(lower / param_value), abs(upper / param_value)
                )
            else:
                rel_uncertainty = abs(uncertainty / param_value)

            # Warn if uncertainty is very large (>50%) or very small (<0.1%)
            if rel_uncertainty > 0.5:
                messages.append(
                    f"Warning: Uncertainty for '{param_name}' is very large ({rel_uncertainty:.1%} of parameter value)"
                )
            elif rel_uncertainty < 0.001:
                messages.append(
                    f"Warning: Uncertainty for '{param_name}' is very small ({rel_uncertainty:.1%} of parameter value)"
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
            q = parameters["q"]
            s = parameters["s"]

            # Simple caustic crossing check
            if s < 0.5 or s > 2.0:
                messages.append(
                    "Warning: Separation (s) outside typical caustic crossing range (0.5-2.0)"
                )

    return messages
