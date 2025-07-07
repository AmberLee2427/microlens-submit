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

## 2. Core Concepts & Workflow

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

`microlens-submit` is currently at version 0.14.0. Below is the prioritized roadmap for developing version 1.0.0.

### v0.14.0 — Modular Architecture & Enhanced UX (Current Release)

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

### v0.15.0 - Physical Parameter Support (Next Release)

- **Task 4: Enhanced Physical Parameter Validation**
  - *Goal:* Validate physical parameters for reasonableness and consistency.
  - *Action:* Extend validation logic to check:
    - Lens mass ranges (typically 0.1-1.0 M☉)
    - Distance ranges (typically 4-10 kpc for Galactic bulge)
    - Planet mass ranges (typically 0.1-10 M⊕)
    - Consistency between derived and fitted parameters
  - *Why:* Catches physically impossible or unlikely parameter combinations.

- **Task 5: Physical Parameter Uncertainties**
  - *Goal:* Support uncertainties for physical parameters (not just model parameters).
  - *Action:* Add `physical_parameter_uncertainties` field to `Solution` model with validation.
  - *Why:* Physical parameters often have significant uncertainties that should be captured.

### v1.0.0 — Official Release

Release after comprehensive testing and PyPI publication.

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
- `export(filename)` — generates `.zip` of active solutions
- `validate()` — checks submission completeness and consistency

#### `Event` Class

Represents a single microlensing event.

**Attributes:**
- `event_id`: Unique identifier
- `solutions`: Maps solution ID to `Solution`

**Methods:**
- `add_solution(model_type, parameters)` — creates and returns new `Solution`
- `get_solution(solution_id)` — fetches a specific `Solution`
- `get_active_solutions()` — returns active solutions
- `clear_solutions()` — deactivates all solutions

#### `Solution` Class

Represents a specific model fit.

**Attributes:**
- `solution_id`, `model_type`, `parameters`, `is_active`
- `bands`: List of photometric bands used
- `higher_order_effects`: List of physical effects modeled
- `t_ref`: Reference time for time-dependent effects
- `compute_info`: Includes timing, dependencies, Git info
- `posterior_path`, `lightcurve_plot_path`, `lens_plane_plot_path`, `notes`, `creation_timestamp`
- Optional metadata: `used_astrometry`, `used_postage_stamps`, `limb_darkening_model`, `limb_darkening_coeffs`, `parameter_uncertainties`, `physical_parameters`, `log_likelihood`, `relative_probability`, `n_data_points`

**Methods:**
- `set_compute_info(cpu_hours=None, wall_time_hours=None)` — captures timing, environment, and Git state
- `deactivate()` / `activate()` — toggles inclusion in export
- `validate()` — validates solution completeness and consistency

---

## 5. Command Line Interface (CLI)

Built with **Typer**, the CLI supports all core functionality.

### Example Commands

```bash
microlens-submit init --team-name "Planet Pounders" --tier "advanced"
microlens-submit add-solution <event_id> 1S1L --param t0=555.5 --param u0=0.1 --log-likelihood -1234.5
microlens-submit add-solution <event_id> 1S2L --params-file params.yaml --notes "# My Analysis\n\n## Results\n..."
microlens-submit import-solutions tests/data/test_import.csv --dry-run
microlens-submit edit-solution <solution_id> --relative-probability 0.7 --append-notes "Updated after review"
microlens-submit validate-solution <solution_id>
microlens-submit validate-event <event_id>
microlens-submit validate-submission
microlens-submit list-solutions <event_id>
microlens-submit compare-solutions <event_id>
microlens-submit deactivate <solution_id>
microlens-submit export --output "final_submission.zip"
```

> **Note:** All CLI-provided fields must conform to the Python types defined in the Pydantic models. Invalid types will raise validation errors. The `export` command includes a validation step and will fail on invalid or incomplete entries unless explicitly overridden.

> **Note:** The file `tests/data/test_import.csv` is used in the test suite and can be used as a template for your own bulk imports or for development/testing purposes.

---

## 6. On-Disk File Structure

```plaintext
<project_path>/
├── submission.json
├── aliases.json
├── events/
│   ├── <event_id>/
│   │   ├── event.json
│   │   └── solutions/
│   │       ├── <solution_id>.json
│   │       └── <solution_id>.md
│   └── <event_id>/
│       ├── event.json
│       └── solutions/
│           ├── <solution_id>.json
│           └── <solution_id>.md
└── tmp/
    └── <solution_id>.md
```

---

## 7. Development Environment Notes

### Test Conda Environments

For local testing across different Python versions, we use the following conda environments:

- **`test_py38`**: Python 3.8 environment for testing compatibility with older Python versions
- **`test_py311`**: Python 3.11 environment for testing with newer Python features

These environments are used to verify that the codebase works correctly across the supported Python version range (3.8+).

### Environment Setup Commands

```bash
# Create Python 3.8 test environment
conda create -y -n test_py38 python=3.8
conda activate test_py38
pip install -e ".[dev]"

# Create Python 3.11 test environment  
conda create -y -n test_py311 python=3.11
conda activate test_py311
pip install -e ".[dev]"
```

### Key Compatibility Notes

- The project uses `importlib_resources` compatibility shims for asset loading to support both Python 3.8 and 3.9+
- Type annotations use `typing` module imports for Python 3.8 compatibility (e.g., `List`, `Optional` instead of `list`, `|`)
- All tests should pass in both environments before merging changes

---

## 8. Pre-Release Checklist

Before releasing any version, ensure the following:

### Code Quality
- [ ] All tests pass locally (`pytest --cov=microlens_submit --cov-report=xml`)
- [ ] All tests pass in CI (GitHub Actions)
- [ ] Code coverage is maintained or improved
- [ ] No linting errors (`flake8`, `black`, `isort`)
- [ ] Type hints are complete and accurate
- [ ] Documentation is up to date

### Compatibility
- [ ] Tests pass on Python 3.8 (`conda activate test_py38`)
- [ ] Tests pass on Python 3.11 (`conda activate test_py311`)
- [ ] No breaking changes to public API
- [ ] Backward compatibility maintained where possible

### Documentation
- [ ] README.md is current and accurate
- [ ] CHANGELOG.md is updated with new features/fixes
- [ ] API documentation is complete
- [ ] CLI help text is comprehensive
- [ ] Examples in documentation work correctly

### Release Process
- [ ] Version number updated in `pyproject.toml`
- [ ] Version number updated in `microlens_submit/__init__.py`
- [ ] CHANGELOG.md updated with release notes
- [ ] Git tag created for the release
- [ ] Release notes prepared for GitHub release

### Testing
- [ ] Manual testing of CLI commands
- [ ] Manual testing of Python API
- [ ] Export functionality tested with real data
- [ ] Dossier generation tested
- [ ] Validation warnings tested

### Deployment
- [ ] Package builds successfully (`python -m build`)
- [ ] Package installs correctly in clean environment
- [ ] All dependencies are correctly specified
- [ ] No sensitive data in package
- [ ] License and metadata are correct

---

## 9. Release Notes Template

### Version X.Y.Z - [Date]

#### Added
- New feature 1
- New feature 2

#### Changed
- Changed behavior 1
- Changed behavior 2

#### Fixed
- Bug fix 1
- Bug fix 2

#### Removed
- Removed feature 1 (if any)

#### Breaking Changes
- Breaking change 1 (if any)

#### Migration Guide
- How to migrate from previous version (if needed)

