"""
Solution model for microlens-submit.

This module contains the Solution class, which represents an individual
microlensing model fit with parameters and metadata.
"""

import logging
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

import psutil
from pydantic import BaseModel, Field, model_validator


class Solution(BaseModel):
    """Container for an individual microlensing model fit.

    This data model stores everything required to describe a single
    microlensing solution, including the numeric parameters of the fit and
    metadata about how it was produced. Instances are normally created via
    :meth:`Event.add_solution` and persisted to disk when
    :meth:`Submission.save` is called.

    Attributes:
        solution_id: Unique identifier for the solution (auto-generated UUID).
        model_type: Specific lens/source configuration such as "1S1L" or "1S2L".
        bands: List of photometric bands used in the fit (e.g., ["0", "1", "2"]).
        higher_order_effects: List of physical effects modeled (e.g., ["parallax"]).
        t_ref: Reference time for time-dependent effects (Julian Date).
        parameters: Dictionary of model parameters used for the fit.
        is_active: Flag indicating whether the solution should be included in
            the final submission export.
        alias: Optional human-readable alias for the solution (e.g., "best_fit", "parallax_model").
            When provided, this alias is used as the primary identifier in dossier displays,
            with the UUID shown as a secondary identifier. The combination of event_id and
            alias must be unique within the project. If not unique, an error will be raised
            during validation or save operations.
        compute_info: Metadata about the computing environment, populated by
            :meth:`set_compute_info`.
        hardware_info: Optional solution-specific hardware metadata override.
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
        saved: Flag indicating whether the solution has been persisted to disk.


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
        >>> solution.alias = "best_parallax_fit"  # Set a human-readable alias
        >>>
        >>> # Record compute information
        >>> solution.set_compute_info(cpu_hours=2.5, wall_time_hours=0.5)
        >>>
        >>> # Add notes
        >>> solution.set_notes('''
        ...     # My Solution Notes
        ...
        ...     This is a simple point lens fit.
        ... ''')
        >>>
        >>> # Validate the solution
        >>> messages = solution.run_validation()
        >>> if messages:
        ...     print("Validation issues:", messages)

    Note:
        The notes_path field supports Markdown formatting, allowing you to create rich,
        structured documentation with headers, lists, code blocks, tables, and links.
        This is particularly useful for creating detailed submission dossiers for evaluators.

        The run_validation() method performs comprehensive validation of parameters,
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
    alias: Optional[str] = None
    compute_info: dict = Field(default_factory=dict)
    hardware_info: Optional[dict] = None
    posterior_path: Optional[str] = None
    lightcurve_plot_path: Optional[str] = None
    lens_plane_plot_path: Optional[str] = None
    notes_path: Optional[str] = None
    used_astrometry: bool = False
    used_postage_stamps: bool = False
    limb_darkening_model: Optional[str] = None
    limb_darkening_coeffs: Optional[dict] = None
    parameter_uncertainties: Optional[dict] = None
    uncertainty_method: Optional[str] = None
    confidence_level: Optional[float] = 0.68
    physical_parameters: Optional[dict] = None
    physical_parameter_uncertainties: Optional[dict] = None
    log_likelihood: Optional[float] = None
    relative_probability: Optional[float] = None
    n_data_points: Optional[int] = None
    creation_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    saved: bool = Field(default=False, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def validate_solution_at_creation(cls, values):
        """Perform only basic type/structure checks at creation. Warn if issues, but allow creation."""
        try:
            import warnings

            from ..validate_parameters import validate_solution_rigorously

            model_type = values.get("model_type")
            parameters = values.get("parameters", {})
            higher_order_effects = values.get("higher_order_effects", [])
            bands = values.get("bands", [])
            t_ref = values.get("t_ref")
            limb_darkening_coeffs = values.get("limb_darkening_coeffs")

            # Only check for totally broken objects (e.g., wrong types)
            basic_errors = []
            if not isinstance(parameters, dict):
                basic_errors.append("parameters must be a dict")
            if bands is not None and not isinstance(bands, list):
                basic_errors.append("bands must be a list")
            if higher_order_effects is not None and not isinstance(higher_order_effects, list):
                basic_errors.append("higher_order_effects must be a list")
            if t_ref is not None and not isinstance(t_ref, (int, float)):
                basic_errors.append("t_ref must be numeric if provided")
            if basic_errors:
                raise ValueError("; ".join(basic_errors))

            # Run full validation, but only warn if there are issues
            validation_warnings = validate_solution_rigorously(
                model_type=model_type,
                parameters=parameters,
                higher_order_effects=higher_order_effects,
                bands=bands,
                t_ref=t_ref,
                limb_darkening_coeffs=limb_darkening_coeffs,
            )
            if validation_warnings:
                warnings.warn(f"Solution created with potential issues: {'; '.join(validation_warnings)}", UserWarning)
        except ImportError:
            # If validate_parameters module is not available, skip validation
            pass
        return values

    def set_compute_info(
        self,
        cpu_hours: Optional[float] = None,
        wall_time_hours: Optional[float] = None,
        git_dir: Optional[str] = None,
    ) -> None:
        """Record compute metadata and capture environment details.

        When called, this method populates :attr:`compute_info` with timing
        information as well as a list of installed Python packages and the
        current Git state. It is safe to call multiple times—previous values
        will be overwritten.

        Args:
            cpu_hours: Total CPU time consumed by the model fit in hours.
            wall_time_hours: Real-world time consumed by the fit in hours.
            git_dir: Optional path to the code repository for git metadata capture.

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

        # Set timing information
        if cpu_hours is not None:
            self.compute_info["cpu_hours"] = cpu_hours
        if wall_time_hours is not None:
            self.compute_info["wall_time_hours"] = wall_time_hours

        # Capture Python environment dependencies
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.compute_info["dependencies"] = result.stdout.strip().split("\n") if result.stdout else []
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.warning("Could not capture pip environment: %s", e)
            self.compute_info["dependencies"] = []

        # Capture Git repository information
        try:
            git_cwd = Path(git_dir).expanduser().resolve() if git_dir else None
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=git_cwd,
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=git_cwd,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
                cwd=git_cwd,
            ).stdout.strip()
            self.compute_info["git_info"] = {
                "commit": commit,
                "branch": branch,
                "is_dirty": bool(status),
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.warning("Could not capture git info: %s", e)
            self.compute_info["git_info"] = None

    def autofill_hardware_info(self) -> None:
        """Populate solution-level hardware metadata from the current environment.

        This mirrors Submission.autofill_nexus_info() but stores the metadata
        on the solution itself. It is optional and can be used when solutions
        are produced on different servers or environments.
        """
        if self.hardware_info is None:
            self.hardware_info = {}
        try:
            self.hardware_info.setdefault("platform", platform.platform())
            self.hardware_info.setdefault("os", platform.system())
        except Exception as exc:
            logging.debug("Failed to read platform info: %s", exc)
        try:
            image = os.environ.get("JUPYTER_IMAGE_SPEC")
            if image:
                self.hardware_info["nexus_image"] = image
        except Exception as exc:
            logging.debug("Failed to read JUPYTER_IMAGE_SPEC: %s", exc)
        try:
            server_name = os.environ.get("JUPYTERHUB_SERVER_NAME")
            if server_name:
                self.hardware_info["server_name"] = server_name
        except Exception as exc:
            logging.debug("Failed to read JUPYTERHUB_SERVER_NAME: %s", exc)
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        self.hardware_info["cpu_details"] = line.split(":", 1)[1].strip()
                        break
        except OSError as exc:
            logging.debug("Failed to read /proc/cpuinfo: %s", exc)
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal"):
                        mem_kb = int(line.split(":", 1)[1].strip().split()[0])
                        self.hardware_info["memory_gb"] = round(mem_kb / 1024**2, 2)
                        break
        except OSError as exc:
            logging.debug("Failed to read /proc/meminfo: %s", exc)
        try:
            if "memory_gb" not in self.hardware_info:
                mem_bytes = psutil.virtual_memory().total
                self.hardware_info["memory_gb"] = round(mem_bytes / 1024**3, 2)
        except Exception as exc:
            logging.debug("Failed to read memory via psutil: %s", exc)
        try:
            if "cpu_details" not in self.hardware_info:
                cpu = platform.processor() or platform.machine()
                freq = psutil.cpu_freq()
                if freq and cpu:
                    self.hardware_info["cpu_details"] = f"{cpu} ({freq.max:.0f} MHz max)"
                elif cpu:
                    self.hardware_info["cpu_details"] = cpu
        except Exception as exc:
            logging.debug("Failed to read CPU via psutil: %s", exc)

    def autofill_nexus_info(self) -> None:
        """Alias for autofill_hardware_info() for Nexus users."""
        self.autofill_hardware_info()

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

    def run_validation(self) -> List[str]:
        """Validate this solution's parameters and configuration.

        This method performs comprehensive validation using centralized validation logic
        to ensure the solution is complete, consistent, and ready for submission.

        The validation includes:

        * Parameter completeness for the given model type
        * Higher-order effect requirements (e.g., parallax needs piEN, piEE)
        * Band-specific flux parameters when bands are specified
        * Reference time requirements for time-dependent effects
        * Parameter data types and physically meaningful ranges
        * Physical consistency checks
        * Model-specific parameter requirements

        Args:
            None

        Returns:
            list[str]: Human-readable validation messages. Empty list indicates all
                      validations passed. Messages may include warnings (non-critical)
                      and errors (critical issues that should be addressed).

        Example:
            >>> solution = event.add_solution("1S2L", {"t0": 2459123.5, "u0": 0.1})
            >>> messages = solution.run_validation()
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
        from ..validate_parameters import (
            check_solution_completeness,
            validate_parameter_types,
            validate_parameter_uncertainties,
            validate_solution_consistency,
        )

        messages = []

        # Check solution completeness
        completeness_messages = check_solution_completeness(
            model_type=self.model_type,
            parameters=self.parameters,
            higher_order_effects=self.higher_order_effects,
            bands=self.bands,
            t_ref=self.t_ref,
        )
        messages.extend(completeness_messages)

        # Check parameter types
        type_messages = validate_parameter_types(parameters=self.parameters, model_type=self.model_type)
        messages.extend(type_messages)

        # Check parameter uncertainties
        uncertainty_messages = validate_parameter_uncertainties(
            parameters=self.parameters, uncertainties=self.parameter_uncertainties
        )
        messages.extend(uncertainty_messages)

        # Check solution consistency
        consistency_messages = validate_solution_consistency(
            model_type=self.model_type,
            parameters=self.parameters,
            relative_probability=self.relative_probability,
        )
        messages.extend(consistency_messages)

        # Check solution metadata (uncertainties, etc.)
        from ..validate_parameters import validate_solution_metadata

        metadata_messages = validate_solution_metadata(
            parameter_uncertainties=self.parameter_uncertainties,
            physical_parameters=self.physical_parameters,
            physical_parameter_uncertainties=self.physical_parameter_uncertainties,
            uncertainty_method=self.uncertainty_method,
            confidence_level=self.confidence_level,
        )
        messages.extend(metadata_messages)

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

    def set_notes(
        self,
        content: str,
        project_root: Optional[Path] = None,
        convert_escapes: bool = False,
    ) -> None:
        """Write notes to the notes file, creating it if needed.

        If notes_path is not set, creates a temporary file in tmp/<solution_id>.md
        and sets notes_path. On Submission.save(), temporary notes files are
        moved to the canonical location.

        ⚠️  WARNING: This method writes files immediately. If you're testing and
        don't want to create files, consider using a temporary project directory
        or checking the content before calling this method.

        Args:
            content: The markdown content to write to the notes file.
            project_root: Optional project root path for resolving relative
                notes_path. If None, uses the current working directory.
            convert_escapes: If True, convert literal \\n and \\r to actual newlines
                and carriage returns. Useful for CSV import where notes contain
                literal escape sequences. Defaults to False for backward compatibility.

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

            For testing purposes, you can:
            1. Use a temporary project directory: load("./tmp_test_project")
            2. Check the content before calling: print("Notes content:", content)
            3. Use a dry-run approach by setting notes_path manually
        """
        if convert_escapes:
            content = content.replace("\\n", "\n").replace("\\r", "\r")

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

            return markdown.markdown(md or "", extensions=["extra", "tables", "fenced_code", "nl2br"])
        return md
