# microlens-submit v0.17.9 Release Notes

**Release Date:** 2026-05-08

## Highlights

This release fixes two validation issues reported by challenge users:

- RMDC event IDs now validate case-insensitively and use the six-digit challenge format, for example `rmdc26_000139`.
- `2S2L` is now recognized as a valid model type wherever model definitions are generated from `parameter_spec.yaml`.

## Changes

### Added
- Tier model-type metadata is now generated from `parameter_spec.yaml`.
- Spec drift checks now cover generated model status, tier event formats, allowed model types, and allowed higher-order effects.

### Changed
- Current RMDC tiers use `event_prefix: "rmdc26_"` plus six-digit formatting, avoiding accidental extra zeros in generated IDs.
- Event ID validation normalizes case before comparison.
- Generated `MODEL_DEFINITIONS` now includes all model types declared in the parameter spec, with each model's status preserved.
- CLI model-type validation and typo suggestions now use generated model definitions rather than stale hardcoded lists.

### Fixed
- Fixed valid `2S2L` solutions being rejected as `Unknown model type`.
- Fixed model-type error messages so the reported valid types stay synchronized with `parameter_spec.yaml`.
- Preserved the legacy `2018-test` three-digit `ulwdc1_293` event format while applying six-digit formatting to current RMDC tiers.

## Validation

- `python -m pytest -q` passed with 91 tests.
- `python spec/check_spec_drift.py` reported no drift.
