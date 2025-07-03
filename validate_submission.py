from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, ValidationError


class Solution(BaseModel):
    """Represents a single model fit."""

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
    """Represents a microlensing event."""

    event_id: str
    solutions: Dict[str, Solution] = Field(default_factory=dict)


class Submission(BaseModel):
    """Container for all events in a submission."""

    project_path: str = Field(default="", exclude=True)
    team_name: str = ""
    tier: str = ""
    hardware_info: Optional[dict] = None
    events: Dict[str, Event] = Field(default_factory=dict)


def load_submission(path: str) -> Submission:
    """Load and validate a submission directory.

    Args:
        path: Path to the submission directory.

    Returns:
        A validated :class:`Submission` instance.
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
