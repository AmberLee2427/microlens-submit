"""Regression tests for evaluator-only dossier behavior."""

import json
import logging
import math
from pathlib import Path

from microlens_submit import load
from microlens_submit.cli.commands.dossier import generate_dossier
from microlens_submit.dossier.anonymization import anonymized_team_name, evaluator_submission
from microlens_submit.dossier.dashboard import _generate_dashboard_content
from microlens_submit.dossier.event_page import _generate_event_page_content
from microlens_submit.dossier.full_report import generate_full_dossier_report_html
from microlens_submit.dossier.plotting import fit_best_model, load_event_dataset
from microlens_submit.dossier.solution_page import _generate_solution_page_content


def test_fit_best_model_does_not_fall_back_for_valid_parameters(tmp_path, caplog):
    data_file = tmp_path / "lightcurve.dat"
    data_file.write_text(
        "HJD mag mag_err band\n"
        "2459120.0 20.0 0.01 I\n"
        "2459125.0 19.0 0.01 I\n"
        "2459130.0 20.0 0.01 I\n",
        encoding="utf-8",
    )
    datasets = load_event_dataset(data_file, bands=["I"])

    with caplog.at_level(logging.WARNING):
        event, chi2 = fit_best_model(
            datasets,
            {"t0": 2459125.0, "u0": 0.1, "tE": 20.0},
            model_type="1S1L",
        )

    assert event is not None
    assert chi2 < float("inf")
    assert "All conventions failed during optimization" not in caplog.text


def test_solution_page_renders_evaluator_truth_and_missing_lens_fallback(tmp_path):
    submission = load(str(tmp_path / "submission"))
    submission.tier = "beginner"
    event = submission.get_event("EVENT001")
    solution = event.add_solution(
        "1S2L",
        {
            "t0": 2459123.5,
            "u0": 0.1,
            "tE": 20.0,
            "q": 0.01,
            "s": 1.2,
            "rho": 0.02,
            "alpha": math.pi / 2,
        },
    )
    event.truth_model = "1S2L"
    event.truth_parameters = {
        "t0": 2459123.5,
        "u0": 0.1,
        "tE": 20.0,
        "q": 0.01,
        "s": 1.2,
        "rho": 0.01,
        "alpha": math.pi / 2,
    }

    html = _generate_solution_page_content(
        solution,
        event,
        submission,
        evaluator_mode=True,
    )

    assert "Truth" in html
    assert "90.00" in html
    assert "Fractional Difference" in html
    assert "log10 comparison" in html
    assert "|Δ log10| = 0.3010" in html
    assert "Fractional Error" not in html
    assert "True Value" not in html
    assert ">Evaluation</th>" not in html
    assert "Lens Plane Geometry Plot Not Generated" in html
    assert "src=''" not in html


def test_solution_only_cli_passes_evaluator_mode(tmp_path):
    submission = load(str(tmp_path))
    event = submission.get_event("EVENT001")
    solution = event.add_solution(
        "1S1L",
        {"t0": 2459123.5, "u0": 0.1, "tE": 20.0},
    )
    submission.save()

    assets_dir = tmp_path / "dossier" / "assets"
    assets_dir.mkdir(parents=True)
    (assets_dir / "event_comparison_metrics.json").write_text(
        json.dumps(
            {
                "EVENT001": {
                    "truth_model": "1S1L",
                    "truth_parameters": {"t0": 2459123.5},
                }
            }
        ),
        encoding="utf-8",
    )

    generate_dossier(
        project_path=tmp_path,
        solution_id=solution.solution_id,
        evaluator=True,
    )

    html = (tmp_path / "dossier" / f"{solution.solution_id}.html").read_text(encoding="utf-8")
    assert "Truth" in html


def test_full_report_reuses_evaluator_dashboard(tmp_path):
    submission = load(str(tmp_path / "submission"))
    event = submission.get_event("EVENT001")
    event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
    output_dir = Path(submission.project_path) / "dossier"
    output_dir.mkdir(parents=True)
    (output_dir / "index.html").write_text(
        "<!-- Regex Start --><p>Evaluator rank: 42nd percentile</p><!-- Regex Finish -->",
        encoding="utf-8",
    )

    generate_full_dossier_report_html(submission, output_dir, evaluator_mode=True)

    html = (output_dir / "full_dossier_report.html").read_text(encoding="utf-8")
    assert "Evaluator rank: 42nd percentile" in html


def test_evaluator_submission_uses_tier_lookup_without_mutating_source(tmp_path):
    tier_dir = tmp_path / "experienced"
    project_dir = tier_dir / "Sierra_Warren_Stellar_Intelligence"
    submission = load(str(project_dir))
    submission.team_name = "Sierra Warren RMDC26"
    submission.tier = "experienced"
    submission.save()
    (tier_dir / "team_name_lookup.json").write_text(
        json.dumps({"Sierra Warren RMDC26": "Team 02"}),
        encoding="utf-8",
    )

    report_submission = evaluator_submission(submission)

    assert report_submission.team_name == "Team 02"
    assert submission.team_name == "Sierra Warren RMDC26"
    assert anonymized_team_name(project_dir) == "Team 02"


def test_evaluator_dossier_renders_anonymous_team_name(tmp_path):
    tier_dir = tmp_path / "beginner"
    project_dir = tier_dir / "real-team-folder"
    submission = load(str(project_dir))
    submission.team_name = "Real Team"
    submission.tier = "beginner"
    submission.repo_url = "https://example.org/repository"
    submission.hardware_info = {"cpu": "test"}
    submission.save()
    (tier_dir / "team_name_lookup.json").write_text(
        json.dumps({"Real Team": "Team 01"}),
        encoding="utf-8",
    )

    generate_dossier(
        project_path=project_dir,
        event_id=None,
        solution_id=None,
        open=False,
        evaluator=True,
        data_dir=None,
        force=False,
    )

    index_html = (project_dir / "dossier" / "index.html").read_text(encoding="utf-8")
    full_report_html = (project_dir / "dossier" / "full_dossier_report.html").read_text(
        encoding="utf-8"
    )
    assert "Team: Team 01" in index_html
    assert "Real Team" not in index_html
    assert "example.org" not in index_html
    assert "Team: Team 01" in full_report_html
    assert "Real Team" not in full_report_html
    assert "example.org" not in full_report_html
    assert json.loads((project_dir / "submission.json").read_text(encoding="utf-8"))["team_name"] == "Real Team"


def test_experienced_evaluator_pages_use_histogram_and_link_to_tier(tmp_path):
    submission = load(str(tmp_path / "experienced-team"))
    submission.team_name = "Experienced Team"
    submission.tier = "experienced"
    event = submission.get_event("EVENT001")
    solution = event.add_solution(
        "1S1L",
        {"t0": 2459123.5, "u0": 0.1, "tE": 20.0},
    )
    event.truth_model = "1S2L"
    event.truth_parameters = {"t0": 2459123.5}

    dashboard = _generate_dashboard_content(
        submission,
        evaluator_mode=True,
        event_comparison_metrics={
            "EVENT001": {"truth_model": "1S2L", "truth_chi2": 1.0}
        },
    )
    event_page = _generate_event_page_content(submission.events["EVENT001"], submission, evaluator_mode=True)
    solution_page = _generate_solution_page_content(
        solution,
        event,
        submission,
        evaluator_mode=True,
    )

    tier_url = "https://rmdc26.rges-pit.com/submissions/experienced/"
    for html in (dashboard, event_page, solution_page):
        assert tier_url in html
    assert "Submitted Event Distribution" in dashboard
    assert "Truth ↕" not in dashboard
    assert "Truth -2 ln L ↕" in dashboard
    assert "Best Δ -2 ln L ↕" in dashboard
    assert "Δχ²_PSPL ↕" in dashboard
    assert "Δχ²_Flat ↕" in dashboard
    assert 'data-truth-chi2="1.0"' in dashboard
    assert "Ground Truth" not in dashboard
    assert "Parameter Accuracy vs. Truths (Evaluator-Only)" in solution_page
    assert "No trusted truth data is available for this tier" not in solution_page
    assert "Event Data Visualizations (Evaluator-Only)" in event_page
