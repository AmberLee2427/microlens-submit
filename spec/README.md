# Parameter Specification Directory

This directory contains the **single source of truth** for microlens-submit parameter definitions.

## Files

| File | Purpose |
|------|---------|
| `parameter_spec.yaml` | Canonical specification for all parameters, model types, tiers, and validation rules |
| `check_spec_drift.py` | Validates that implementation matches the spec (for CI) |
| `generate_from_spec.py` | Regenerates implementation code and docs from the spec |

## Workflow

### For Collaborators (Editing Parameters)

1. **Edit `parameter_spec.yaml`** with your changes
2. **Run the drift check** to see what's different:
   ```bash
   python spec/check_spec_drift.py --verbose
   ```
3. **Preview generated changes**:
   ```bash
   python spec/generate_from_spec.py --preview
   ```
4. **Apply changes** (when ready):
   ```bash
   python spec/generate_from_spec.py --apply
   ```
5. **Run tests** to verify nothing broke:
   ```bash
   pytest tests/
   ```

### For Agents (Reading Parameters)

The `parameter_spec.yaml` file is the authoritative source for:

- **Tier definitions** (`tiers`): What event IDs are valid for each tier
- **Model types** (`model_types`): What parameters each model requires
- **Higher-order effects** (`higher_order_effects`): What effects modify models
- **Parameters** (`parameters`): Type, units, and description for each parameter
- **Validation rules** (`validation_rules`): Constraints and error messages

When implementing changes to validation logic, read this file first.

## Spec Structure

```yaml
meta:                        # Version and maintainers
tiers:                       # Challenge tiers (beginner, experienced, etc.)
  <tier_name>:
    description: "..."
    event_prefix: "rmdc26_"  # OR event_list: [...]
    event_range: [0, 200]
    allowed_model_types: [...]
    allowed_higher_order_effects: [...]

model_types:                 # Model type definitions
  <model_type>:
    description: "..."
    notation: "1 Source, 1 Lens"
    required_params: [t0, u0, tE, ...]
    status: "active"         # or "planned"

higher_order_effects:        # Higher-order effect definitions
  <effect>:
    description: "..."
    requires_t_ref: true/false
    required_params: [...]
    optional_params: [...]

parameters:                  # Individual parameter definitions
  <param_name>:
    description: "..."
    type: float/int/str
    units: "HJD"
    category: core/binary_lens/parallax/...
    constraints:
      positive: true
      range: [0, 1]

validation_rules:            # Additional validation constraints
  parameter_constraints:
    <param>:
      must_be_positive: true
      range: [min, max]
      error: "Error message"
      warning: "Warning message"
```

## CI Integration

Add to your CI workflow:

```yaml
- name: Check parameter spec drift
  run: python spec/check_spec_drift.py
```

This will fail the build if the implementation has drifted from the spec.
