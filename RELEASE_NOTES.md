# microlens-submit v0.16.4 Release Notes

**Release Date:** 2026-01-14

## Changelog

## [0.16.4] - 2026-01-14

### Added
- Added `remove-event`/`remove-solution` CLI commands and `remove_event`/`remove_solution` API helpers with a `--force` guard for hard deletes.
- Added `git_dir` metadata plus `set-git-dir` to capture Git info when the repo lives outside the submission directory.
- Added optional GPU fields in `hardware_info` (`gpu.model`, `gpu.count`, `gpu.memory_gb`) alongside platform/OS capture.
- Added non-Nexus hardware auto-fill using `psutil` for CPU and memory details.
- Added conda-forge recipe (`conda/recipe/meta.yaml`) to the version bump script (`scripts/bump_version`).
- Added sha256 update in `conda/recipe/meta.yaml` to the release workflow.
- Added a workflow release job to copy the local updated version on the conda-forge recipe to the feedstock fork (`AmberLee2427/microlens-submit-feedstock`) and send a PR, after PyPI release.


### Changed
- Updated tiers to `beginner`/`experienced`; event ID validation now uses inclusive ranges and 3-digit IDs for `2018-test`.
- CLI numeric parsing now accepts leading decimals like `.001`.
- Clarified quickstart/tutorial guidance around working directories and hardware info requirements.


### Fixed
- CSV import now skips blank rows to avoid NoneType parsing errors.
- Validation messaging now highlights missing bands when flux parameters are provided.
- Improved Windows notes editor fallback for better default editor selection.
