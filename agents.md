# Development Plan: `microlens-submit`

**Version:** 2.0.0
**Author:** Gemini & Amber
**Date:** July 3, 2025

---

## 1. Project Overview & Goals

The `microlens-submit` library is a Python-based toolkit designed to help participants in a microlensing data challenge manage and package their results.

### Primary Goals

- Provide a simple, programmatic **Python API** for creating and modifying submissions.
- Offer a full **Command Line Interface (CLI)** for language-agnostic use, supporting participants whose analysis code is not in Python.
- Support a long-term, iterative workflow by treating the submission as a **persistent, on-disk project**.
- Handle complex submission requirements, including degenerate solutions, optional posteriors, and different modeling approaches.
- Ensure data integrity through **aggressive input validation**.
- Capture detailed **computational metadata**, including timing and environment dependencies for each model fit.
- Be easily installable via pip from the Python Package Index (PyPI).
- **Standardize the final submission format** into a clean, easy-to-parse zip archive.

---

## 2. Development Environment & Testing

### Testing Conda Environments

The project uses two conda environments for testing across Python versions:

- **`test_py38`**: Python 3.8 environment for testing compatibility with older Python versions
- **`test_py311`**: Python 3.11 environment for testing with current Python versions

**To run tests in both environments:**
```bash
# Test in Python 3.8
conda activate test_py38
python -m pytest -v

# Test in Python 3.11
conda activate test_py311
python -m pytest -v
```

**Note:** The `test_py311` environment may require installing `importlib_resources`:
```bash
conda activate test_py311
pip install importlib_resources
```

---

## 3. Core Concepts & Workflow

The library is built around a stateful, object-oriented model that mirrors the structure of the challenge. The user's submission is treated as a persistent project on their local disk. The primary workflow is through the Python API, with a parallel CLI providing access to the same functionality.

### User Workflow

1. **Initialize/Load:** Use `microlens_submit.load(project_path)` or `microlens-submit init` to load or create a submission project.
2. **Modify:** Retrieve `Event` objects from the main `Submission` object. Add one or more `Solution` objects for each event.
3. **Record Metadata:** For each `Solution`, record model parameters and call `.set_compute_info()` to log timing and environment dependencies.
4. **Manage Solutions:** Use `.deactivate()` to soft-delete unsatisfactory fits (excluded from final export but retained in history).
5. **Save Progress:** Call `.save()` to persist all changes to disk.
6. **Export:** Use `.export()` or `microlens-submit export` to generate the final `.zip` archive.

---

## 3. Development Roadmap & Feature Plan

`microlens-submit` is currently at version 0.16.0. Below is the prioritized roadmap for developing version 1.0.0.

### v0.15.0 — Tier Validation & Enhanced Naming (Current Release)

- **Task 1: Modular Architecture** ✅ **COMPLETED**
  - *Goal:* Improve code maintainability and organization.
  - *Action:* Split monolithic files into modular packages:
    - Split `dossier.py` into `dossier/` package with specialized modules
    - Refactored CLI into `cli/` package with organized command modules
    - Created `dossier/generator.py` for HTML generation logic
    - Created `dossier/templates.py` for template management
    - Created `dossier/utils.py` for dossier-specific utilities
    - Created `cli/commands/` directory with specialized command modules
    - Created `cli/utils.py` for CLI-specific utilities
  - *Why:* Enhanced code readability, debugging capabilities, and maintainability while preserving backward compatibility.

- **Task 2: Enhanced Error Messaging** ✅ **COMPLETED**
  - *Goal:* Provide better user guidance and error recovery.
  - *Action:* Implement comprehensive error handling improvements:
    - Added actionable suggestions for common typos and parameter errors
    - Integrated validation warnings with helpful guidance
    - Enhanced CLI error messages with specific recommendations
    - Added parameter validation with user-friendly error descriptions
  - *Why:* Reduces user frustration and improves error recovery experience.

- **Task 3: Improved CLI Help** ✅ **COMPLETED**
  - *Goal:* Enhance command-line interface usability.
  - *Action:* Improved CLI help system:
    - Added [BASIC] and [ADVANCED] tags to help users understand option complexity
    - Enhanced option descriptions with practical usage examples
    - Improved help text for complex parameters like `--limb-darkening-model`
    - Added usage examples in command docstrings for better user guidance
  - *Why:* Makes the CLI more accessible to users of all experience levels.

### v0.16.0 — Comprehensive Validation & Dossier Enhancement (Current Release)

- **Task 1: Tier Validation System** ✅ **COMPLETED**
  - *Goal:* Implement comprehensive tier-based validation for challenge submissions.
  - *Action:* Created complete tier validation system:
    - New `tier_validation.py` module with support for "standard", "advanced", "test", "2018-test", and "None" tiers
    - Event ID validation against tier-specific event lists
    - CLI tier validation with fallback to "None" for invalid tiers
    - Comprehensive tier validation tests in `tests/test_tier_validation.py`
    - Integration with CLI init command for automatic tier validation
  - *Why:* Ensures submissions are validated against the correct event lists and tier requirements.

- **Task 2: Enhanced Validation Logic** ✅ **COMPLETED**
  - *Goal:* Improve parameter validation and solution completeness checking.
  - *Action:* Enhanced validation system:
    - Enhanced `validate_parameters.py` with better error messages and validation rules
    - Improved validation for higher-order effects and parameter consistency
    - Better handling of parameter uncertainties and type validation
    - Enhanced solution completeness checking with more detailed feedback
    - Improved CLI validation commands with better error reporting
  - *Why:* Provides better user feedback and catches validation issues earlier.

- **Task 3: Dossier Generation Enhancements** ✅ **COMPLETED**
  - *Goal:* Improve HTML dossier generation and user experience.
  - *Action:* Enhanced dossier functionality:
    - Added model_type display at the top of each solution section in full dossier reports
    - Added `--open` flag to `microlens-submit generate-dossier` CLI command for automatic browser opening
    - Added `open: bool = False` parameter to `generate_dashboard_html()` API function
    - Enhanced dossier navigation and metadata display
    - Improved full dossier report generation with better solution identification
  - *Why:* Streamlines workflow and improves dossier readability for evaluators.

- **Task 4: Submission Manual Integration** ✅ **COMPLETED**
  - *Goal:* Improve documentation accessibility and integration with Sphinx documentation.
  - *Action:* Converted and integrated submission manual:
    - Converted SUBMISSION_MANUAL.md to reStructuredText format (`docs/submission_manual.rst`)
    - Integrated submission manual into main Sphinx documentation site
    - Updated all internal links and references to point to new documentation location
    - Added GitHub link to validate_submission.py script in submission manual
    - Removed old markdown file and logo references for cleaner structure
  - *Why:* Better documentation integration, improved accessibility, and cleaner project structure.

- **Task 5: Comprehensive Code Quality & Pre-commit Integration** ✅ **COMPLETED**
  - *Goal:* Ensure consistent code quality and formatting across the project.
  - *Action:* Implemented comprehensive pre-commit hooks and code cleanup:
    - Fixed all pre-commit hook violations including line length, unused imports, and style issues
    - Resolved f-string formatting issues in CLI commands
    - Fixed line length violations in dossier generation code
    - Removed unused imports across the codebase
    - Ensured all tests pass in both Python 3.8 and 3.11 environments
    - Added pre-commit configuration with black, isort, flake8, and other quality checks
  - *Why:* Maintains high code quality standards and prevents common formatting issues.

### v0.17.0 - Physical Parameter Support (Next Release)

- **Task 6: Fix BIC Calculation Bug** 🔴 **CRITICAL BUG**
  - *Goal:* Fix incorrect parameter counting in BIC calculation for relative probability computation.
  - *Action:* Update BIC calculation in both `submission.py` and `validation.py` to count only model parameters:
    - Current bug: `k = len(s.parameters)` counts ALL parameters including metadata like `t_ref`, `limb_darkening_coeffs`
    - Fix: Use existing parameter definitions from `validate_parameters.py` to count only actual model parameters
    - Update BIC calculation to use: core model parameters + higher-order effect parameters + flux parameters
    - Exclude metadata parameters like `t_ref`, `limb_darkening_coeffs` from parameter count
    - Update both `Submission.export()` and `compare_solutions()` CLI command
  - *Why:* Current BIC calculation over-penalizes complex models by counting metadata as "free parameters", leading to incorrect relative probability calculations.
  - *Impact:* This affects automatic relative probability calculation during export and solution comparison.

- **Task 7: Automated Release workflow**
  - *Goal:* Automate the release process as a GItHub Actions workflow.
  - *Actions:* Add a GitHub Actions workflow to automatically update all version numbers in the codebase, build the package and upload it to TestPyPI and PyPI.
    - Trigger by pushing a version tag.
    - Add API keys as GitHub secrets.
    - Update badges, where necessary.
    - Update version numbers in the codebase, e.g. `__init__.py`.
    - Update version numbers in the docsumentation, etc. e.g. `CITATION.cff`
  - *Why:* Current implementation is time consuming and prone to error.
  - *Impact:* Increased release and documentation reliability and decrease of manual intervention.

- **Task 8: Enhanced Physical Parameter Validation**
  - *Goal:* Validate physical parameters for reasonableness and consistency.
  - *Action:* Extend validation logic to check:
    - Lens mass ranges (typically 0.1-1.0 M☉)
    - Distance ranges (typically 4-10 kpc for Galactic bulge)
    - Planet mass ranges (typically 0.1-10 M⊕)
    - Consistency between derived and fitted parameters
  - *Why:* Catches physically impossible or unlikely parameter combinations.

- **Task 9: Physical Parameter Uncertainties**
  - *Goal:* Support uncertainties for physical parameters (not just model parameters).
  - *Action:* Add `physical_parameter_uncertainties` field to `Solution` model with validation.
  - *Why:* Physical parameters often have significant uncertainties that should be captured.

- **Task 10: Event Notes Section** 📝 **NEW FEATURE**
  - *Goal:* Add support for event-level notes to complement solution-level notes.
  - *Action:* Implement event notes functionality:
    - Add `notes_path` field to `Event` model (similar to solution notes)
    - Create `add_event_notes()` method to `Event` class
    - Add CLI command `microlens-submit add-event-notes <event_id> <notes_file>`
    - Include event notes in dossier generation
    - Update validation to check event notes file exists if specified
  - *Why:* Users need to document event-level observations, data quality issues, or general context that applies to all solutions for an event.
  - *Implementation:* Mirror the existing solution notes system but at the event level. Don't take the examples function names as law, they should be as similar as possible to, if not the same as, the solution-specific versions.

### v1.0.0 — Official Release

Release after comprehensive testing on the Roman Research Nexus with Data Challenge 2 test data.

- **Task 8: Interactive Mode**
  - *Goal:* Provide a guided, interactive experience for new users to reduce complexity and improve onboarding.
  - *Action:* Add an interactive CLI mode that guides users through:
    - Project initialization with prompts for team name and tier
    - Step-by-step solution creation with parameter entry
    - Validation feedback with suggestions for fixing issues
    - Progressive disclosure of advanced options
  - *Why:* Reduces cognitive load for new users and provides better error recovery.
  - *Implementation:* Use Python's `input()` or a library like `prompt_toolkit` for rich interactive prompts.

---

## 4. Python Class Structure (Target API)

### 4.1. Data Validation

All user input is validated with `Pydantic` models. Invalid data will raise clear `ValidationError`s before it can be saved.

### 4.2. Core Classes

#### `Submission` Class

Manages the overall submission.

**Attributes:**
- `project_path`: Root directory of the submission
- `team_name`: Participant's team
- `tier`: Challenge tier
- `events`: Maps event ID to `Event` objects
- `hardware_info` (optional): Describes computational platform

**Methods:**
- `__init__(self, project_path)` — use `microlens_submit.load()` instead
- `get_event(event_id)` — fetches or creates an `Event`
- `save()` — writes submission state to disk
- `export(filename)`
