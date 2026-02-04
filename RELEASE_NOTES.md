# microlens-submit v0.17.0 Release Notes

**Release Date:** 2026-02-04

## Changelog

## [0.17.0] - 2026-02-04

### Added
- **Physical Parameters**: Added 24 physical parameters (Mtot, M1-M4, D_L, D_S, thetaE, piE components, mu_rel components, phi) to parameter spec
- **Physical Parameter Validation**: Comprehensive validation including mass consistency checks, vector magnitude verification, distance constraints, and unit confusion warnings
- **Uncertainty Metadata**: Added three new Solution fields:
  - `uncertainty_method`: Method used to derive uncertainties (mcmc_posterior, fisher_matrix, bootstrap, propagation, inference, literature, other)
  - `confidence_level`: Confidence level for uncertainties (default: 0.68 for 1-sigma)
  - `physical_parameter_uncertainties`: Uncertainties for physical parameters (symmetric or asymmetric)
- **CLI Options**: Added `--physical-param-uncertainty`, `--uncertainty-method`, and `--confidence-level` options to `add-solution` command
- **Tests**: Added 3 new comprehensive BIC calculation tests verifying parameter counting
- **Version Management**: Enhanced `bump_version.py` to update and validate `parameter_spec.yaml` (includes drift check)

### Fixed
- **BIC Calculation Bug**: Fixed critical bug where BIC calculation counted ALL parameters including metadata (t_ref, limb_darkening_coeffs) and physical parameters (Mtot, D_L, etc.) as "free parameters". Now correctly counts only fitted model parameters using new `count_model_parameters()` function. This affects relative probability calculations during export and solution comparison.

### Changed
- Physical parameters now validated with `validate_physical_parameters()` automatically when present
- Solution metadata validation now includes uncertainty metadata checks
- BIC calculation in `submission.py` and `validation.py` now uses `count_model_parameters()` instead of `len(s.parameters)`

### Documentation
- Added comprehensive examples of physical parameters and uncertainty metadata to tutorial and usage examples
- Tutorial emphasizes uncertainties are **optional but strongly recommended** for evaluation readiness
- Created `PHYSICAL_PARAMS_SUMMARY.md` with complete implementation guide
