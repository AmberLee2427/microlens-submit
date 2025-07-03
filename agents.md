# Development Plan: `microlens-submit`

**Version:** 1.2.1  
**Author:** Gemini & Amber  
**Date:** July 1, 2025

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

`microlens-submit` is currently at version 0.1.0. Below is the prioritized roadmap for developing version 1.0.0. Tasks are grouped into batches, and future work assumes earlier tasks are completed.

### v0.2.0 — Feature Batch 1: The "No-Brainer" Upgrades (Immediate Priority)

- **Task 1: Full Provenance Capture**
  - *Goal:* Ensure reproducibility by logging exactly what code generated each result.
  - *Action:* Extend `Solution.set_compute_info` to capture:
    - Full Git commit hash
    - Current branch name
    - Dirty status (uncommitted changes)
    - Must fail silently if not a Git repo or if Git is unavailable
  - *Why:* Enables verifiable, scientific provenance for every model fit.

- **Task 2: Structured Metadata Injection**
  - *Goal:* Move beyond the unstructured `notes` field by supporting machine-readable, structured metadata.
  - *Action:* Add optional fields to the `Solution` Pydantic model and expose them in the CLI:
    - `used_astrometry`, `used_postage_stamps`, `limb_darkening_model`, `limb_darkening_coeffs`, `parameter_uncertainties`, `physical_parameters`, `log_likelihood`, `log_prior`
  - *Why:* Improves quality, structure, and downstream usability of submitted data.

- **Task 3: Hardware & Platform Specification**
  - *Goal:* Capture the computational environment for context.
  - *Action:* Add optional `hardware_info` to the `Submission` model.
  - *Why:* Important for reproducibility and benchmarking across environments like the Roman Science Platform.

### v0.3.0 — Feature Batch 2: The "Luxury" Upgrades (Next Priority)

- **Task 4: Intelligent Solution Comparison**
  - *Goal:* Provide quick feedback on degenerate model fits.
  - *Action:* New CLI command: `microlens-submit compare-solutions <event_id>`
    - Fetch and compare `log_likelihood`, `log_prior`
    - Calculate metrics like BIC
    - Display ranked solution table
  - *Why:* Helps users make better modeling decisions.

- **Task 5: Pre-flight Validation & Checklist**
  - *Goal:* Prevent incomplete or invalid submissions.
  - *Action:* Add validation to `export`, prompting user with:
    - Missing solutions or metadata
    - Absent hardware info
  - *Why:* Reduces submission errors and improves overall data quality.

### v0.4.0 — Feature Batch 3: The "Future-Proofing" (Long-Term Vision)

> The task are out of order from here on due to a revision.

- **Task 8: The "DIY" Support Package**
  - *Goal:* Provide an alternative for those not using the main tool.
  - *Action:* Supply:
    - A `SUBMISSION_MANUAL.md` with schema documentation
    - A `validate_submission.py` script for compliance checks
  - *Why:* Encourages good practices while respecting autonomy.

### v0.5.0 — Feature Batch 4: Seamless Nexus Integration

- **Task 7: Seamless Nexus Integration**
  - *Goal:* Tight integration with the Roman Science Platform.
  - *Action:*
    - Auto-populate hardware info from Nexus
    - Include Jupyter-ready templates with tool pre-installed
  - *Why:* Lowers friction and increases adoption.

### v0.6.0 — Feature Batch 5: CLI Usability & Model Validation

- **Task 6: Parameter File Support**
  - *Goal:* Reduce manual entry errors by allowing parameters in a JSON file.
  - *Action:* Add a `--params-file` option to the CLI `add-solution` command.
  - *Why:* Makes the CLI less fragile for human users.

- **Task 7: Model Validation**
  - *Goal:* Prepare for plugin architecture by storing the modeling software name.
  - *Action:* Add a `model_name` field to the `Solution` class and expose it in the CLI.
  - *Why:* Enables future validation by external packages.

- **Task 8: Posterior & Plot Packaging**
  - *Goal:* Ensure external files referenced by solutions are included in exports.
  - *Action:* Add `lightcurve_plot_path` and `lens_plane_plot_path` fields to `Solution` and collect them (and posterior files) during `export`.
  - *Why:* Simplifies sharing complete results and prevents missing file errors.

### v0.9.0 — Strongly Typed Model & Effects & Parameter Validation Foundation

- **Task:** Remove generic `model_name` and enforce strict `model_type` values.
- **Task:** Add `bands`, `higher_order_effects`, and `t_ref` fields to `Solution`.
- **Task:** Begin conditional parameter validation based on these fields.

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
- `compute_info`: Includes timing, dependencies, Git info
- `posterior_path`, `notes`, `creation_timestamp`
- Optional metadata: `used_astrometry`, `used_postage_stamps`, `limb_darkening_model`, `limb_darkening_coeffs`, `parameter_uncertainties`, `physical_parameters`, `log_likelihood`, `log_prior`

**Methods:**
- `set_compute_info(cpu_hours=None, wall_time_hours=None)` — captures timing, environment, and Git state
- `deactivate()` / `activate()` — toggles inclusion in export

---

## 5. Command Line Interface (CLI)

Built with **Typer**, the CLI supports all core functionality.

### Example Commands

```bash
microlens-submit init --team-name "Planet Pounders" --tier "advanced"
microlens-submit add-solution <event_id> --model-type 1S2L --param t0=555.5 --param u0=0.1 --log-likelihood -1234.5
microlens-submit list-solutions <event_id>
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
  "parameters": {"t0": 555.5, "u0": 0.1, "tE": 25.0},
  "physical_parameters": {"M_L": 0.5, "D_L": 7.8},
  "log_likelihood": -1234.56,
  "posterior_path": "posteriors/posterior_A.h5",
  "notes": "Binary model provides a much better fit.",
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

> **Note:** `posterior_path` should point to a structured file (e.g., HDF5). Future updates may add format validation.

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
params = {"t0": 123.5, "u0": 0.1, "tE": 12.0, "q": 0.1, "s": 1.2}
sol = evt.add_solution(model_type="1S2L", parameters=params)
sol.set_compute_info(cpu_hours=24.0)
sol.notes = "Binary model provides a much better fit."
sol.physical_parameters = {"M_L": 0.5, "D_L": 7.8}
sol.log_likelihood = -1234.56

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

The tool will be published to **PyPI**.

### Installation

```bash
pip install microlens-submit
```

### Packaging

The project will use `pyproject.toml` for dependency and entry point configuration.

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
   - CHANGELOG.md exists and is updated (if applicable)

3. **Version Management:**
   - Update version in `pyproject.toml`
   - Update version in `microlens_submit/__init__.py` (if applicable)
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

- **Patch releases (0.1.0 → 0.1.1):** Bug fixes, minor improvements
- **Minor releases (0.1.0 → 0.2.0):** New features, non-breaking changes
- **Major releases (0.1.0 → 1.0.0):** Breaking changes, major rewrites

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

1. **Update Development Version:** Increment the version in `pyproject.toml` to the next development version (e.g., 0.1.0 → 0.1.1-dev)
2. **Create Release Branch:** If implementing new features, create a new branch from the release tag
3. **Update Roadmap:** Mark completed tasks in this document

### 10.7. Automated Release Workflow

For future automation, consider implementing:

1. **GitHub Actions** for automated testing and building
2. **Release drafter** for automatic changelog generation
3. **Automated PyPI publishing** on tag creation

### 10.8. Current Release Status

- **v0.1.0:** ✅ Released - Initial implementation with basic CLI and API
- **v0.2.0:** ✅ Released - Feature Batch 1 (Provenance Capture, Structured Metadata, Hardware Info)
- **v0.3.0:** ✅ Released - Feature Batch 2 (Solution Comparison, Pre-flight Validation)
- **v0.4.0:** ✅ Released - DIY Support Package (Manual and Validation Tools)
- **v0.5.0:** ✅ Released - Seamless Nexus Integration
- **v0.6.0:** ✅ Released - CLI Usability & Model Validation
- **v0.7.0:** ✅ Released - Plot Packaging & Validation
- **v0.8.0:** ✅ Released - Relative Probability Handling
- **v0.9.0:** 🚧 In Development - Strongly Typed Model & Effects
- **v1.0.0:** 📋 Planned - Official Release

