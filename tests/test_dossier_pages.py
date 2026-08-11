"""Tests for dossier page generation utilities."""

from pathlib import Path

import pytest

from microlens_submit.dossier import generate_event_page, generate_solution_page
from microlens_submit.dossier.dashboard import _generate_dashboard_content
from microlens_submit.tier_validation import get_tier_event_list
from microlens_submit.utils import load


def _basic_submission(tmp_path: Path):
    """Create a minimal submission with one event and solution."""
    sub = load(str(tmp_path))
    sub.team_name = "UnitTesters"
    sub.tier = "beginner"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}
    evt = sub.get_event("E001")
    evt.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
    return sub, evt


def test_generate_dashboard_content_contains_event(tmp_path):
    """Dashboard HTML contains team name and event link."""
    sub, evt = _basic_submission(tmp_path)
    html = _generate_dashboard_content(sub)
    assert f"{evt.event_id}.html" in html
    assert "UnitTesters" in html


def test_generate_event_page_creates_file(tmp_path):
    """generate_event_page writes an HTML file for the event."""
    sub, evt = _basic_submission(tmp_path)
    out_dir = tmp_path / "dossier"
    out_dir.mkdir()
    generate_event_page(evt, sub, out_dir)
    page = out_dir / f"{evt.event_id}.html"
    assert page.exists()
    content = page.read_text(encoding="utf-8")
    assert evt.event_id in content


def test_generate_event_page_missing_directory(tmp_path):
    """Missing output directory raises an error."""
    sub, evt = _basic_submission(tmp_path)
    out_dir = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        generate_event_page(evt, sub, out_dir)


def test_generate_solution_page_uses_absolute_uri_for_external_lightcurve(tmp_path):
    """Solution pages can render lightcurves stored outside the project."""
    sub, evt = _basic_submission(tmp_path / "project")
    solution = next(iter(evt.solutions.values()))
    lightcurve = tmp_path / "external lightcurve.png"
    lightcurve.write_bytes(b"image")
    solution.lightcurve_plot_path = str(lightcurve)
    output_dir = Path(sub.project_path) / "dossier"
    output_dir.mkdir()

    generate_solution_page(solution, evt, sub, output_dir)

    page = (output_dir / f"{solution.solution_id}.html").read_text(encoding="utf-8")
    assert lightcurve.as_uri() in page


def test_dashboard_shows_beginner_tier_event_count(tmp_path):
    """Dashboard shows the 188-event beginner tier total."""
    sub = load(str(tmp_path))
    sub.team_name = "TestTeam"
    sub.tier = "beginner"
    evt = sub.get_event("rmdc26_000001")
    evt.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    html = _generate_dashboard_content(sub)

    assert len(get_tier_event_list("beginner")) == 188
    assert "/ 188 Events Processed" in html


def test_dashboard_shows_experienced_tier_event_count(tmp_path):
    """Dashboard shows the 2,288-event experienced tier total."""
    sub = load(str(tmp_path))
    sub.team_name = "TestTeam"
    sub.tier = "experienced"

    html = _generate_dashboard_content(sub)

    assert len(get_tier_event_list("experienced")) == 2288
    assert "/ 2288 Events Processed" in html


def test_dashboard_handles_invalid_tier(tmp_path):
    """Dashboard gracefully handles invalid tier with N/A display."""
    sub = load(str(tmp_path))
    sub.team_name = "TestTeam"
    sub.tier = "invalid-tier-name"
    evt = sub.get_event("EVENT001")
    evt.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    html = _generate_dashboard_content(sub)

    # Should show N/A for invalid tier
    assert "/ N/A Events Processed" in html
    assert "(N/A)" in html


def test_dashboard_handles_none_tier(tmp_path):
    """Dashboard gracefully handles None tier with N/A display."""
    sub = load(str(tmp_path))
    sub.team_name = "TestTeam"
    sub.tier = None
    evt = sub.get_event("EVENT001")
    evt.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    html = _generate_dashboard_content(sub)

    # Should show N/A for None tier
    assert "/ N/A Events Processed" in html
    assert "(N/A)" in html


def test_dashboard_handles_none_tier_string(tmp_path):
    """Dashboard gracefully handles 'None' tier string (sentinel for invalid tiers) with N/A display."""
    sub = load(str(tmp_path))
    sub.team_name = "TestTeam"
    sub.tier = "None"  # String "None" is the sentinel value for invalid tiers
    evt = sub.get_event("EVENT001")
    evt.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    html = _generate_dashboard_content(sub)

    # Should show N/A for "None" tier string, not "0 / 0" or "X / 0"
    assert "/ N/A Events Processed" in html
    assert "(N/A)" in html
    # Should NOT show 0 events
    assert "/ 0 Events Processed" not in html
