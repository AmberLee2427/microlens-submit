from __future__ import annotations

"""Core API for microlens-submit."""

from pathlib import Path
from datetime import datetime
import json
import uuid
from typing import Dict


class Solution:
    """Represents a single model fit for an event.

    Parameters
    ----------
    solution_id : str
        Unique identifier for this solution.
    model_type : str
        Type of model (e.g., ``single_lens``).
    parameters : dict
        Best-fit parameters for the model.
    """

    def __init__(self, solution_id: str, model_type: str, parameters: dict) -> None:
        self.solution_id: str = solution_id
        self.model_type: str = model_type
        self.parameters: dict = parameters
        self.is_active: bool = True
        self.compute_info: dict = {}
        self.notes: str = ""
        self.creation_timestamp: str = datetime.utcnow().isoformat()

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

    def _to_dict(self) -> dict:
        return {
            "solution_id": self.solution_id,
            "model_type": self.model_type,
            "parameters": self.parameters,
            "is_active": self.is_active,
            "compute_info": self.compute_info,
            "notes": self.notes,
            "creation_timestamp": self.creation_timestamp,
        }

    @classmethod
    def _from_dict(cls, data: dict) -> "Solution":
        sol = cls(
            solution_id=data["solution_id"],
            model_type=data.get("model_type", ""),
            parameters=data.get("parameters", {}),
        )
        sol.is_active = data.get("is_active", True)
        sol.compute_info = data.get("compute_info", {})
        sol.notes = data.get("notes", "")
        sol.creation_timestamp = data.get(
            "creation_timestamp", datetime.utcnow().isoformat()
        )
        return sol

    def _save(self, event_path: Path) -> None:
        solutions_dir = event_path / "solutions"
        solutions_dir.mkdir(parents=True, exist_ok=True)
        out_path = solutions_dir / f"{self.solution_id}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(self._to_dict(), fh, indent=2)


class Event:
    """Represents a microlensing event within the submission."""

    def __init__(self, event_id: str, submission: "Submission") -> None:
        self.event_id: str = event_id
        self.solutions: Dict[str, Solution] = {}
        self._submission = submission

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

    def _to_dict(self) -> dict:
        return {"event_id": self.event_id}

    @classmethod
    def _from_dir(cls, event_dir: Path, submission: "Submission") -> "Event":
        event_json = event_dir / "event.json"
        if event_json.exists():
            with event_json.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            event_id = data.get("event_id", event_dir.name)
        else:
            event_id = event_dir.name
        event = cls(event_id=event_id, submission=submission)
        solutions_dir = event_dir / "solutions"
        if solutions_dir.exists():
            for sol_file in solutions_dir.glob("*.json"):
                with sol_file.open("r", encoding="utf-8") as fh:
                    sdata = json.load(fh)
                sol = Solution._from_dict(sdata)
                event.solutions[sol.solution_id] = sol
        return event

    def _save(self) -> None:
        base = Path(self._submission.project_path) / "events" / self.event_id
        base.mkdir(parents=True, exist_ok=True)
        with (base / "event.json").open("w", encoding="utf-8") as fh:
            json.dump(self._to_dict(), fh, indent=2)
        for sol in self.solutions.values():
            sol._save(base)


class Submission:
    """Container for all challenge events and solutions."""

    def __init__(self, project_path: str) -> None:
        self.project_path = str(Path(project_path))
        self.team_name: str = ""
        self.tier: str = ""
        self.events: Dict[str, Event] = {}

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
        sub_data = {"team_name": self.team_name, "tier": self.tier}
        with (project / "submission.json").open("w", encoding="utf-8") as fh:
            json.dump(sub_data, fh, indent=2)
        for event in self.events.values():
            event._save()


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
            json.dump({"team_name": "", "tier": ""}, fh, indent=2)
        return submission

    submission = Submission(project_path=str(project))
    sub_json = project / "submission.json"
    if sub_json.exists():
        with sub_json.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            submission.team_name = data.get("team_name", "")
            submission.tier = data.get("tier", "")

    if events_dir.exists():
        for event_dir in events_dir.iterdir():
            if event_dir.is_dir():
                event = Event._from_dir(event_dir, submission)
                submission.events[event.event_id] = event

    return submission
