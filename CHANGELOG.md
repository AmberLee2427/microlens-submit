# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.0] - 2024-12-19

### Added
- **Bulk CSV Import**: New CLI command `import-solutions` and API function `import_solutions_from_csv()` for importing multiple solutions from a CSV file in one step
  - Supports column mapping via YAML parameter map files
  - Handles solution aliases with uniqueness validation within events
  - Supports duplicate handling (error/override/ignore), notes, dry-run, and validation options
  - Properly converts literal `\n` characters to actual newlines in notes from CSV files
  - See the tutorial and README for usage examples
- **Solution Aliases**: Human-readable identifiers for solutions with automatic uniqueness validation
  - Aliases are displayed prominently in dossier generation and CLI output
  - Integrated into all CLI commands that reference solutions
  - Supports alias-based solution identification and management
- **Enhanced Notes Handling**: Improved handling of notes with literal escape sequences
  - CSV import automatically converts literal `\n` and `\r` to actual newlines
  - Added `convert_escapes` parameter to `set_notes()` method for controlled conversion
  - Maintains backward compatibility with existing notes functionality
- **Test Data**: Added `tests/data/test_import.csv` as a comprehensive test file for CSV import functionality
  - Used in both CLI and API tests as a real-world example and template for users
  - Includes various parameter types, aliases, notes, and edge cases for testing

### Changed
- **Code Quality**: Improved formatting and readability throughout the codebase
  - Added proper spacing and logical grouping in dense functions
  - Enhanced code maintainability and debugging capabilities
- **Documentation**: Updated tutorial, README, and API documentation to cover CSV import and alias features
- **CLI Enhancements**: Added alias support to all solution-related CLI commands

### Fixed
- **Notes Rendering**: Fixed issue where literal `\n` characters in notes were rendered as text instead of line breaks in HTML
  - CSV import now properly converts escape sequences to actual newlines
  - Maintains compatibility with existing notes that don't need conversion

## [0.12.2] - 2024-12-19

### Fixed
- **Critical Bug Fix**: Renamed `Solution.validate()` method to `Solution.run_validation()` to resolve Pydantic conflict
  - Pydantic was interpreting the `validate` method as a field validator, causing import errors
  - This was breaking Sphinx documentation generation and module imports
  - All references updated across API, CLI, tests, and documentation
  - Method functionality remains identical, only the name changed

### Changed
- Updated all documentation and examples to use `run_validation()` instead of `validate()`
- Updated CLI commands and help text for consistency
- Updated test suite to use the new method name

## [0.12.1] - 2024-12-19

### Added
- **New CLI Command**: `set-hardware-info` for managing compute platform information
  - Supports setting CPU, memory, platform, and Nexus image details
  - Includes `--clear`, `--dry-run`, and update options
  - Integrates with dossier generation for hardware documentation
- **Enhanced Documentation**: Comprehensive improvements to Sphinx documentation
  - Expanded API reference with detailed examples and best practices
  - Enhanced tutorial with step-by-step workflow and troubleshooting
  - Improved index page with key features and quick start guide
  - Added custom CSS styling for RGES-PIT color scheme
- **Example Parameter Files**: Created comprehensive example parameter files
  - `tests/example_params.yaml` and `tests/example_params.json`
  - Demonstrates different parameter formats, uncertainties, and model types
  - Useful for testing and tutorial purposes

### Changed
- **Version Update**: Bumped version from v0.12.0-dev to v0.12.1
- **Documentation**: Updated all version references across codebase
- **Tutorial**: Updated CLI commands in `Submission_Tool_Tutorial.ipynb` to match current syntax
- **GitHub Logo**: Ensured GitHub logo is properly packaged and included in dossier generation

### Fixed
- **CI Test Failures**: Fixed test assertions for CLI comparison and validation commands
  - Updated table header counting logic for solution comparison output
  - Added missing repo_url setting in validation tests
- **Documentation Build**: Improved Sphinx configuration for better autodoc and theme options

## [0.12.0] - 2024-12-18

### Added
- **Comprehensive Documentation**: Complete Sphinx documentation with API reference, tutorial, and examples
- **Enhanced Dossier Generation**: Improved HTML dashboard with better styling and navigation
- **Parameter File Support**: Added support for JSON and YAML parameter files in CLI
- **Validation System**: Centralized parameter validation with comprehensive error checking
- **Hardware Information**: Automatic detection and manual setting of compute platform details
- **Notes Management**: Enhanced markdown notes support with file-based editing
- **Solution Comparison**: BIC-based solution ranking and relative probability calculation
- **Export Improvements**: Better handling of external files and automatic path updates

### Changed
- **API Improvements**: Enhanced Solution and Submission classes with better validation
- **CLI Enhancements**: More robust command-line interface with better error handling
- **Project Structure**: Improved organization with better separation of concerns

### Fixed
- **Bug Fixes**: Various fixes for data persistence, validation, and export functionality
- **Documentation**: Comprehensive docstring updates with Google style formatting

## [0.11.0] - 2024-12-17

### Added
- **Initial Release**: Basic submission management functionality
- **Core API**: Solution, Event, and Submission classes
- **CLI Interface**: Basic command-line tools for project management
- **Export Functionality**: ZIP archive creation for submissions

### Changed
- **Project Structure**: Organized code into logical modules
- **Documentation**: Basic README and docstrings

### Fixed
- **Initial Implementation**: Core functionality for microlensing submission management
