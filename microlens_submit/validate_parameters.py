"""
Parameter validation module for microlens-submit.

This module provides centralized validation logic for checking solution completeness
and parameter consistency against model definitions.

 Define core parameters that might be expected for different model types.
 This structure is a suggestion and can be adapted.
 'required_params_core' are the fundamental microlensing parameters.
 'required_higher_order_params' are parameters specifically associated with higher-order effects.
 'optional_higher_order_params' are optional parameters for higher-order effects.
 'special_attributes' are parameters that live outside the 'parameters' dictionary (like t_ref).
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
        "required_params_core": ["t0", "u0", "tE"], # Core lens params
    },
    # Add other model types as needed:
    # "2S2L": { "description": "Binary Source, Binary Point Lens", "required_params_core": ["t0", "u0", "tE", "s", "q", "alpha"]},
    # "1S3L": { "description": "Point Source, Triple Point Lens", "required_params_core": ["t0", "u0", "tE", "s1", "q1", "alpha1", "s2", "q2", "alpha2"]},
    # "2S3L": { "description": "Binary Source, Triple Point Lens", "required_params_core": ["t0", "u0", "tE", "s1", "q1", "alpha1", "s2", "q2", "alpha2"]},
}

HIGHER_ORDER_EFFECT_DEFINITIONS = {
    "parallax": {
        "description": "Microlens parallax effect",
        "requires_t_ref": True, # A flag to check for the 't_ref' attribute
        "required_higher_order_params": ["piEN", "piEE"], # These are often part of the main parameters if fitted
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
        "optional_higher_order_params": ["dzdt"], # Relative radial rate of change of lenses (if needed)
    },
    "xallarap": {
        "description": "Source orbital motion (xallarap)",
        "requires_t_ref": True,  # Xallarap often has a t_ref related to its epoch
        "required_higher_order_params": [],  # Specific parameters (e.g., orbital period, inclination) to be added here
    },
    "gaussian-process": {
        "description": "Gaussian process model for time-correlated noise",
        "requires_t_ref": False, # GP parameters are usually not time-referenced in this way
        "required_higher_order_params": [], # Placeholder for common GP hyperparameters
        "optional_higher_order_params": ["ln_K", "ln_lambda", "ln_period", "ln_gamma"], # Common GP params, or specific names like "amplitude", "timescale", "periodicity" etc.
    },
    "stellar-rotation": {
        "description": "Effect of stellar rotation on the light curve (e.g., spots)",
        "requires_t_ref": False, # Usually not time-referenced directly in this context
        "required_higher_order_params": [], # Specific parameters (e.g., rotation period, inclination) to be added here
        "optional_higher_order_params": ["v_rot_sin_i", "epsilon"], # Guessing common params: rotational velocity times sin(inclination), spot coverage
    },
    "fitted-limb-darkening": {
        "description": "Limb darkening coefficients fitted as parameters",
        "requires_t_ref": False,
        "required_higher_order_params": [], # Parameters are usually u1, u2, etc. (linear, quadratic)
        "optional_higher_order_params": ["u1", "u2", "u3", "u4"], # Common limb darkening coefficients (linear, quadratic, cubic, quartic)
    },
    # The "other" effect type is handled by allowing any other string in `higher_order_effects` list itself.
}

# This dictionary defines properties/constraints for each known parameter
# (e.g., expected type, units, a more detailed description, corresponding uncertainty field name)
PARAMETER_PROPERTIES = {
    # Core Microlensing Parameters
    "t0": {"type": "float", "units": "HJD", "description": "Time of closest approach"},
    "u0": {"type": "float", "units": "thetaE", "description": "Minimum impact parameter"},
    "tE": {"type": "float", "units": "days", "description": "Einstein radius crossing time"},
    "s": {"type": "float", "units": "thetaE", "description": "Binary separation scaled by Einstein radius"},
    "q": {"type": "float", "units": "mass ratio", "description": "Mass ratio M2/M1"},
    "alpha": {"type": "float", "units": "rad", "description": "Angle of source trajectory relative to binary axis"},
    
    # Higher-Order Effect Parameters
    "rho": {"type": "float", "units": "thetaE", "description": "Source radius scaled by Einstein radius (Finite Source)"},
    "piEN": {"type": "float", "units": "Einstein radius", "description": "Parallax vector component (North) (Parallax)"},
    "piEE": {"type": "float", "units": "Einstein radius", "description": "Parallax vector component (East) (Parallax)"},
    "dsdt": {"type": "float", "units": "thetaE/year", "description": "Rate of change of binary separation (Lens Orbital Motion)"},
    "dadt": {"type": "float", "units": "rad/year", "description": "Rate of change of binary angle (Lens Orbital Motion)"},
    "dzdt": {"type": "float", "units": "au/year", "description": "Relative radial rate of change of lenses (Lens Orbital Motion, if applicable)"}, # Example, may vary
    
    # Flux Parameters (dynamically generated by get_required_flux_params)
    # Ensure these names precisely match how they're generated by get_required_flux_params
    "F0_S": {"type": "float", "units": "counts/s", "description": "Source flux in band 0"},
    "F0_B": {"type": "float", "units": "counts/s", "description": "Blend flux in band 0"},
    "F1_S": {"type": "float", "units": "counts/s", "description": "Source flux in band 1"},
    "F1_B": {"type": "float", "units": "counts/s", "description": "Blend flux in band 1"},
    "F2_S": {"type": "float", "units": "counts/s", "description": "Source flux in band 2"},
    "F2_B": {"type": "float", "units": "counts/s", "description": "Blend flux in band 2"},

    # Binary Source Flux Parameters (e.g., for "2S" models)
    "F0_S1": {"type": "float", "units": "counts/s", "description": "Primary source flux in band 0"},
    "F0_S2": {"type": "float", "units": "counts/s", "description": "Secondary source flux in band 0"},
    "F1_S1": {"type": "float", "units": "counts/s", "description": "Primary source flux in band 1"},
    "F1_S2": {"type": "float", "units": "counts/s", "description": "Secondary source flux in band 1"},
    "F2_S1": {"type": "float", "units": "counts/s", "description": "Primary source flux in band 2"},
    "F2_S2": {"type": "float", "units": "counts/s", "description": "Secondary source flux in band 2"},

    # Gaussian Process parameters (examples, often ln-scaled)
    "ln_K": {"type": "float", "units": "mag^2", "description": "Log-amplitude of the GP kernel (GP)"},
    "ln_lambda": {"type": "float", "units": "days", "description": "Log-lengthscale of the GP kernel (GP)"},
    "ln_period": {"type": "float", "units": "days", "description": "Log-period of the GP kernel (GP)"},
    "ln_gamma": {"type": "float", "units": " ", "description": "Log-smoothing parameter of the GP kernel (GP)"}, # Specific interpretation varies by kernel
    
    # Stellar Rotation parameters (examples)
    "v_rot_sin_i": {"type": "float", "units": "km/s", "description": "Rotational velocity times sin(inclination) (Stellar Rotation)"},
    "epsilon": {"type": "float", "units": " ", "description": "Spot coverage/brightness parameter (Stellar Rotation)"}, # Example, may vary
    
    # Fitted Limb Darkening coefficients (examples)
    "u1": {"type": "float", "units": " ", "description": "Linear limb darkening coefficient (Fitted Limb Darkening)"},
    "u2": {"type": "float", "units": " ", "description": "Quadratic limb darkening coefficient (Fitted Limb Darkening)"},
    "u3": {"type": "float", "units": " ", "description": "Cubic limb darkening coefficient (Fitted Limb Darkening)"},
    "u4": {"type": "float", "units": " ", "description": "Quartic limb darkening coefficient (Fitted Limb Darkening)"},
}

def get_required_flux_params(model_type, bands):
    """
    Get the required flux parameters for a given model type and bands.
    
    Args:
        model_type (str): The type of model (e.g., "1S1L", "2S1L")
        bands (list): List of band IDs (e.g., ["0", "1", "2"])
    
    Returns:
        list: List of required flux parameters (e.g., ["F0_S", "F0_B", "F1_S", "F1_B"])
    """
    flux_params = []
    if not bands:
        return flux_params # No bands, no flux parameters
        
    for band in bands:
        if model_type.startswith("1S"): # Single source models
            flux_params.append(f"F{band}_S") # Source flux for this band
            flux_params.append(f"F{band}_B") # Blend flux for this band
        elif model_type.startswith("2S"): # Binary source models
            flux_params.append(f"F{band}_S1") # First source flux for this band
            flux_params.append(f"F{band}_S2") # Second source flux for this band
            flux_params.append(f"F{band}_B")  # Blend flux for this band (common for binary sources)
        # Add more source types (e.g., 3S) if necessary in the future
    return flux_params


def check_solution_completeness(
    model_type: str,
    parameters: Dict[str, Any],
    higher_order_effects: Optional[List[str]] = None,
    bands: Optional[List[str]] = None,
    t_ref: Optional[float] = None,
    **kwargs
) -> List[str]:
    """
    Check if a solution has all required parameters based on its model type and effects.
    
    This function validates that all required parameters are present for the given
    model type and any higher-order effects. It returns a list of human-readable
    warning or error messages instead of raising exceptions immediately.
    
    Args:
        model_type: The type of microlensing model (e.g., '1S1L', '1S2L')
        parameters: Dictionary of model parameters
        higher_order_effects: List of higher-order effects (e.g., ['parallax', 'finite-source'])
        bands: List of photometric bands used
        t_ref: Reference time for time-dependent effects
        **kwargs: Additional solution attributes to validate
        
    Returns:
        List of validation messages (empty list if all validations pass)
    """
    messages = []
    
    # Validate model type
    if model_type not in MODEL_DEFINITIONS:
        messages.append(f"Unknown model type: '{model_type}'. Valid types: {list(MODEL_DEFINITIONS.keys())}")
        return messages
    
    model_def = MODEL_DEFINITIONS[model_type]
    
    # Check required core parameters
    required_core_params = model_def.get('required_params_core', [])
    for param in required_core_params:
        if param not in parameters:
            messages.append(f"Missing required core parameter '{param}' for model type '{model_type}'")
    
    # Validate higher-order effects
    if higher_order_effects:
        for effect in higher_order_effects:
            if effect not in HIGHER_ORDER_EFFECT_DEFINITIONS:
                messages.append(f"Unknown higher-order effect: '{effect}'. Valid effects: {list(HIGHER_ORDER_EFFECT_DEFINITIONS.keys())}")
                continue
            
            effect_def = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]
            
            # Check required parameters for this effect
            effect_required = effect_def.get('required_higher_order_params', [])
            for param in effect_required:
                if param not in parameters:
                    messages.append(f"Missing required parameter '{param}' for effect '{effect}'")
            
            # Check optional parameters for this effect
            effect_optional = effect_def.get('optional_higher_order_params', [])
            for param in effect_optional:
                if param not in parameters:
                    messages.append(f"Warning: Optional parameter '{param}' not provided for effect '{effect}'")
            
            # Check if t_ref is required for this effect
            if effect_def.get('requires_t_ref', False) and t_ref is None:
                messages.append(f"Reference time (t_ref) required for effect '{effect}'")
    
    # Validate band-specific parameters
    if bands:
        required_flux_params = get_required_flux_params(model_type, bands)
        for param in required_flux_params:
            if param not in parameters:
                messages.append(f"Missing required flux parameter '{param}' for bands {bands}")
    
    # Check for invalid parameters (not in any definition)
    all_valid_params = set()
    
    # Add core model parameters
    all_valid_params.update(required_core_params)
    
    # Add higher-order effect parameters
    if higher_order_effects:
        for effect in higher_order_effects:
            if effect in HIGHER_ORDER_EFFECT_DEFINITIONS:
                effect_def = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]
                all_valid_params.update(effect_def.get('required_higher_order_params', []))
                all_valid_params.update(effect_def.get('optional_higher_order_params', []))
    
    # Add band-specific parameters if bands are specified
    if bands:
        all_valid_params.update(get_required_flux_params(model_type, bands))
    
    # Check for invalid parameters
    invalid_params = set(parameters.keys()) - all_valid_params
    for param in invalid_params:
        messages.append(f"Warning: Parameter '{param}' not recognized for model type '{model_type}'")
    
    return messages


def validate_parameter_types(
    parameters: Dict[str, Any],
    model_type: str
) -> List[str]:
    """
    Validate parameter types and value ranges.
    
    Args:
        parameters: Dictionary of model parameters
        model_type: The type of microlensing model
        
    Returns:
        List of validation messages
    """
    messages = []
    
    if model_type not in MODEL_DEFINITIONS:
        return [f"Unknown model type: '{model_type}'"]
    
    for param, value in parameters.items():
        if param in PARAMETER_PROPERTIES:
            prop = PARAMETER_PROPERTIES[param]
            
            # Check type
            expected_type = prop.get('type')
            if expected_type == 'float' and not isinstance(value, (int, float)):
                messages.append(f"Parameter '{param}' should be numeric, got {type(value).__name__}")
            elif expected_type == 'int' and not isinstance(value, int):
                messages.append(f"Parameter '{param}' should be integer, got {type(value).__name__}")
            elif expected_type == 'str' and not isinstance(value, str):
                messages.append(f"Parameter '{param}' should be string, got {type(value).__name__}")
    
    return messages


def validate_parameter_uncertainties(
    parameters: Dict[str, Any],
    uncertainties: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Validate parameter uncertainties for reasonableness and consistency.
    
    Args:
        parameters: Dictionary of model parameters
        uncertainties: Dictionary of parameter uncertainties
        
    Returns:
        List of validation messages
    """
    messages = []
    
    if not uncertainties:
        return messages
    
    for param_name, uncertainty in uncertainties.items():
        if param_name not in parameters:
            messages.append(f"Uncertainty provided for unknown parameter '{param_name}'")
            continue
            
        param_value = parameters[param_name]
        
        # Handle different uncertainty formats
        if isinstance(uncertainty, (list, tuple)):
            # [lower, upper] format
            if len(uncertainty) != 2:
                messages.append(f"Uncertainty for '{param_name}' should be [lower, upper] or single value")
                continue
            lower, upper = uncertainty
            if not (isinstance(lower, (int, float)) and isinstance(upper, (int, float))):
                messages.append(f"Uncertainty bounds for '{param_name}' must be numeric")
                continue
            if lower < 0 or upper < 0:
                messages.append(f"Uncertainty bounds for '{param_name}' must be positive")
                continue
            if lower > upper:
                messages.append(f"Lower uncertainty for '{param_name}' ({lower}) > upper uncertainty ({upper})")
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
                rel_uncertainty = max(abs(lower/param_value), abs(upper/param_value))
            else:
                rel_uncertainty = abs(uncertainty/param_value)
            
            # Warn if uncertainty is very large (>50%) or very small (<0.1%)
            if rel_uncertainty > 0.5:
                messages.append(f"Warning: Uncertainty for '{param_name}' is very large ({rel_uncertainty:.1%} of parameter value)")
            elif rel_uncertainty < 0.001:
                messages.append(f"Warning: Uncertainty for '{param_name}' is very small ({rel_uncertainty:.1%} of parameter value)")
    
    return messages


def validate_solution_consistency(
    model_type: str,
    parameters: Dict[str, Any],
    **kwargs: Any,
) -> List[str]:
    """
    Validate internal consistency of solution parameters.
    
    Args:
        model_type: The type of microlensing model
        parameters: Dictionary of model parameters
        **kwargs: Additional solution attributes. Supports
            ``relative_probability`` for range checking.
        
    Returns:
        List of validation messages
    """
    messages = []
    
    # Check for physically impossible values
    if 'tE' in parameters and parameters['tE'] <= 0:
        messages.append("Einstein crossing time (tE) must be positive")
    
    if 'q' in parameters and (parameters['q'] <= 0 or parameters['q'] > 1):
        messages.append("Mass ratio (q) should be between 0 and 1")
    
    if 's' in parameters and parameters['s'] <= 0:
        messages.append("Separation (s) must be positive")

    rel_prob = kwargs.get("relative_probability")
    if rel_prob is not None and not 0 <= rel_prob <= 1:
        messages.append("Relative probability should be between 0 and 1")
    
    # Check for binary lens specific consistency (1S2L, 2S2L models)
    if model_type in ['1S2L', '2S2L']:
        if 'q' in parameters and 's' in parameters:
            # Check for caustic crossing conditions
            q = parameters['q']
            s = parameters['s']
            
            # Simple caustic crossing check
            if s < 0.5 or s > 2.0:
                messages.append("Warning: Separation (s) outside typical caustic crossing range (0.5-2.0)")
    
    return messages
