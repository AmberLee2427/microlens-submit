# microlens-submit v0.17.6 Release Notes

**Release Date:** 2026-02-10

## Changelog

## [0.17.6] - 2026-02-10

### Fixed
- Fixed `OSError` (cross-device link) when saving solution notes on systems with separate filesystems (like Nexus), by using `shutil.move` instead of `os.replace`.
