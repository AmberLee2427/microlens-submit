# **Development Plan: `microlens-submit`**

**Version:** 1.1  
**Author:** Gemini & Amber  
**Date:** June 30, 2025

## **1\. Project Overview & Goals**

The `microlens-submit` library is a Python-based toolkit designed to help participants in a microlensing data challenge manage and package their results.

The primary goals are:

* Provide a simple, programmatic **Python API** for creating and modifying submissions.  
* Offer a full **Command Line Interface (CLI)** for language-agnostic use, supporting participants whose analysis code is not in Python.  
* Support a long-term, iterative workflow by treating the submission as a **persistent, on-disk project**.  
* Handle complex submission requirements, including degenerate solutions, optional posteriors, and different modeling approaches.  
* Ensure data integrity through **aggressive input validation**.  
* Capture detailed **computational metadata**, including timing and environment dependencies for each model fit.  
* Be easily installable via pip from the Python Package Index (PyPI).  
* **Standardize the final submission format** into a clean, easy-to-parse zip archive.

## **2\. Core Concepts & Workflow**

The library is built around a stateful, object-oriented model that mirrors the structure of the challenge. The user's submission is treated as a persistent project on their local disk. The primary workflow is through the Python API, with a parallel CLI providing access to the same functionality.

**The user workflow is as follows:**

1. **Initialize/Load:** The user starts by calling `microlens_submit.load(project_path)` or `microlens-submit init` to load or create a submission project.  
2. **Modify:** The user gets Event objects from the main `Submission` object. For each event, they can add one or more Solution objects, representing different model fits.  
3. **Record Metadata:** For each `Solution`, the user records the model parameters and calls `.set_compute_info()` to log timing and capture the environment dependencies for that specific run.  
4. **Manage Solutions:** If a fit is unsatisfactory, the user can `.deactivate()` it. This "soft deletes" the solution—it remains in the project history but is excluded from the final export.  
5. **Save Progress:** The user periodically calls `.save()` to write all changes back to the file system.  
6. **Export:** When the challenge is complete, the user calls `.export()` or `microlens-submit export` to generate the final `.zip` archive.

## **3\. Python Class Structure (The API)**

The library will expose three main classes: `Submission`, `Event`, and `Solution`.

### **3.1. Data Validation**

The library will aggressively validate all user input to prevent data corruption and ensure compliance with the submission format. This will be implemented using `Pydantic` to define strict, typed schemas for all data structures. This ensures that any attempt to save malformed data will raise a clear `ValidationError`.

### **3.2. Core Classes**

### **`Submission` Class**

Manages the overall submission project.

**Attributes:**

* `project_path` (str): The root directory of the submission project.  
* `team_name` (str): The participant's team name.  
* `tier` (str): The challenge tier (e.g., "standard", "advanced").  
* `events` (dict): A dictionary mapping `event_id` to `Event` objects.

**Methods:**

* `__init__(self, project_path)`: Internal constructor. Users should use `microlens_submit.load()`.  
* `get_event(self, event_id)`: Retrieves an `Event` object. If it doesn't exist, it is created and returned. This prevents key errors for new events. The event IDs are validated against the known event IDs for the data challenge tier; it does not accept random keys. Only expected ones.  
* `save(self)`: Serializes the entire submission state to JSON files within the `project_path`.  
* `export(self, filename)`: Creates a final `.zip` archive containing only active solutions and their associated files.

### **`Event` Class**

Represents a single microlensing event being modeled.

**Attributes:**

* `event_id` (str): The unique identifier for the event.  
* `solutions` (dict): A dictionary mapping `solution_id` to `Solution` objects.

**Methods:**

* `add_solution(self, model_type, parameters)`: Creates a new `Solution` object, adds it to the event, and returns it.  
* `get_solution(self, solution_id)`: Retrieves an existing `Solution` object by its ID.  
* `get_active_solutions(self)`: Returns a list of all active `Solution` objects for the event.  
* `clear_solutions(self)`: Deactivates all solutions for this event. It does **not** delete them.

### **`Solution` Class**

Represents a single, specific model fit for an `Event`.

**Attributes:**

* `solution_id` (str): A unique ID for the solution (e.g., a UUID generated on creation).  
* `model_type` (str): The type of model (e.g., "single\_lens", "binary\_lens", "false\_positive").  
* `parameters` (dict): The best-fit model parameters.  
* `is_active` (bool): Flag indicating if the solution should be included in the final export. Defaults to `True`.  
* `compute_info` (dict): Stores CPU hours, wall time, and dependencies.  
* `posterior_path` (str, optional): A relative path to an associated posterior file.  
* `notes` (str, optional): User-provided notes about the fit.  
* `creation_timestamp` (str): ISO 8601 timestamp of when the solution was created.

**Methods:**

* `set_compute_info(self, cpu_hours=None, wall_time_hours=None)`: Records timing information. This method will also be responsible for automatically capturing the current Python environment (`pip freeze`) *at the time of execution* and storing it in the compute\_info attribute.  
* `deactivate(self)`: Sets `is_active` to `False`.  
* `activate(self)`: Sets `is_active` to `True`.

## **4\. Command Line Interface (CLI)**

A full-featured CLI will provide access to all core library functions, making the tool language-agnostic. The CLI will be built using the **`Typer`** library for its modern features, automatic help generation, and robust command structure.

**Example CLI Commands:**

* `microlens-submit init --team-name "Planet Pounders" --tier "advanced"`: Initializes a new submission project in the current directory.  
* `microlens-submit add-solution <event_id> --model-type binary_lens --param t0=555.5 --param u0=0.1`: Adds a new, active solution to an event.  
* `microlens-submit list-solutions <event_id>`: Displays a summary of all solutions (active and inactive) for a given event.  
* `microlens-submit deactivate <solution_id>`: Deactivates a specific solution.  
* `microlens-submit export --output "final_submission.zip"`: Packages all active solutions into the final zip file.

## **5\. On-Disk File Structure**

The `project_path` will be organized as follows to ensure persistence and clarity. All data will be stored in JSON format.

```  
<project_path>/  
├── submission.json  
├── events/  
│   ├── <event_id_1>/  
│   │   ├── event.json  
│   │   ├── solutions/  
│   │   │   ├── <solution_id_A>.json  
│   │   │   └── <solution_id_B>.json  
│   │   └── posteriors/  
│   │       └── posterior_A.h5  
│   │  
│   └── <event_id_2>/  
│       ├── event.json  
│       └── ...  
```

**File Contents:**

* **`Submission.json`**:  
  ```text  
  {  
    "team_name": "Team Supernova",  
    "tier": "advanced",  
    "challenge_version": "1.0"  
  }  
  ```

* **`events/<event_id>/event.json`**:  
  ```text  
  {  
    "event_id": "ogle-2025-blg-0042",  
    "last_modified": "2025-07-15T14:00:00Z"  
  }  
  ```

* **`events/<event_id>/solutions/<solution_id>.json`**:  
  ```text  
  {  
    "solution_id": "a1b2c3d4-e5f6-...",  
    "creation_timestamp": "2025-07-15T13:45:10Z",  
    "is_active": true,  
    "model_type": "binary_lens",  
    "parameters": {  
      "t0": 555.5, "u0": 0.1, "tE": 25.0  
    },  
    "posterior_path": "posteriors/posterior_A.h5",  
    "notes": "Initial fit, looks promising.",  
    "compute_info": {  
      "cpu_hours": 15.5,  
      "wall_time_hours": 2.1,  
      "dependencies": [  
        "numpy==1.21.2",  
        "scipy==1.7.1",  
        "emcee==3.1.0"  
      ]  
    }  
  }  
  ```

## **6\. Example Usage (Full Lifecycle)**

This snippet demonstrates the intended use of the library from start to finish.

```python  
import microlens_submit  
import time

# --- Day 1: Initial Setup ---  
# Load/create the project  
sub = microlens_submit.load(project_path="./my_challenge_submission")  
sub.team_name = "Planet Pounders"  
sub.tier = "advanced"

# Get an event and add a first-pass solution  
evt = sub.get_event("event-001")  
params_1 = {"t0": 123.4, "u0": 0.5, "tE": 10.0}  
sol_1 = evt.add_solution(model_type="single_lens", parameters=params_1)

# Record compute info for this specific run  
sol_1.set_compute_info(cpu_hours=0.5)  
sol_1.notes = "Quick initial fit. Might be a binary."

# Save progress  
sub.save()

# --- Day 20: Re-fitting with a better model ---  
sub = microlens_submit.load(project_path="./my_challenge_submission")  
evt = sub.get_event("event-001")

# Deactivate the old, simple solution  
old_solution = evt.get_solution(sol_1.solution_id) # Assume we stored the ID  
old_solution.deactivate()

# Run a more complex fit  
params_2 = {"t0": 123.5, "u0": 0.1, "tE": 12.0, "q": 0.1, "s": 1.2}  
sol_2 = evt.add_solution(model_type="binary_lens", parameters=params_2)  
sol_2.set_compute_info(cpu_hours=24.0)  
sol_2.notes = "Binary model provides a much better fit."

# Save again  
sub.save()

# --- Final Day: Export ---  
sub = microlens_submit.load(project_path="./my_challenge_submission")  
# Final checks...  
# ...

# Create the final submission package  
sub.export(filename="planet_pounders_final.zip")  
```

## **7\. Distribution & Installation**

The package will be distributed as a modern Python package on the **Python Package Index (PyPI)**.

* **Installation:** The tool will be installable with a single command:  
* **Packaging:** The project will use a `pyproject.toml` file to manage dependencies, project metadata, and define the entry point for the command-line script.
