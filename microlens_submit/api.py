from __future__ import annotations

"""Core API for microlens-submit.

The :class:`Submission` class provides a method :meth:`Submission.export` that
creates the final zip archive using ``zipfile.ZIP_DEFLATED`` compression.
"""

import logging
import os
import subprocess
import sys
import uuid
import zipfile
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field


class Solution(BaseModel):
    """Container for an individual model fit.

    This data model stores everything required to describe a single
    microlensing solution, including the numeric parameters of the fit and
    metadata about how it was produced.  Instances are normally created via
    :meth:`Event.add_solution` and persisted to disk when
    :meth:`Submission.save` is called.

    Attributes:
        solution_id: Unique identifier for the solution.
        model_type: Short string describing the type of model (e.g.
            ``"point_lens"`` or ``"binary_lens"``).
        model_name: Optional name of the software used to produce the fit.
        parameters: Dictionary of model parameters used for the fit.
        is_active: Flag indicating whether the solution should be included in
            the final submission export.
        compute_info: Metadata about the computing environment.  Populated by
            :meth:`set_compute_info`.
        posterior_path: Optional path to a file containing posterior samples.
        notes: Free-form notes about the solution.
        used_astrometry: Whether astrometric information was used when fitting
            this solution.
        used_postage_stamps: Whether postage stamp data was used.
        limb_darkening_model: Name of the limb darkening model employed.
        limb_darkening_coeffs: Mapping of limb darkening coefficients.
        parameter_uncertainties: Uncertainties for parameters in ``parameters``.
        physical_parameters: Physical parameters derived from the model.
        log_likelihood: Log-likelihood value of the fit.
        log_prior: Log-prior value of the fit.
        relative_probability: Optional probability of this solution being the best model.
        n_data_points: Number of data points used in the fit.
        creation_timestamp: UTC timestamp when the solution was created.
    """

    solution_id: str
    model_type: str
    model_name: Optional[str] = None
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

    def set_compute_info(
        self,
        cpu_hours: float | None = None,
        wall_time_hours: float | None = None,
    ) -> None:
        """Record compute metadata and capture environment details.

        When called, this method populates :attr:`compute_info` with timing
        information as well as a list of installed Python packages and the
        current Git state.  It is safe to call multiple times—previous values
        will be overwritten.

        Args:
            cpu_hours: Total CPU time consumed by the model fit in hours.
            wall_time_hours: Real-world time consumed by the fit in hours.
        """

        if cpu_hours is not None:
            self.compute_info["cpu_hours"] = cpu_hours
        if wall_time_hours is not None:
            self.compute_info["wall_time_hours"] = wall_time_hours

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.compute_info["dependencies"] = (
                result.stdout.strip().split("\n") if result.stdout else []
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.warning("Could not capture pip environment: %s", e)
            self.compute_info["dependencies"] = []

        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            self.compute_info["git_info"] = {
                "commit": commit,
                "branch": branch,
                "is_dirty": bool(status),
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.warning("Could not capture git info: %s", e)
            self.compute_info["git_info"] = None

    def deactivate(self) -> None:
        """Mark this solution as inactive."""
        self.is_active = False

    def activate(self) -> None:
        """Mark this solution as active."""
        self.is_active = True

    def _save(self, event_path: Path) -> None:
        """Write this solution to disk.

        Args:
            event_path: Directory of the parent event within the project.
        """
        solutions_dir = event_path / "solutions"
        solutions_dir.mkdir(parents=True, exist_ok=True)
        out_path = solutions_dir / f"{self.solution_id}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            fh.write(self.model_dump_json(indent=2))


class Event(BaseModel):
    """A collection of solutions for a single microlensing event.

    Events act as containers that group one or more :class:`Solution` objects
    under a common ``event_id``.  They are created on demand via
    :meth:`Submission.get_event` and are written to disk when the parent
    submission is saved.

    Attributes:
        event_id: Identifier used to reference the event within the project.
        solutions: Mapping of solution IDs to :class:`Solution` instances.
        submission: The parent :class:`Submission` or ``None`` if detached.
    """

    event_id: str
    solutions: Dict[str, Solution] = Field(default_factory=dict)
    submission: Optional["Submission"] = Field(default=None, exclude=True)

    def add_solution(self, model_type: str, parameters: dict) -> Solution:
        """Create and attach a new solution to this event.

        Parameters are stored as provided and the new solution is returned for
        further modification.

        Args:
            model_type: Short label describing the model type.
            parameters: Dictionary of model parameters.

        Returns:
            Solution: The newly created solution instance.
        """
        solution_id = str(uuid.uuid4())
        sol = Solution(
            solution_id=solution_id, model_type=model_type, parameters=parameters
        )
        self.solutions[solution_id] = sol
        return sol

    def get_solution(self, solution_id: str) -> Solution:
        """Return a previously added solution.

        Args:
            solution_id: Identifier of the solution to retrieve.

        Returns:
            Solution: The corresponding solution.
        """
        return self.solutions[solution_id]

    def get_active_solutions(self) -> list[Solution]:
        """Return all solutions currently marked as active."""

        return [sol for sol in self.solutions.values() if sol.is_active]

    def clear_solutions(self) -> None:
        """Deactivate every solution associated with this event."""

        for sol in self.solutions.values():
            sol.is_active = False

    @classmethod
    def _from_dir(cls, event_dir: Path, submission: "Submission") -> "Event":
        """Load an event from disk."""
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
        """Write this event and its solutions to disk."""
        if self.submission is None:
            raise ValueError("Event is not attached to a submission")
        base = Path(self.submission.project_path) / "events" / self.event_id
        base.mkdir(parents=True, exist_ok=True)
        with (base / "event.json").open("w", encoding="utf-8") as fh:
            fh.write(
                self.model_dump_json(exclude={"solutions", "submission"}, indent=2)
            )
        for sol in self.solutions.values():
            sol._save(base)


class Submission(BaseModel):
    """Top-level object representing an on-disk submission project.

    A ``Submission`` manages a collection of :class:`Event` objects and handles
    serialization to the project directory.  Users typically obtain an instance
    via :func:`load` and then interact with events and solutions before calling
    :meth:`save` or :meth:`export`.

    Attributes:
        project_path: Root directory where submission files are stored.
        team_name: Name of the participating team.
        tier: Challenge tier for the submission.
        hardware_info: Optional dictionary describing the compute platform.
        events: Mapping of event IDs to :class:`Event` instances.
    """

    project_path: str = Field(default="", exclude=True)
    team_name: str = ""
    tier: str = ""
    hardware_info: Optional[dict] = None
    events: Dict[str, Event] = Field(default_factory=dict)

    def validate(self) -> list[str]:
        """Check the submission for missing or incomplete information.

        The method performs lightweight validation and returns a list of
        warnings describing potential issues.  It does not raise exceptions and
        can be used to provide user feedback prior to exporting.

        Returns:
            list[str]: Human-readable warning messages.
        """

        warnings: list[str] = []
        if not self.hardware_info:
            warnings.append("Hardware info is missing")

        for event in self.events.values():
            active = [sol for sol in event.solutions.values() if sol.is_active]
            if not active:
                warnings.append(f"Event {event.event_id} has no active solutions")
            for sol in active:
                if sol.log_likelihood is None:
                    warnings.append(
                        f"Solution {sol.solution_id} in event {event.event_id} is missing log_likelihood"
                    )
                if sol.lightcurve_plot_path is None:
                    warnings.append(
                        f"Solution {sol.solution_id} in event {event.event_id} is missing lightcurve_plot_path"
                    )
                if sol.lens_plane_plot_path is None:
                    warnings.append(
                        f"Solution {sol.solution_id} in event {event.event_id} is missing lens_plane_plot_path"
                    )

        return warnings

    def get_event(self, event_id: str) -> Event:
        """Return the event with ``event_id``.

        If the event does not yet exist in the submission it will be created
        automatically and attached to the submission.

        Args:
            event_id: Identifier of the event.

        Returns:
            Event: The corresponding event object.
        """
        if event_id not in self.events:
            self.events[event_id] = Event(event_id=event_id, submission=self)
        return self.events[event_id]

    def autofill_nexus_info(self) -> None:
        """Populate :attr:`hardware_info` with Roman Nexus platform details.

        This helper reads a few well-known files from the Roman Science
        Platform environment to infer CPU model, available memory and the image
        identifier.  Missing information is silently ignored.
        """

        if self.hardware_info is None:
            self.hardware_info = {}

        try:
            image = os.environ.get("JUPYTER_IMAGE_SPEC")
            if image:
                self.hardware_info["nexus_image"] = image
        except Exception as exc:  # pragma: no cover - environment may not exist
            logging.debug("Failed to read JUPYTER_IMAGE_SPEC: %s", exc)

        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        self.hardware_info["cpu_details"] = line.split(":", 1)[
                            1
                        ].strip()
                        break
        except OSError as exc:  # pragma: no cover
            logging.debug("Failed to read /proc/cpuinfo: %s", exc)

        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal"):
                        mem_kb = int(line.split(":", 1)[1].strip().split()[0])
                        self.hardware_info["memory_gb"] = round(mem_kb / 1024**2, 2)
                        break
        except OSError as exc:  # pragma: no cover
            logging.debug("Failed to read /proc/meminfo: %s", exc)

    def save(self) -> None:
        """Persist the current state of the submission to ``project_path``."""
        project = Path(self.project_path)
        events_dir = project / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        with (project / "submission.json").open("w", encoding="utf-8") as fh:
            fh.write(self.model_dump_json(exclude={"events", "project_path"}, indent=2))
        for event in self.events.values():
            event.submission = self
            event._save()

    def export(self, output_path: str) -> None:
        """Create a zip archive of all active solutions.

        The archive is created using ``zipfile.ZIP_DEFLATED`` compression to
        minimize file size.

        Args:
            output_path: Destination path for the zip archive.
        """
        project = Path(self.project_path)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            submission_json = project / "submission.json"
            if submission_json.exists():
                zf.write(submission_json, arcname="submission.json")
            events_dir = project / "events"
            for event in self.events.values():
                event_dir = events_dir / event.event_id
                event_json = event_dir / "event.json"
                if event_json.exists():
                    zf.write(event_json, arcname=f"events/{event.event_id}/event.json")
                active_sols = [s for s in event.solutions.values() if s.is_active]

                # Determine relative probabilities for this event
                rel_prob_map: dict[str, float] = {}
                if active_sols:
                    provided_sum = sum(
                        s.relative_probability or 0.0
                        for s in active_sols
                        if s.relative_probability is not None
                    )
                    need_calc = [
                        s for s in active_sols if s.relative_probability is None
                    ]
                    if need_calc:
                        can_calc = True
                        for s in need_calc:
                            if (
                                s.log_likelihood is None
                                or s.n_data_points is None
                                or s.n_data_points <= 0
                                or len(s.parameters) == 0
                            ):
                                can_calc = False
                                break
                        remaining = max(1.0 - provided_sum, 0.0)
                        if can_calc:
                            bic_vals = {
                                s.solution_id: len(s.parameters)
                                * math.log(s.n_data_points)
                                - 2 * s.log_likelihood
                                for s in need_calc
                            }
                            bic_min = min(bic_vals.values())
                            weights = {
                                sid: math.exp(-0.5 * (bic - bic_min))
                                for sid, bic in bic_vals.items()
                            }
                            wsum = sum(weights.values())
                            for sid, w in weights.items():
                                rel_prob_map[sid] = (
                                    remaining * w / wsum
                                    if wsum > 0
                                    else remaining / len(weights)
                                )
                            logging.warning(
                                "relative_probability calculated for event %s using BIC",
                                event.event_id,
                            )
                        else:
                            eq = remaining / len(need_calc) if need_calc else 0.0
                            for s in need_calc:
                                rel_prob_map[s.solution_id] = eq
                            logging.warning(
                                "relative_probability set equally for event %s due to missing data",
                                event.event_id,
                            )

                for sol in active_sols:
                    sol_path = event_dir / "solutions" / f"{sol.solution_id}.json"
                    if sol_path.exists():
                        arc = (
                            f"events/{event.event_id}/solutions/{sol.solution_id}.json"
                        )
                        export_sol = sol.model_copy()
                        for attr in [
                            "posterior_path",
                            "lightcurve_plot_path",
                            "lens_plane_plot_path",
                        ]:
                            path = getattr(sol, attr)
                            if path is not None:
                                filename = Path(path).name
                                new_path = f"events/{event.event_id}/solutions/{sol.solution_id}/{filename}"
                                setattr(export_sol, attr, new_path)
                        if export_sol.relative_probability is None:
                            export_sol.relative_probability = rel_prob_map.get(
                                sol.solution_id
                            )
                        zf.writestr(arc, export_sol.model_dump_json(indent=2))
                    # Include any referenced external files
                    sol_dir_arc = f"events/{event.event_id}/solutions/{sol.solution_id}"
                    for attr in [
                        "posterior_path",
                        "lightcurve_plot_path",
                        "lens_plane_plot_path",
                    ]:
                        path = getattr(sol, attr)
                        if path is not None:
                            file_path = Path(self.project_path) / path
                            if not file_path.exists():
                                raise ValueError(
                                    f"Error: File specified by {attr} in solution {sol.solution_id} does not exist: {file_path}"
                                )
                            zf.write(
                                file_path,
                                arcname=f"{sol_dir_arc}/{Path(path).name}",
                            )


def load(project_path: str) -> Submission:
    """Load an existing submission or create a new one.

    The directory specified by ``project_path`` becomes the working
    directory for all subsequent operations.  If the directory does not
    exist, a new project structure is created automatically.

    Args:
        project_path: Location of the submission project on disk.

    Returns:
        Submission: The loaded or newly created submission instance.

    Example:
        >>> from microlens_submit import load
        >>> sub = load("./my_project")
        >>> evt = sub.get_event("event-001")
        >>> evt.add_solution("point_lens", {"t0": 123.4})
        >>> sub.save()
    """
    project = Path(project_path)
    events_dir = project / "events"

    if not project.exists():
        events_dir.mkdir(parents=True, exist_ok=True)
        submission = Submission(project_path=str(project))
        with (project / "submission.json").open("w", encoding="utf-8") as fh:
            fh.write(
                submission.model_dump_json(exclude={"events", "project_path"}, indent=2)
            )
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


# Resolve forward references
Event.model_rebuild()
Submission.model_rebuild()
