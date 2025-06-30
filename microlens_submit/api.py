from __future__ import annotations

"""Core API for microlens-submit."""

from pathlib import Path
from datetime import datetime
import json
import uuid
import zipfile
from typing import Dict
from pydantic import BaseModel, Field


class Solution(BaseModel):
    """Represents a single model fit for an event."""

    solution_id: str
    model_type: str
    parameters: dict
    is_active: bool = True
    compute_info: dict = Field(default_factory=dict)
    notes: str = ""
    creation_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def set_compute_info(self, cpu_hours: float | None = None) -> None:
        """Record basic compute metadata.

        Parameters
        ----------
        cpu_hours : float, optional
            CPU hours consumed by this fit.
        """
        if cpu_hours is not None:
            self.compute_info["cpu_hours"] = cpu_hours

    def deactivate(self) -> None:
        """Mark this solution as inactive."""
        self.is_active = False

    def activate(self) -> None:
        """Mark this solution as active."""
        self.is_active = True

    def _save(self, event_path: Path) -> None:
        solutions_dir = event_path / "solutions"
        solutions_dir.mkdir(parents=True, exist_ok=True)
        out_path = solutions_dir / f"{self.solution_id}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            fh.write(self.model_dump_json(indent=2))


class Event(BaseModel):
    """Represents a microlensing event within the submission."""

    event_id: str
    solutions: Dict[str, Solution] = Field(default_factory=dict)
    submission: "Submission" | None = Field(default=None, exclude=True)

    def add_solution(self, model_type: str, parameters: dict) -> Solution:
        """Create and register a new :class:`Solution`.

        Parameters
        ----------
        model_type : str
            The type of model being added.
        parameters : dict
            Model parameters.

        Returns
        -------
        Solution
            The newly created solution instance.
        """
        solution_id = str(uuid.uuid4())
        sol = Solution(solution_id=solution_id, model_type=model_type, parameters=parameters)
        self.solutions[solution_id] = sol
        return sol

    def get_solution(self, solution_id: str) -> Solution:
        """Retrieve a solution by ID."""
        return self.solutions[solution_id]

    @classmethod
    def _from_dir(cls, event_dir: Path, submission: "Submission") -> "Event":
        event_json = event_dir / "event.json"
        if event_json.exists():
            with event_json.open("r", encoding="utf-8") as fh:
                event = cls.model_validate_json(fh.read())
        else:
            event = cls(event_id=event_dir.name)
        event.submission = submission
        solutions_dir = event_dir / "solutions"
        if solutions_dir.exists():
            for sol_file in solutions_dir.glob("*.json"):
                with sol_file.open("r", encoding="utf-8") as fh:
                    sol = Solution.model_validate_json(fh.read())
                event.solutions[sol.solution_id] = sol
        return event

    def _save(self) -> None:
        if self.submission is None:
            raise ValueError("Event is not attached to a submission")
        base = Path(self.submission.project_path) / "events" / self.event_id
        base.mkdir(parents=True, exist_ok=True)
        with (base / "event.json").open("w", encoding="utf-8") as fh:
            fh.write(self.model_dump_json(exclude={"solutions", "submission"}, indent=2))
        for sol in self.solutions.values():
            sol._save(base)


class Submission(BaseModel):
    """Container for all challenge events and solutions."""

    project_path: str = Field(exclude=True)
    team_name: str = ""
    tier: str = ""
    events: Dict[str, Event] = Field(default_factory=dict)

    def get_event(self, event_id: str) -> Event:
        """Retrieve an :class:`Event`, creating it if necessary."""
        if event_id not in self.events:
            self.events[event_id] = Event(event_id=event_id, submission=self)
        return self.events[event_id]

    def save(self) -> None:
        """Write the submission state to disk."""
        project = Path(self.project_path)
        events_dir = project / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        with (project / "submission.json").open("w", encoding="utf-8") as fh:
            fh.write(
                self.model_dump_json(
                    exclude={"events", "project_path"}, indent=2
                )
            )
        for event in self.events.values():
            event.submission = self
            event._save()

    def export(self, output_path: str) -> None:
        """Create a zip archive of active solutions only."""
        project = Path(self.project_path)
        with zipfile.ZipFile(output_path, "w") as zf:
            events_dir = project / "events"
            for event in self.events.values():
                event_dir = events_dir / event.event_id
                event_json = event_dir / "event.json"
                if event_json.exists():
                    zf.write(event_json, arcname=f"events/{event.event_id}/event.json")
                for sol in event.solutions.values():
                    if sol.is_active:
                        sol_path = event_dir / "solutions" / f"{sol.solution_id}.json"
                        if sol_path.exists():
                            arc = f"events/{event.event_id}/solutions/{sol.solution_id}.json"
                            zf.write(sol_path, arcname=arc)


def load(project_path: str) -> Submission:
    """Load or initialize a submission project.

    Parameters
    ----------
    project_path : str
        Path to the submission project on disk.

    Returns
    -------
    Submission
        The loaded or newly created :class:`Submission` instance.
    """
    project = Path(project_path)
    events_dir = project / "events"

    if not project.exists():
        events_dir.mkdir(parents=True, exist_ok=True)
        submission = Submission(project_path=str(project))
        with (project / "submission.json").open("w", encoding="utf-8") as fh:
            fh.write(submission.model_dump_json(exclude={"events", "project_path"}, indent=2))
        return submission

    sub_json = project / "submission.json"
    if sub_json.exists():
        with sub_json.open("r", encoding="utf-8") as fh:
            submission = Submission.model_validate_json(fh.read())
        submission.project_path = str(project)
    else:
        submission = Submission(project_path=str(project))

    if events_dir.exists():
        for event_dir in events_dir.iterdir():
            if event_dir.is_dir():
                event = Event._from_dir(event_dir, submission)
                submission.events[event.event_id] = event

    return submission
