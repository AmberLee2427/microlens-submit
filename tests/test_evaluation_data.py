import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from microlens_submit import load
from microlens_submit.cli.main import app
from microlens_submit.dossier.evaluation_data import (
    build_truth_parameters,
    default_evaluation_data_dir,
    find_lightcurve_file,
    load_truth_mapping,
    load_truth_records,
    log10_error_to_fractional_difference,
    match_truth_lens_component,
    model_types_for_tier,
    parameter_comparison_error,
    resolve_evaluation_data,
)
from scripts.generate_interactive_plots import (
    _lightcurve_y_range,
    generate_comparison_metrics,
    generate_confusion_matrix,
    generate_lightcurve_plots,
)
from scripts.generate_cohort_stats import generate_cohort_confusion_matrix


def _write_parquet(path: Path) -> None:
    pd.DataFrame({"name": ["RMDC26_000001"]}).to_parquet(path)


def test_scale_parameter_comparisons_use_log10_space():
    for parameter in ("q", "s", "tE", "rho"):
        error = parameter_comparison_error(0.01, 0.001, parameter)
        assert error == pytest.approx(1.0)
        assert log10_error_to_fractional_difference(error) == pytest.approx(9.0)


def test_default_evaluation_data_dir_is_next_to_cohorts(tmp_path):
    cohort_dir = tmp_path / "rmdc26_submissions" / "experienced"

    assert default_evaluation_data_dir(cohort_dir, "experienced") == (
        tmp_path / "rmdc26_submissions" / "evaluator_data" / "experienced"
    )


def test_beginner_evaluation_data_is_normalized(tmp_path):
    data_dir = tmp_path / "beginner-data"
    data_dir.mkdir()
    lightcurve_dir = data_dir / "Original Lightcurves"
    lightcurve_dir.mkdir()
    lightcurve_path = lightcurve_dir / "RUN_A_2_10_7.det.lc"
    lightcurve_path.write_text("# test lightcurve\n", encoding="utf-8")
    _write_parquet(data_dir / "RMDC26_Beginner_Tier.parquet")
    (data_dir / "RMDC26_beginner_tier_w_id.txt").write_text(
        "runname field event subrun anon_id\n"
        "RUN_A 10 7 2 RMDC26_000001\n",
        encoding="utf-8",
    )
    (tmp_path / "beginner_tier_predictions.csv").write_text(
        "anon_id,predicted_class\nRMDC26_000001,1S2L\n",
        encoding="utf-8",
    )

    truth_path = data_dir / "RMDC26_Events.out.hdf5"
    truth = pd.DataFrame(
        {
            "runname": ["RUN_A"],
            "event": [7],
            "subrun": [2],
            "field": [10],
            "EventID": [7],
            "SubRun": [2],
            "t0lens1": [10.0],
            "u0lens1": [0.1],
            "tE_helio": [20.0],
            "Planet_q": [0.01],
        }
    )
    truth.to_hdf(truth_path, key="beginner", mode="w")
    truth.to_hdf(truth_path, key="rerun", mode="a")

    data = resolve_evaluation_data(data_dir, "beginner")
    records = load_truth_records(data)
    mapping = load_truth_mapping(data, records)

    assert records["anon_id"].tolist() == ["RMDC26_000001", "RMDC26_000001"]
    assert mapping == {"RMDC26_000001": "1S2L"}
    assert find_lightcurve_file(data, records.iloc[0]) == lightcurve_path


def test_experienced_truth_and_gz_lightcurve_are_normalized(tmp_path):
    data_dir = tmp_path / "experienced-data"
    selected_lc = data_dir / "selected_lc" / "RUN_A"
    selected_lc.mkdir(parents=True)
    _write_parquet(data_dir / "RMDC26_Experienced_Data.parquet")
    (data_dir / "RMDC26_Experienced_Data_name_manifest.csv").write_text(
        "name,runname,subrun,field,event_id,lc_name\n"
        "RMDC26_000123,RUN_A,5,6,7,RUN_A_5_6_7.det.lc\n",
        encoding="utf-8",
    )

    truth_path = data_dir / "RMDC26_Experienced_Data_out.hdf5"
    truth = pd.DataFrame(
        {
            "event_name": ["RMDC26_000123"],
            "nsource": [2],
            "nlens": [3],
            "nplanets": [2],
            "t0lens1": [10.0],
            "u0lens1": [0.1],
            "te_helio": [20.0],
            "alpha": [30.0],
            "planet_0_q": [0.001],
            "planet_0_s0": [1.2],
            "planet_0_mass": [5.0],
            "planet_0_dl": [4.0],
            "planet_1_q": [0.002],
            "planet_1_s0": [2.0],
            "planet_1_mass": [8.0],
            "planet_1_dl": [6.0],
            "source2_s": [0.5],
            "source2_alpha": [20.0],
            "obs_0_fs": [2.0],
            "obs_0_fs2": [0.5],
        }
    )
    truth.to_hdf(truth_path, key="selected_events", mode="w")
    lc_path = selected_lc / "RUN_A_5_6_7.det.lc.gz"
    pd.DataFrame({"BJD": [2461400.0]}).to_csv(lc_path, index=False, compression="gzip")

    data = resolve_evaluation_data(data_dir, "experienced")
    records = load_truth_records(data)
    mapping = load_truth_mapping(data, records)
    params = build_truth_parameters(records.iloc[0])

    assert mapping == {"RMDC26_000123": "2S3L"}
    assert records.iloc[0]["is_planet"]
    assert records.iloc[0]["Obs_0_fs2ofs1"] == 0.25
    assert params["t0"] == 2461416.5
    assert [candidate["label"] for candidate in params["lens_candidates"]] == [
        "planet_0",
        "planet_1",
    ]
    matched = match_truth_lens_component(params, model_s=1.95, model_q=0.0021)
    assert matched["label"] == "planet_1"
    assert matched["mass"] == 8.0
    assert matched["dl"] == 6.0
    assert find_lightcurve_file(data, records.iloc[0]) == lc_path
    assert model_types_for_tier("experienced") == [
        "1S1L",
        "1S2L",
        "1S3L",
        "1S4L",
        "2S1L",
        "2S2L",
        "2S3L",
        "2S4L",
    ]

    assets_dir = tmp_path / "project" / "dossier" / "assets"
    generate_confusion_matrix(tmp_path / "project", data_dir, assets_dir, tier="experienced")
    generate_comparison_metrics(tmp_path / "project", data_dir, assets_dir, tier="experienced")
    assert (assets_dir / "confusion_matrix.html").exists()
    assert "Submitted Event Model Distribution" in (
        assets_dir / "confusion_matrix.html"
    ).read_text(encoding="utf-8")
    comparison = json.loads(
        (assets_dir / "event_comparison_metrics.json").read_text(encoding="utf-8")
    )
    assert comparison["RMDC26_000123"]["truth_model"] == "2S3L"
    assert comparison["RMDC26_000123"]["truth_parameters"]["q"] == 0.001
    assert comparison["RMDC26_000123"]["truth_parameters"]["s"] == 1.2
    cached_comparison = (assets_dir / "event_comparison_metrics.json").read_text(encoding="utf-8")
    generate_comparison_metrics(tmp_path / "project", data_dir, assets_dir, tier="experienced")
    assert (assets_dir / "event_comparison_metrics.json").read_text(encoding="utf-8") == cached_comparison

    team_dir = tmp_path / "team"
    submission = load(str(team_dir))
    submission.team_name = "Experienced Team"
    submission.tier = "experienced"
    event = submission.get_event("RMDC26_000123")
    event.add_solution(
        "1S3L",
        {
            "t0": 2461416.5,
            "u0": 0.1,
            "tE": 20.0,
        },
    )
    submission.save()
    cohort_output = tmp_path / "cohort-analysis"
    generate_cohort_confusion_matrix(tmp_path, data_dir, cohort_output, tier="experienced")
    assert (cohort_output / "cohort_metrics.json").exists()


def test_experienced_evaluation_data_can_resolve_without_truth(tmp_path):
    data_dir = tmp_path / "experienced-data"
    data_dir.mkdir()
    parquet_path = data_dir / "RMDC26_Experienced_Data.parquet"
    _write_parquet(parquet_path)

    data = resolve_evaluation_data(data_dir, "experienced", require_truth=False)

    assert data.parquet_path == parquet_path
    assert data.mapping_path is None
    assert data.truth_path is None


def test_experienced_lens_companion_is_a_match_candidate():
    params = build_truth_parameters(
        pd.Series(
            {
                "nplanets": 2,
                "lenscompanions": 1,
                "planet_0_q": 0.001,
                "planet_0_s": 1.2,
                "planet_1_q": 0.002,
                "planet_1_s": 2.0,
                "planet_2_q": 0.5,
                "planet_2_s": 0.8,
            }
        )
    )

    labels = [candidate["label"] for candidate in params["lens_candidates"]]
    assert labels == ["planet_0", "planet_1", "lens_companion"]
    assert match_truth_lens_component(params, model_s=0.81, model_q=0.49)["label"] == "lens_companion"


def test_evaluate_cohort_rejects_mixed_tiers(tmp_path):
    cohort_dir = tmp_path / "cohort"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name, tier in (("beginner-team", "beginner"), ("experienced-team", "experienced")):
        team_dir = cohort_dir / name
        team_dir.mkdir(parents=True)
        (team_dir / "submission.json").write_text(
            json.dumps({"team_name": name, "tier": tier}),
            encoding="utf-8",
        )

    result = CliRunner().invoke(
        app,
        [
            "evaluate-cohort",
            str(cohort_dir),
            "--data-dir",
            str(data_dir),
        ],
    )

    assert result.exit_code == 1
    assert "A cohort must contain one tier only" in result.stdout


def test_evaluate_cohort_experienced_does_not_require_truth_data(tmp_path):
    cohort_dir = tmp_path / "experienced-cohort"
    team_dir = cohort_dir / "team"
    team_dir.mkdir(parents=True)
    (team_dir / "submission.json").write_text(
        json.dumps({"team_name": "Experienced Team", "tier": "experienced"}),
        encoding="utf-8",
    )
    missing_data_dir = tmp_path / "missing-data"

    result = CliRunner().invoke(
        app,
        [
            "evaluate-cohort",
            str(cohort_dir),
            "--data-dir",
            str(missing_data_dir),
        ],
    )

    assert result.exit_code == 0
    histogram = cohort_dir / "cohort_analysis" / "cohort_confusion_matrix.html"
    assert histogram.exists()
    assert "Cohort Submitted Event Model Distribution" in histogram.read_text(
        encoding="utf-8"
    )


def test_experienced_parquet_lightcurve_plot_uses_flux_columns(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "events" / "RMDC26_000123").mkdir(parents=True)
    parquet_path = tmp_path / "experienced.parquet"
    pd.DataFrame(
        {
            "name": ["RMDC26_000123", "RMDC26_000123"],
            "bjd": [2461400.0, 2461401.0],
            "filt": ["F146", "F146"],
            "flux_uJy": [1.0, 1.1],
            "flux_err_uJy": [0.01, 0.01],
        }
    ).to_parquet(parquet_path)

    output_dir = tmp_path / "interactive"
    generate_lightcurve_plots(project_dir, parquet_path, output_dir)

    assert (output_dir / "RMDC26_000123_lc.html").exists()


def test_lightcurve_y_range_preserves_flux_orientation():
    frame = pd.DataFrame(
        {
            "upper": [1.1, 1.2],
            "lower": [0.9, 1.0],
        }
    )

    assert _lightcurve_y_range(frame, "flux") == pytest.approx((0.8, 1.3))
    assert _lightcurve_y_range(frame, "mag") == pytest.approx((1.3, 0.8))
