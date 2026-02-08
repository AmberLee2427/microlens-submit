"""Tests for notebook-friendly dossier display helpers."""

from pathlib import Path

from microlens_submit import load


def _build_submission(tmp_path: Path):
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Test Team"
    sub.tier = "test"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}
    evt = sub.get_event("test-event")
    params = {"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "F0_S": 1000.0, "F0_B": 500.0}
    sol = evt.add_solution("1S1L", params, bands=["0"])
    sol.log_likelihood = -1234.56
    sol.n_data_points = 1250
    return sub, evt, sol


def test_notebook_display_dashboard_inlines_assets(tmp_path):
    sub, _, _ = _build_submission(tmp_path)
    html = sub.notebook_display_dashboard()
    assert "data:image/png;base64" in html


def test_notebook_display_event_inlines_assets(tmp_path):
    sub, evt, _ = _build_submission(tmp_path)
    html = sub.notebook_display_event(evt.event_id)
    assert "data:image/png;base64" in html


def test_notebook_display_solution_inlines_assets(tmp_path):
    sub, _, sol = _build_submission(tmp_path)
    html = sub.notebook_display_solution(sol.solution_id)
    assert "data:image/png;base64" in html


def test_notebook_display_full_dossier_inlines_assets(tmp_path):
    sub, _, _ = _build_submission(tmp_path)
    # Ensure assets exist before full report generation
    _ = sub.notebook_display_dashboard()
    html = sub.notebook_display_full_dossier()
    assert "data:image/png;base64" in html
