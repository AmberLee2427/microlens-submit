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
