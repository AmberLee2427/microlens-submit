"""Tests for dossier page generation utilities."""

from pathlib import Path

import pytest

from microlens_submit.dossier import generate_event_page
from microlens_submit.dossier.dashboard import _generate_dashboard_content
from microlens_submit.utils import load


def _basic_submission(tmp_path: Path):
    """Create a minimal submission with one event and solution."""
    sub = load(str(tmp_path))
    sub.team_name = "UnitTesters"
    sub.tier = "standard"
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
