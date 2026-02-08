# microlens-submit v0.17.2 Release Notes

**Release Date:** 2026-02-08

## Changelog

## [0.17.2] - 2026-02-08

### Added
- Renamed CLI-focused tutorial file (`docs/cli_tutorial.rst`) and updated docs index references.
- Added a Python API example for inspecting solutions and resolving duplicate aliases in usage examples.

### Changed
- Dossier asset linking now resolves local plot/posterior paths without copying into the dossier output (reverted to v<0.17.0 behaviour).
- Duplicate-alias validation now reports the conflicting solution IDs with guidance for renaming.

### Fixed
- Fixed dossier logo asset loading to use packaged assets reliably across environments (e.g., Roman Nexus).
- Ensured event/solution-only dossier generation copies shared logo assets.
- Fixed flux-parameter detection so `F0_S`/`F0_B` are recognized for banded flux terms.
- Added `data_challenge_0_129_335` to the `test` tier event list (runtime and spec).
