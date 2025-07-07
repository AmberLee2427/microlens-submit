"""
Event model for microlens-submit.

This module contains the Event class, which represents a collection of solutions
for a single microlensing event.
"""

import uuid
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field

from .solution import Solution


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

    def add_solution(
        self, model_type: str, parameters: dict, alias: Optional[str] = None
    ) -> Solution:
        """Create and attach a new solution to this event.

        Parameters are stored as provided and the new solution is returned for
        further modification. A unique solution_id is automatically generated.

        Args:
            model_type: Short label describing the model type (e.g., "1S1L", "1S2L").
            parameters: Dictionary of model parameters for the fit.
            alias: Optional human-readable alias for the solution (e.g., "best_fit", "parallax_model").
                When provided, this alias is used as the primary identifier in dossier displays,
                with the UUID shown as a secondary identifier. The combination of event_id and
                alias must be unique within the project.

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
            >>> # Create a solution with an alias
            >>> solution_with_alias = event.add_solution("1S2L", {
            ...     "t0": 2459123.5, "u0": 0.1, "tE": 20.0,
            ...     "s": 1.2, "q": 0.5, "alpha": 45.0
            ... }, alias="best_binary_fit")
            >>>
            >>> # The solution is automatically added to the event
            >>> print(f"Event now has {len(event.solutions)} solutions")
            >>> print(f"Solution ID: {solution.solution_id}")

        Note:
            The solution is automatically marked as active and assigned a
            unique UUID. You can modify the solution attributes after creation
            and then save the submission to persist changes. If an alias is
            provided, it will be validated for uniqueness when the submission
            is saved. Remember to call submission.save() to persist the solution
            to disk.
        """
        solution_id = str(uuid.uuid4())
        sol = Solution(
            solution_id=solution_id,
            model_type=model_type,
            parameters=parameters,
            alias=alias,
        )
        self.solutions[solution_id] = sol

        # Provide feedback about the created solution
        alias_info = f" with alias '{alias}'" if alias else ""
        print(f"✅ Created solution {solution_id[:8]}...{alias_info}")
        print(f"   Model: {model_type}, Parameters: {len(parameters)}")
        if alias:
            print(
                f"   ⚠️  Note: Alias '{alias}' will be validated for uniqueness when saved"
            )
        print(f"   💾 Remember to call submission.save() to persist to disk")

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

    def run_validation(self) -> list[str]:
        """Validate all active solutions in this event.

        This method performs validation on all active solutions in the event,
        including parameter validation, physical consistency checks, and
        event-specific validation like relative probability sums.

        Returns:
            list[str]: Human-readable validation messages. Empty list indicates
                      all validations passed. Messages may include warnings
                      (non-critical) and errors (critical issues).

        Example:
            >>> event = submission.get_event("EVENT001")
            >>>
            >>> # Validate the event
            >>> warnings = event.run_validation()
            >>> if warnings:
            ...     print("Event validation issues:")
            ...     for msg in warnings:
            ...         print(f"  - {msg}")
            ... else:
            ...     print("✅ Event is valid!")

        Note:
            This method validates all active solutions regardless of whether
            they have been saved to disk. It does not check alias uniqueness
            across the entire submission (use submission.run_validation() for that).
            Always validate before saving or exporting.
        """
        warnings = []

        # Get all active solutions (saved or unsaved)
        active = [sol for sol in self.solutions.values() if sol.is_active]

        if not active:
            warnings.append(f"Event {self.event_id} has no active solutions")
            return warnings

        # Check relative probabilities for active solutions
        if len(active) > 1:
            # Multiple active solutions - check if probabilities sum to 1.0
            total_prob = sum(sol.relative_probability or 0.0 for sol in active)

            if (
                total_prob > 0.0 and abs(total_prob - 1.0) > 1e-6
            ):  # Allow small floating point errors
                warnings.append(
                    f"Relative probabilities for active solutions sum to {total_prob:.3f}, "
                    f"should sum to 1.0. Solutions: {[sol.solution_id[:8] + '...' for sol in active]}"
                )
        elif len(active) == 1:
            # Single active solution - probability should be 1.0 or None
            sol = active[0]
            if (
                sol.relative_probability is not None
                and abs(sol.relative_probability - 1.0) > 1e-6
            ):
                warnings.append(
                    f"Single active solution has relative_probability {sol.relative_probability:.3f}, "
                    f"should be 1.0 or None"
                )

        # Validate each active solution
        for sol in active:
            # Use the centralized validation
            solution_messages = sol.run_validation()
            for msg in solution_messages:
                warnings.append(f"Solution {sol.solution_id}: {msg}")

            # Additional checks for missing metadata
            if sol.log_likelihood is None:
                warnings.append(f"Solution {sol.solution_id} is missing log_likelihood")
            if sol.lightcurve_plot_path is None:
                warnings.append(
                    f"Solution {sol.solution_id} is missing lightcurve_plot_path"
                )
            if sol.lens_plane_plot_path is None:
                warnings.append(
                    f"Solution {sol.solution_id} is missing lens_plane_plot_path"
                )

            # Check for missing compute info
            compute_info = sol.compute_info or {}
            if "cpu_hours" not in compute_info:
                warnings.append(f"Solution {sol.solution_id} is missing cpu_hours")
            if "wall_time_hours" not in compute_info:
                warnings.append(
                    f"Solution {sol.solution_id} is missing wall_time_hours"
                )

        return warnings

    def remove_solution(self, solution_id: str, force: bool = False) -> bool:
        """Completely remove a solution from this event.

        ⚠️  WARNING: This permanently removes the solution from memory and any
        associated files. This action cannot be undone. Use deactivate() instead
        if you want to keep the solution but exclude it from exports.

        Args:
            solution_id: Identifier of the solution to remove.
            force: If True, skip confirmation prompts and remove immediately.
                  If False, will warn about data loss.

        Returns:
            bool: True if solution was removed, False if not found or cancelled.

        Raises:
            ValueError: If solution is saved and force=False (to prevent accidental
                      removal of persisted data).

        Example:
            >>> event = submission.get_event("EVENT001")
            >>>
            >>> # Remove an unsaved solution (safe)
            >>> solution = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1})
            >>> removed = event.remove_solution(solution.solution_id)
            >>> print(f"Removed: {removed}")
            >>>
            >>> # Remove a saved solution (requires force=True)
            >>> saved_solution = event.get_solution("existing_uuid")
            >>> if saved_solution.saved:
            ...     removed = event.remove_solution(saved_solution.solution_id, force=True)
            ...     print(f"Force removed saved solution: {removed}")

        Note:
            This method:
            1. Removes the solution from the event's solutions dict
            2. Cleans up any temporary notes files in tmp/
            3. For saved solutions, requires force=True to prevent accidents
            4. Cannot be undone - use deactivate() if you want to keep the data
        """
        if solution_id not in self.solutions:
            return False

        solution = self.solutions[solution_id]

        # Safety check for saved solutions
        if solution.saved and not force:
            raise ValueError(
                f"Cannot remove saved solution {solution_id[:8]}... without force=True. "
                f"Use solution.deactivate() to exclude from exports instead, or "
                f"call remove_solution(solution_id, force=True) to force removal."
            )

        # Clean up temporary files
        if solution.notes_path and not solution.saved:
            notes_path = Path(solution.notes_path)
            if notes_path.parts and notes_path.parts[0] == "tmp":
                # Remove temporary notes file
                full_path = (
                    Path(self.submission.project_path) / notes_path
                    if self.submission
                    else notes_path
                )
                try:
                    if full_path.exists():
                        full_path.unlink()
                        print(f"🗑️  Removed temporary notes file: {notes_path}")
                except OSError as e:
                    print(
                        f"⚠️  Warning: Could not remove temporary file {notes_path}: {e}"
                    )

        # Remove from solutions dict
        del self.solutions[solution_id]

        print(f"🗑️  Removed solution {solution_id[:8]}... from event {self.event_id}")
        return True

    def remove_all_solutions(self, force: bool = False) -> int:
        """Remove all solutions from this event.

        ⚠️  WARNING: This permanently removes ALL solutions from this event.
        This action cannot be undone. Use clear_solutions() instead if you want
        to keep the solutions but exclude them from exports.

        Args:
            force: If True, skip confirmation prompts and remove immediately.
                  If False, will warn about data loss.

        Returns:
            int: Number of solutions removed.

        Example:
            >>> event = submission.get_event("EVENT001")
            >>>
            >>> # Remove all solutions (use with caution!)
            >>> removed_count = event.remove_all_solutions(force=True)
            >>> print(f"Removed {removed_count} solutions from event {event.event_id}")

        Note:
            This is equivalent to calling remove_solution() for each solution
            in the event. Use clear_solutions() if you want to keep the data.
        """
        solution_ids = list(self.solutions.keys())
        removed_count = 0

        for solution_id in solution_ids:
            try:
                if self.remove_solution(solution_id, force=force):
                    removed_count += 1
            except ValueError as e:
                if not force:
                    print(
                        f"⚠️  Skipped saved solution {solution_id[:8]}... (use force=True to remove)"
                    )
                else:
                    # Force=True should override the saved check
                    if self.remove_solution(solution_id, force=True):
                        removed_count += 1

        return removed_count

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
                # Mark loaded solutions as saved since they came from disk
                sol.saved = True
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