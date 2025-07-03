## Release v0.12.0

### What's New
- **Submission Dossier Generator:** New `generate-dossier` CLI command that creates comprehensive HTML dashboards for submission review
- **HTML Dashboard:** Generates professional `index.html` with submission overview, event summaries, and solution statistics following Dashboard_Design.md specifications
- **Tailwind CSS Design:** Modern, responsive design using Tailwind CSS with custom RGES-PIT color palette
- **Rich Metadata Display:** Shows team information, hardware details, compute statistics, and model type distributions
- **Progress Tracking:** Visual progress bar showing completion percentage against total challenge events (293)
- **Event Navigation:** Links to future event-specific pages (structure prepared for v0.13.0 expansion)
- **Parameter Distribution Placeholders:** Placeholder plots for key parameter distributions with professional styling

### Dossier Features
- **Summary Cards:** Quick overview of total events, active solutions, and hardware information
- **Submission Metadata:** Team name, challenge tier, and generation timestamp
- **Hardware Information:** Display of compute platform details when available
- **Progress Visualization:** Progress bar showing events processed vs. total challenge events
- **Events Overview:** Table showing all events with active solution counts and model types
- **Compute Time Summary:** Total CPU and wall time hours across all solutions
- **Directory Structure:** Creates organized output with `assets/` and `events/` subdirectories for future expansion

### Usage
```bash
microlens-submit generate-dossier /path/to/output/directory
```

### Bug Fixes
- None

### Breaking Changes
- None

### Dependencies
- No new dependencies

<br>

## Release v0.11.0

### What's New
- **Enhanced Parameter Validation:** Comprehensive docstring for `validate()` method with detailed explanation of all validation checks
- **Parameter Uncertainty Validation:** New validation logic for parameter uncertainties, including support for asymmetric uncertainties [lower, upper]
- **Structured Parameter Files:** Support for JSON and YAML files containing both parameters and uncertainties in a single file
- **Improved CLI:** Enhanced `--params-file` option now supports YAML format and structured parameter files
- **Code Cleanup:** Removed deprecated `log_prior` field (not used in calculations)

### Structured Parameter File Format
Parameter files can now use either simple or structured format:

**Simple format (JSON/YAML):**
```json
{
  "t0": 2459123.5,
  "u0": 0.15,
  "tE": 20.5
}
```

**Structured format (JSON/YAML):**
```json
{
  "parameters": {
    "t0": 2459123.5,
    "u0": 0.15,
    "tE": 20.5
  },
  "uncertainties": {
    "t0": [0.1, 0.1],
    "u0": 0.02,
    "tE": [0.3, 0.4]
  }
}
```

### Uncertainty Validation
- Validates uncertainty values are positive
- Supports both single values and [lower, upper] asymmetric uncertainties
- Warns if uncertainties are very large (>50%) or very small (<0.1%) relative to parameter values
- Checks that uncertainty bounds are properly ordered (lower ≤ upper)

### Bug Fixes
- None

### Breaking Changes
- **Removed `log_prior` field:** This field was not used in any calculations and has been removed from the API and CLI

### Dependencies
- Added `PyYAML>=6.0` for YAML file support

<br>

## Release v0.10.0

### What's New
- **Centralized Parameter Validation:** Added comprehensive validation logic that checks parameter completeness, types, and physical consistency based on model type and higher-order effects.
- **CLI Validation Commands:** New commands `validate-solution`, `validate-event`, and `validate-submission` for checking solutions and submissions.
- **Automatic Validation:** Solutions are automatically validated when added via CLI, with warnings displayed but saving never blocked.
- **Enhanced Dry-Run:** `--dry-run` now includes validation results, showing warnings before saving.
- **Validation Module:** New `validate_parameters.py` module with extensible validation logic for different model types and effects.

### Bug Fixes
- None

### Breaking Changes
- None

### Dependencies
- N/A

<br>

## Release v0.9.0

### What's New
- Removed the `model_name` field from `Solution` and CLI.
- Introduced strongly typed `model_type` values (e.g., `1S1L`, `1S2L`).
- Added `bands` attribute for photometric bands.
- Added `higher_order_effects` list to flag physical effects.
- Added a dedicated `t_ref` field.
- Foundation for parameter validation based on `model_type` and `bands`.

### Bug Fixes
- None

### Breaking Changes
- None

### Dependencies
- N/A

<br>

## Release v0.8.0

### What's New
- Added `relative_probability` field to `Solution` model with CLI and API support.
- `Submission.export` automatically computes this probability via BIC when not provided, or assigns equal values if BIC inputs are missing.
- `compare-solutions` now shows relative probabilities and calculates them on demand.

### Bug Fixes
- None

### Breaking Changes
- None

### Dependencies
- N/A

<br>

## Release v0.7.1

### What's New
- Clarified external file (plots, posteriors) storage and path handling in
  `SUBMISSION_MANUAL.md`. Internal paths within `solution.json` files in exported
  archives now point to the file's location inside the zip, allowing immediate
  use after extraction.

### Bug Fixes
- None

### Breaking Changes
- None

### Dependencies
- No dependency changes

<br>

## Release v0.7.0

### What's New
- Added `lightcurve_plot_path` and `lens_plane_plot_path` fields to the `Solution` model and CLI.
- Posterior and plot files referenced by solutions are automatically packaged on export.

### Bug Fixes
- Validation now warns when plot paths are missing.
- Export raises an error if any referenced file does not exist.

### Breaking Changes
- None

### Dependencies
- No dependency changes

<br>

## Release v0.6.1

### What's New
- `add-solution` supports a `--dry-run` flag to validate inputs without saving.

### Bug Fixes
- N/A

### Breaking Changes
- None

### Dependencies
- No dependency changes

<br>

## Release v0.6.0

### What's New
- `add-solution` accepts a `--params-file` option for JSON parameter files.
- Added optional `model_name` field to `Solution` and CLI.

### Bug Fixes
- N/A

### Breaking Changes
- None

### Dependencies
- No dependency changes

<br>

## Release v0.5.0

### What's New
- Added `nexus-init` command to capture platform metadata on the Roman Research Nexus.
- `Submission.autofill_nexus_info` auto-populates hardware details from the environment.
- New Jupyter notebook tutorial for Nexus users.

### Bug Fixes
- N/A

### Breaking Changes
- None

### Dependencies
- No dependency changes

<br>

## Release v0.4.0

### What's New
- Added `SUBMISSION_MANUAL.md` documenting the submission format.
- Added standalone `validate_submission.py` for validating directories.

### Bug Fixes
- N/A

### Breaking Changes
- None

### Dependencies
- No dependency changes

<br>

## Release v0.3.0

### What's New
- Added `compare-solutions` command to evaluate solutions using BIC.
- `export` now performs pre-flight validation and supports a `--force` flag.

### Bug Fixes
- BIC calculation now uses the number of data points stored for each solution.

### Breaking Changes
- None

### Dependencies
- No dependency changes

<br>

## Release v0.2.0

### What's New
- Added structured metadata fields to `Solution` and `Submission` models including astrometry usage, limb darkening info, physical parameters, and hardware information.
- `Solution.set_compute_info` now records Git repository state (commit hash, branch, dirty status) while failing gracefully when Git is unavailable.
- CLI `add-solution` command updated with options to supply the new metadata from the command line.

### Bug Fixes
- N/A

### Breaking Changes
- None

### Dependencies
- No dependency changes
