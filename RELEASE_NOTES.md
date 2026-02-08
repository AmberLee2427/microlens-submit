# microlens-submit v0.17.3 Release Notes

**Release Date:** 2026-02-08

## Changelog

## [0.17.3] - 2026-02-08

### Added
- Solution-level hardware metadata overrides and autofill helpers.
- Notebook display helpers for dashboard, event, solution, and full dossier pages.
- Python API support for setting `bands` during `event.add_solution()`.
- Tests covering notebook display helpers and `bands` in the Python API.

### Changed
- CLI `edit-solution` now supports solution-level hardware overrides (JSON), autofill, and clearing.
- Notebook display helpers inline local assets for JupyterHub/JupyterLab display.

### Fixed
- Asset inlining now handles single-quoted `src` attributes in dossier HTML.
