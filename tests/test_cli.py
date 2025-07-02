import json
import zipfile
from pathlib import Path
from typer.testing import CliRunner

from microlens_submit import api
from microlens_submit.cli import app

runner = CliRunner()


def test_global_no_color_option():
    """The --no-color flag disables ANSI color codes."""
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["--no-color", "init", "--team-name", "Team", "--tier", "test"],
        )
        assert result.exit_code == 0
        assert "\x1b[" not in result.stdout


def test_cli_init_and_add():
    with runner.isolated_filesystem():
        result = runner.invoke(
            app, ["init", "--team-name", "Test Team", "--tier", "test"]
        )
        assert result.exit_code == 0
        assert Path("submission.json").exists()

        result = runner.invoke(
            app,
            [
                "add-solution",
                "test-event",
                "other",
                "--param",
                "p1=1",
                "--relative-probability",
                "0.7",
                "--lightcurve-plot-path",
                "lc.png",
                "--lens-plane-plot-path",
                "lens.png",
            ],
        )
        assert result.exit_code == 0

        sub = api.load(".")
        evt = sub.get_event("test-event")
        assert len(evt.solutions) == 1
        sol_id = next(iter(evt.solutions))
        assert sol_id in result.stdout
        sol = evt.solutions[sol_id]
        assert sol.parameters["p1"] == 1
        assert sol.lightcurve_plot_path == "lc.png"
        assert sol.lens_plane_plot_path == "lens.png"
        assert sol.relative_probability == 0.7


def test_cli_export():
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        assert (
            runner.invoke(
                app,
                ["add-solution", "evt", "other", "--param", "x=1"],
            ).exit_code
            == 0
        )
        assert (
            runner.invoke(
                app,
                ["add-solution", "evt", "other", "--param", "y=2"],
            ).exit_code
            == 0
        )
        sub = api.load(".")
        evt = sub.get_event("evt")
        sol1, sol2 = list(evt.solutions.keys())

        assert runner.invoke(app, ["deactivate", sol2]).exit_code == 0
        result = runner.invoke(app, ["export", "submission.zip", "--force"])
        assert result.exit_code == 0
        assert Path("submission.zip").exists()
        with zipfile.ZipFile("submission.zip") as zf:
            names = zf.namelist()
            solution_files = [n for n in names if "solutions" in n]
            assert "submission.json" in names
        assert solution_files == [f"events/evt/solutions/{sol1}.json"]


def test_cli_list_solutions():
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        assert (
            runner.invoke(
                app, ["add-solution", "evt", "other", "--param", "a=1"]
            ).exit_code
            == 0
        )
        assert (
            runner.invoke(
                app, ["add-solution", "evt", "other", "--param", "b=2"]
            ).exit_code
            == 0
        )
        sub = api.load(".")
        evt = sub.get_event("evt")
        ids = list(evt.solutions.keys())
        result = runner.invoke(app, ["list-solutions", "evt"])
        assert result.exit_code == 0
        for sid in ids:
            assert sid in result.stdout


def test_cli_compare_solutions():
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "other",
                "--param",
                "x=1",
                "--log-likelihood",
                "-10",
                "--n-data-points",
                "50",
            ],
        )
        assert result.exit_code == 0
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "other",
                "--param",
                "y=2",
                "--log-likelihood",
                "-12",
                "--n-data-points",
                "60",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["compare-solutions", "evt"])
        assert result.exit_code == 0
        assert "BIC" in result.stdout
        assert "Relative" in result.stdout and "Prob" in result.stdout


def test_cli_compare_solutions_skips_zero_data_points():
    """Solutions with non-positive n_data_points are ignored."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "other",
                "--param",
                "x=1",
                "--log-likelihood",
                "-5",
                "--n-data-points",
                "0",
            ],
        )
        assert result.exit_code == 0
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "other",
                "--param",
                "y=2",
                "--log-likelihood",
                "-6",
                "--n-data-points",
                "10",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["compare-solutions", "evt"])
        assert result.exit_code == 0
        # Only the valid solution should appear in the table
        assert "other" in result.stdout
        assert "Skipping" in result.stdout


def test_params_file_option_and_bands():
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        params = {"p1": 1, "p2": 2}
        with open("params.json", "w", encoding="utf-8") as fh:
            json.dump(params, fh)
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S1L",
                "--params-file",
                "params.json",
                "--bands",
                "0,1",
                "--higher-order-effect",
                "parallax",
                "--t-ref",
                "123.0",
            ],
        )
        assert result.exit_code == 0
        sub = api.load(".")
        sol = next(iter(sub.get_event("evt").solutions.values()))
        assert sol.parameters == params
        assert sol.bands == ["0", "1"]
        assert sol.higher_order_effects == ["parallax"]
        assert sol.t_ref == 123.0

        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S1L",
                "--param",
                "a=1",
                "--params-file",
                "params.json",
            ],
        )
        assert result.exit_code != 0


def test_add_solution_dry_run():
    """--dry-run prints info without saving to disk."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )

        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "other",
                "--param",
                "x=1",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Parsed Input" in result.stdout
        assert "Schema Output" in result.stdout
        assert not Path("events/evt").exists()


def test_cli_activate():
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        assert (
            runner.invoke(
                app, ["add-solution", "evt", "other", "--param", "x=1"]
            ).exit_code
            == 0
        )
        sub = api.load(".")
        sol_id = next(iter(sub.get_event("evt").solutions))

        assert runner.invoke(app, ["deactivate", sol_id]).exit_code == 0
        sub = api.load(".")
        assert not sub.get_event("evt").solutions[sol_id].is_active

        result = runner.invoke(app, ["activate", sol_id])
        assert result.exit_code == 0
        sub = api.load(".")
        assert sub.get_event("evt").solutions[sol_id].is_active
