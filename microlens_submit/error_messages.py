"""
Enhanced error messaging for microlens-submit.

This module provides improved error messages with suggestions and context
to help users understand and fix issues more easily.
"""

import re
from typing import Dict, List, Optional

from microlens_submit.text_symbols import symbol


def get_model_type_suggestions(invalid_type: str) -> List[str]:
    """Get suggestions for model type corrections."""
    valid_types = ["1S1L", "1S2L", "2S1L", "2S2L", "1S3L", "2S3L", "other"]

    # Common typos and their corrections
    common_typos = {
        "1s1l": "1S1L",
        "1s2l": "1S2L",
        "2s1l": "2S1L",
        "2s2l": "2S2L",
        "1s3l": "1S3L",
        "2s3l": "2S3L",
        "1S1l": "1S1L",
        "1S2l": "1S2L",
        "2S1l": "2S1L",
        "2S2l": "2S2L",
        "1S3l": "1S3L",
        "2S3l": "2S3L",
        "1sl1": "1S1L",
        "1sl2": "1S2L",
        "2sl1": "2S1L",
        "2sl2": "2S2L",
        "1sl3": "1S3L",
        "2sl3": "2S3L",
    }

    suggestions = []

    # Check for exact typo match
    if invalid_type in common_typos:
        suggestions.append(f"Did you mean '{common_typos[invalid_type]}'?")

    # Check for similar patterns
    if invalid_type.upper() in valid_types:
        suggestions.append(f"Model types are case-sensitive. Try '{invalid_type.upper()}'")

    # Check for partial matches
    for valid_type in valid_types:
        if valid_type.lower() in invalid_type.lower() or invalid_type.lower() in valid_type.lower():
            if valid_type not in suggestions:
                suggestions.append(f"Did you mean '{valid_type}'?")

    return suggestions


def get_parameter_suggestions(model_type: str, user_param: str) -> List[str]:
    """Get suggestions for missing parameter corrections."""
    # Common parameter typos and their corrections
    common_typos = {
        "t0": ["t_0", "T0", "T_0"],
        "u0": ["u_0", "U0", "U_0"],
        "tE": ["te", "TE", "t_e", "T_E", "einstein_time"],
        "s": ["sep", "separation", "S"],
        "q": ["mass_ratio", "Q", "ratio"],
        "alpha": ["angle", "ANGLE", "ALPHA"],
        "piEN": ["pien", "PIEN", "pi_en", "PI_EN"],
        "piEE": ["piee", "PIEE", "pi_ee", "PI_EE"],
    }

    suggestions = []
    # If the user_param matches a typo for any canonical param,
    # suggest the canonical param
    for canonical, typos in common_typos.items():
        for typo in typos:
            if user_param.lower() == typo.lower():
                suggestions.append(f"Did you mean '{canonical}' instead of '{user_param}'?")
    # Also suggest case sensitivity if relevant
    for canonical in common_typos.keys():
        if user_param.lower() == canonical.lower() and user_param != canonical:
            suggestions.append(f"Parameter names are case-sensitive. Try '{canonical}'")
    return suggestions


def get_higher_order_effect_suggestions(invalid_effect: str) -> List[str]:
    """Get suggestions for higher-order effect corrections."""
    valid_effects = [
        "parallax",
        "finite-source",
        "lens-orbital-motion",
        "xallarap",
        "gaussian-process",
        "stellar-rotation",
        "fitted-limb-darkening",
    ]

    # Common typos and their corrections
    common_typos = {
        "parallax": ["paralax", "parallax", "PARALLAX"],
        "finite-source": [
            "finite_source",
            "finite source",
            "finite-source",
            "FINITE-SOURCE",
        ],
        "lens-orbital-motion": [
            "lens_orbital_motion",
            "lens orbital motion",
            "LENS-ORBITAL-MOTION",
        ],
        "xallarap": ["xallarap", "XALLARAP", "xallarap"],
        "gaussian-process": [
            "gaussian_process",
            "gaussian process",
            "GAUSSIAN-PROCESS",
        ],
        "stellar-rotation": [
            "stellar_rotation",
            "stellar rotation",
            "STELLAR-ROTATION",
        ],
        "fitted-limb-darkening": [
            "fitted_limb_darkening",
            "fitted limb darkening",
            "FITTED-LIMB-DARKENING",
        ],
    }

    suggestions = []

    # Check for exact typo match
    if invalid_effect in common_typos:
        for typo in common_typos[invalid_effect]:
            suggestions.append(f"Did you mean '{typo}' instead of '{invalid_effect}'?")

    # Check for case variations
    if invalid_effect.lower() in [e.lower() for e in valid_effects]:
        for effect in valid_effects:
            if effect.lower() == invalid_effect.lower():
                suggestions.append(f"Effect names are case-sensitive. Try '{effect}'")
                break

    # Check for partial matches
    for valid_effect in valid_effects:
        if valid_effect.lower() in invalid_effect.lower() or invalid_effect.lower() in valid_effect.lower():
            if valid_effect not in suggestions:
                suggestions.append(f"Did you mean '{valid_effect}'?")

    return suggestions


def format_validation_message(message: str, suggestions: Optional[List[str]] = None) -> str:
    """Format a validation message with optional suggestions."""
    if not suggestions:
        return message

    formatted = message
    if len(suggestions) == 1:
        formatted += f"\n{symbol('hint')} Suggestion: {suggestions[0]}"
    else:
        formatted += f"\n{symbol('hint')} Suggestions:"
        for suggestion in suggestions:
            formatted += f"\n   • {suggestion}"

    return formatted


def enhance_validation_messages(messages: List[str], model_type: str, parameters: Dict) -> List[str]:
    """Enhance validation messages with helpful suggestions."""
    enhanced_messages = []

    for message in messages:
        suggestions = []

        # Check for model type errors
        if "Unknown model type:" in message:
            # Extract the invalid model type from the message
            match = re.search(r"Unknown model type: '([^']+)'", message)
            if match:
                invalid_type = match.group(1)
                suggestions = get_model_type_suggestions(invalid_type)

        # Check for missing parameter errors
        elif "Missing required core parameter" in message:
            # Extract the missing parameter from the message
            match = re.search(r"Missing required core parameter '([^']+)'", message)
            if match:
                missing_param = match.group(1)
                suggestions = get_parameter_suggestions(model_type, missing_param)

        # Check for missing higher-order effect parameters
        elif "Missing required parameter" in message and "for effect" in message:
            # Extract the missing parameter and effect from the message
            match = re.search(r"Missing required parameter '([^']+)' for effect '([^']+)'", message)
            if match:
                missing_param = match.group(1)
                suggestions = get_parameter_suggestions(model_type, missing_param)

        # Check for unknown higher-order effect errors
        elif "Unknown higher-order effect:" in message:
            # Extract the invalid effect from the message
            match = re.search(r"Unknown higher-order effect: '([^']+)'", message)
            if match:
                invalid_effect = match.group(1)
                suggestions = get_higher_order_effect_suggestions(invalid_effect)

        # Check for unrecognized parameter warnings
        elif "Parameter" in message and "not recognized" in message:
            # Extract the unrecognized parameter from the message
            match = re.search(r"Parameter '([^']+)' not recognized", message)
            if not match:
                # Try with "Warning:" prefix
                match = re.search(r"Warning: Parameter '([^']+)' not recognized", message)
            if match:
                unrecognized_param = match.group(1)
                suggestions = get_parameter_suggestions(model_type, unrecognized_param)

        enhanced_messages.append(format_validation_message(message, suggestions))

    return enhanced_messages


def get_quick_fix_suggestions(model_type: str, missing_params: List[str]) -> List[str]:
    """Get quick fix suggestions for common missing parameters."""
    suggestions = []

    # Common parameter examples for each model type
    model_examples = {
        "1S1L": {"t0": "2459123.5", "u0": "0.1", "tE": "20.0"},
        "1S2L": {
            "t0": "2459123.5",
            "u0": "0.1",
            "tE": "20.0",
            "s": "1.2",
            "q": "0.001",
            "alpha": "45.0",
        },
        "2S1L": {
            "t0": "2459123.5",
            "u0": "0.1",
            "tE": "20.0",
            "q_flux": "0.5",
            "t_star": "0.1",
        },
    }

    if model_type in model_examples:
        examples = model_examples[model_type]
        for param in missing_params:
            if param in examples:
                suggestions.append(f"Add --param {param}={examples[param]}")

    return suggestions


def format_cli_error_with_suggestions(error_message: str, context: Dict) -> str:
    """Format CLI errors with contextual suggestions."""
    enhanced = error_message

    # Add context-specific suggestions
    if "model_type must be one of" in error_message:
        enhanced += f"\n\n{symbol('hint')} Quick Start Examples:"
        enhanced += (
            "\n   microlens-submit add-solution EVENT123 1S1L " "--param t0=2459123.5 --param u0=0.1 --param tE=20.0"
        )
        enhanced += (
            "\n   microlens-submit add-solution EVENT123 1S2L "
            "--param t0=2459123.5 --param u0=0.1 --param tE=20.0 "
            "--param s=1.2 --param q=0.001 --param alpha=45.0"
        )

    elif "Invalid parameter format" in error_message:
        enhanced += "\n\n�� Parameter Format:"
        enhanced += "\n   Use --param name=value (e.g., --param t0=2459123.5)"
        enhanced += "\n   Multiple parameters: --param t0=2459123.5 " "--param u0=0.1 --param tE=20.0"

    elif "Cannot use --param with --params-file" in error_message:
        enhanced += f"\n\n{symbol('hint')} Parameter Options:"
        enhanced += "\n   Use --param for individual parameters on command line"
        enhanced += "\n   Use --params-file for parameters from a JSON/YAML file"
        enhanced += "\n   Choose one method, not both"

    return enhanced
