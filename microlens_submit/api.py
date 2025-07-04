from __future__ import annotations

"""Core API for microlens-submit.

This module provides the core data models and API for managing microlensing
challenge submissions. The main classes are:

- :class:`Submission`: Top-level container for a submission project
- :class:`Event`: Container for solutions to a single microlensing event  
- :class:`Solution`: Individual model fit with parameters and metadata

The :class:`Submission` class provides methods for validation, export, and
persistence. The :func:`load` function is the main entry point for loading
or creating submission projects.

Example:
    >>> from microlens_submit import load
    >>> 
    >>> # Load or create a submission project
    >>> submission = load("./my_project")
    >>> 
    >>> # Set submission metadata
    >>> submission.team_name = "Team Alpha"
    >>> submission.tier = "advanced"
    >>> submission.repo_url = "https://github.com/team/repo"
    >>> 
    >>> # Add an event and solution
    >>> event = submission.get_event("EVENT001")
    >>> solution = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
    >>> solution.log_likelihood = -1234.56
    >>> solution.set_compute_info(cpu_hours=2.5, wall_time_hours=0.5)
    >>> 
    >>> # Save the submission
    >>> submission.save()
    >>> 
    >>> # Export for submission
    >>> submission.export("submission.zip")
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
from typing import Dict, Optional, Literal, List

from pydantic import BaseModel, Field


class Solution(BaseModel):
    """Container for an individual microlensing model fit.

    This data model stores everything required to describe a single
    microlensing solution, including the numeric parameters of the fit and
    metadata about how it was produced. Instances are normally created via
    `Event.add_solution` and persisted to disk when
    `Submission.save` is called.

    Attributes:
        solution_id: Unique identifier for the solution (auto-generated UUID).
        model_type: Specific lens/source configuration such as "1S1L" or "1S2L".
        bands: List of photometric bands used in the fit (e.g., ["0", "1", "2"]).
        higher_order_effects: List of physical effects modeled (e.g., ["parallax"]).
        t_ref: Reference time for time-dependent effects (Julian Date).
        parameters: Dictionary of model parameters used for the fit.
        is_active: Flag indicating whether the solution should be included in
            the final submission export.
        compute_info: Metadata about the computing environment, populated by
            :meth:`set_compute_info`.
        posterior_path: Optional path to a file containing posterior samples.
        lightcurve_plot_path: Optional path to the lightcurve plot file.
        lens_plane_plot_path: Optional path to the lens plane plot file.
        notes_path: Path to the markdown notes file for this solution.
        used_astrometry: Whether astrometric information was used when fitting.
        used_postage_stamps: Whether postage stamp data was used.
        limb_darkening_model: Name of the limb darkening model employed.
        limb_darkening_coeffs: Mapping of limb darkening coefficients.
        parameter_uncertainties: Uncertainties for parameters in parameters.
        physical_parameters: Physical parameters derived from the model.
        log_likelihood: Log-likelihood value of the fit.
        relative_probability: Optional probability of this solution being the best model.
        n_data_points: Number of data points used in the fit.
        creation_timestamp: UTC timestamp when the solution was created.
        
    Example:
        >>> from microlens_submit import load
        >>> 
        >>> # Load a submission and get an event
        >>> submission = load("./my_project")
        >>> event = submission.get_event("EVENT001")
        >>> 
        >>> # Create a simple 1S1L solution
        >>> solution = event.add_solution("1S1L", {
        ...     "t0": 2459123.5,  # Time of closest approach
        ...     "u0": 0.1,       # Impact parameter
        ...     "tE": 20.0       # Einstein crossing time
        ... })
        >>> 
        >>> # Add metadata
        >>> solution.log_likelihood = -1234.56
        >>> solution.n_data_points = 1250
        >>> solution.relative_probability = 0.8
        >>> solution.higher_order_effects = ["parallax"]
        >>> solution.t_ref = 2459123.0
        >>> 
        >>> # Record compute information
        >>> solution.set_compute_info(cpu_hours=2.5, wall_time_hours=0.5)
        >>> 
        >>> # Add notes
        >>> solution.set_notes("# My Solution Notes\n\nThis is a simple point lens fit.")
        >>> 
        >>> # Validate the solution
        >>> messages = solution.validate()
        >>> if messages:
        ...     print("Validation issues:", messages)
        
    Note:
        The notes_path field supports Markdown formatting, allowing you to create rich,
        structured documentation with headers, lists, code blocks, tables, and links.
        This is particularly useful for creating detailed submission dossiers for evaluators.
        
        The validate() method performs comprehensive validation of parameters,
        higher-order effects, and physical consistency. Always validate solutions
        before submission.
    """

    solution_id: str
    model_type: Literal["1S1L", "1S2L", "2S1L", "2S2L", "1S3L", "2S3L", "other"]
    bands: List[str] = Field(default_factory=list)
    higher_order_effects: List[
        Literal[
            "lens-orbital-motion",
            "parallax",
            "finite-source",
            "limb-darkening",
            "xallarap",
            "stellar-rotation",
            "fitted-limb-darkening",
            "gaussian-process",
            "other",
        ]
    ] = Field(default_factory=list)
    t_ref: Optional[float] = None
    parameters: dict
    is_active: bool = True
    compute_info: dict = Field(default_factory=dict)
    posterior_path: Optional[str] = None
    lightcurve_plot_path: Optional[str] = None
    lens_plane_plot_path: Optional[str] = None
    notes_path: Optional[str] = None
    used_astrometry: bool = False
    used_postage_stamps: bool = False
    limb_darkening_model: Optional[str] = None
    limb_darkening_coeffs: Optional[dict] = None
    parameter_uncertainties: Optional[dict] = None
    physical_parameters: Optional[dict] = None
    log_likelihood: Optional[float] = None
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
        current Git state. It is safe to call multiple times—previous values
        will be overwritten.

        Args:
            cpu_hours: Total CPU time consumed by the model fit in hours.
            wall_time_hours: Real-world time consumed by the fit in hours.

        Example:
            >>> solution = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1})
            >>> 
            >>> # Record compute information
            >>> solution.set_compute_info(cpu_hours=2.5, wall_time_hours=0.5)
            >>> 
            >>> # The compute_info now contains:
            >>> # - cpu_hours: 2.5
            >>> # - wall_time_hours: 0.5
            >>> # - dependencies: [list of installed packages]
            >>> # - git_info: {commit, branch, is_dirty}
            
        Note:
            This method automatically captures the current Python environment
            (via pip freeze) and Git state (commit, branch, dirty status).
            If Git is not available or not a repository, git_info will be None.
            If pip is not available, dependencies will be an empty list.
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
        """Mark this solution as inactive.
        
        Inactive solutions are excluded from submission exports and dossier
        generation. This is useful for keeping alternative fits without
        including them in the final submission.
        
        Example:
            >>> solution = event.get_solution("solution_uuid")
            >>> solution.deactivate()
            >>> 
            >>> # The solution is now inactive and won't be included in exports
            >>> submission.save()  # Persist the change
            
        Note:
            This method only changes the is_active flag. The solution data
            remains intact and can be reactivated later using activate().
        """
        self.is_active = False

    def activate(self) -> None:
        """Mark this solution as active.
        
        Active solutions are included in submission exports and dossier
        generation. This is the default state for new solutions.
        
        Example:
            >>> solution = event.get_solution("solution_uuid")
            >>> solution.activate()
            >>> 
            >>> # The solution is now active and will be included in exports
            >>> submission.save()  # Persist the change
            
        Note:
            This method only changes the is_active flag. The solution data
            remains intact.
        """
        self.is_active = True

    def validate(self) -> list[str]:
        """Validate this solution's parameters and configuration.
        
        This method performs comprehensive validation using centralized validation logic
        to ensure the solution is complete, consistent, and ready for submission.
        
        **Validation Checks:**
        
        **Parameter Completeness:**
        - Ensures all required parameters are present for the given model type
        - Validates higher-order effect requirements (e.g., parallax needs piEN, piEE)
        - Checks band-specific flux parameters when bands are specified
        - Verifies t_ref is provided when required by time-dependent effects
        
        **Parameter Types and Values:**
        - Validates parameter data types (float, int, string)
        - Checks physically meaningful parameter ranges
        - Ensures positive values for quantities that must be positive (tE, s, etc.)
        - Validates mass ratio (q) is between 0 and 1
        
        **Physical Consistency:**
        - Checks for physically impossible parameter combinations
        - Validates binary lens separation ranges for caustic crossing
        - Ensures relative_probability is between 0 and 1 when specified
        
        **Model-Specific Validation:**
        - 1S1L: Requires t0, u0, tE
        - 1S2L: Requires t0, u0, tE, s, q, alpha
        - 2S1L: Requires t0, u0, tE (core lens parameters)
        - Higher-order effects: Validates effect-specific parameters
        
        **Higher-Order Effects Supported:**
        - parallax: Requires piEN, piEE, t_ref
        - finite-source: Requires rho
        - lens-orbital-motion: Requires dsdt, dadt, t_ref
        - gaussian-process: Optional ln_K, ln_lambda, ln_period, ln_gamma
        - fitted-limb-darkening: Optional u1, u2, u3, u4
    
        Args:
            None
            
        Returns:
            list[str]: Human-readable validation messages. Empty list indicates all
                      validations passed. Messages may include warnings (non-critical)
                      and errors (critical issues that should be addressed).
                      
        Example:
            >>> solution = event.add_solution("1S2L", {"t0": 2459123.5, "u0": 0.1})
            >>> messages = solution.validate()
            >>> if messages:
            ...     print("Validation issues found:")
            ...     for msg in messages:
            ...         print(f"  - {msg}")
            ... else:
            ...     print("Solution is valid!")
            
        Note:
            Always validate solutions before submission. The validation logic
            is centralized and covers all model types and higher-order effects.
            Some warnings may be non-critical but should be reviewed.
        """
        from .validate_parameters import (
            check_solution_completeness,
            validate_parameter_types,
            validate_solution_consistency,
            validate_parameter_uncertainties
        )
        
        messages = []
        
        # Check solution completeness
        completeness_messages = check_solution_completeness(
            model_type=self.model_type,
            parameters=self.parameters,
            higher_order_effects=self.higher_order_effects,
            bands=self.bands,
            t_ref=self.t_ref
        )
        messages.extend(completeness_messages)
        
        # Check parameter types
        type_messages = validate_parameter_types(
            parameters=self.parameters,
            model_type=self.model_type
        )
        messages.extend(type_messages)
        
        # Check parameter uncertainties
        uncertainty_messages = validate_parameter_uncertainties(
            parameters=self.parameters,
            uncertainties=self.parameter_uncertainties
        )
        messages.extend(uncertainty_messages)
        
        # Check solution consistency
        consistency_messages = validate_solution_consistency(
            model_type=self.model_type,
            parameters=self.parameters,
            relative_probability=self.relative_probability,
        )
        messages.extend(consistency_messages)
        
        return messages

    def _save(self, event_path: Path) -> None:
        """Write this solution to disk.

        Args:
            event_path: Directory of the parent event within the project.

        Example:
            >>> # This is called automatically by Event._save()
            >>> event._save()  # This calls solution._save() for each solution
            
        Note:
            This is an internal method. Solutions are automatically saved
            when the parent event is saved via submission.save().
        """
        solutions_dir = event_path / "solutions"
        solutions_dir.mkdir(parents=True, exist_ok=True)
        out_path = solutions_dir / f"{self.solution_id}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            fh.write(self.model_dump_json(indent=2))

    def get_notes(self, project_root: Optional[Path] = None) -> str:
        """Read notes from the notes file, if present.
        
        Args:
            project_root: Optional project root path for resolving relative
                notes_path. If None, uses the current working directory.
        
        Returns:
            str: The contents of the notes file as a string, or empty string
                if no notes file exists or notes_path is not set.
        
        Example:
            >>> solution = event.get_solution("solution_uuid")
            >>> notes = solution.get_notes(project_root=Path("./my_project"))
            >>> print(notes)
            # My Solution Notes
            
            This is a detailed description of my fit...
            
        Note:
            This method handles both absolute and relative notes_path values.
            If notes_path is relative, it's resolved against project_root.
        """
        if not self.notes_path:
            return ""
        path = Path(self.notes_path)
        if not path.is_absolute() and project_root is not None:
            path = project_root / path
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def set_notes(self, content: str, project_root: Optional[Path] = None) -> None:
        """Write notes to the notes file, creating it if needed.
        
        If notes_path is not set, creates a temporary file in tmp/<solution_id>.md
        and sets notes_path. On Submission.save(), temporary notes files are
        moved to the canonical location.
        
        Args:
            content: The markdown content to write to the notes file.
            project_root: Optional project root path for resolving relative
                notes_path. If None, uses the current working directory.
        
        Example:
            >>> solution = event.get_solution("solution_uuid")
            >>> 
            >>> # Set notes with markdown content
            >>> solution.set_notes('''
            ... # My Solution Notes
            ... 
            ... This is a detailed description of my microlensing fit.
            ... 
            ... ## Parameters
            ... - t0: Time of closest approach
            ... - u0: Impact parameter
            ... - tE: Einstein crossing time
            ... 
            ... ## Notes
            ... The fit shows clear evidence of a binary lens...
            ... ''', project_root=Path("./my_project"))
            >>> 
            >>> # The notes are now saved and can be read back
            >>> notes = solution.get_notes(project_root=Path("./my_project"))
            
        Note:
            This method supports markdown formatting. The notes will be
            rendered as HTML in the dossier with syntax highlighting
            for code blocks.
        """
        if not self.notes_path:
            # Use tmp/ for unsaved notes
            tmp_dir = Path(project_root or ".") / "tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = tmp_dir / f"{self.solution_id}.md"
            self.notes_path = str(tmp_path.relative_to(project_root or "."))
        path = Path(self.notes_path)
        if not path.is_absolute() and project_root is not None:
            path = project_root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @property
    def notes(self) -> str:
        """Return the Markdown notes string from the notes file (read-only).
        
        Returns:
            str: The contents of the notes file as a string, or empty string
                if no notes file exists.
        
        Example:
            >>> solution = event.get_solution("solution_uuid")
            >>> print(solution.notes)
            # My Solution Notes
            
            This is a detailed description of my fit...
            
        Note:
            This is a read-only property. Use set_notes() to modify the notes.
            The property uses the current working directory to resolve relative
            notes_path. For more control, use get_notes() with project_root.
        """
        return self.get_notes()

    def view_notes(self, render_html: bool = True, project_root: Optional[Path] = None) -> str:
        """Return the notes as Markdown or rendered HTML.
        
        Args:
            render_html: If True, return HTML using markdown.markdown with
                extensions for tables and fenced code blocks. If False,
                return the raw Markdown string.
            project_root: Optionally specify the project root for relative
                notes_path resolution.
        
        Returns:
            str: Markdown or HTML string depending on render_html parameter.
        
        Example:
            >>> solution = event.get_solution("solution_uuid")
            >>> 
            >>> # Get raw markdown
            >>> md = solution.view_notes(render_html=False)
            >>> print(md)
            # My Solution Notes
            
            >>> # Get rendered HTML (useful for Jupyter/IPython)
            >>> html = solution.view_notes(render_html=True)
            >>> print(html)
            <h1>My Solution Notes</h1>
            <p>...</p>
            
        Note:
            When render_html=True, the markdown is rendered with extensions
            for tables, fenced code blocks, and other advanced features.
            This is particularly useful for displaying notes in Jupyter
            notebooks or other HTML contexts.
        """
        md = self.get_notes(project_root=project_root)
        if render_html:
            import markdown
            return markdown.markdown(md or "", extensions=["extra", "tables", "fenced_code"])
        return md


class Event(BaseModel):
    """A collection of solutions for a single microlensing event.

    Events act as containers that group one or more :class:`Solution` objects
    under a common ``event_id``. They are created on demand via
    :meth:`Submission.get_event` and are written to disk when the parent
    submission is saved.

    Attributes:
        event_id: Identifier used to reference the event within the project.
        solutions: Mapping of solution IDs to :class:`Solution` instances.
        submission: The parent :class:`Submission` or ``None`` if detached.
        
    Example:
        >>> from microlens_submit import load
        >>> 
        >>> # Load a submission and get/create an event
        >>> submission = load("./my_project")
        >>> event = submission.get_event("EVENT001")
        >>> 
        >>> # Add multiple solutions to the event
        >>> solution1 = event.add_solution("1S1L", {
        ...     "t0": 2459123.5, "u0": 0.1, "tE": 20.0
        ... })
        >>> solution2 = event.add_solution("1S2L", {
        ...     "t0": 2459123.5, "u0": 0.1, "tE": 20.0,
        ...     "s": 1.2, "q": 0.5, "alpha": 45.0
        ... })
        >>> 
        >>> # Get active solutions
        >>> active_solutions = event.get_active_solutions()
        >>> print(f"Event {event.event_id} has {len(active_solutions)} active solutions")
        >>> 
        >>> # Deactivate a solution
        >>> solution1.deactivate()
        >>> 
        >>> # Save the submission (includes all events and solutions)
        >>> submission.save()
        
    Note:
        Events are automatically created when you call submission.get_event()
        with a new event_id. All solutions for an event are stored together
        in the project directory structure.
    """

    event_id: str
    solutions: Dict[str, Solution] = Field(default_factory=dict)
    submission: Optional["Submission"] = Field(default=None, exclude=True)

    def add_solution(self, model_type: str, parameters: dict) -> Solution:
        """Create and attach a new solution to this event.

        Parameters are stored as provided and the new solution is returned for
        further modification. A unique solution_id is automatically generated.

        Args:
            model_type: Short label describing the model type (e.g., "1S1L", "1S2L").
            parameters: Dictionary of model parameters for the fit.

        Returns:
            Solution: The newly created solution instance.

        Example:
            >>> event = submission.get_event("EVENT001")
            >>> 
            >>> # Create a simple point lens solution
            >>> solution = event.add_solution("1S1L", {
            ...     "t0": 2459123.5,  # Time of closest approach
            ...     "u0": 0.1,       # Impact parameter
            ...     "tE": 20.0       # Einstein crossing time
            ... })
            >>> 
            >>> # The solution is automatically added to the event
            >>> print(f"Event now has {len(event.solutions)} solutions")
            >>> print(f"Solution ID: {solution.solution_id}")
            
        Note:
            The solution is automatically marked as active and assigned a
            unique UUID. You can modify the solution attributes after creation
            and then save the submission to persist changes.
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

        Raises:
            KeyError: If the solution_id is not found in this event.

        Example:
            >>> event = submission.get_event("EVENT001")
            >>> 
            >>> # Get a specific solution
            >>> solution = event.get_solution("solution_uuid_here")
            >>> print(f"Model type: {solution.model_type}")
            >>> print(f"Parameters: {solution.parameters}")
            
        Note:
            Use this method to retrieve existing solutions. If you need to
            create a new solution, use add_solution() instead.
        """
        return self.solutions[solution_id]

    def get_active_solutions(self) -> list[Solution]:
        """Return all solutions currently marked as active.
        
        Returns:
            list[Solution]: List of all active solutions in this event.
            
        Example:
            >>> event = submission.get_event("EVENT001")
            >>> 
            >>> # Get only active solutions
            >>> active_solutions = event.get_active_solutions()
            >>> print(f"Event has {len(active_solutions)} active solutions")
            >>> 
            >>> # Only active solutions are included in exports
            >>> for solution in active_solutions:
            ...     print(f"- {solution.solution_id}: {solution.model_type}")
            
        Note:
            Only active solutions are included in submission exports and
            dossier generation. Use deactivate() to exclude solutions from
            the final submission.
        """
        return [sol for sol in self.solutions.values() if sol.is_active]

    def clear_solutions(self) -> None:
        """Deactivate every solution associated with this event.
        
        This method marks all solutions in the event as inactive, effectively
        removing them from submission exports and dossier generation.
        
        Example:
            >>> event = submission.get_event("EVENT001")
            >>> 
            >>> # Deactivate all solutions in this event
            >>> event.clear_solutions()
            >>> 
            >>> # Now no solutions are active
            >>> active_solutions = event.get_active_solutions()
            >>> print(f"Active solutions: {len(active_solutions)}")  # 0
            
        Note:
            This only deactivates solutions; they are not deleted. You can
            reactivate individual solutions using solution.activate().
        """
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
    serialization to the project directory. Users typically obtain an instance
    via :func:`load` and then interact with events and solutions before calling
    :meth:`save` or :meth:`export`.

    Attributes:
        project_path: Root directory where submission files are stored.
        team_name: Name of the participating team.
        tier: Challenge tier for the submission (e.g., "basic", "advanced").
        hardware_info: Optional dictionary describing the compute platform.
        events: Mapping of event IDs to :class:`Event` instances.
        repo_url: GitHub repository URL for the team codebase.
        
    Example:
        >>> from microlens_submit import load
        >>> 
        >>> # Load or create a submission project
        >>> submission = load("./my_project")
        >>> 
        >>> # Set submission metadata
        >>> submission.team_name = "Team Alpha"
        >>> submission.tier = "advanced"
        >>> submission.repo_url = "https://github.com/team/microlens-submit"
        >>> 
        >>> # Add events and solutions
        >>> event1 = submission.get_event("EVENT001")
        >>> solution1 = event1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
        >>> 
        >>> event2 = submission.get_event("EVENT002")
        >>> solution2 = event2.add_solution("1S2L", {"t0": 2459156.2, "u0": 0.08, "tE": 35.7, "s": 0.95, "q": 0.0005, "alpha": 78.3})
        >>> 
        >>> # Validate the submission
        >>> warnings = submission.validate()
        >>> if warnings:
        ...     print("Validation warnings:")
        ...     for warning in warnings:
        ...         print(f"  - {warning}")
        ... else:
        ...     print("✅ Submission is valid!")
        >>> 
        >>> # Save the submission
        >>> submission.save()
        >>> 
        >>> # Export for submission
        >>> submission.export("submission.zip")
        
    Note:
        The submission project structure is automatically created when you
        first call load() with a new directory. All data is stored in JSON
        format with a clear directory structure for events and solutions.
    """

    project_path: str = Field(default="", exclude=True)
    team_name: str = ""
    tier: str = ""
    hardware_info: Optional[dict] = None
    events: Dict[str, Event] = Field(default_factory=dict)
    repo_url: Optional[str] = None

    def validate(self) -> list[str]:
        """Check the submission for missing or incomplete information.

        The method performs lightweight validation and returns a list of
        warnings describing potential issues. It does not raise exceptions and
        can be used to provide user feedback prior to exporting.

        Returns:
            list[str]: Human-readable warning messages. Empty list indicates
                      no issues found.

        Example:
            >>> submission = load("./my_project")
            >>> 
            >>> # Validate the submission
            >>> warnings = submission.validate()
            >>> if warnings:
            ...     print("Validation warnings:")
            ...     for warning in warnings:
            ...         print(f"  - {warning}")
            ... else:
            ...     print("✅ Submission is valid!")
            
        Note:
            This method checks for common issues like missing repo_url,
            inactive events, incomplete solution data, and validation
            problems in individual solutions. Always validate before
            exporting your submission.
        """

        warnings: list[str] = []
        if not self.hardware_info:
            warnings.append("Hardware info is missing")

        # Check for missing or invalid repo_url
        if not self.repo_url or not isinstance(self.repo_url, str) or not self.repo_url.strip():
            warnings.append("repo_url (GitHub repository URL) is missing from submission.json")
        elif not ("github.com" in self.repo_url):
            warnings.append(f"repo_url does not appear to be a valid GitHub URL: {self.repo_url}")

        for event in self.events.values():
            active = [sol for sol in event.solutions.values() if sol.is_active]
            if not active:
                warnings.append(f"Event {event.event_id} has no active solutions")
            else:
                # Check relative probabilities for active solutions
                if len(active) > 1:
                    # Multiple active solutions - check if probabilities sum to 1.0
                    total_prob = sum(sol.relative_probability or 0.0 for sol in active)
                    
                    if total_prob > 0.0 and abs(total_prob - 1.0) > 1e-6:  # Allow small floating point errors
                        warnings.append(
                            f"Event {event.event_id}: Relative probabilities for active solutions sum to {total_prob:.3f}, "
                            f"should sum to 1.0. Solutions: {[sol.solution_id[:8] + '...' for sol in active]}"
                        )
                elif len(active) == 1:
                    # Single active solution - probability should be 1.0 or None
                    sol = active[0]
                    if sol.relative_probability is not None and abs(sol.relative_probability - 1.0) > 1e-6:
                        warnings.append(
                            f"Event {event.event_id}: Single active solution has relative_probability {sol.relative_probability:.3f}, "
                            f"should be 1.0 or None"
                        )
            
            for sol in active:
                # Use the new centralized validation
                solution_messages = sol.validate()
                for msg in solution_messages:
                    warnings.append(f"Solution {sol.solution_id} in event {event.event_id}: {msg}")
                
                # Additional checks for missing metadata
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
                # Check for missing compute info
                compute_info = sol.compute_info or {}
                if "cpu_hours" not in compute_info:
                    warnings.append(
                        f"Solution {sol.solution_id} in event {event.event_id} is missing cpu_hours"
                    )
                if "wall_time_hours" not in compute_info:
                    warnings.append(
                        f"Solution {sol.solution_id} in event {event.event_id} is missing wall_time_hours"
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

        Example:
            >>> submission = load("./my_project")
            >>> 
            >>> # Get an existing event or create a new one
            >>> event = submission.get_event("EVENT001")
            >>> 
            >>> # The event is automatically added to the submission
            >>> print(f"Submission has {len(submission.events)} events")
            >>> print(f"Event {event.event_id} has {len(event.solutions)} solutions")
            
        Note:
            Events are created on-demand when you first access them. This
            allows you to work with events without explicitly creating them
            first. The event is automatically saved when you call
            submission.save().
        """
        if event_id not in self.events:
            self.events[event_id] = Event(event_id=event_id, submission=self)
        return self.events[event_id]

    def autofill_nexus_info(self) -> None:
        """Populate :attr:`hardware_info` with Roman Nexus platform details.

        This helper reads a few well-known files from the Roman Science
        Platform environment to infer CPU model, available memory and the image
        identifier. Missing information is silently ignored.

        Example:
            >>> submission = load("./my_project")
            >>> 
            >>> # Auto-detect Nexus platform information
            >>> submission.autofill_nexus_info()
            >>> 
            >>> # Check what was detected
            >>> if submission.hardware_info:
            ...     print("Hardware info:", submission.hardware_info)
            ... else:
            ...     print("No hardware info detected")
            
        Note:
            This method is designed for the Roman Science Platform environment.
            It reads from /proc/cpuinfo, /proc/meminfo, and JUPYTER_IMAGE_SPEC
            environment variable. If these are not available (e.g., on a
            different platform), the method will silently skip them.
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
        """Persist the current state of the submission to ``project_path``.
        
        This method writes all submission data to disk, including events,
        solutions, and metadata. It also handles moving temporary notes
        files to their canonical locations.
        
        Example:
            >>> submission = load("./my_project")
            >>> 
            >>> # Make changes to the submission
            >>> submission.team_name = "Team Alpha"
            >>> event = submission.get_event("EVENT001")
            >>> solution = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
            >>> 
            >>> # Save all changes to disk
            >>> submission.save()
            >>> 
            >>> # All data is now persisted in the project directory
            
        Note:
            This method creates the project directory structure if it doesn't
            exist and moves any temporary notes files from tmp/ to their
            canonical locations in events/{event_id}/solutions/{solution_id}.md.
            Always call save() after making changes to persist them.
        """
        project = Path(self.project_path)
        events_dir = project / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        # Move any notes files from tmp/ to canonical location
        for event in self.events.values():
            for sol in event.solutions.values():
                if sol.notes_path:
                    notes_path = Path(sol.notes_path)
                    if notes_path.parts and notes_path.parts[0] == "tmp":
                        # Move to canonical location
                        canonical = Path("events") / event.event_id / "solutions" / f"{sol.solution_id}.md"
                        src = project / notes_path
                        dst = project / canonical
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if src.exists():
                            src.replace(dst)
                        sol.notes_path = str(canonical)
        with (project / "submission.json").open("w", encoding="utf-8") as fh:
            fh.write(self.model_dump_json(exclude={"events", "project_path"}, indent=2))
        for event in self.events.values():
            event.submission = self
            event._save()

    def export(self, output_path: str) -> None:
        """Create a zip archive of all active solutions.

        The archive is created using ``zipfile.ZIP_DEFLATED`` compression to
        minimize file size. Only active solutions are included in the export.

        Args:
            output_path: Destination path for the zip archive.

        Raises:
            ValueError: If referenced files (plots, posterior data) don't exist.
            OSError: If unable to create the zip file.

        Example:
            >>> submission = load("./my_project")
            >>> 
            >>> # Validate before export
            >>> warnings = submission.validate()
            >>> if warnings:
            ...     print("Fix validation issues before export:", warnings)
            ... else:
            ...     # Export the submission
            ...     submission.export("my_submission.zip")
            ...     print("Submission exported to my_submission.zip")
            
        Note:
            The export includes:
            - submission.json with metadata
            - All active solutions with parameters
            - Notes files for each solution
            - Referenced files (plots, posterior data)
            
            Relative probabilities are automatically calculated for solutions
            that don't have them set, using BIC if sufficient data is available.
            Only active solutions are included in the export.
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
                        if sol.notes_path:
                            notes_file = Path(self.project_path) / sol.notes_path
                            if notes_file.exists():
                                notes_filename = notes_file.name
                                notes_arc = f"events/{event.event_id}/solutions/{sol.solution_id}/{notes_filename}"
                                export_sol.notes_path = notes_arc
                                zf.write(notes_file, arcname=notes_arc)
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
    directory for all subsequent operations. If the directory does not
    exist, a new project structure is created automatically.

    Args:
        project_path: Location of the submission project on disk.

    Returns:
        Submission: The loaded or newly created submission instance.

    Raises:
        OSError: If unable to create the project directory or read files.
        ValueError: If existing submission.json is invalid.

    Example:
        >>> from microlens_submit import load
        >>> 
        >>> # Load existing project
        >>> submission = load("./existing_project")
        >>> print(f"Team: {submission.team_name}")
        >>> print(f"Events: {len(submission.events)}")
        >>> 
        >>> # Create new project
        >>> submission = load("./new_project")
        >>> submission.team_name = "Team Beta"
        >>> submission.tier = "basic"
        >>> submission.save()
        >>> 
        >>> # The project structure is automatically created:
        >>> # ./new_project/
        >>> # ├── submission.json
        >>> # └── events/
        >>> #     └── (event directories created as needed)
        
    Note:
        This is the main entry point for working with submission projects.
        The function automatically creates the project directory structure
        if it doesn't exist, making it safe to use with new projects.
        All subsequent operations (adding events, solutions, etc.) work
        with the returned Submission instance.
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
