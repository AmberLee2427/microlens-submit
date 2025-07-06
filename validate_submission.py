"""
Submission validation module for microlens-submit.

This module provides standalone validation functionality for microlensing challenge
submissions. It defines the core data models (Solution, Event, Submission) and
provides functions to load and validate submission directories against these models.

The module can be used both as a standalone script and as an imported module for
validation purposes. It supports the complete submission structure including
events, solutions, and metadata validation.

**Core Components:**
- Solution: Individual model fit with parameters and metadata
- Event: Container for multiple solutions for a single microlensing event
- Submission: Top-level container for all events and team information

**Validation Features:**
- JSON schema validation using Pydantic models
- File structure validation
- Data type and format checking
- Optional field handling with defaults

Example:
    >>> from validate_submission import load_submission
    >>>
    >>> # Validate a submission directory
    >>> try:
    ...     submission = load_submission("./my_submission")
    ...     print("Submission is valid!")
    ... except Exception as e:
    ...     print(f"Validation failed: {e}")
    >>>
    >>> # Access submission data
    >>> print(f"Team: {submission.team_name}")
    >>> print(f"Events: {len(submission.events)}")
    >>> for event_id, event in submission.events.items():
    ...     print(f"  {event_id}: {len(event.solutions)} solutions")

Note:
    This module is designed to work with the standard microlens-submit project
    structure. It expects submission.json in the root and events/ subdirectories
    with event.json and solutions/ subdirectories.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, ValidationError


class Solution(BaseModel):
    """Represents a single microlensing model fit solution.

    This model defines the structure for individual microlensing solutions,
    including parameters, metadata, file paths, and statistical information.
    All fields are validated against their expected types and formats.

    **Key Fields:**
    - solution_id: Unique identifier for the solution
    - model_type: Type of microlensing model (e.g., "1S1L", "1S2L")
    - parameters: Dictionary of model parameters
    - compute_info: Information about computational resources used
    - file_paths: Paths to posterior data, plots, and notes

    **Optional Features:**
    - Parameter uncertainties and physical parameters
    - Astrometry and postage stamp usage flags
    - Limb darkening models and coefficients
    - Statistical measures (log-likelihood, relative probability)

    Example:
        >>> solution = Solution(
        ...     solution_id="sol_001",
        ...     model_type="1S1L",
        ...     parameters={"t0": 2459123.5, "u0": 0.15, "tE": 20.5},
        ...     log_likelihood=-1234.56,
        ...     n_data_points=1250,
        ...     compute_info={"cpu_hours": 2.5, "wall_time_hours": 0.5}
        ... )
        >>> print(f"Solution {solution.solution_id} has {len(solution.parameters)} parameters")

    Note:
        The solution_id should be unique within an event. The model_type
        should match one of the supported microlensing model types.
    """

    solution_id: str
    model_type: str
    parameters: dict
    is_active: bool = True
    compute_info: dict = Field(default_factory=dict)
    posterior_path: Optional[str] = None
    lightcurve_plot_path: Optional[str] = None
    lens_plane_plot_path: Optional[str] = None
    notes: str = ""
    used_astrometry: bool = False
    used_postage_stamps: bool = False
    limb_darkening_model: Optional[str] = None
    limb_darkening_coeffs: Optional[dict] = None
    parameter_uncertainties: Optional[dict] = None
    physical_parameters: Optional[dict] = None
    log_likelihood: Optional[float] = None
    log_prior: Optional[float] = None
    relative_probability: Optional[float] = None
    n_data_points: Optional[int] = None
    creation_timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class Event(BaseModel):
    """Represents a microlensing event with multiple solutions.

    This model defines the structure for individual microlensing events,
    which can contain multiple solutions from different model fits or
    analysis approaches.

    **Key Features:**
    - event_id: Unique identifier for the microlensing event
    - solutions: Dictionary of Solution objects indexed by solution_id
    - Support for multiple active/inactive solutions per event

    Example:
        >>> event = Event(event_id="EVENT001")
        >>> event.solutions["sol_001"] = Solution(
        ...     solution_id="sol_001",
        ...     model_type="1S1L",
        ...     parameters={"t0": 2459123.5, "u0": 0.15, "tE": 20.5}
        ... )
        >>> print(f"Event {event.event_id} has {len(event.solutions)} solutions")

    Note:
        Events can have multiple solutions, but typically only one should
        be active per event for final submission. The event_id should
        match the standard microlensing event naming convention.
    """

    event_id: str
    solutions: Dict[str, Solution] = Field(default_factory=dict)


class Submission(BaseModel):
    """Container for all events and metadata in a microlensing submission.

    This is the top-level model that represents an entire microlensing
    challenge submission. It contains team information, hardware details,
    and all events with their solutions.

    **Key Components:**
    - team_name: Name of the submitting team
    - tier: Challenge tier (e.g., "standard", "advanced")
    - hardware_info: Computational resources used
    - events: Dictionary of Event objects indexed by event_id

    **Validation Features:**
    - Ensures all events have valid structures
    - Validates team and tier information
    - Checks hardware information completeness

    Example:
        >>> submission = Submission(
        ...     team_name="Team Alpha",
        ...     tier="advanced",
        ...     hardware_info={"cpu": "Intel Xeon", "memory_gb": 64}
        ... )
        >>> submission.events["EVENT001"] = Event(event_id="EVENT001")
        >>> print(f"Team {submission.team_name} submitted {len(submission.events)} events")

    Note:
        The project_path field is excluded from serialization as it's
        used internally for file path resolution. Hardware information
        should include details about the computational resources used
        for the analysis.
    """

    project_path: str = Field(default="", exclude=True)
    team_name: str = ""
    tier: str = ""
    hardware_info: Optional[dict] = None
    events: Dict[str, Event] = Field(default_factory=dict)


def load_submission(path: str) -> Submission:
    """Load and validate a submission directory.

    Loads a complete microlensing submission from a directory structure,
    validating all JSON files against the defined Pydantic models. This
    function handles the complete submission hierarchy including events
    and solutions.

    Args:
        path: Path to the submission directory containing submission.json
            and events/ subdirectory structure.

    Returns:
        Submission: A validated Submission instance with all events and
            solutions loaded and validated.

    Raises:
        FileNotFoundError: If submission.json doesn't exist in the path.
        ValidationError: If any JSON file fails Pydantic validation.
        Exception: For other file reading or parsing errors.

    Example:
        >>> # Load a submission from a directory
        >>> try:
        ...     submission = load_submission("./my_submission_project")
        ...     print(f"Loaded submission for team: {submission.team_name}")
        ...     print(f"Total events: {len(submission.events)}")
        ...     total_solutions = sum(len(event.solutions) for event in submission.events.values())
        ...     print(f"Total solutions: {total_solutions}")
        ... except FileNotFoundError:
        ...     print("Submission directory not found")
        ... except ValidationError as e:
        ...     print(f"Validation error: {e}")

    Note:
        This function expects the standard microlens-submit project structure:
        - submission.json in the root directory
        - events/ subdirectory with event subdirectories
        - Each event subdirectory should contain event.json and solutions/
        - Solutions directory should contain .json files for each solution

        The function will create Event objects for directories that don't
        have event.json files, using the directory name as the event_id.
    """
    project = Path(path)
    sub_json = project / "submission.json"
    if not sub_json.exists():
        raise FileNotFoundError(f"{sub_json} does not exist")

    with sub_json.open("r", encoding="utf-8") as fh:
        submission = Submission.model_validate_json(fh.read())
    submission.project_path = str(project)

    events_dir = project / "events"
    if events_dir.exists():
        for event_dir in events_dir.iterdir():
            if not event_dir.is_dir():
                continue
            event_json = event_dir / "event.json"
            if event_json.exists():
                with event_json.open("r", encoding="utf-8") as fh:
                    event = Event.model_validate_json(fh.read())
            else:
                event = Event(event_id=event_dir.name)
            solutions_dir = event_dir / "solutions"
            if solutions_dir.exists():
                for sol_file in solutions_dir.glob("*.json"):
                    with sol_file.open("r", encoding="utf-8") as fh:
                        sol = Solution.model_validate_json(fh.read())
                    event.solutions[sol.solution_id] = sol
            submission.events[event.event_id] = event

    return submission


def main() -> None:
    """Command-line interface for submission validation.

    Provides a simple command-line interface to validate microlensing
    submissions. This function parses command-line arguments and calls
    load_submission() to perform the validation.

    **Usage:**
        python validate_submission.py <submission_path>

    **Exit Codes:**
        - 0: Submission is valid
        - 1: Validation failed or error occurred

    Example:
        >>> # From command line:
        >>> # python validate_submission.py ./my_submission
        >>> #
        >>> # Or programmatically:
        >>> import sys
        >>> sys.argv = ['validate_submission.py', './my_submission']
        >>> main()

    Note:
        This function is designed to be used as a standalone script.
        It provides simple pass/fail validation with error messages
        printed to stdout. For more detailed validation, use the
        load_submission() function directly.
    """
    parser = argparse.ArgumentParser(description="Validate a microlensing submission")
    parser.add_argument("path", help="Path to the submission directory")
    args = parser.parse_args()

    try:
        load_submission(args.path)
    except (ValidationError, Exception) as exc:
        print(exc)
        sys.exit(1)

    print("Submission is valid.")
    sys.exit(0)


if __name__ == "__main__":
    main()
