"""
Submission model for microlens-submit.

This module contains the Submission class, which represents the top-level
container for a microlensing challenge submission project.
"""

import base64
import json
import logging
import math
import mimetypes
import os
import platform
import re
import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote

import psutil
from pydantic import BaseModel, Field

from ..text_symbols import symbol
from ..validate_parameters import count_model_parameters
from .event import Event
from .solution import Solution


class Submission(BaseModel):
    """Top-level object representing an on-disk submission project.

    A ``Submission`` manages a collection of :class:`Event` objects and handles
    serialization to the project directory. Users typically obtain an instance
    via :func:`load` and then interact with events and solutions before calling
    :meth:`save` or :meth:`export`.

    Attributes:
        project_path: Root directory where submission files are stored.
        team_name: Name of the participating team (required for validation).
        tier: Challenge tier for the submission (e.g., "beginner", "experienced") (required for validation).
        hardware_info: Dictionary describing the compute platform (required for validation).
        events: Mapping of event IDs to :class:`Event` instances.
        repo_url: GitHub repository URL for the team codebase (required for validation).
        git_dir: Optional path to the codebase (used for git metadata capture).

    Example:
        >>> from microlens_submit import load
        >>>
        >>> # Load or create a submission project
        >>> submission = load("./my_project")
        >>>
        >>> # Set submission metadata
        >>> submission.team_name = "Team Alpha"
        >>> submission.tier = "experienced"
        >>> submission.repo_url = "https://github.com/team/microlens-submit"
        >>>
        >>> # Add events and solutions
        >>> event1 = submission.get_event("EVENT001")
        >>> solution1 = event1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
        >>>
        >>> event2 = submission.get_event("EVENT002")
        >>> params2 = {"t0": 2459156.2, "u0": 0.08, "tE": 35.7, "s": 0.95, "q": 0.0005, "alpha": 78.3}
        >>> solution2 = event2.add_solution("1S2L", params2)
        >>>
        >>> # Validate the submission
        >>> warnings = submission.run_validation()
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
    git_dir: Optional[str] = None

    def run_validation_warnings(self) -> List[str]:
        """Validate the submission and return warnings only (non-blocking issues).

        This method performs validation but only returns warnings for missing
        optional fields. It does not fail for missing required fields like
        repo_url or hardware_info.

        Returns:
            List[str]: Human-readable warning messages. Empty list indicates
                      no warnings.
        """
        messages = []

        # Check metadata completeness (warnings only)
        if not self.team_name:
            messages.append("team_name is required")
        if not self.tier:
            messages.append("tier is required")
        if not self.repo_url:
            messages.append("repo_url is required (GitHub repository URL)")
        if not self.hardware_info:
            messages.append("Hardware info is missing")

        # Validate tier and event IDs
        if self.tier:
            try:
                from ..tier_validation import get_available_tiers, get_event_validation_error, validate_event_id

                # Check if tier is valid first
                available_tiers = get_available_tiers()
                if self.tier not in available_tiers:
                    messages.append(
                        f"Invalid tier '{self.tier}' changed to 'None'. Available tiers: {available_tiers}."
                    )
                    # Automatically change to None tier
                    self.tier = "None"

                # Only validate events if tier is not "None"
                if self.tier != "None":
                    for event_id in self.events.keys():
                        if not validate_event_id(event_id, self.tier):
                            error_msg = get_event_validation_error(event_id, self.tier)
                            if error_msg:
                                messages.append(error_msg)
            except ImportError:
                # Tier validation module not available, skip validation
                pass
            except ValueError as e:
                # Invalid tier (fallback for other validation errors)
                messages.append(f"Invalid tier '{self.tier}': {e}")

        # Validate all events
        for event_id, event in self.events.items():
            event_messages = event.run_validation()
            for msg in event_messages:
                messages.append(f"Event {event_id}: {msg}")

        # Check for duplicate aliases across events
        alias_messages = self._validate_alias_uniqueness()
        messages.extend(alias_messages)

        return messages

    def run_validation(self) -> List[str]:
        """Validate the entire submission for missing or incomplete information.

        This method performs comprehensive validation of the submission structure,
        including metadata completeness, event configuration, and solution validation.
        It returns a list of human-readable validation messages.

        Returns:
            List[str]: Human-readable validation messages. Empty list indicates
                      all validations passed.

        Example:
            >>> submission = load("./my_project")
            >>> messages = submission.run_validation()
            >>> if messages:
            ...     print("Validation issues found:")
            ...     for msg in messages:
            ...         print(f"  - {msg}")
            ... else:
            ...     print("Submission is valid!")

        Note:
            This method calls run_validation() on all events and solutions,
            providing a comprehensive validation report for the entire submission.
        """
        messages = []

        # Check metadata completeness (strict validation for save/export)
        if not self.team_name:
            messages.append("team_name is required")
        if not self.tier:
            messages.append("tier is required")
        if not self.repo_url:
            messages.append("repo_url is required (GitHub repository URL)")

        # Check hardware info
        if not self.hardware_info:
            messages.append("Hardware info is missing")

        # Validate tier and event IDs
        if self.tier:
            try:
                from ..tier_validation import get_available_tiers, get_event_validation_error, validate_event_id

                # Check if tier is valid first
                available_tiers = get_available_tiers()
                if self.tier not in available_tiers:
                    messages.append(
                        f"Invalid tier '{self.tier}' changed to 'None'. Available tiers: {available_tiers}."
                    )
                    # Automatically change to None tier
                    self.tier = "None"

                # Only validate events if tier is not "None"
                if self.tier != "None":
                    for event_id in self.events.keys():
                        if not validate_event_id(event_id, self.tier):
                            error_msg = get_event_validation_error(event_id, self.tier)
                            if error_msg:
                                messages.append(error_msg)
            except ImportError:
                # Tier validation module not available, skip validation
                pass
            except ValueError as e:
                # Invalid tier (fallback for other validation errors)
                messages.append(f"Invalid tier '{self.tier}': {e}")

        # Validate all events
        for event_id, event in self.events.items():
            event_messages = event.run_validation()
            for msg in event_messages:
                messages.append(f"Event {event_id}: {msg}")

        # Check for duplicate aliases across events
        alias_messages = self._validate_alias_uniqueness()
        messages.extend(alias_messages)

        return messages

    def get_event(self, event_id: str) -> Event:
        if event_id not in self.events:
            self.events[event_id] = Event(event_id=event_id, submission=self)
        return self.events[event_id]

    def autofill_nexus_info(self) -> None:
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

    def _get_alias_lookup_path(self) -> Path:
        return Path(self.project_path) / "aliases.json"

    def _load_alias_lookup(self) -> Dict[str, str]:
        alias_path = self._get_alias_lookup_path()
        if alias_path.exists():
            try:
                with alias_path.open("r", encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError) as e:
                logging.warning("Failed to load alias lookup table: %s", e)
                return {}
        return {}

    def _save_alias_lookup(self, alias_lookup: Dict[str, str]) -> None:
        alias_path = self._get_alias_lookup_path()
        try:
            with alias_path.open("w", encoding="utf-8") as fh:
                json.dump(alias_lookup, fh, indent=2, sort_keys=True)
        except OSError as e:
            logging.error("Failed to save alias lookup table: %s", e)
            raise

    def _build_alias_lookup(self) -> Dict[str, str]:
        alias_lookup = {}
        for event_id, event in self.events.items():
            for solution in event.solutions.values():
                if solution.alias:
                    alias_key = f"{event_id} {solution.alias}"
                    alias_lookup[alias_key] = solution.solution_id
        return alias_lookup

    def _validate_alias_uniqueness(self) -> List[str]:
        errors = []
        for event_id, event in self.events.items():
            alias_map: Dict[str, List[str]] = {}
            for solution in event.solutions.values():
                if solution.alias:
                    alias_map.setdefault(solution.alias, []).append(solution.solution_id)
            for alias, solution_ids in alias_map.items():
                if len(solution_ids) > 1:
                    errors.append(
                        f"Duplicate alias '{alias}' found in event '{event_id}' for solutions {solution_ids}. "
                        "Aliases must be unique within each event. "
                        "Tip: rename with solution.alias = 'new_alias' (or CLI --alias) and re-save. "
                        "See docs/api.rst (Solution Aliases) for examples."
                    )
        return errors

    def get_solution_by_alias(self, event_id: str, alias: str) -> Optional[Solution]:
        if event_id not in self.events:
            return None
        event = self.events[event_id]
        for solution in event.solutions.values():
            if solution.alias == alias:
                return solution
        return None

    def get_solution_status(self) -> dict:
        status = {
            "saved": 0,
            "unsaved": 0,
            "total": 0,
            "events": {},
            "duplicate_aliases": [],
        }
        alias_errors = self._validate_alias_uniqueness()
        status["duplicate_aliases"] = alias_errors
        for event_id, event in self.events.items():
            event_status = {
                "saved": 0,
                "unsaved": 0,
                "total": len(event.solutions),
                "solutions": {},
            }
            for sol_id, solution in event.solutions.items():
                sol_status = {
                    "saved": solution.saved,
                    "alias": solution.alias,
                    "model_type": solution.model_type,
                    "is_active": solution.is_active,
                }
                event_status["solutions"][sol_id[:8] + "..."] = sol_status
                if solution.saved:
                    event_status["saved"] += 1
                    status["saved"] += 1
                else:
                    event_status["unsaved"] += 1
                    status["unsaved"] += 1
                status["total"] += 1
            status["events"][event_id] = event_status
        return status

    def print_solution_status(self) -> None:
        status = self.get_solution_status()
        print(f"{symbol('progress')} Solution Status Summary:")
        print(f"   Total solutions: {status['total']}")
        print(f"   Saved to disk: {status['saved']}")
        print(f"   Unsaved (in memory): {status['unsaved']}")
        if status["unsaved"] > 0:
            print(f"   {symbol('save')} Call submission.save() to persist unsaved solutions")
        if status["duplicate_aliases"]:
            print(f"   {symbol('error')} Alias conflicts found:")
            for error in status["duplicate_aliases"]:
                print(f"      {error}")
            print(f"   {symbol('hint')} Resolve conflicts before saving")
        for event_id, event_status in status["events"].items():
            print(f"\n{symbol('folder')} Event {event_id}:")
            print(f"   Solutions: {event_status['saved']} saved, {event_status['unsaved']} unsaved")
            for sol_id, sol_status in event_status["solutions"].items():
                status_icon = symbol("check") if sol_status["saved"] else symbol("pending")
                alias_info = f" (alias: {sol_status['alias']})" if sol_status["alias"] else ""
                active_info = "" if sol_status["is_active"] else " [inactive]"
                print(f"   {status_icon} {sol_id} - {sol_status['model_type']}{alias_info}{active_info}")

    def save(self, force: bool = False) -> None:
        # Run comprehensive validation first
        validation_errors = self.run_validation()
        if validation_errors:
            print(f"{symbol('warning')}  Save completed with validation warnings:")
            for error in validation_errors:
                print(f"   {error}")
            print(f"{symbol('hint')} Fix validation errors before exporting for submission")

            if not force:
                print(f"{symbol('save')} Submission saved locally (incomplete - not ready for submission)")
            else:
                print(f"{symbol('save')} Submission saved locally (forced save with validation errors)")
        else:
            print(f"{symbol('check')} Submission saved successfully (ready for export)")

        # Check for alias conflicts (existing behavior)
        alias_errors = self._validate_alias_uniqueness()
        if alias_errors:
            print(f"{symbol('error')} Save failed due to alias validation errors:")
            for error in alias_errors:
                print(f"   {error}")
            print(f"{symbol('hint')} Solutions with duplicate aliases remain in memory but are not saved")
            print("   Use different aliases or remove aliases to resolve conflicts")
            raise ValueError("Alias validation failed:\n" + "\n".join(alias_errors))

        unsaved_count = sum(1 for event in self.events.values() for sol in event.solutions.values() if not sol.saved)
        project = Path(self.project_path)
        events_dir = project / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        for event in self.events.values():
            for sol in event.solutions.values():
                if sol.notes_path:
                    notes_path = Path(sol.notes_path)
                    if notes_path.is_absolute():
                        src = notes_path
                    else:
                        src = project / notes_path
                    is_temp = (not notes_path.is_absolute() and notes_path.parts and notes_path.parts[0] == "tmp") or (
                        "tmp" in notes_path.parts and notes_path.name == f"{sol.solution_id}.md"
                    )
                    if is_temp:
                        canonical = Path("events") / event.event_id / "solutions" / f"{sol.solution_id}.md"
                        dst = project / canonical
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if src.exists():
                            shutil.move(src, dst)
                        sol.notes_path = str(canonical)
        with (project / "submission.json").open("w", encoding="utf-8") as fh:
            fh.write(self.model_dump_json(exclude={"events", "project_path"}, indent=2))
        alias_lookup = self._build_alias_lookup()
        self._save_alias_lookup(alias_lookup)
        for event in self.events.values():
            event.submission = self
            event._save()
            for sol in event.solutions.values():
                sol.saved = True
        if unsaved_count > 0:
            print(f"{symbol('check')} Successfully saved {unsaved_count} new solution(s) to disk")
        else:
            print(f"{symbol('check')} Successfully saved submission to disk")
        saved_aliases = [
            f"{event_id} {sol.alias}"
            for event_id, event in self.events.items()
            for sol in event.solutions.values()
            if sol.alias and sol.saved
        ]
        if saved_aliases:
            print(f"{symbol('clipboard')} Saved aliases: {', '.join(saved_aliases)}")

    def export(self, output_path: str) -> None:
        # Run comprehensive validation first - export is strict
        validation_errors = self.run_validation()
        if validation_errors:
            print(f"{symbol('error')} Export failed due to validation errors:")
            for error in validation_errors:
                print(f"   {error}")
            print(f"{symbol('hint')} Fix validation errors before exporting for submission")
            print(f"{symbol('hint')} Use submission.save() to save incomplete work locally")
            raise ValueError("Validation failed:\n" + "\n".join(validation_errors))

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
                rel_prob_map: Dict[str, float] = {}
                if active_sols:
                    provided_sum = sum(
                        s.relative_probability or 0.0 for s in active_sols if s.relative_probability is not None
                    )
                    need_calc = [s for s in active_sols if s.relative_probability is None]
                    if need_calc:
                        can_calc = True
                        for s in need_calc:
                            if (
                                s.log_likelihood is None
                                or s.n_data_points is None
                                or s.n_data_points <= 0
                                or count_model_parameters(s.parameters) == 0
                            ):
                                can_calc = False
                                break
                        remaining = max(1.0 - provided_sum, 0.0)
                        if can_calc:
                            bic_vals = {
                                s.solution_id: count_model_parameters(s.parameters) * math.log(s.n_data_points)
                                - 2 * s.log_likelihood
                                for s in need_calc
                            }
                            bic_min = min(bic_vals.values())
                            weights = {sid: math.exp(-0.5 * (bic - bic_min)) for sid, bic in bic_vals.items()}
                            wsum = sum(weights.values())
                            for sid, w in weights.items():
                                rel_prob_map[sid] = remaining * w / wsum if wsum > 0 else remaining / len(weights)
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
                        arc = f"events/{event.event_id}/solutions/{sol.solution_id}.json"
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
                            export_sol.relative_probability = rel_prob_map.get(sol.solution_id)
                        zf.writestr(arc, export_sol.model_dump_json(indent=2))
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
                                    f"Error: File specified by {attr} in solution {sol.solution_id} "
                                    f"does not exist: {file_path}"
                                )
                            zf.write(
                                file_path,
                                arcname=f"{sol_dir_arc}/{Path(path).name}",
                            )

    def notebook_display_dashboard(self, output_dir: Optional[str] = None) -> str:
        """Return dashboard HTML with local assets inlined for Jupyter display.

        This is a convenience helper for JupyterLab/JupyterHub, where relative
        file URLs are often blocked. It reads the generated dossier HTML and
        replaces local asset image paths with base64 data URIs.

        Args:
            output_dir: Optional dossier output directory. Defaults to
                <project_path>/dossier.

        Returns:
            str: HTML content suitable for display with IPython.display.HTML.
        """
        from microlens_submit.dossier import generate_dashboard_html

        dossier_dir = Path(output_dir) if output_dir else Path(self.project_path) / "dossier"
        dossier_dir.mkdir(parents=True, exist_ok=True)
        index_path = dossier_dir / "index.html"
        if not index_path.exists():
            generate_dashboard_html(self, dossier_dir)
        html = index_path.read_text(encoding="utf-8")

        return self._inline_dossier_assets(html, dossier_dir)

    def notebook_display_event(self, event_id: str, output_dir: Optional[str] = None) -> str:
        """Return event dossier HTML with local assets inlined for Jupyter display.

        Args:
            event_id: Event identifier to render.
            output_dir: Optional dossier output directory. Defaults to
                <project_path>/dossier.

        Returns:
            str: HTML content suitable for display with IPython.display.HTML.
        """
        from microlens_submit.dossier import generate_event_page
        from microlens_submit.dossier.utils import copy_dossier_assets

        dossier_dir = Path(output_dir) if output_dir else Path(self.project_path) / "dossier"
        dossier_dir.mkdir(parents=True, exist_ok=True)
        copy_dossier_assets(dossier_dir)
        event_path = dossier_dir / f"{event_id}.html"
        if not event_path.exists():
            event = self.get_event(event_id)
            generate_event_page(event, self, dossier_dir)
        html = event_path.read_text(encoding="utf-8")

        return self._inline_dossier_assets(html, dossier_dir)

    def notebook_display_solution(
        self,
        solution_id: str,
        output_dir: Optional[str] = None,
        regenerate: bool = False,
    ) -> str:
        """Return solution dossier HTML with local assets inlined for Jupyter display.

        Args:
            solution_id: Solution identifier to render.
            output_dir: Optional dossier output directory. Defaults to
                <project_path>/dossier.
            regenerate: If True, regenerate the solution HTML even if it exists.

        Returns:
            str: HTML content suitable for display with IPython.display.HTML.
        """
        from microlens_submit.dossier import generate_solution_page
        from microlens_submit.dossier.utils import copy_dossier_assets

        dossier_dir = Path(output_dir) if output_dir else Path(self.project_path) / "dossier"
        dossier_dir.mkdir(parents=True, exist_ok=True)
        copy_dossier_assets(dossier_dir)
        solution_path = dossier_dir / f"{solution_id}.html"
        if regenerate or not solution_path.exists():
            event = None
            for ev in self.events.values():
                if solution_id in ev.solutions:
                    event = ev
                    break
            if event is None:
                raise ValueError(f"Solution {solution_id} not found in submission")
            solution = event.solutions[solution_id]
            generate_solution_page(solution, event, self, dossier_dir)
        html = solution_path.read_text(encoding="utf-8")

        return self._inline_dossier_assets(html, dossier_dir)

    def notebook_display_full_dossier(self, output_dir: Optional[str] = None) -> str:
        """Return full dossier HTML with local assets inlined for Jupyter display.

        Args:
            output_dir: Optional dossier output directory. Defaults to
                <project_path>/dossier.

        Returns:
            str: HTML content suitable for display with IPython.display.HTML.
        """
        from microlens_submit.dossier.full_report import generate_full_dossier_report_html
        from microlens_submit.dossier.utils import copy_dossier_assets

        dossier_dir = Path(output_dir) if output_dir else Path(self.project_path) / "dossier"
        dossier_dir.mkdir(parents=True, exist_ok=True)
        copy_dossier_assets(dossier_dir)
        full_path = dossier_dir / "full_dossier_report.html"
        if not full_path.exists():
            generate_full_dossier_report_html(self, dossier_dir)
        html = full_path.read_text(encoding="utf-8")

        return self._inline_dossier_assets(html, dossier_dir)

    def _inline_dossier_assets(self, html: str, dossier_dir: Path) -> str:
        assets_dir = dossier_dir / "assets"
        if not assets_dir.exists():
            return html
        for img_path in assets_dir.glob("*.png"):
            data = base64.b64encode(img_path.read_bytes()).decode("utf-8")
            html = html.replace(
                f'src="assets/{img_path.name}"',
                f'src="data:image/png;base64,{data}"',
            )
            html = html.replace(
                f'src="./assets/{img_path.name}"',
                f'src="data:image/png;base64,{data}"',
            )
            html = html.replace(
                f"src='assets/{img_path.name}'",
                f"src='data:image/png;base64,{data}'",
            )
            html = html.replace(
                f"src='./assets/{img_path.name}'",
                f"src='data:image/png;base64,{data}'",
            )
        # Inline any local image references (plots, posteriors) for Jupyter display
        for match in re.finditer(r"src=['\"]([^'\"]+)['\"]", html):
            src = match.group(1)
            if src.startswith(("http://", "https://", "data:")):
                continue
            cleaned = unquote(src.split("?")[0].split("#")[0])
            src_path = Path(cleaned)
            if not src_path.is_absolute():
                src_path = (dossier_dir / src_path).resolve()
            if not src_path.exists() or not src_path.is_file():
                continue
            mime_type, _ = mimetypes.guess_type(src_path.name)
            if not mime_type or not mime_type.startswith("image/"):
                continue
            data = base64.b64encode(src_path.read_bytes()).decode("utf-8")
            html = html.replace(src, f"data:{mime_type};base64,{data}")
        return html

    def remove_event(self, event_id: str, force: bool = False) -> bool:
        if event_id not in self.events:
            return False
        event = self.events[event_id]
        has_saved_solutions = any(sol.saved for sol in event.solutions.values())
        if has_saved_solutions and not force:
            saved_count = sum(1 for sol in event.solutions.values() if sol.saved)
            raise ValueError(
                f"Cannot remove event '{event_id}' with {saved_count} saved solutions without force=True. "
                f"Use event.clear_solutions() to exclude all solutions from exports instead, or "
                f"call remove_event(event_id, force=True) to force removal."
            )
        for solution in event.solutions.values():
            if not solution.saved and solution.notes_path:
                notes_path = Path(solution.notes_path)
                if notes_path.parts and notes_path.parts[0] == "tmp":
                    full_path = Path(self.project_path) / notes_path
                    try:
                        if full_path.exists():
                            full_path.unlink()
                            print(f"{symbol('trash')} Removed temporary notes file: {notes_path}")
                    except OSError as e:
                        print(f"{symbol('warning')}  Warning: Could not remove temporary file {notes_path}: {e}")
        del self.events[event_id]
        print(f"{symbol('trash')} Removed event '{event_id}' with {len(event.solutions)} solutions")
        return True

    # ... (all methods from Submission class, unchanged, including docstrings)
