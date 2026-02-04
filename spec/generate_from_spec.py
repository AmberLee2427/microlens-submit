#!/usr/bin/env python
"""
Generate implementation code and documentation from the parameter spec.

This script reads `spec/parameter_spec.yaml` and generates:
1. Code snippets for `validate_parameters.py`
2. reStructuredText tables for `docs/submission_manual.rst`

Usage:
    python spec/generate_from_spec.py --preview     # Show what would be generated
    python spec/generate_from_spec.py --apply       # Apply changes to files
    python spec/generate_from_spec.py --docs-only   # Only regenerate docs
    python spec/generate_from_spec.py --code-only   # Only regenerate code

The generated code uses special markers to identify auto-generated sections:
    # --- BEGIN AUTO-GENERATED: MODEL_DEFINITIONS ---
    # --- END AUTO-GENERATED: MODEL_DEFINITIONS ---

WARNING: This script modifies source files. Always review changes before committing.
"""

import re
import sys
from pathlib import Path
from typing import Any

SPEC_DIR = Path(__file__).parent
PROJECT_ROOT = SPEC_DIR.parent

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(2)


def load_spec() -> dict[str, Any]:
    """Load the canonical parameter specification."""
    spec_path = SPEC_DIR / "parameter_spec.yaml"
    with open(spec_path) as f:
        data = yaml.safe_load(f)

    # Merge physical_parameters into parameters for unified processing
    if "physical_parameters" in data:
        if "parameters" not in data:
            data["parameters"] = {}

        # Add physical parameters to the main parameters dict
        for param_name, param_spec in data["physical_parameters"].items():
            # If category isn't set, default to 'physical'
            if "category" not in param_spec:
                param_spec["category"] = "physical"

            if param_name not in data["parameters"]:
                data["parameters"][param_name] = param_spec

    return data


def generate_model_definitions_python(spec: dict) -> str:
    """Generate MODEL_DEFINITIONS dictionary as Python code."""
    lines = ["MODEL_DEFINITIONS = {"]

    for model_type, model_spec in spec.get("model_types", {}).items():
        if model_spec.get("status") == "planned":
            # Comment out planned models
            lines.append(f"    # {model_type!r}: {{")
            lines.append(f'    #     "description": {model_spec.get("description", "")!r},')
            params = model_spec.get("required_params", [])
            lines.append(f'    #     "required_params_core": {params!r},')
            lines.append("    # },")
        else:
            lines.append(f"    {model_type!r}: {{")
            lines.append(f'        "description": {model_spec.get("description", "")!r},')
            params = model_spec.get("required_params", [])
            lines.append(f'        "required_params_core": {params!r},')
            lines.append("    },")

    lines.append("}")
    return "\n".join(lines)


def generate_effect_definitions_python(spec: dict) -> str:
    """Generate HIGHER_ORDER_EFFECT_DEFINITIONS dictionary as Python code."""
    lines = ["HIGHER_ORDER_EFFECT_DEFINITIONS = {"]

    for effect, effect_spec in spec.get("higher_order_effects", {}).items():
        lines.append(f"    {effect!r}: {{")
        lines.append(f'        "description": {effect_spec.get("description", "")!r},')
        lines.append(f'        "requires_t_ref": {effect_spec.get("requires_t_ref", False)!r},')

        req_params = effect_spec.get("required_params", [])
        lines.append(f'        "required_higher_order_params": {req_params!r},')

        opt_params = effect_spec.get("optional_params", [])
        if opt_params:
            lines.append(f'        "optional_higher_order_params": {opt_params!r},')

        lines.append("    },")

    lines.append("}")
    return "\n".join(lines)


def generate_parameter_properties_python(spec: dict) -> str:
    """Generate PARAMETER_PROPERTIES dictionary as Python code."""
    lines = ["PARAMETER_PROPERTIES = {"]

    # Group parameters by category
    params = spec.get("parameters", {})
    categories: dict[str, list[tuple[str, dict]]] = {}

    for param_name, param_spec in params.items():
        if param_spec.get("status") == "planned":
            continue
        category = param_spec.get("category", "other")
        if category not in categories:
            categories[category] = []
        categories[category].append((param_name, param_spec))

    # Category display names
    category_names = {
        "core": "Core Microlensing Parameters",
        "binary_lens": "Binary Lens Parameters",
        "triple_lens": "Triple Lens Parameters",
        "finite_source": "Finite Source Parameters",
        "parallax": "Parallax Parameters",
        "lens_orbital_motion": "Lens Orbital Motion Parameters",
        "gaussian_process": "Gaussian Process Parameters",
        "stellar_rotation": "Stellar Rotation Parameters",
        "limb_darkening": "Limb Darkening Parameters",
        "physical": "Derived Physical Parameters",
    }

    for category, category_params in categories.items():
        lines.append(f"    # {category_names.get(category, category.title())}")
        for param_name, param_spec in category_params:
            lines.append(f"    {param_name!r}: {{")
            lines.append(f'        "type": {param_spec.get("type", "float")!r},')
            lines.append(f'        "units": {param_spec.get("units", "")!r},')
            lines.append(f'        "description": {param_spec.get("description", "")!r},')
            lines.append("    },")
        lines.append("")

    lines.append("}")
    return "\n".join(lines)


def generate_tier_definitions_python(spec: dict) -> str:
    """Generate TIER_DEFINITIONS dictionary as Python code."""
    lines = ["TIER_DEFINITIONS = {"]

    for tier, tier_spec in spec.get("tiers", {}).items():
        lines.append(f"    {tier!r}: {{")
        lines.append(f'        "description": {tier_spec.get("description", "")!r},')

        if "event_prefix" in tier_spec:
            lines.append(f'        "event_prefix": {tier_spec["event_prefix"]!r},')

        if "event_range" in tier_spec:
            lines.append(f'        "event_range": {tier_spec["event_range"]!r},')

        if "event_list" in tier_spec:
            lines.append(f'        "event_list": {tier_spec["event_list"]!r},')

        lines.append("    },")

    lines.append("}")
    return "\n".join(lines)


def generate_model_type_rst_table(spec: dict) -> str:
    """Generate reStructuredText table for model types."""
    lines = [
        ".. list-table:: Model Types",
        "   :widths: 15 25 40 20",
        "   :header-rows: 1",
        "",
        "   * - Model Type",
        "     - Notation",
        "     - Required Parameters",
        "     - Status",
    ]

    for model_type, model_spec in spec.get("model_types", {}).items():
        status = model_spec.get("status", "active")
        if status == "planned":
            status_text = "Planned"
        else:
            status_text = "Active"

        params = ", ".join(f"``{p}``" for p in model_spec.get("required_params", []))
        if not params:
            params = "(none)"

        lines.extend(
            [
                f"   * - ``{model_type}``",
                f"     - {model_spec.get('notation', '')}",
                f"     - {params}",
                f"     - {status_text}",
            ]
        )

    return "\n".join(lines)


def generate_effects_rst_table(spec: dict) -> str:
    """Generate reStructuredText table for higher-order effects."""
    lines = [
        ".. list-table:: Higher-Order Effects",
        "   :widths: 20 10 30 40",
        "   :header-rows: 1",
        "",
        "   * - Effect",
        "     - t_ref",
        "     - Required Parameters",
        "     - Description",
    ]

    for effect, effect_spec in spec.get("higher_order_effects", {}).items():
        t_ref = "Yes" if effect_spec.get("requires_t_ref", False) else "No"
        params = ", ".join(f"``{p}``" for p in effect_spec.get("required_params", []))
        if not params:
            params = "(none)"

        lines.extend(
            [
                f"   * - ``{effect}``",
                f"     - {t_ref}",
                f"     - {params}",
                f"     - {effect_spec.get('description', '')}",
            ]
        )

    return "\n".join(lines)


def generate_parameters_rst_table(spec: dict, categories: list[str]) -> str:
    """Generate reStructuredText table for parameters filtered by category."""
    lines = [
        ".. list-table:: Parameter Reference",
        "   :widths: 15 10 15 45 15",
        "   :header-rows: 1",
        "",
        "   * - Parameter",
        "     - Type",
        "     - Units",
        "     - Description",
        "     - Category",
    ]

    for param_name, param_spec in spec.get("parameters", {}).items():
        if param_spec.get("status") == "planned":
            continue
        if param_spec.get("category") not in categories:
            continue
        units = param_spec.get("units", "")
        if not units:
            units = "—"

        category = param_spec.get("category", "")
        category_display = category.replace("_", " ").title()

        lines.extend(
            [
                f"   * - ``{param_name}``",
                f"     - {param_spec.get('type', 'float')}",
                f"     - {units}",
                f"     - {param_spec.get('description', '')}",
                f"     - {category_display}",
            ]
        )

    return "\n".join(lines)


def update_file_section(
    filepath: Path, start_marker: str, end_marker: str, new_content: str, preview: bool = False
) -> bool:
    """Update a section of a file between markers."""
    if not filepath.exists():
        print(f"  WARNING: File not found: {filepath}")
        return False

    content = filepath.read_text()

    # Find the section
    pattern = re.compile(
        rf"({re.escape(start_marker)})(.*?)({re.escape(end_marker)})",
        re.DOTALL,
    )

    match = pattern.search(content)
    if not match:
        print(f"  WARNING: Markers not found in {filepath}")
        print(f"    Start: {start_marker}")
        print(f"    End: {end_marker}")
        return False

    # Create replacement
    replacement = f"{start_marker}\n{new_content}\n{end_marker}"

    if preview:
        print(f"\n--- {filepath.relative_to(PROJECT_ROOT)} ---")
        print("Would replace lines between markers:")
        print(replacement[:500] + "..." if len(replacement) > 500 else replacement)
        return True

    new_content_full = pattern.sub(replacement, content)
    filepath.write_text(new_content_full)
    print(f"  Updated: {filepath.relative_to(PROJECT_ROOT)}")
    return True


def main():
    """Main entry point."""
    args = set(sys.argv[1:])

    preview = "--preview" in args
    docs_only = "--docs-only" in args
    code_only = "--code-only" in args
    apply_changes = "--apply" in args

    if not (preview or apply_changes):
        print("Usage:")
        print("  python spec/generate_from_spec.py --preview  # Show what would change")
        print("  python spec/generate_from_spec.py --apply    # Apply changes")
        print()
        print("Options:")
        print("  --docs-only   Only update documentation")
        print("  --code-only   Only update code files")
        sys.exit(0)

    print("=" * 60)
    print("Generating from Parameter Specification")
    print("=" * 60)

    spec = load_spec()
    print(f"Spec version: {spec.get('meta', {}).get('version', 'unknown')}")
    print()

    # Generate Python code
    if not docs_only:
        print("Generating Python code...")
        print(f"  MODEL_DEFINITIONS: {len(spec.get('model_types', {}))} models")
        print(f"  HIGHER_ORDER_EFFECT_DEFINITIONS: {len(spec.get('higher_order_effects', {}))} effects")
        print(f"  PARAMETER_PROPERTIES: {len(spec.get('parameters', {}))} parameters")

        model_code = generate_model_definitions_python(spec)
        effect_code = generate_effect_definitions_python(spec)
        param_code = generate_parameter_properties_python(spec)
        tier_code = generate_tier_definitions_python(spec)

        if preview:
            print("\n--- MODEL_DEFINITIONS (preview) ---")
            print(model_code[:800] + "..." if len(model_code) > 800 else model_code)

    # Generate RST documentation
    if not code_only:
        print("\nGenerating documentation tables...")
        model_table = generate_model_type_rst_table(spec)
        effect_table = generate_effects_rst_table(spec)
        core_categories = ["core", "binary_lens", "triple_lens"]
        higher_order_categories = [
            "finite_source",
            "parallax",
            "xallarap",
            "lens_orbital_motion",
            "gaussian_process",
            "stellar_rotation",
            "limb_darkening",
        ]
        core_param_table = generate_parameters_rst_table(spec, core_categories)
        higher_order_param_table = generate_parameters_rst_table(spec, higher_order_categories)

        if preview:
            print("\n--- Model Types Table (preview) ---")
            print(model_table)

    print()
    if preview:
        print("=" * 60)
        print("Preview complete. Use --apply to make changes.")
        print("=" * 60)
    elif apply_changes:
        files_updated = []
        if not docs_only:
            print("Applying code updates...")
            validate_path = PROJECT_ROOT / "microlens_submit" / "validate_parameters.py"
            tier_path = PROJECT_ROOT / "microlens_submit" / "tier_validation.py"

            files_updated.append(
                update_file_section(
                    validate_path,
                    "# --- BEGIN AUTO-GENERATED: MODEL_DEFINITIONS ---",
                    "# --- END AUTO-GENERATED: MODEL_DEFINITIONS ---",
                    model_code,
                )
            )
            files_updated.append(
                update_file_section(
                    validate_path,
                    "# --- BEGIN AUTO-GENERATED: HIGHER_ORDER_EFFECT_DEFINITIONS ---",
                    "# --- END AUTO-GENERATED: HIGHER_ORDER_EFFECT_DEFINITIONS ---",
                    effect_code,
                )
            )
            files_updated.append(
                update_file_section(
                    validate_path,
                    "# --- BEGIN AUTO-GENERATED: PARAMETER_PROPERTIES ---",
                    "# --- END AUTO-GENERATED: PARAMETER_PROPERTIES ---",
                    param_code,
                )
            )
            files_updated.append(
                update_file_section(
                    tier_path,
                    "# --- BEGIN AUTO-GENERATED: TIER_DEFINITIONS ---",
                    "# --- END AUTO-GENERATED: TIER_DEFINITIONS ---",
                    tier_code,
                )
            )

        if not code_only:
            print("Applying documentation updates...")
            manual_path = PROJECT_ROOT / "docs" / "submission_manual.rst"

            files_updated.append(
                update_file_section(
                    manual_path,
                    ".. BEGIN AUTO-GENERATED: MODEL_TYPES_TABLE",
                    ".. END AUTO-GENERATED: MODEL_TYPES_TABLE",
                    model_table,
                )
            )
            files_updated.append(
                update_file_section(
                    manual_path,
                    ".. BEGIN AUTO-GENERATED: HIGHER_ORDER_EFFECTS_TABLE",
                    ".. END AUTO-GENERATED: HIGHER_ORDER_EFFECTS_TABLE",
                    effect_table,
                )
            )
            files_updated.append(
                update_file_section(
                    manual_path,
                    ".. BEGIN AUTO-GENERATED: CORE_PARAMETERS_TABLE",
                    ".. END AUTO-GENERATED: CORE_PARAMETERS_TABLE",
                    core_param_table,
                )
            )
            files_updated.append(
                update_file_section(
                    manual_path,
                    ".. BEGIN AUTO-GENERATED: HIGHER_ORDER_PARAMETERS_TABLE",
                    ".. END AUTO-GENERATED: HIGHER_ORDER_PARAMETERS_TABLE",
                    higher_order_param_table,
                )
            )

        if not any(files_updated):
            print("No files updated. Ensure markers exist in target files.")
        print("=" * 60)
        print("Changes applied. Review and commit the modified files.")
        print("=" * 60)
        print()
        print("NOTE: Manual review recommended before committing.")
        print("Run tests: pytest tests/")


if __name__ == "__main__":
    main()
