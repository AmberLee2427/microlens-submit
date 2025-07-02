# microlens_submit/validation_rules.py

# Define core parameters that might be expected for different model types.
# This structure is a suggestion and can be adapted.
# 'required_params_core' are the fundamental microlensing parameters.
# 'required_higher_order_params' are parameters specifically associated with higher-order effects.
# 'optional_higher_order_params' are optional parameters for higher-order effects.
# 'special_attributes' are parameters that live outside the 'parameters' dictionary (like t_ref).

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