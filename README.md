# microlens-submit
A stateful submission toolkit for the RGES-PIT Microlensing Data Challenge.

[![PyPI version](https://badge.fury.io/py/microlens-submit.svg)](https://badge.fury.io/py/microlens-submit)
[![Build Status](https://travis-ci.org/AmberLee2427/microlens-submit.svg?branch=main)](https://travis-ci.org/AmberLee2427/microlens-submit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`microlens-submit` provides a robust, version-controlled workflow for managing, validating, and packaging your challenge submission over a long period. It supports both a programmatic Python API and a full-featured Command Line Interface (CLI) for language-agnostic use.

## Key Features

* **Persistent Projects:** Treat your submission as a local project that you can load, edit, and save over weeks or months.
* **Python API & CLI:** Use the tool directly in your Python analysis scripts or via the command line.
* **Solution Management:** Easily add, update, and deactivate degenerate solutions for any event without losing your work history.
* **Automatic Validation:** Aggressive data validation powered by Pydantic ensures your submission is always compliant with the challenge rules.
* **Environment Capture:** Automatically records your Python dependencies for each specific model fit, ensuring reproducibility.
* **Optional Posterior Storage:** Record the path to posterior samples for any solution.
* **Simple Export:** Packages all your active solutions into a clean, standardized `.zip` archive for final submission.

## Installation

This package is pre-release. It is currently available on TestPyPI:

```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple microlens-submit==0.1.0
```

The package will be available on PyPI:

```bash
pip install microlens-submit
```

### Quickstart Using the Command Line Interface (CLI)

The CLI is the recommended way to interact with your submission project.

You can pass ``--no-color`` to any command if your terminal does not support ANSI colors.

1. Initialize your project: `microlens-submit init --team-name "Planet Pounders" --tier "advanced"`
2. Add a new solution to an event:
   ```bash
   microlens-submit add-solution ogle-2025-blg-0042 \
       --model-type binary_lens \
       --param t0=555.5 \
       --param u0=0.1 \
       --param tE=25.0 \
       --notes "This is a great fit!"
   ```
   This will create a new solution and print its unique `solution_id`.
3. Deactivate a solution that didn't work out: `microlens-submit deactivate <solution_id>`
4. List all solutions for an event: `microlens-submit list-solutions ogle-2025-blg-0042`
5. Export your final submission: `microlens-submit export --output "final_submission.zip"`

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
sol = evt.add_solution(model_type="binary_lens", parameters=params)

# Record compute info for this specific run
sol.set_compute_info(cpu_hours=15.5)
sol.notes = "This fit was generated from our Python script."

# Save progress to disk
sub.save()

# When ready, export the final package
sub.export(filename="final_submission.zip")
```

## Development
---
The full development plan can be found in agents.md. Contributions are welcome!

To build and test this project, the development environment needs the following Python libraries. You can provide these to Codex or set up a `requirements-dev.txt` file.

### Core Dependencies:
* **`typer[all]`**: For building the powerful command-line interface. The `[all]` extra ensures shell completion support is included.
* **`pydantic`**: For aggressive data validation and settings management.

### Testing Dependencies:
* **`pytest`**: The standard framework for testing Python code.
* **`pytest-cov`**: To measure test coverage.

### Packaging & Distribution Dependencies:
* **`build`**: For building the package from the `pyproject.toml` file.
* **`twine`**: For uploading the final package to PyPI.

