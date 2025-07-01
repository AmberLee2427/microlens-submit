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
            ["add-solution", "test-event", "test", "--param", "p1=1"],
        )
        assert result.exit_code == 0

        sub = api.load(".")
        evt = sub.get_event("test-event")
        assert len(evt.solutions) == 1
        sol_id = next(iter(evt.solutions))
        assert sol_id in result.stdout
        assert evt.solutions[sol_id].parameters["p1"] == 1


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
                ["add-solution", "evt", "test", "--param", "x=1"],
            ).exit_code
            == 0
        )
        assert (
            runner.invoke(
                app,
                ["add-solution", "evt", "test", "--param", "y=2"],
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
            solution_files = [n for n in zf.namelist() if "solutions" in n]
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
                app, ["add-solution", "evt", "test", "--param", "a=1"]
            ).exit_code
            == 0
        )
        assert (
            runner.invoke(
                app, ["add-solution", "evt", "test", "--param", "b=2"]
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
                "model1",
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
                "model2",
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
