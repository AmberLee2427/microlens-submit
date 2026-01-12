"""Utility functions for microlens-submit.

This module contains utility functions for importing data and loading
submissions.
"""

import csv
import json
import shutil
from pathlib import Path
from typing import Optional

# Resolve forward references
from .models.event import Event
from .models.submission import Submission


def load(project_path: str) -> Submission:
    """Load or create a submission project from a directory.

    This is the main entry point for working with submission projects. If the
    directory doesn't exist, it will be created with a basic project structure.
    If it exists, the submission data will be loaded from disk.

    Args:
        project_path: Path to the project directory.

    Returns:
        A :class:`Submission` instance representing the project.

    Example:
        >>> from microlens_submit import load
        >>>
        >>> # Load or create a submission project
        >>> submission = load("./my_project")
        >>>
        >>> # Set submission metadata
        >>> submission.team_name = "Team Alpha"
        >>> submission.tier = "experienced"
        >>> submission.repo_url = "https://github.com/team/repo"
        >>>
        >>> # Add an event and solution
        >>> event = submission.get_event("EVENT001")
        >>> params = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}
        >>> solution = event.add_solution("1S1L", params)
        >>> solution.log_likelihood = -1234.56
        >>> solution.set_compute_info(cpu_hours=2.5, wall_time_hours=0.5)
        >>>
        >>> # Save the submission
        >>> submission.save()
        >>>
        >>> # Export for submission
        >>> submission.export("submission.zip")

    Note:
        The project directory structure is automatically created when you
        first call load() with a new directory. All data is stored in JSON
        format with a clear directory structure for events and solutions.
    """
    project = Path(project_path)
    events_dir = project / "events"

    if not project.exists():
        events_dir.mkdir(parents=True, exist_ok=True)
        submission = Submission(project_path=str(project))
        with (project / "submission.json").open("w", encoding="utf-8") as fh:
            fh.write(
                submission.model_dump_json(
                    exclude={"events", "project_path"},
                    indent=2,
                )
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


def import_solutions_from_csv(
    submission,
    csv_file: Path,
    parameter_map_file: Optional[Path] = None,
    delimiter: Optional[str] = None,
    dry_run: bool = False,
    validate: bool = False,
    on_duplicate: str = "error",
    project_path: Optional[Path] = None,
) -> dict:
    """Import solutions from a CSV file into a :class:`Submission`.

    The CSV must contain an ``event_id`` column along with either ``solution_id``
    or ``solution_alias`` and a ``model_tags`` column. Parameter values can be
    provided as individual columns or via a JSON-encoded ``parameters`` column.
    Additional columns such as ``notes`` are also supported. The optional
    ``parameter_map_file`` can map arbitrary CSV column names to the expected
    attribute names.

    Args:
        submission: The active :class:`Submission` object.
        csv_file: Path to the CSV file to read.
        parameter_map_file: Optional YAML file that remaps CSV column names.
        delimiter: CSV delimiter. If ``None`` the delimiter is automatically
            detected.
        dry_run: If ``True``, parse and validate the file but do not persist
            any changes.
        validate: If ``True``, run solution validation as each row is imported.
        on_duplicate: Policy for handling duplicate alias keys: ``error``,
            ``override``, or ``ignore``.
        project_path: Project root used for resolving relative file paths.

    Returns:
        dict: Summary statistics describing the import operation.

    Example:
        >>> from microlens_submit.utils import load, import_solutions_from_csv
        >>> sub = load("./project")
        >>> stats = import_solutions_from_csv(
        ...     sub,
        ...     Path("solutions.csv"),
        ...     validate=True,
        ... )
        >>> print(stats["successful_imports"], "solutions imported")

    Note:
        This function performs no console output. Use the CLI wrapper
        :func:`microlens_submit.cli.import_solutions` for user-facing messages.
    """
    if on_duplicate not in ["error", "override", "ignore"]:
        raise ValueError(f"Invalid on_duplicate: {on_duplicate}")

    if project_path is None:
        project_path = Path(".")

    # Load parameter mapping if provided
    if parameter_map_file:
        with open(parameter_map_file, "r", encoding="utf-8") as f:
            # TODO: Implement parameter mapping functionality
            pass

    # Auto-detect delimiter if not specified
    if not delimiter:
        with open(csv_file, "r", encoding="utf-8") as f:
            sample = f.read(1024)
            if "\t" in sample:
                delimiter = "\t"
            elif ";" in sample:
                delimiter = ";"
            else:
                delimiter = ","

    stats = {
        "total_rows": 0,
        "successful_imports": 0,
        "skipped_rows": 0,
        "validation_errors": 0,
        "duplicate_handled": 0,
        "errors": [],
    }

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        lines = f.readlines()
        header_row = 0

        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                header_row = i
                break

        header_line = lines[header_row].strip()
        if header_line.startswith("# "):
            header_line = header_line[2:]
        elif header_line.startswith("#"):
            header_line = header_line[1:]

        reader = csv.DictReader(
            [header_line] + lines[header_row + 1 :],
            delimiter=delimiter,
        )

        for row_num, row in enumerate(reader, start=header_row + 2):
            stats["total_rows"] += 1

            try:
                # Validate required fields
                if not row.get("event_id"):
                    stats["skipped_rows"] += 1
                    stats["errors"].append(f"Row {row_num}: " f"Missing event_id")
                    continue

                solution_id = row.get("solution_id")
                solution_alias = row.get("solution_alias")

                if not solution_id and not solution_alias:
                    stats["skipped_rows"] += 1
                    stats["errors"].append(f"Row {row_num}: " "Missing solution_id or solution_alias")
                    continue

                if not row.get("model_tags"):
                    stats["skipped_rows"] += 1
                    stats["errors"].append(f"Row {row_num}: " f"Missing model_tags")
                    continue

                # Parse model tags
                try:
                    model_tags = json.loads(row["model_tags"])
                    if not isinstance(model_tags, list):
                        raise ValueError("model_tags must be a list")
                except json.JSONDecodeError:
                    stats["skipped_rows"] += 1
                    stats["errors"].append(f"Row {row_num}: " f"Invalid model_tags JSON")
                    continue

                # Extract model type and higher order effects
                model_type = None
                higher_order_effects = []
                allowed_tags = ["1S1L", "1S2L", "2S1L", "2S2L", "1S3L", "2S3L", "other"]

                for tag in model_tags:
                    if tag in allowed_tags:
                        if model_type:
                            stats["skipped_rows"] += 1
                            stats["errors"].append(f"Row {row_num}:" "Multiple model types specified")
                            continue
                        model_type = tag
                    elif tag in [
                        "parallax",
                        "finite-source",
                        "lens-orbital-motion",
                        "xallarap",
                        "gaussian-process",
                        "stellar-rotation",
                        "fitted-limb-darkening",
                        "other",
                    ]:
                        higher_order_effects.append(tag)

                if not model_type:
                    stats["skipped_rows"] += 1
                    stats["errors"].append(f"Row {row_num}: " f"No valid model type found in model_tags")
                    continue

                # Parse parameters
                parameters = {}
                for key, value in row.items():
                    if key is None:
                        continue
                    if key not in [
                        "event_id",
                        "solution_id",
                        "solution_alias",
                        "model_tags",
                        "notes",
                        "parameters",
                    ]:
                        if isinstance(value, str) and value.strip():
                            try:
                                parameters[key] = float(value)
                            except ValueError:
                                parameters[key] = value
                        elif value and str(value).strip():
                            try:
                                parameters[key] = float(value)
                            except (ValueError, TypeError):
                                parameters[key] = str(value)

                if not parameters and row.get("parameters"):
                    try:
                        parameters = json.loads(row["parameters"])
                    except json.JSONDecodeError:
                        stats["skipped_rows"] += 1
                        stats["errors"].append(f"Row {row_num}: " f"Invalid parameters JSON")
                        continue

                # Handle notes
                notes = row.get("notes", "").strip()
                notes_path = None
                notes_content = None

                if notes:
                    notes_file = Path(notes)
                    if notes_file.exists() and notes_file.is_file():
                        notes_path = str(notes_file)
                    else:
                        # CSV files encode newlines as literal \n, so we convert
                        # them to real newlines here.
                        # We do NOT do this when reading .md files or in
                        # set_notes(), because users may want literal '\n'.
                        notes_content = notes.replace("\\n", "\n").replace("\\r", "\r")
                else:
                    pass

                # Get or create event
                event = submission.get_event(row["event_id"])

                # Check for duplicates
                alias_key = f"{row['event_id']} {solution_alias or solution_id}"
                existing_solution = None

                if solution_alias:
                    existing_solution = submission.get_solution_by_alias(
                        row["event_id"],
                        solution_alias,
                    )
                elif solution_id:
                    existing_solution = event.get_solution(solution_id)

                if existing_solution:
                    if on_duplicate == "error":
                        stats["skipped_rows"] += 1
                        stats["errors"].append(f"Row {row_num}: " f"Duplicate alias key '{alias_key}'")
                        continue
                    elif on_duplicate == "ignore":
                        stats["duplicate_handled"] += 1
                        continue
                    elif on_duplicate == "override":
                        event.remove_solution(
                            existing_solution.solution_id,
                            force=True,
                        )
                        stats["duplicate_handled"] += 1

                if not dry_run:
                    solution = event.add_solution(model_type, parameters)

                    if solution_alias:
                        solution.alias = solution_alias
                    elif solution_id:
                        solution.alias = solution_id

                    if higher_order_effects:
                        solution.higher_order_effects = higher_order_effects

                    if notes_path:
                        tmp_path = Path(project_path) / "tmp"
                        solution_notes_path = tmp_path / f"{solution.solution_id}.md"
                        solution_notes_path.parent.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                        shutil.copy2(notes_path, solution_notes_path)
                        solution.notes_path = str(solution_notes_path.relative_to(project_path))
                    elif notes_content:
                        solution.set_notes(
                            notes_content,
                            project_path,
                            convert_escapes=True,
                        )

                    if validate:
                        validation_messages = solution.run_validation()
                        if validation_messages:
                            stats["validation_errors"] += 1
                            for msg in validation_messages:
                                stats["errors"].append(f"Row {row_num} validation: " f"{msg}")

                stats["successful_imports"] += 1

            except Exception as e:
                stats["errors"].append(f"Row {row_num}: {str(e)}")
                continue

    return stats
