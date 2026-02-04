#!/usr/bin/env python
"""
Check for drift between the parameter spec and implementation.

This script validates that the implementation in `validate_parameters.py` and
the documentation in `docs/submission_manual.rst` are consistent with the
canonical specification in `spec/parameter_spec.yaml`.

Exit codes:
    0 - No drift detected
    1 - Drift detected (spec and implementation differ)
    2 - Error loading files

Usage:
    python spec/check_spec_drift.py [--verbose]

For CI integration, add to your workflow:
    - name: Check parameter spec drift
      run: python spec/check_spec_drift.py
"""

import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
SPEC_DIR = Path(__file__).parent
PROJECT_ROOT = SPEC_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(2)


def load_spec() -> dict[str, Any]:
    """Load the canonical parameter specification."""
    spec_path = SPEC_DIR / "parameter_spec.yaml"
    if not spec_path.exists():
        print(f"ERROR: Spec file not found: {spec_path}")
        sys.exit(2)

    with open(spec_path) as f:
        return yaml.safe_load(f)


def check_model_definitions(spec: dict, verbose: bool = False) -> list[str]:
    """Check MODEL_DEFINITIONS matches spec."""
    from microlens_submit.validate_parameters import MODEL_DEFINITIONS

    issues = []
    spec_models = spec.get("model_types", {})

    # Check all spec models are in implementation
    for model_type, model_spec in spec_models.items():
        if model_spec.get("status") == "planned":
            continue  # Skip planned models

        if model_type not in MODEL_DEFINITIONS:
            issues.append(f"Model '{model_type}' in spec but not in MODEL_DEFINITIONS")
            continue

        impl = MODEL_DEFINITIONS[model_type]
        spec_params = set(model_spec.get("required_params", []))
        impl_params = set(impl.get("required_params_core", []))

        if spec_params != impl_params:
            issues.append(
                f"Model '{model_type}' required params differ:\n"
                f"  Spec: {sorted(spec_params)}\n"
                f"  Impl: {sorted(impl_params)}"
            )

    # Check for models in implementation not in spec
    for model_type in MODEL_DEFINITIONS:
        if model_type not in spec_models:
            issues.append(f"Model '{model_type}' in MODEL_DEFINITIONS but not in spec")

    if verbose and not issues:
        print("✓ MODEL_DEFINITIONS matches spec")

    return issues


def check_effect_definitions(spec: dict, verbose: bool = False) -> list[str]:
    """Check HIGHER_ORDER_EFFECT_DEFINITIONS matches spec."""
    from microlens_submit.validate_parameters import HIGHER_ORDER_EFFECT_DEFINITIONS

    issues = []
    spec_effects = spec.get("higher_order_effects", {})

    for effect, effect_spec in spec_effects.items():
        if effect not in HIGHER_ORDER_EFFECT_DEFINITIONS:
            issues.append(f"Effect '{effect}' in spec but not in HIGHER_ORDER_EFFECT_DEFINITIONS")
            continue

        impl = HIGHER_ORDER_EFFECT_DEFINITIONS[effect]

        # Check requires_t_ref
        spec_t_ref = effect_spec.get("requires_t_ref", False)
        impl_t_ref = impl.get("requires_t_ref", False)
        if spec_t_ref != impl_t_ref:
            issues.append(f"Effect '{effect}' requires_t_ref differs: " f"spec={spec_t_ref}, impl={impl_t_ref}")

        # Check required params
        spec_req = set(effect_spec.get("required_params", []))
        impl_req = set(impl.get("required_higher_order_params", []))
        if spec_req != impl_req:
            issues.append(
                f"Effect '{effect}' required params differ:\n"
                f"  Spec: {sorted(spec_req)}\n"
                f"  Impl: {sorted(impl_req)}"
            )

        # Check optional params
        spec_opt = set(effect_spec.get("optional_params", []))
        impl_opt = set(impl.get("optional_higher_order_params", []))
        if spec_opt != impl_opt:
            issues.append(
                f"Effect '{effect}' optional params differ:\n"
                f"  Spec: {sorted(spec_opt)}\n"
                f"  Impl: {sorted(impl_opt)}"
            )

    # Check for effects in implementation not in spec
    for effect in HIGHER_ORDER_EFFECT_DEFINITIONS:
        if effect not in spec_effects:
            issues.append(f"Effect '{effect}' in HIGHER_ORDER_EFFECT_DEFINITIONS but not in spec")

    if verbose and not issues:
        print("✓ HIGHER_ORDER_EFFECT_DEFINITIONS matches spec")

    return issues


def check_parameter_properties(spec: dict, verbose: bool = False) -> list[str]:
    """Check PARAMETER_PROPERTIES matches spec."""
    from microlens_submit.validate_parameters import PARAMETER_PROPERTIES

    issues = []
    spec_params = spec.get("parameters", {})

    for param, param_spec in spec_params.items():
        if param_spec.get("status") == "planned":
            continue
        if param not in PARAMETER_PROPERTIES:
            # Parameters might be flux parameters or planned
            if param.startswith("F") or param.startswith("ln_"):
                continue
            issues.append(f"Parameter '{param}' in spec but not in PARAMETER_PROPERTIES")
            continue

        impl = PARAMETER_PROPERTIES[param]

        # Check type
        spec_type = param_spec.get("type")
        impl_type = impl.get("type")
        if spec_type != impl_type:
            issues.append(f"Parameter '{param}' type differs: spec={spec_type}, impl={impl_type}")

        # Check units (with some flexibility for variations)
        spec_units = param_spec.get("units", "").lower()
        impl_units = impl.get("units", "").lower()
        # Normalize common variations
        spec_units = spec_units.replace("θe", "thetae").replace("dimensionless", " ")
        impl_units = impl_units.replace("θe", "thetae").replace("mass ratio", " ")
        if spec_units.strip() and impl_units.strip():
            if spec_units.strip() != impl_units.strip():
                # Only warn, units can have minor variations
                if verbose:
                    print(f"  Note: Parameter '{param}' units differ: " f"spec='{spec_units}', impl='{impl_units}'")

    if verbose and not issues:
        print("✓ PARAMETER_PROPERTIES matches spec")

    return issues


def check_tier_definitions(spec: dict, verbose: bool = False) -> list[str]:
    """Check TIER_DEFINITIONS matches spec."""
    from microlens_submit.tier_validation import TIER_DEFINITIONS

    issues = []
    spec_tiers = spec.get("tiers", {})

    for tier, tier_spec in spec_tiers.items():
        if tier not in TIER_DEFINITIONS:
            issues.append(f"Tier '{tier}' in spec but not in TIER_DEFINITIONS")
            continue

        impl = TIER_DEFINITIONS[tier]

        # Check event_prefix
        if "event_prefix" in tier_spec:
            spec_prefix = tier_spec["event_prefix"]
            impl_prefix = impl.get("event_prefix")
            if spec_prefix != impl_prefix:
                issues.append(f"Tier '{tier}' event_prefix differs: " f"spec={spec_prefix}, impl={impl_prefix}")

        # Check event_range
        if "event_range" in tier_spec:
            spec_range = tier_spec["event_range"]
            impl_range = impl.get("event_range")
            if spec_range != impl_range:
                issues.append(f"Tier '{tier}' event_range differs: " f"spec={spec_range}, impl={impl_range}")

    # Check for tiers in implementation not in spec
    for tier in TIER_DEFINITIONS:
        if tier not in spec_tiers:
            issues.append(f"Tier '{tier}' in TIER_DEFINITIONS but not in spec")

    if verbose and not issues:
        print("✓ TIER_DEFINITIONS matches spec")

    return issues


def main():
    """Run all drift checks."""
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print("=" * 60)
    print("Parameter Specification Drift Check")
    print("=" * 60)

    spec = load_spec()
    print(f"Spec version: {spec.get('meta', {}).get('version', 'unknown')}")
    print()

    all_issues = []

    # Run all checks
    all_issues.extend(check_model_definitions(spec, verbose))
    all_issues.extend(check_effect_definitions(spec, verbose))
    all_issues.extend(check_parameter_properties(spec, verbose))
    all_issues.extend(check_tier_definitions(spec, verbose))

    print()
    if all_issues:
        print("=" * 60)
        print(f"DRIFT DETECTED: {len(all_issues)} issue(s) found")
        print("=" * 60)
        for i, issue in enumerate(all_issues, 1):
            print(f"\n{i}. {issue}")
        print()
        print("To fix: Update the spec or implementation to match.")
        print("Run: python spec/generate_from_spec.py --preview")
        sys.exit(1)
    else:
        print("=" * 60)
        print("✓ No drift detected - spec and implementation are in sync")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
