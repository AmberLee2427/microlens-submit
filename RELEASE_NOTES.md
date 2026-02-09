# microlens-submit v0.17.4 Release Notes

**Release Date:** 2026-02-09

## Changelog

## [0.17.4] - 2026-02-09

### Added
- Added `regenerate` flag for `notebook_display_solution()` to force HTML refresh.

### Changed
- Dossier notebook rendering now inlines local plot images referenced by solution pages.
- Temporary notes created without a project root now track their absolute location.

### Fixed
- Submission save now relocates temporary notes even when the tmp file lives outside the project directory.
- Conda recipe now uses the `pypi.io` source URL to avoid PyPI source 404s during build.
