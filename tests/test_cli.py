import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from microlens_submit import api
from microlens_submit.cli import app

runner = CliRunner()


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
        sol_id = result.stdout.strip()

        sub = api.load(".")
        evt = sub.get_event("test-event")
        assert sol_id in evt.solutions
        assert evt.solutions[sol_id].parameters["p1"] == 1


def test_cli_export():
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        sol1 = runner.invoke(
            app,
            ["add-solution", "evt", "test", "--param", "x=1"],
        ).stdout.strip()
        sol2 = runner.invoke(
            app,
            ["add-solution", "evt", "test", "--param", "y=2"],
        ).stdout.strip()

        assert runner.invoke(app, ["deactivate", sol2]).exit_code == 0
        result = runner.invoke(app, ["export", "submission.zip"])
        assert result.exit_code == 0
        assert Path("submission.zip").exists()
        with zipfile.ZipFile("submission.zip") as zf:
            solution_files = [n for n in zf.namelist() if "solutions" in n]
        assert solution_files == [f"events/evt/solutions/{sol1}.json"]
