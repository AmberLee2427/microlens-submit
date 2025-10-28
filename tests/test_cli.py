"""
Test suite for microlens-submit command-line interface functionality.

This module contains comprehensive tests for the CLI commands and functionality
of microlens-submit. It tests all major CLI operations including project
initialization, solution management, validation, and export operations.

**Test Coverage:**
- CLI initialization and project setup
- Solution addition with various parameter formats
- Export functionality and file handling
- Solution listing and comparison
- Validation commands (submission, event, solution)
- Solution editing and metadata management
- Parameter file handling (JSON, YAML)
- Higher-order effects and model parameters
- Compute information and notes management
- Dossier generation

**Key Test Areas:**
- Command-line argument parsing and validation
- File I/O operations and path handling
- Parameter file parsing (JSON, YAML, structured)
- Interactive prompts and user input handling
- Error handling and exit codes
- Output formatting and display
- Integration with API functionality

**CLI Commands Tested:**
- init: Project initialization
- add-solution: Solution creation with various options
- export: Submission packaging
- list-solutions: Solution display
- compare-solutions: BIC-based comparison
- validate-submission: Submission validation
- validate-event: Event-specific validation
- validate-solution: Solution-specific validation
- edit-solution: Solution modification
- activate/deactivate: Solution status management
- generate-dossier: HTML report creation

Example:
    >>> import pytest
    >>> from typer.testing import CliRunner
    >>> from microlens_submit.cli import app
    >>>
    >>> # Run a specific CLI test
    >>> def test_basic_cli_functionality():
    ...     runner = CliRunner()
    ...     with runner.isolated_filesystem():
    ...         result = runner.invoke(
    ...             app,
    ...             ["init", "--team-name", "Test Team", "--tier", "test"]
    ...         )
    ...         assert result.exit_code == 0
    ...         assert "submission.json" in result.stdout

Note:
    All tests use Typer's CliRunner for isolated testing environments.
    Tests verify both command success/failure and output correctness.
    The test suite ensures CLI functionality matches API behavior.
"""

# Install package in editable mode to ensure assets are available when running tests
import os
import subprocess
import sys

if os.environ.get("MICROLENS_SKIP_EDITABLE_INSTALL") != "1":
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        # If we're not in the right directory or package isn't set up, continue anyway
        # The asset check fixture will catch missing assets
        pass

import json
import zipfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from microlens_submit.cli import app
from microlens_submit.utils import load

runner = CliRunner()


@pytest.fixture(scope="session", autouse=True)
def check_assets_exist():
    """Check that required assets exist before running tests."""
    assets = [
        Path(__file__).parent.parent / "microlens_submit" / "assets" / "rges-pit_logo.png",
        Path(__file__).parent.parent / "microlens_submit" / "assets" / "github-desktop_logo.png",
    ]
    for asset in assets:
        assert asset.exists(), f"Required asset missing: {asset}. Make sure to run 'pip install -e .' before testing."


def test_global_no_color_option():
    """Test that the --no-color flag disables ANSI color codes.

    Verifies that the global --no-color option correctly disables
    colored output in CLI commands.

    Args:
        None (uses isolated filesystem).

    Example:
        >>> # This test verifies:
        >>> # 1. Running CLI command with --no-color flag
        >>> # 2. Checking that no ANSI escape codes are present
        >>> # 3. Ensuring command still executes successfully

    Note:
        The --no-color option is useful for automated environments
        where color codes might interfere with output parsing.
    """
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["--no-color", "init", "--team-name", "Team", "--tier", "test"],
        )
        assert result.exit_code == 0
        assert "\x1b[" not in result.stdout


def test_cli_init_and_add():
    """Test basic CLI initialization and solution addition workflow.

    Verifies the complete workflow of initializing a project and adding
    a solution with various parameters and metadata.

    Args:
        None (uses isolated filesystem).

    Example:
        >>> # This test verifies:
        >>> # 1. Project initialization with team info
        >>> # 2. Solution addition with parameters
        >>> # 3. Setting metadata (relative probability, plot paths)
        >>> # 4. Verifying data persistence and correctness

    Note:
        This is a fundamental test that ensures the basic CLI workflow
        functions correctly and data is properly saved.
    """
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["init", "--team-name", "Test Team", "--tier", "test"])
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

        # sub = load(".")
        evt = load(".").get_event("test-event")
        assert len(evt.solutions) == 1
        sol_id = next(iter(evt.solutions))
        assert sol_id in result.stdout
        sol = evt.solutions[sol_id]
        assert sol.parameters["p1"] == 1
        assert sol.lightcurve_plot_path == "lc.png"
        assert sol.lens_plane_plot_path == "lens.png"
        assert sol.relative_probability == 0.7


def test_cli_export():
    """Test CLI export functionality with solution management.

    Verifies that the export command correctly packages submissions
    and handles active/inactive solution filtering.

    Args:
        None (uses isolated filesystem).

    Example:
        >>> # This test verifies:
        >>> # 1. Creating multiple solutions
        >>> # 2. Deactivating one solution
        >>> # 3. Exporting with --force flag
        >>> # 4. Checking export contents and structure

    Note:
        The export command should only include active solutions
        and properly handle notes files and solution metadata.
    """
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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
        # sub = load(".")
        evt = load(".").get_event("evt")
        sol1, sol2 = list(evt.solutions.keys())

        assert runner.invoke(app, ["deactivate", sol2]).exit_code == 0

        # Set required fields for export
        sub = load(".")
        sub.repo_url = "https://github.com/test/team"
        sub.hardware_info = {"cpu": "test"}
        sub.save()

        result = runner.invoke(app, ["export", "submission.zip"])
        assert result.exit_code == 0
        assert Path("submission.zip").exists()
        with zipfile.ZipFile("submission.zip") as zf:
            names = zf.namelist()
            solution_json = f"events/evt/solutions/{sol1}.json"
            notes_md = f"events/evt/solutions/{sol1}/{sol1}.md"
            # Allow for both .json and .md files
            assert solution_json in names
            assert notes_md in names
            assert "submission.json" in names


def test_cli_list_solutions():
    """Test CLI solution listing functionality.

    Verifies that the list-solutions command correctly displays
    all solutions for a given event.

    Args:
        None (uses isolated filesystem).

    Example:
        >>> # This test verifies:
        >>> # 1. Creating multiple solutions for an event
        >>> # 2. Running list-solutions command
        >>> # 3. Checking that all solution IDs are displayed

    Note:
        The list-solutions command provides a quick overview
        of all solutions in an event with their basic metadata.
    """
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
        assert runner.invoke(app, ["add-solution", "evt", "other", "--param", "a=1"]).exit_code == 0
        assert runner.invoke(app, ["add-solution", "evt", "other", "--param", "b=2"]).exit_code == 0
        # sub = load(".")
        evt = load(".").get_event("evt")
        ids = list(evt.solutions.keys())
        result = runner.invoke(app, ["list-solutions", "evt"])
        assert result.exit_code == 0
        for sid in ids:
            assert sid in result.stdout


def test_cli_compare_solutions():
    """Test CLI solution comparison functionality.

    Verifies that the compare-solutions command correctly calculates
    and displays BIC-based comparisons between solutions.

    Args:
        None (uses isolated filesystem).

    Example:
        >>> # This test verifies:
        >>> # 1. Creating solutions with different log-likelihoods
        >>> # 2. Running compare-solutions command
        >>> # 3. Checking that BIC and relative probabilities are shown

    Note:
        The compare-solutions command uses BIC to automatically
        calculate relative probabilities for solutions that lack them.
    """
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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
    """Test that solutions with non-positive n_data_points are ignored in comparison.

    Verifies that the compare-solutions command correctly skips
    solutions that have invalid or zero data point counts.

    Args:
        None (uses isolated filesystem).

    Example:
        >>> # This test verifies:
        >>> # 1. Creating solutions with zero data points
        >>> # 2. Running compare-solutions command
        >>> # 3. Checking that problematic solutions are skipped

    Note:
        Solutions with n_data_points <= 0 cannot have BIC calculated
        and are therefore excluded from automatic comparison.
    """
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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
                "-10",
                "--n-data-points",
                "50",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(app, ["compare-solutions", "evt"])
        assert result.exit_code == 0
        # Should only show the valid solution in the table. Depending on console support
        # Rich may render Unicode box characters or ASCII fallbacks. Count the header row
        # that contains the "Relative" column (ignoring the footer line that describes BIC).
        header_lines = [
            line for line in result.stdout.splitlines() if "Relative" in line and "Relative probabilities" not in line
        ]
        assert len(header_lines) == 1


def test_params_file_option_and_bands():
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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
        # sub = load(".")
        sol = next(iter(load(".").get_event("evt").solutions.values()))
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
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

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
        # Directory may exist, but no .json or .md files should be created
        evt_dir = Path("events/evt/solutions")
        if evt_dir.exists():
            files = list(evt_dir.glob("*"))
            assert not any(f.suffix in {".json", ".md"} for f in files)


def test_cli_activate():
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
        assert runner.invoke(app, ["add-solution", "evt", "other", "--param", "x=1"]).exit_code == 0
        # sub = load(".")
        sol_id = next(iter(load(".").get_event("evt").solutions))

        assert runner.invoke(app, ["deactivate", sol_id]).exit_code == 0
        # sub = load(".")
        assert not load(".").get_event("evt").solutions[sol_id].is_active

        result = runner.invoke(app, ["activate", sol_id])
        assert result.exit_code == 0
        # sub = load(".")
        assert load(".").get_event("evt").solutions[sol_id].is_active


def test_cli_validate_solution():
    """Test validate-solution command."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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

        # sub = load(".")
        sol_id = next(iter(load(".").get_event("evt").solutions))

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

        # sub = load(".")
        sol_id2 = next(iter(load(".").get_event("evt2").solutions))

        result = runner.invoke(app, ["validate-solution", sol_id2])
        assert result.exit_code == 0
        assert "Missing required" in result.stdout


def test_cli_validate_event():
    """Test validate-event command."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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

        # Set repo URL to make validation pass
        result = runner.invoke(app, ["set-repo-url", "https://github.com/test/team"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["validate-submission"])
        assert result.exit_code == 0
        # Should have warnings about missing metadata
        assert "validation issue" in result.stdout or "missing" in result.stdout


def test_cli_edit_solution():
    """Test edit-solution command."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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

        # sub = load(".")
        sol_id = next(iter(load(".").get_event("evt").solutions))

        # Test updating notes
        result = runner.invoke(app, ["edit-solution", sol_id, "--notes", "Updated notes"])
        assert result.exit_code == 0
        assert "Updated" in result.stdout

        # Test appending notes
        result = runner.invoke(app, ["edit-solution", sol_id, "--append-notes", "Additional info"])
        assert result.exit_code == 0
        assert "Append" in result.stdout or "Appended" in result.stdout

        # Test updating parameters
        result = runner.invoke(app, ["edit-solution", sol_id, "--param", "t0=556.0"])
        assert result.exit_code == 0
        assert "Update parameter" in result.stdout

        # Test updating uncertainties
        result = runner.invoke(app, ["edit-solution", sol_id, "--param-uncertainty", "t0=0.1"])
        assert result.exit_code == 0
        assert "Update uncertainty" in result.stdout

        # Test updating compute info
        result = runner.invoke(
            app,
            [
                "edit-solution",
                sol_id,
                "--cpu-hours",
                "10.5",
                "--wall-time-hours",
                "2.5",
            ],
        )
        assert result.exit_code == 0
        assert "Update cpu_hours" in result.stdout

        # Test dry run
        result = runner.invoke(app, ["edit-solution", sol_id, "--relative-probability", "0.8", "--dry-run"])
        assert result.exit_code == 0
        assert "Changes for" in result.stdout
        assert "No changes would be made" not in result.stdout

        # Test clearing attributes
        result = runner.invoke(app, ["edit-solution", sol_id, "--clear-notes"])
        assert result.exit_code == 0
        assert "Cleared notes" in result.stdout


def test_cli_edit_solution_not_found():
    """Test edit-solution with non-existent solution."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
        result = runner.invoke(app, ["edit-solution", "non-existent-id", "--notes", "test"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


def test_cli_yaml_params_file():
    """Test YAML parameter file support."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

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

        # sub = load(".")
        sol = next(iter(load(".").get_event("evt").solutions.values()))
        assert sol.parameters["t0"] == 555.5
        assert sol.parameters["u0"] == 0.1
        assert sol.parameters["tE"] == 25.0
        assert sol.parameter_uncertainties["t0"] == [0.1, 0.1]
        assert sol.parameter_uncertainties["u0"] == 0.02
        assert sol.parameter_uncertainties["tE"] == [0.3, 0.4]


def test_cli_structured_json_params_file():
    """Test structured JSON parameter file with uncertainties."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

        # Create structured JSON parameter file
        params = {
            "parameters": {"t0": 555.5, "u0": 0.1, "tE": 25.0},
            "uncertainties": {"t0": [0.1, 0.1], "u0": 0.02, "tE": [0.3, 0.4]},
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

        # sub = load(".")
        sol = next(iter(load(".").get_event("evt").solutions.values()))
        assert sol.parameters["t0"] == 555.5
        assert sol.parameters["u0"] == 0.1
        assert sol.parameters["tE"] == 25.0
        assert sol.parameter_uncertainties["t0"] == [0.1, 0.1]
        assert sol.parameter_uncertainties["u0"] == 0.02
        assert sol.parameter_uncertainties["tE"] == [0.3, 0.4]


def test_cli_simple_params_file():
    """Test simple parameter file (parameters only, no uncertainties)."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

        # Create simple JSON parameter file
        params = {"t0": 555.5, "u0": 0.1, "tE": 25.0}
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

        # sub = load(".")
        sol = next(iter(load(".").get_event("evt").solutions.values()))
        assert sol.parameters["t0"] == 555.5
        assert sol.parameters["u0"] == 0.1
        assert sol.parameters["tE"] == 25.0
        # Should have no uncertainties (empty dict, not None)
        assert sol.parameter_uncertainties == {}


def test_cli_params_file_mutually_exclusive():
    """Test that --param and --params-file are mutually exclusive."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

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
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

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
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

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
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

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
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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

        # sub = load(".")
        sol_id = next(iter(load(".").get_event("evt").solutions))

        # Test updating higher-order effects
        result = runner.invoke(
            app,
            [
                "edit-solution",
                sol_id,
                "--higher-order-effect",
                "finite-source",
                "--higher-order-effect",
                "parallax",
            ],
        )
        assert result.exit_code == 0
        assert "Update higher_order_effects" in result.stdout

        # Test clearing higher-order effects
        result = runner.invoke(app, ["edit-solution", sol_id, "--clear-higher-order-effects"])
        assert result.exit_code == 0
        assert "Clear higher_order_effects" in result.stdout


def test_cli_compute_info_options():
    """Test compute info options in add-solution."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0

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

        # sub = load(".")
        sol = next(iter(load(".").get_event("evt").solutions.values()))
        assert sol.compute_info["cpu_hours"] == 15.5
        assert sol.compute_info["wall_time_hours"] == 3.2


def test_markdown_notes_round_trip():
    """Test that a Markdown-rich note is preserved through CLI and API."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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
        # sub = load(".")
        sol = next(iter(load(".").get_event("evt").solutions.values()))
        assert sol.notes == md_note
        # Now update via edit-solution
        new_md = md_note + "\n---\nAppended"
        result = runner.invoke(app, ["edit-solution", sol.solution_id, "--notes", new_md])
        assert result.exit_code == 0
        # sub = load(".")
        sol2 = next(iter(load(".").get_event("evt").solutions.values()))
        assert sol2.notes == new_md


def test_markdown_notes_in_list_and_compare():
    """Test that Markdown notes appear in list-solutions and compare-solutions output."""
    with runner.isolated_filesystem():
        assert runner.invoke(app, ["init", "--team-name", "Team", "--tier", "test"]).exit_code == 0
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
        # sub = load(".")
        sol = next(iter(load(".").get_event("evt").solutions.values()))
        # Check list-solutions output
        result = runner.invoke(app, ["list-solutions", "evt"])
        assert result.exit_code == 0
        assert "# Header" in result.stdout or "Bullet" in result.stdout or "**Bold**" in result.stdout
        # Check compare-solutions output
        result = runner.invoke(app, ["compare-solutions", "evt"])
        assert result.exit_code == 0
        # Notes are not shown in compare-solutions, but ensure command runs and solution is present
        assert sol.solution_id[:8] in result.stdout


def test_cli_generate_dossier():
    """Test generate-dossier command creates dossier/index.html with expected content."""
    from microlens_submit import __version__

    with runner.isolated_filesystem():
        # Initialize project
        result = runner.invoke(app, ["init", "--team-name", "DossierTesters", "--tier", "standard"])
        assert result.exit_code == 0

        # Set GitHub repository URL
        result = runner.invoke(
            app,
            ["set-repo-url", "https://github.com/AmberLee2427/microlens-submit.git"],
        )
        assert result.exit_code == 0

        # Add a solution
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
        # Generate dossier
        result = runner.invoke(app, ["generate-dossier"])
        assert result.exit_code == 0
        dossier_index = Path("dossier/index.html")
        assert dossier_index.exists()
        html = dossier_index.read_text(encoding="utf-8")
        assert "DossierTesters" in html
        assert f"microlens-submit v{__version__}" in html


def test_cli_generate_dossier_selective_event():
    """Test generate-dossier --event-id flag generates only specific event page."""
    with runner.isolated_filesystem():
        # Initialize project
        result = runner.invoke(app, ["init", "--team-name", "SelectiveTesters", "--tier", "standard"])
        assert result.exit_code == 0

        # Add solutions to multiple events
        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT001",
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

        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT002",
                "1S2L",
                "--param",
                "t0=556.0",
                "--param",
                "u0=0.2",
                "--param",
                "tE=30.0",
            ],
        )
        assert result.exit_code == 0

        # Generate dossier for specific event only
        result = runner.invoke(app, ["generate-dossier", "--event-id", "EVENT001"])
        assert result.exit_code == 0
        assert "Generating dossier for event EVENT001" in result.stdout

        # Check that only EVENT001 page was generated
        dossier_dir = Path("dossier")
        assert dossier_dir.exists()

        # Should NOT have index.html (full dashboard)
        assert not (dossier_dir / "index.html").exists()

        # Should NOT have full dossier report
        assert not (dossier_dir / "full_dossier_report.html").exists()

        # Should have EVENT001 page
        assert (dossier_dir / "EVENT001.html").exists()

        # Should NOT have EVENT002 page
        assert not (dossier_dir / "EVENT002.html").exists()

        # Verify EVENT001 page content
        event_html = (dossier_dir / "EVENT001.html").read_text(encoding="utf-8")
        assert "EVENT001" in event_html
        assert "1S1L" in event_html
        # Event pages show solution metadata, not parameter values
        # Parameter values are shown on individual solution pages


def test_cli_generate_dossier_selective_solution():
    """Test generate-dossier --solution-id flag generates only specific solution page."""
    with runner.isolated_filesystem():
        # Initialize project
        result = runner.invoke(app, ["init", "--team-name", "SolutionTesters", "--tier", "standard"])
        assert result.exit_code == 0

        # Add multiple solutions to same event
        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT001",
                "1S1L",
                "--param",
                "t0=555.5",
                "--param",
                "u0=0.1",
                "--param",
                "tE=25.0",
                "--alias",
                "simple_fit",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT001",
                "1S2L",
                "--param",
                "t0=556.0",
                "--param",
                "u0=0.2",
                "--param",
                "tE=30.0",
                "--alias",
                "binary_fit",
            ],
        )
        assert result.exit_code == 0

        # Get the solution ID from the first solution
        submission = load(".")
        event = submission.events["EVENT001"]
        # Find the 1S1L solution specifically (not using next(iter()) which is non-deterministic)
        solution_id = None
        for sol_id, solution in event.solutions.items():
            if solution.model_type == "1S1L":
                solution_id = sol_id
                break
        assert solution_id is not None, "Could not find 1S1L solution"

        # Generate dossier for specific solution only
        result = runner.invoke(app, ["generate-dossier", "--solution-id", solution_id])
        assert result.exit_code == 0
        assert f"Generating dossier for solution {solution_id}" in result.stdout

        # Check that only the specific solution page was generated
        dossier_dir = Path("dossier")
        assert dossier_dir.exists()

        # Should NOT have index.html (full dashboard)
        assert not (dossier_dir / "index.html").exists()

        # Should NOT have full dossier report
        assert not (dossier_dir / "full_dossier_report.html").exists()

        # Should NOT have event page
        assert not (dossier_dir / "EVENT001.html").exists()

        # Should have solution page
        solution_file = dossier_dir / f"{solution_id}.html"
        assert solution_file.exists()

        # Verify solution page content
        solution_html = solution_file.read_text(encoding="utf-8")
        assert solution_id in solution_html
        assert "1S1L" in solution_html
        assert "555.5" in solution_html  # t0 parameter


def test_cli_generate_dossier_invalid_event():
    """Test generate-dossier --event-id with invalid event ID returns error."""
    with runner.isolated_filesystem():
        # Initialize project
        result = runner.invoke(app, ["init", "--team-name", "ErrorTesters", "--tier", "standard"])
        assert result.exit_code == 0

        # Try to generate dossier for non-existent event
        result = runner.invoke(app, ["generate-dossier", "--event-id", "NONEXISTENT"])
        assert result.exit_code == 1
        assert "Event NONEXISTENT not found" in result.stdout


def test_cli_generate_dossier_invalid_solution():
    """Test generate-dossier --solution-id with invalid solution ID returns error."""
    with runner.isolated_filesystem():
        # Initialize project
        result = runner.invoke(app, ["init", "--team-name", "ErrorTesters", "--tier", "standard"])
        assert result.exit_code == 0

        # Try to generate dossier for non-existent solution
        result = runner.invoke(
            app,
            [
                "generate-dossier",
                "--solution-id",
                "00000000-0000-0000-0000-000000000000",
            ],
        )
        assert result.exit_code == 1
        assert "Solution 00000000-0000-0000-0000-000000000000 not found" in result.stdout


def test_cli_generate_dossier_full_generation():
    """Test generate-dossier without flags generates complete dossier."""
    with runner.isolated_filesystem():
        # Initialize project
        result = runner.invoke(app, ["init", "--team-name", "FullTesters", "--tier", "standard"])
        assert result.exit_code == 0

        # Add solutions to multiple events
        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT001",
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

        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT002",
                "1S2L",
                "--param",
                "t0=556.0",
                "--param",
                "u0=0.2",
                "--param",
                "tE=30.0",
            ],
        )
        assert result.exit_code == 0

        # Generate full dossier
        result = runner.invoke(app, ["generate-dossier"])
        assert result.exit_code == 0
        assert "Generating comprehensive dossier for all events and solutions" in result.stdout
        assert "Generating comprehensive printable dossier" in result.stdout

        # Check that complete dossier was generated
        dossier_dir = Path("dossier")
        assert dossier_dir.exists()

        # Should have index.html (full dashboard)
        assert (dossier_dir / "index.html").exists()

        # Should have full dossier report
        assert (dossier_dir / "full_dossier_report.html").exists()

        # Should have both event pages
        assert (dossier_dir / "EVENT001.html").exists()
        assert (dossier_dir / "EVENT002.html").exists()

        # Should have solution pages
        submission = load(".")
        for event in submission.events.values():
            for solution_id in event.solutions:
                assert (dossier_dir / f"{solution_id}.html").exists()


def test_cli_generate_dossier_priority_flags():
    """Test that --solution-id takes priority over --event-id when both are provided."""
    with runner.isolated_filesystem():
        # Initialize project
        result = runner.invoke(app, ["init", "--team-name", "PriorityTesters", "--tier", "standard"])
        assert result.exit_code == 0

        # Add a solution
        result = runner.invoke(
            app,
            [
                "add-solution",
                "EVENT001",
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

        # Get the solution ID
        submission = load(".")
        event = submission.events["EVENT001"]
        solution_id = next(iter(event.solutions.keys()))

        # Generate dossier with both flags (solution-id should take priority)
        result = runner.invoke(
            app,
            [
                "generate-dossier",
                "--event-id",
                "EVENT001",
                "--solution-id",
                solution_id,
            ],
        )
        assert result.exit_code == 0
        assert f"Generating dossier for solution {solution_id}" in result.stdout
        assert "Generating dossier for event" not in result.stdout

        # Check that only solution page was generated (not event page)
        dossier_dir = Path("dossier")
        assert not (dossier_dir / "EVENT001.html").exists()
        assert (dossier_dir / f"{solution_id}.html").exists()


def test_csv_import_functionality():
    """Test the CSV import functionality with individual parameter columns."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test CSV file
        csv_content = """# event_id,solution_alias,model_tags,t0,u0,tE,s,q,alpha,notes
OGLE-2023-BLG-0001,simple_1S1L,"[""1S1L""]",2459123.5,0.1,20.0,,,,,"# Simple Point Lens"
OGLE-2023-BLG-0001,binary_1S2L,"[""1S2L""]",2459123.5,0.1,20.0,1.2,0.5,45.0,"# Binary Lens"
OGLE-2023-BLG-0002,finite_source,"[""1S1L"", ""finite-source""]",2459156.2,0.08,35.7,,,,,"# Finite Source"
"""
        csv_file = Path(tmpdir) / "test_import.csv"
        csv_file.write_text(csv_content)

        # Load project
        submission = load(tmpdir)
        submission.team_name = "Test Team"

        # Test dry run import
        import subprocess

        result = subprocess.run(
            [
                "microlens-submit",
                "import-solutions",
                str(csv_file),
                "--project-path",
                tmpdir,
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Total rows processed: 3" in result.stdout
        assert "Successful imports: 3" in result.stdout

        # Test actual import
        result = subprocess.run(
            [
                "microlens-submit",
                "import-solutions",
                str(csv_file),
                "--project-path",
                tmpdir,
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Successful imports: 3" in result.stdout

        # Verify solutions were created
        submission = load(tmpdir)
        assert "OGLE-2023-BLG-0001" in submission.events
        assert "OGLE-2023-BLG-0002" in submission.events

        event1 = submission.events["OGLE-2023-BLG-0001"]
        event2 = submission.events["OGLE-2023-BLG-0002"]

        assert len(event1.solutions) == 2
        assert len(event2.solutions) == 1

        # Check aliases
        aliases = [sol.alias for sol in event1.solutions.values()]
        assert "simple_1S1L" in aliases
        assert "binary_1S2L" in aliases

        # Check parameters
        simple_sol = next(sol for sol in event1.solutions.values() if sol.alias == "simple_1S1L")
        assert simple_sol.model_type == "1S1L"
        assert simple_sol.parameters["t0"] == 2459123.5
        assert simple_sol.parameters["u0"] == 0.1
        assert simple_sol.parameters["tE"] == 20.0

        binary_sol = next(sol for sol in event1.solutions.values() if sol.alias == "binary_1S2L")
        assert binary_sol.model_type == "1S2L"
        assert binary_sol.parameters["s"] == 1.2
        assert binary_sol.parameters["q"] == 0.5
        assert binary_sol.parameters["alpha"] == 45.0

        finite_sol = next(sol for sol in event2.solutions.values())
        assert finite_sol.model_type == "1S1L"
        assert "finite-source" in finite_sol.higher_order_effects


def test_csv_import_duplicate_handling():
    """Test CSV import duplicate handling modes."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test CSV file
        csv_content = """# event_id,solution_alias,model_tags,t0,u0,tE,notes
OGLE-2023-BLG-0001,test_solution,"[""1S1L""]",2459123.5,0.1,20.0,"First import"
"""
        csv_file = Path(tmpdir) / "test_import.csv"
        csv_file.write_text(csv_content)

        # Load project
        submission = load(tmpdir)
        submission.team_name = "Test Team"

        # First import
        import subprocess

        result1 = subprocess.run(
            [
                "microlens-submit",
                "import-solutions",
                str(csv_file),
                "--project-path",
                tmpdir,
            ],
            capture_output=True,
            text=True,
        )

        assert result1.returncode == 0
        assert "Successful imports: 1" in result1.stdout

        # Test error mode (default)
        result2 = subprocess.run(
            [
                "microlens-submit",
                "import-solutions",
                str(csv_file),
                "--project-path",
                tmpdir,
                "--on-duplicate",
                "error",
            ],
            capture_output=True,
            text=True,
        )

        assert result2.returncode == 0
        assert "Skipped rows: 1" in result2.stdout
        assert "Successful imports: 0" in result2.stdout
        assert "Duplicate alias key" in result2.stdout

        # Test ignore mode
        result3 = subprocess.run(
            [
                "microlens-submit",
                "import-solutions",
                str(csv_file),
                "--project-path",
                tmpdir,
                "--on-duplicate",
                "ignore",
            ],
            capture_output=True,
            text=True,
        )

        assert result3.returncode == 0
        assert "Duplicates handled: 1" in result3.stdout
        assert "Successful imports: 0" in result3.stdout

        # Test override mode
        result4 = subprocess.run(
            [
                "microlens-submit",
                "import-solutions",
                str(csv_file),
                "--project-path",
                tmpdir,
                "--on-duplicate",
                "override",
            ],
            capture_output=True,
            text=True,
        )

        assert result4.returncode == 0
        assert "Duplicates handled: 1" in result4.stdout
        assert "Successful imports: 1" in result4.stdout


def test_cli_import_calls_api(monkeypatch, tmp_path):
    """Ensure CLI import-solutions delegates to the API function."""
    csv_file = tmp_path / "dummy.csv"
    csv_file.write_text("dummy")

    from microlens_submit.utils import load as load_api

    submission = load_api(tmp_path)
    submission.team_name = "Test Team"
    submission.save()

    called: dict = {}

    def fake_import(
        submission,
        csv_file,
        parameter_map_file=None,
        delimiter=None,
        dry_run=False,
        validate=False,
        on_duplicate="error",
        project_path=None,
    ):
        called.update(
            dict(
                csv_file=csv_file,
                delimiter=delimiter,
                dry_run=dry_run,
                validate=validate,
                on_duplicate=on_duplicate,
                project_path=project_path,
                parameter_map_file=parameter_map_file,
            )
        )
        return {
            "total_rows": 1,
            "successful_imports": 1,
            "skipped_rows": 0,
            "validation_errors": 0,
            "duplicate_handled": 0,
            "errors": [],
        }

    monkeypatch.setattr("microlens_submit.cli.commands.solutions.import_solutions_from_csv", fake_import)

    result = CliRunner().invoke(
        app,
        [
            "import-solutions",
            str(csv_file),
            "--project-path",
            str(tmp_path),
            "--delimiter",
            ";",
            "--dry-run",
            "--validate",
            "--on-duplicate",
            "override",
        ],
    )

    assert result.exit_code == 0
    assert called["csv_file"] == csv_file
    assert called["delimiter"] == ";"
    assert called["dry_run"] is True
    assert called["validate"] is True
    assert called["on_duplicate"] == "override"
    assert called["project_path"] == tmp_path
    assert "Successful imports: 1" in result.stdout


def test_csv_import_from_data_file():
    """Test CSV import using the actual test file from tests/data."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        # Use the actual test CSV file from tests/data
        csv_file = Path(__file__).parent / "data" / "test_import.csv"
        assert csv_file.exists(), f"Test CSV file not found: {csv_file}"

        # Load project
        submission = load(tmpdir)
        submission.team_name = "Test Team"

        # Test dry run import
        import subprocess

        result = subprocess.run(
            [
                "microlens-submit",
                "import-solutions",
                str(csv_file),
                "--project-path",
                tmpdir,
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Total rows processed: 6" in result.stdout
        assert "Successful imports: 6" in result.stdout  # All rows are valid

        # Test actual import
        result = subprocess.run(
            [
                "microlens-submit",
                "import-solutions",
                str(csv_file),
                "--project-path",
                tmpdir,
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Successful imports: 6" in result.stdout

        # Verify solutions were created
        submission = load(tmpdir)
        assert "OGLE-2023-BLG-0001" in submission.events
        assert "OGLE-2023-BLG-0002" in submission.events
        assert "OGLE-2023-BLG-0003" in submission.events
        assert "OGLE-2023-BLG-0004" in submission.events

        event1 = submission.events["OGLE-2023-BLG-0001"]
        event2 = submission.events["OGLE-2023-BLG-0002"]
        event3 = submission.events["OGLE-2023-BLG-0003"]
        event4 = submission.events["OGLE-2023-BLG-0004"]

        assert len(event1.solutions) == 2
        assert len(event2.solutions) == 2
        assert len(event3.solutions) == 1
        assert len(event4.solutions) == 1

        # Check aliases
        aliases = [sol.alias for sol in event1.solutions.values()]
        assert "simple_1S1L" in aliases
        assert "binary_parallax" in aliases

        # Check parameters for simple solution
        simple_sol = next(sol for sol in event1.solutions.values() if sol.alias == "simple_1S1L")
        assert simple_sol.model_type == "1S1L"
        assert simple_sol.parameters["t0"] == 2459123.5
        assert simple_sol.parameters["u0"] == 0.1
        assert simple_sol.parameters["tE"] == 20.0

        # Check parameters for binary parallax solution
        binary_sol = next(sol for sol in event1.solutions.values() if sol.alias == "binary_parallax")
        assert binary_sol.model_type == "1S2L"
        assert binary_sol.parameters["s"] == 1.2
        assert binary_sol.parameters["q"] == 0.5
        assert binary_sol.parameters["alpha"] == 45.0
        assert binary_sol.parameters["piEN"] == 0.1
        assert binary_sol.parameters["piEE"] == 0.05
        assert "parallax" in binary_sol.higher_order_effects

        # Check finite source solution
        finite_sol = next(sol for sol in event2.solutions.values() if sol.alias == "finite_source")
        assert finite_sol.model_type == "1S1L"
        assert "finite-source" in finite_sol.higher_order_effects
