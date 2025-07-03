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


def test_cli_validate_solution():
    """Test validate-solution command."""
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
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
            ],
        )
        assert result.exit_code == 0
        
        sub = api.load(".")
        sol_id = next(iter(sub.get_event("evt").solutions))
        
        # Test validation of valid solution
        result = runner.invoke(app, ["validate-solution", sol_id])
        assert result.exit_code == 0
        assert "All validations passed" in result.stdout
        
        # Test validation of invalid solution (missing required parameter)
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt2",
                "1S2L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                # Missing required parameters: tE, s, q, alpha
            ],
        )
        assert result.exit_code == 0
        
        sub = api.load(".")
        sol_id2 = next(iter(sub.get_event("evt2").solutions))
        
        result = runner.invoke(app, ["validate-solution", sol_id2])
        assert result.exit_code == 0
        assert "Missing required" in result.stdout


def test_cli_validate_event():
    """Test validate-event command."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        # Add valid solution
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
            ],
        )
        assert result.exit_code == 0
        
        # Add invalid solution
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S2L",
                "--param",
                "t0=555.5",
                # Missing required parameters
            ],
        )
        assert result.exit_code == 0
        
        result = runner.invoke(app, ["validate-event", "evt"])
        assert result.exit_code == 0
        assert "validation issue" in result.stdout or "Missing required" in result.stdout


def test_cli_validate_submission():
    """Test validate-submission command."""
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
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
            ],
        )
        assert result.exit_code == 0
        
        result = runner.invoke(app, ["validate-submission"])
        assert result.exit_code == 0
        # Should have warnings about missing metadata
        assert "validation issue" in result.stdout or "missing" in result.stdout


def test_cli_edit_solution():
    """Test edit-solution command."""
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
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
                "--notes",
                "Initial notes",
            ],
        )
        assert result.exit_code == 0
        
        sub = api.load(".")
        sol_id = next(iter(sub.get_event("evt").solutions))
        
        # Test updating notes
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--notes", "Updated notes"]
        )
        assert result.exit_code == 0
        assert "Updated" in result.stdout
        
        # Test appending notes
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--append-notes", "Additional info"]
        )
        assert result.exit_code == 0
        assert "Append" in result.stdout
        
        # Test updating parameters
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--param", "t0=556.0"]
        )
        assert result.exit_code == 0
        assert "Update parameter" in result.stdout
        
        # Test updating uncertainties
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--param-uncertainty", "t0=0.1"]
        )
        assert result.exit_code == 0
        assert "Update uncertainty" in result.stdout
        
        # Test updating compute info
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--cpu-hours", "10.5", "--wall-time-hours", "2.5"]
        )
        assert result.exit_code == 0
        assert "Update cpu_hours" in result.stdout
        
        # Test dry run
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--relative-probability", "0.8", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Changes for" in result.stdout
        assert "No changes would be made" not in result.stdout
        
        # Test clearing attributes
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--clear-notes"]
        )
        assert result.exit_code == 0
        assert "Clear notes" in result.stdout


def test_cli_edit_solution_not_found():
    """Test edit-solution with non-existent solution."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        result = runner.invoke(
            app, ["edit-solution", "non-existent-id", "--notes", "test"]
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout


def test_cli_yaml_params_file():
    """Test YAML parameter file support."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        
        # Create YAML parameter file
        yaml_content = """
parameters:
  t0: 555.5
  u0: 0.1
  tE: 25.0
uncertainties:
  t0: [0.1, 0.1]
  u0: 0.02
  tE: [0.3, 0.4]
"""
        with open("params.yaml", "w", encoding="utf-8") as fh:
            fh.write(yaml_content)
        
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S1L",
                "--params-file",
                "params.yaml",
            ],
        )
        assert result.exit_code == 0
        
        sub = api.load(".")
        sol = next(iter(sub.get_event("evt").solutions.values()))
        assert sol.parameters["t0"] == 555.5
        assert sol.parameters["u0"] == 0.1
        assert sol.parameters["tE"] == 25.0
        assert sol.parameter_uncertainties["t0"] == [0.1, 0.1]
        assert sol.parameter_uncertainties["u0"] == 0.02
        assert sol.parameter_uncertainties["tE"] == [0.3, 0.4]


def test_cli_structured_json_params_file():
    """Test structured JSON parameter file with uncertainties."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        
        # Create structured JSON parameter file
        params = {
            "parameters": {
                "t0": 555.5,
                "u0": 0.1,
                "tE": 25.0
            },
            "uncertainties": {
                "t0": [0.1, 0.1],
                "u0": 0.02,
                "tE": [0.3, 0.4]
            }
        }
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
            ],
        )
        assert result.exit_code == 0
        
        sub = api.load(".")
        sol = next(iter(sub.get_event("evt").solutions.values()))
        assert sol.parameters["t0"] == 555.5
        assert sol.parameters["u0"] == 0.1
        assert sol.parameters["tE"] == 25.0
        assert sol.parameter_uncertainties["t0"] == [0.1, 0.1]
        assert sol.parameter_uncertainties["u0"] == 0.02
        assert sol.parameter_uncertainties["tE"] == [0.3, 0.4]


def test_cli_simple_params_file():
    """Test simple parameter file (parameters only, no uncertainties)."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        
        # Create simple JSON parameter file
        params = {
            "t0": 555.5,
            "u0": 0.1,
            "tE": 25.0
        }
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
            ],
        )
        assert result.exit_code == 0
        
        sub = api.load(".")
        sol = next(iter(sub.get_event("evt").solutions.values()))
        assert sol.parameters["t0"] == 555.5
        assert sol.parameters["u0"] == 0.1
        assert sol.parameters["tE"] == 25.0
        # Should have no uncertainties (empty dict, not None)
        assert sol.parameter_uncertainties == {}


def test_cli_params_file_mutually_exclusive():
    """Test that --param and --params-file are mutually exclusive."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        
        # Create parameter file
        params = {"t0": 555.5}
        with open("params.json", "w", encoding="utf-8") as fh:
            json.dump(params, fh)
        
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S1L",
                "--param",
                "t0=555.5",
                "--params-file",
                "params.json",
            ],
        )
        # Just check that the command fails - the specific error message may vary
        assert result.exit_code != 0


def test_cli_params_file_required():
    """Test that either --param or --params-file is required."""
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
                "1S1L",
            ],
        )
        # Just check that the command fails - the specific error message may vary
        assert result.exit_code != 0


def test_cli_validation_in_dry_run():
    """Test that validation warnings are shown in dry-run mode."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        
        # Add solution with missing required parameters
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S2L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                # Missing tE, s, q, alpha
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Validation Warnings" in result.stdout
        assert "Missing required" in result.stdout


def test_cli_validation_on_add_solution():
    """Test that validation warnings are shown when adding solutions."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        
        # Add solution with missing required parameters
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S2L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                # Missing tE, s, q, alpha
            ],
        )
        assert result.exit_code == 0
        assert "Validation Warnings" in result.stdout
        assert "Missing required" in result.stdout
        # Should still save despite warnings
        assert "Created solution" in result.stdout


def test_cli_higher_order_effects_editing():
    """Test editing higher-order effects."""
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
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
                "--higher-order-effect",
                "parallax",
            ],
        )
        assert result.exit_code == 0
        
        sub = api.load(".")
        sol_id = next(iter(sub.get_event("evt").solutions))
        
        # Test updating higher-order effects
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--higher-order-effect", "finite-source", "--higher-order-effect", "parallax"]
        )
        assert result.exit_code == 0
        assert "Update higher_order_effects" in result.stdout
        
        # Test clearing higher-order effects
        result = runner.invoke(
            app, ["edit-solution", sol_id, "--clear-higher-order-effects"]
        )
        assert result.exit_code == 0
        assert "Clear higher_order_effects" in result.stdout


def test_cli_compute_info_options():
    """Test compute info options in add-solution."""
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
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
                "--cpu-hours",
                "15.5",
                "--wall-time-hours",
                "3.2",
            ],
        )
        assert result.exit_code == 0
        
        sub = api.load(".")
        sol = next(iter(sub.get_event("evt").solutions.values()))
        assert sol.compute_info["cpu_hours"] == 15.5
        assert sol.compute_info["wall_time_hours"] == 3.2


def test_markdown_notes_round_trip():
    """Test that a Markdown-rich note is preserved through CLI and API."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        md_note = """# Header\n\n- Bullet\n- **Bold**\n\n[Link](https://example.com)\n"""
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
                "--notes",
                md_note,
            ],
        )
        assert result.exit_code == 0
        sub = api.load(".")
        sol = next(iter(sub.get_event("evt").solutions.values()))
        assert sol.notes == md_note
        # Now update via edit-solution
        new_md = md_note + "\n---\nAppended"
        result = runner.invoke(
            app, ["edit-solution", sol.solution_id, "--notes", new_md]
        )
        assert result.exit_code == 0
        sub = api.load(".")
        sol2 = next(iter(sub.get_event("evt").solutions.values()))
        assert sol2.notes == new_md


def test_markdown_notes_in_list_and_compare():
    """Test that Markdown notes appear in list-solutions and compare-solutions output."""
    with runner.isolated_filesystem():
        assert (
            runner.invoke(
                app, ["init", "--team-name", "Team", "--tier", "test"]
            ).exit_code
            == 0
        )
        md_note = "# Header\n- Bullet\n**Bold**"
        result = runner.invoke(
            app,
            [
                "add-solution",
                "evt",
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
                "--notes",
                md_note,
                "--log-likelihood",
                "-10",
                "--n-data-points",
                "100",
            ],
        )
        assert result.exit_code == 0
        sub = api.load(".")
        sol = next(iter(sub.get_event("evt").solutions.values()))
        # Check list-solutions output
        result = runner.invoke(app, ["list-solutions", "evt"])
        assert result.exit_code == 0
        assert "# Header" in result.stdout or "Bullet" in result.stdout or "**Bold**" in result.stdout
        # Check compare-solutions output
        result = runner.invoke(app, ["compare-solutions", "evt"])
        assert result.exit_code == 0
        # Notes are not shown in compare-solutions, but ensure command runs and solution is present
        assert sol.solution_id[:8] in result.stdout
