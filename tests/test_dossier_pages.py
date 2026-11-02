"""Tests for dossier page generation utilities."""

from pathlib import Path

import pytest

from microlens_submit.dossier import generate_event_page
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


def test_dashboard_uses_tier_event_count(tmp_path):
    """Dashboard uses tier-based event count instead of hardcoded 293."""
    sub = load(str(tmp_path))
    sub.team_name = "TestTeam"
    sub.tier = "beginner"
    evt = sub.get_event("rmdc26_000001")
    evt.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    html = _generate_dashboard_content(sub)

    # Should show tier-specific count (dynamically computed from tier definition)
    expected = len(get_tier_event_list("beginner"))
    assert f"/ {expected} Events" in html
    # Should not show the old hardcoded 293
    assert "/ 293 Events" not in html


def test_dashboard_handles_invalid_tier(tmp_path):
    """Dashboard gracefully handles invalid tier with N/A display."""
    sub = load(str(tmp_path))
    sub.team_name = "TestTeam"
    sub.tier = "invalid-tier-name"
    evt = sub.get_event("EVENT001")
    evt.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    html = _generate_dashboard_content(sub)

    # Should show N/A for invalid tier
    assert "/ N/A Events" in html
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
    assert "/ N/A Events" in html
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
    assert "/ N/A Events" in html
    assert "(N/A)" in html
    # Should NOT show 0 events
    assert "/ 0 Events" not in html


def test_dashboard_accuracy_subsections(tmp_path):
    """Dashboard splits Accuracy section into Planet Detection, Modelling, and Physical Parameters."""
    sub, _ = _basic_submission(tmp_path)

    html = _generate_dashboard_content(
        sub,
        q_scatter_html="<!-- Q Plot -->",
        te_scatter_html="<!-- tE Plot -->",
        planet_metrics_table_html="<!-- Planet Table -->",
        modelling_metrics_table_html="<!-- Modelling Table -->",
        bl_s_scatter_html="<!-- BL s Plot -->",
        bl_alpha_scatter_html="<!-- BL alpha Plot -->",
        bs_s_scatter_html="<!-- BS s Plot -->",
        bs_alpha_scatter_html="<!-- BS alpha Plot -->",
        bs_flux_ratio_scatter_html="<!-- BS flux ratio Plot -->",
        phys_mass_scatter_html="<!-- Companion Mass Plot -->",
        phys_dl_scatter_html="<!-- Lens Distance Plot -->",
    )

    # Verify the Accuracy heading exists
    assert "Accuracy" in html

    # Verify the three subsections exist
    assert "Planet Detection &amp; Parameters" in html or "Planet Detection & Parameters" in html
    assert "Modelling Parameters" in html
    assert "Physical Parameters" in html

    # Verify the tables are embedded
    assert "<!-- Planet Table -->" in html
    assert "<!-- Modelling Table -->" in html

    # Verify individual plots are correctly embedded
    assert "<!-- Q Plot -->" in html
    assert "<!-- tE Plot -->" in html
    assert "<!-- BL s Plot -->" in html
    assert "<!-- BL alpha Plot -->" in html
    assert "<!-- BS s Plot -->" in html
    assert "<!-- BS alpha Plot -->" in html
    assert "<!-- BS flux ratio Plot -->" in html
    assert "<!-- Companion Mass Plot -->" in html
    assert "<!-- Lens Distance Plot -->" in html


def test_dashboard_precision_posteriors(tmp_path):
    """Dashboard Precision section calculates and displays posterior coverage."""
    sub, evt = _basic_submission(tmp_path)

    # Add a posterior path to the solution to verify it is counted
    sol = next(iter(evt.solutions.values()))
    sol.posterior_path = "assets/posteriors/event_posterior.json"

    html = _generate_dashboard_content(sub)

    # Should show Posterior Coverage card
    assert "Posterior Coverage" in html
    # Should show 100% since the only active solution has a posterior attached
    assert "100.0%" in html


def test_dashboard_precision_uncertainties_plot(tmp_path):
    """Dashboard Precision section embeds uncertainties_hist_html if provided."""
    sub, _ = _basic_submission(tmp_path)

    html = _generate_dashboard_content(
        sub,
        precision_stats={"median_frac_uncerts": {"q": 0.05}},
        uncertainties_hist_html="<!-- Uncertainties Histogram -->",
    )

    assert "<!-- Uncertainties Histogram -->" in html
