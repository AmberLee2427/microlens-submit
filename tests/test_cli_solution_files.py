from typer.testing import CliRunner

from microlens_submit.cli import app
from microlens_submit.utils import load

runner = CliRunner()


def test_add_solution_with_paths(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # 1. Init
        result = runner.invoke(app, ["init", "--team-name", "Test Team", "--tier", "test", "."])
        assert result.exit_code == 0

        # 2. Add solution with paths
        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT001",
                "1S1L",
                "--param",
                "t0=100",
                "--param",
                "u0=0.1",
                "--param",
                "tE=10",
                "--lightcurve-plot-path",
                "plots/lc.png",
                "--lens-plane-plot-path",
                "plots/lp.png",
                "--posterior-path",
                "posteriors/samples.h5",
                "--alias",
                "test_sol",
            ],
        )
        assert result.exit_code == 0, result.stdout

        # 3. Verify
        sub = load(".")
        event = sub.get_event("EVENT001")
        sol = next(iter(event.solutions.values()))
        assert sol.lightcurve_plot_path == "plots/lc.png"
        assert sol.lens_plane_plot_path == "plots/lp.png"
        assert sol.posterior_path == "posteriors/samples.h5"


def test_edit_solution_paths(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # 1. Init
        result = runner.invoke(app, ["init", "--team-name", "Test Team", "--tier", "test", "."])
        assert result.exit_code == 0

        # 2. Add solution
        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT001",
                "1S1L",
                "--param",
                "t0=100",
                "--param",
                "u0=0.1",
                "--param",
                "tE=10",
                "--alias",
                "editable_sol",
            ],
        )
        assert result.exit_code == 0

        # Get solution id
        sub = load(".")
        event = sub.get_event("EVENT001")
        sol_id = next(iter(event.solutions.values())).solution_id

        # 3. Edit solution to add paths
        result = runner.invoke(
            app,
            [
                "edit-solution",
                sol_id,
                "--lightcurve-plot-path",
                "plots/new_lc.png",
                "--lens-plane-plot-path",
                "plots/new_lp.png",
                "--posterior-path",
                "posteriors/new_samples.h5",
            ],
        )
        assert result.exit_code == 0, result.stdout

        # Verify
        sub = load(".")
        sol = sub.get_event("EVENT001").solutions[sol_id]
        assert sol.lightcurve_plot_path == "plots/new_lc.png"
        assert sol.lens_plane_plot_path == "plots/new_lp.png"
        assert sol.posterior_path == "posteriors/new_samples.h5"

        # 4. Clear paths
        result = runner.invoke(
            app,
            [
                "edit-solution",
                sol_id,
                "--clear-lightcurve-plot-path",
                "--clear-lens-plane-plot-path",
                "--clear-posterior-path",
            ],
        )
        assert result.exit_code == 0, result.stdout

        # Verify cleared
        sub = load(".")
        sol = sub.get_event("EVENT001").solutions[sol_id]
        assert sol.lightcurve_plot_path is None
        assert sol.lens_plane_plot_path is None
        assert sol.posterior_path is None
