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
