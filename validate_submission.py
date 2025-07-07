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
import json
import sys
from pathlib import Path
from typing import Dict, Optional

from pydantic import ValidationError

from microlens_submit.api import Event, Solution, Submission


# The Solution, Event, and Submission classes are imported from
# ``microlens_submit.api`` to ensure consistency with the main library.


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
        sub_data = json.load(fh)
    submission = Submission.model_validate(sub_data)
    submission.project_path = str(project)

    events_dir = project / "events"
    if events_dir.exists():
        for event_dir in events_dir.iterdir():
            if not event_dir.is_dir():
                continue
            event_json = event_dir / "event.json"
            if event_json.exists():
                with event_json.open("r", encoding="utf-8") as fh:
                    event_data = json.load(fh)
                event = Event.model_validate(event_data)
            else:
                event = Event(event_id=event_dir.name)
            event.submission = submission
            solutions_dir = event_dir / "solutions"
            if solutions_dir.exists():
                for sol_file in solutions_dir.glob("*.json"):
                    with sol_file.open("r", encoding="utf-8") as fh:
                        sol_data = json.load(fh)
                    if "notes" in sol_data and "notes_path" not in sol_data:
                        sol_data["notes_path"] = sol_data.pop("notes")
                    sol = Solution.model_validate(sol_data)
                    sol.saved = True
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
