<p align="center">
  <a href="https://github.com/AmberLee2427/microlens-submit">
    <img src="./microlens_submit/assets/rges-pit_logo.png" alt="logo" width="300"/>
  </a>
</p>

<h1 align="center">microlens-submit</h1>

*A stateful submission toolkit for the RGES-PIT Microlensing Data Challenge.*

[![PyPI - v0.16.0](https://img.shields.io/pypi/v/microlens-submit.svg)](https://pypi.org/project/microlens-submit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/AmberLee2427/microlens-submit/actions/workflows/ci.yml/badge.svg)](https://github.com/AmberLee2427/microlens-submit/actions/workflows/ci.yml)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/microlens-submit.svg)](https://pypi.org/project/microlens-submit/)

<br>

`microlens-submit` provides a robust, version-controlled workflow for managing, validating, and packaging your challenge submission over a long period. It supports both a programmatic Python API and a full-featured Command Line Interface (CLI) for language-agnostic use.

Full documentation is hosted on [Read the Docs](https://microlens-submit.readthedocs.io/en/latest/). A comprehensive tutorial notebook is available at `docs/Submission_Tool_Tutorial.ipynb`. Challenge participants who prefer not to use this tool can consult the [Submission Manual](https://microlens-submit.readthedocs.io/en/latest/submission_manual.html) for the manual submission format.

## Key Features

* **Persistent Projects:** Treat your submission as a local project that you can load, edit, and save over weeks or months.
* **Python API & CLI:** Use the tool directly in your Python analysis scripts or via the command line.
* **Solution Management:** Easily add, update, and deactivate degenerate solutions for any event without losing your work history.
* **Active Solution Control:** Quickly list just the active solutions or mark
  all solutions inactive in one call.
* **Automatic Validation:** Aggressive data validation powered by Pydantic ensures your submission is always compliant with the challenge rules.
* **Parameter Validation:** Centralized validation logic checks parameter completeness, types, and physical consistency based on model type and higher-order effects.
* **Rich Documentation:** Notes field supports Markdown formatting for creating detailed, structured documentation and submission dossiers.
* **Environment Capture:** Automatically records your Python dependencies for each specific model fit, ensuring reproducibility.
* **Optional Posterior Storage:** Record the path to posterior samples for any solution.
* **Simple Export:** Packages all your active solutions into a clean, standardized `.zip` archive for final submission.
* **Bulk Import:** Import multiple solutions at once from a CSV file using the `import-solutions` CLI command. Supports column mapping, alias handling, duplicate handling, notes, dry-run, and validation options.

## Installation

The package is available on PyPI:

```bash
pip install microlens-submit
```

### Quickstart Using the Command Line Interface (CLI)

The CLI is the recommended way to interact with your submission project.

You can pass ``--no-color`` to any command if your terminal does not support ANSI colors.

1. Initialize your project: `microlens-submit init --team-name "Planet Pounders" --tier "advanced"`
2. Add a new solution to an event:
   ```bash
   microlens-submit add-solution ogle-2025-blg-0042 1S2L \
       --param t0=555.5 \
       --param u0=0.1 \
       --param tE=25.0 \
       --notes "This is a great fit!"
   ```
   Model types must be one of `1S1L`, `1S2L`, `2S1L`, `2S2L`, `1S3L`, `2S3L`, or `other`.
   This will create a new solution and print its unique `solution_id`.
   You can run the same command with `--dry-run` first to verify the
   parsed input without saving anything.
3. **Bulk import multiple solutions from a CSV file:**
   ```bash
   microlens-submit import-solutions tests/data/test_import.csv --dry-run
   ```
   See the file `tests/data/test_import.csv` for a comprehensive example covering all features and edge cases. You can use this file as a template for your own imports.
4. Deactivate a solution that didn't work out: `microlens-submit deactivate <solution_id>`
5. List all solutions for an event: `microlens-submit list-solutions ogle-2025-blg-0042`
6. Validate solutions and check for issues: `microlens-submit validate-solution <solution_id>`
7. Export your final submission: `microlens-submit export final_submission.zip`

**Note:** When you add a solution, it's automatically validated and any warnings are displayed. Use `--dry-run` to check validation without saving.

### Using the Python API

For those who want to integrate the tool directly into their Python analysis pipeline.

```python
import microlens_submit

# Load or create the project
sub = microlens_submit.load(project_path="./my_challenge_submission")
sub.team_name = "Planet Pounders"
sub.tier = "advanced"

# Get an event and add a solution
evt = sub.get_event("ogle-2025-blg-0042")
params = {"t0": 555.5, "u0": 0.1, "tE": 25.0}
sol = evt.add_solution(model_type="1S2L", parameters=params)

# Record compute info for this specific run
sol.set_compute_info(cpu_hours=15.5)
sol.notes = "This fit was generated from our Python script."

# Save progress to disk
sub.save()

# When ready, export the final package
sub.export("final_submission.zip")
```

## Development

The full development plan can be found in agents.md. Contributions are welcome!

To build and test this project, install the development dependencies using either `pip install -e .[dev]` or `pip install -r requirements-dev.txt`. These packages are required to run the test suite and are listed in `requirements-dev.txt`.
After installing the dependencies, run `pre-commit install` to set up the Git hooks for automatic formatting and linting. The development environment needs the following Python libraries.

### Core Dependencies:
* **`typer[all]`**: For building the powerful command-line interface. The `[all]` extra ensures shell completion support is included.
* **`pydantic`**: For aggressive data validation and settings management.

### Testing Dependencies:
* **`pytest`**: The standard framework for testing Python code.
* **`pytest-cov`**: To measure test coverage.

### Packaging & Distribution Dependencies:
* **`build`**: For building the package from the `pyproject.toml` file.
* **`twine`**: For uploading the final package to PyPI.

### Test Data

A comprehensive test CSV file is provided at `tests/data/test_import.csv`. This file is used in the test suite and can be copied or adapted for your own bulk imports or for development/testing purposes.

## Citation

If you use **microlens-submit** in your research, please cite the project using
the metadata provided in the `CITATION.cff` file. Most reference managers can
import this file directly.
