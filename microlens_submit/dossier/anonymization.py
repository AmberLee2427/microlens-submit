"""Helpers for applying evaluator-only team-name anonymization."""

import json
from pathlib import Path
from typing import Dict, Optional

from ..models.submission import Submission


TEAM_NAME_LOOKUP_FILENAME = "team_name_lookup.json"


def load_team_name_lookup(tier_dir: Path) -> Dict[str, str]:
    """Load the real-to-anonymous team-name mapping for a tier.

    A missing lookup file preserves the existing behavior for projects that do
    not use evaluator anonymization. If a lookup file is present, malformed
    entries are rejected rather than silently producing an incomplete mapping.
    """
    lookup_path = Path(tier_dir) / TEAM_NAME_LOOKUP_FILENAME
    if not lookup_path.exists():
        return {}

    with lookup_path.open("r", encoding="utf-8") as handle:
        raw_lookup = json.load(handle)

    if not isinstance(raw_lookup, dict):
        raise ValueError(f"Team-name lookup must be a JSON object: {lookup_path}")

    lookup: Dict[str, str] = {}
    for real_name, anonymous_name in raw_lookup.items():
        if not isinstance(real_name, str) or not real_name.strip():
            raise ValueError(f"Lookup keys must be non-empty strings: {lookup_path}")
        if not isinstance(anonymous_name, str) or not anonymous_name.strip():
            raise ValueError(f"Lookup values must be non-empty strings: {lookup_path}")
        lookup[real_name] = anonymous_name

    if len(set(lookup.values())) != len(lookup):
        raise ValueError(f"Anonymous team names must be unique: {lookup_path}")

    return lookup


def _submission_team_name(project_dir: Path) -> str:
    """Read a submission's real team name without loading its event data."""
    submission_path = Path(project_dir) / "submission.json"
    try:
        with submission_path.open("r", encoding="utf-8") as handle:
            raw_submission = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return Path(project_dir).name

    team_name = raw_submission.get("team_name") if isinstance(raw_submission, dict) else None
    return team_name if isinstance(team_name, str) and team_name else Path(project_dir).name


def anonymized_team_name(
    project_dir: Path,
    lookup: Optional[Dict[str, str]] = None,
) -> str:
    """Return the evaluator-facing name for a submission project.

    The metadata name is checked first, followed by the directory name. The
    latter supports cohorts whose directory name differs from ``team_name``.
    When no lookup file is configured, the directory name is retained for
    compatibility with existing cohort metrics.
    """
    project_dir = Path(project_dir)
    lookup = load_team_name_lookup(project_dir.parent) if lookup is None else lookup
    if not lookup:
        return project_dir.name

    real_name = _submission_team_name(project_dir)
    for candidate in (real_name, project_dir.name):
        if candidate in lookup:
            return lookup[candidate]

    raise KeyError(
        f"No anonymous team name is configured for {real_name!r} "
        f"({project_dir.name}) in {project_dir.parent / TEAM_NAME_LOOKUP_FILENAME}"
    )


def evaluator_submission(submission: Submission) -> Submission:
    """Return a display-only submission copy with its evaluator name applied."""
    project_dir = Path(submission.project_path)
    lookup = load_team_name_lookup(project_dir.parent)
    if not lookup:
        return submission

    display_name = anonymized_team_name(project_dir, lookup)
    if display_name == submission.team_name:
        return submission
    return submission.model_copy(update={"team_name": display_name})
