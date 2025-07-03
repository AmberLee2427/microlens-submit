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

`microlens-submit` is currently at version 0.12.0-dev. Below is the prioritized roadmap for developing version 1.0.0.

### v0.12.0 — Dossier Generator & Enhanced Validation (Next Priority)

- **Task 1: Submission Dossier Generator**
  - *Goal:* Allow participants to preview exactly what evaluators will receive.
  - *Action:* Create a new CLI command `generate-dossier` that produces a human-readable report including:
    - Team and submission metadata
    - Summary of all active solutions with key parameters
    - Rendered Markdown notes for each solution
    - Validation status and warnings
    - Physical parameter summaries
    - Relative probability distributions
    - See Dashboard_Design.md for the proposed `index.html` design plan
    - Have subpages for event and solution summaries
  - *Why:* Helps participants ensure their submission is complete and professional before final submission.

- **Task 2: Enhanced Physical Parameter Validation**
  - *Goal:* Validate physical parameters for reasonableness and consistency.
  - *Action:* Extend validation logic to check:
    - Lens mass ranges (typically 0.1-1.0 M☉)
    - Distance ranges (typically 4-10 kpc for Galactic bulge)
    - Planet mass ranges (typically 0.1-10 M⊕)
    - Consistency between derived and fitted parameters
  - *Why:* Catches physically impossible or unlikely parameter combinations.

- **Task 3: Physical Parameter Uncertainties**
  - *Goal:* Support uncertainties for physical parameters (not just model parameters).
  - *Action:* Add `physical_parameter_uncertainties` field to `Solution` model with validation.
  - *Why:* Physical parameters often have significant uncertainties that should be captured.

### v0.13.0 — High Automation Support (Advanced Users)

- **Task 4: Solution YAML Format**
  - *Goal:* Enable high-automation workflows for power users.
  - *Action:* Add support for `solution.yaml` files that define complete solutions including:
    - All parameters, uncertainties, and metadata
    - Markdown notes with full formatting
    - Compute information
    - File paths for plots and posteriors
  - *Why:* Allows automated generation of solutions from analysis pipelines.

- **Task 5: Batch Solution Import**
  - *Goal:* Import multiple solutions from structured files.
  - *Action:* CLI command to import solutions from directories of YAML files.
  - *Why:* Streamlines workflows for users with many solutions to add.

### v1.0.0 — Official Release

Release after comprehensive testing and PyPI publication.

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

---

## 6. On-Disk File Structure

```plaintext
<project_path>/
├── submission.json
├── events/
│   └── <event_id>/
│       ├── event.json
│       └── solutions/
│           ├── <solution_id_A>.json
│           └── <solution_id_B>.json
```

### Example Solution File

```json
{
  "solution_id": "a1b2c3d4-e5f6-...",
  "creation_timestamp": "2025-07-15T13:45:10Z",
  "is_active": true,
  "model_type": "1S2L",
  "bands": ["0", "1", "2"],
  "higher_order_effects": ["parallax", "finite-source"],
  "t_ref": 2459123.5,
  "parameters": {"t0": 555.5, "u0": 0.1, "tE": 25.0, "s": 1.2, "q": 0.001, "alpha": 45.0},
  "parameter_uncertainties": {"t0": [0.1, 0.1], "u0": 0.02, "tE": [0.3, 0.4]},
  "physical_parameters": {"M_L": 0.5, "D_L": 7.8, "M_planet": 1.5, "a": 2.8},
  "log_likelihood": -1234.56,
  "relative_probability": 0.7,
  "n_data_points": 1250,
  "posterior_path": "posteriors/posterior_A.h5",
  "lightcurve_plot_path": "plots/event001_lc.png",
  "lens_plane_plot_path": "plots/event001_lens.png",
  "notes": "# Binary Lens Solution\n\n## Model Overview\nThis solution represents a **binary lens** with a planetary companion...",
  "compute_info": {
    "cpu_hours": 15.5,
    "wall_time_hours": 2.1,
    "dependencies": [
      "numpy==1.21.2",
      "scipy==1.7.1",
      "emcee==3.1.0"
    ],
    "git_info": {
      "commit": "f4ac2a9f...e1",
      "branch": "feature/new-model",
      "is_dirty": true
    }
  }
}
```

> **Note:** The `notes` field supports Markdown formatting for rich documentation. `posterior_path`, `lightcurve_plot_path`, and `lens_plane_plot_path` should point to files within the project directory.

---

## 7. Example Usage: Full Lifecycle

```python
import microlens_submit

# Initialize the submission
sub = microlens_submit.load(project_path="./my_challenge_submission")
sub.team_name = "Planet Pounders"
sub.tier = "advanced"
sub.hardware_info = {"cpu": "Intel i9", "ram_gb": 64}

# Add a solution
evt = sub.get_event("event-001")
params = {"t0": 123.5, "u0": 0.1, "tE": 12.0, "q": 0.1, "s": 1.2, "alpha": 45.0}
sol = evt.add_solution(model_type="1S2L", parameters=params)
sol.bands = ["0", "1"]
sol.higher_order_effects = ["parallax"]
sol.t_ref = 2459123.5
sol.set_compute_info(cpu_hours=24.0)
sol.notes = "# Binary Lens Solution\n\n## Model Overview\nThis solution represents a **binary lens**..."
sol.physical_parameters = {"M_L": 0.5, "D_L": 7.8, "M_planet": 1.5, "a": 2.8}
sol.parameter_uncertainties = {"t0": 0.1, "u0": 0.02, "tE": 0.5}
sol.log_likelihood = -1234.56
sol.relative_probability = 0.7
sol.n_data_points = 1250

# Validate the solution
validation_messages = sol.validate()
if validation_messages:
    print("Validation warnings:", validation_messages)

# Save work
sub.save()

# Final export
sub = microlens_submit.load(project_path="./my_challenge_submission")
sub.export(filename="planet_pounders_final.zip")
```

---

## 8. Style Guidelines

- **Formatting:** Use `black` for all Python code
- **Type Hinting:** Required for all functions
- **Docstrings:** Google-style for all public APIs
- **Commits:** Follow Conventional Commits

---

## 9. Distribution & Installation

The tool is published to **PyPI**.

### Installation

```bash
pip install microlens-submit
```

### Packaging

The project uses `pyproject.toml` for dependency and entry point configuration.

---

## 10. Release Management & Instructions for Agents

### 10.1. Release Process Overview

Before creating any PRs that implement new features or significant changes, agents should follow this release process to ensure proper versioning and distribution.

### 10.2. Pre-Release Checklist

Before creating a release, ensure:

1. **Code Quality:**
   - All tests pass (`pytest`)
   - Code is formatted (`black .`)
   - No linting errors
   - Working tree is clean (`git status`)

2. **Documentation:**
   - README.md is up to date
   - API documentation is current
   - CHANGELOG.md exists and is updated
   - Tutorial notebook is current

3. **Version Management:**
   - Update version in `pyproject.toml`
   - Update version in `microlens_submit/__init__.py`
   - Consider if this is a major, minor, or patch release

### 10.3. Release Commands for Agents

When ready to create a release, execute these commands in sequence:

```bash
# 1. Ensure working tree is clean
git status

# 2. Run tests to ensure everything works
pytest

# 3. Format code
black .

# 4. Create and push the git tag
git tag -a v<X.Y.Z> -m "Release v<X.Y.Z> - <brief description>"
git push origin v<X.Y.Z>

# 5. Build the distribution
python -m build

# 6. Check the built distribution
twine check dist/*

# 7. Upload to PyPI (if this is a production release)
# twine upload dist/*
```

### 10.4. Version Numbering Strategy

- **Patch releases (0.12.0 → 0.12.1):** Bug fixes, minor improvements
- **Minor releases (0.12.0 → 0.13.0):** New features, non-breaking changes
- **Major releases (0.12.0 → 1.0.0):** Breaking changes, major rewrites

### 10.5. Release Notes Template

When creating a release, include:

```markdown
## Release v<X.Y.Z>

### What's New
- [Feature 1]
- [Feature 2]

### Bug Fixes
- [Bug fix 1]
- [Bug fix 2]

### Breaking Changes
- [Any breaking changes]

### Dependencies
- Updated [dependency] to version [X.Y.Z]
```

### 10.6. Post-Release Tasks

After creating a release:

1. **Update Development Version:** Increment the version in `pyproject.toml` to the next development version (e.g., 0.12.0 → 0.12.1-dev)
2. **Create Release Branch:** If implementing new features, create a new branch from the release tag
3. **Update Roadmap:** Mark completed tasks in this document

### 10.7. Automated Release Workflow

For future automation, consider implementing:

1. **GitHub Actions** for automated testing and building
2. **Release drafter** for automatic changelog generation
3. **Automated PyPI publishing** on tag creation

### 10.8. Current Release Status

- **v0.11.0:** ✅ Released - Enhanced Parameter Validation, YAML Support, Markdown Notes
- **v0.12.0:** 🔄 In Development - Dossier Generator & Enhanced Validation
- **v0.13.0:** 📋 Planned - High Automation Support
- **v1.0.0:** 📋 Planned - Official Release

