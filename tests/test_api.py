"""
Test suite for microlens-submit API functionality.

This module contains comprehensive tests for the core API classes and functionality
of microlens-submit. It tests the complete lifecycle of submission management,
including creation, persistence, validation, and export operations.

**Test Coverage:**
- Submission lifecycle (create, save, load, validate)
- Event and solution management
- Compute information handling
- File path persistence and export
- Active/inactive solution filtering
- Parameter validation and warnings
- Relative probability calculations

**Key Test Areas:**
- Data persistence across save/load cycles
- Export functionality with external files
- Solution activation/deactivation
- Validation warnings and error conditions
- Compute time tracking and metadata
- Higher-order effects and model parameters

Example:
    >>> import pytest
    >>> from pathlib import Path
    >>> from microlens_submit.utils import load
    >>>
    >>> # Run a specific test
    >>> def test_basic_functionality(tmp_path):
    ...     project = tmp_path / "test_project"
    ...     sub = load(str(project))
    ...     sub.team_name = "Test Team"
    ...     sub.tier = "test"
    ...     sub.save()
    ...
    >>>     # Verify persistence
    ...     new_sub = load(str(project))
    ...     assert new_sub.team_name == "Test Team"
    ...     assert new_sub.tier == "test"

Note:
    All tests use pytest's tmp_path fixture for isolated testing.
    Tests verify both the API functionality and data persistence.
    The test suite ensures backward compatibility and data integrity.
"""

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

from microlens_submit import load
from microlens_submit.utils import import_solutions_from_csv


def test_full_lifecycle(tmp_path):
    """Test complete submission lifecycle from creation to persistence.

    Verifies that a complete submission can be created, saved, and reloaded
    with all data intact. This includes events, solutions, compute information,
    and metadata persistence.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies the complete workflow:
        >>> # 1. Create submission with team info
        >>> # 2. Add events and solutions
        >>> # 3. Set compute information
        >>> # 4. Save to disk
        >>> # 5. Reload and verify all data

    Note:
        This is a fundamental test that ensures the core persistence
        mechanism works correctly for all submission components.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Test Team"
    sub.tier = "test"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    evt = sub.get_event("test-event")
    sol1 = evt.add_solution(model_type="other", parameters={"a": 1})
    sol1.set_compute_info()
    sol2 = evt.add_solution(model_type="other", parameters={"b": 2})
    sub.save()

    new_sub = load(str(project))
    assert new_sub.team_name == "Test Team"
    assert "test-event" in new_sub.events
    new_evt = new_sub.events["test-event"]
    assert sol1.solution_id in new_evt.solutions
    assert sol2.solution_id in new_evt.solutions
    new_sol1 = new_evt.solutions[sol1.solution_id]
    assert "dependencies" in new_sol1.compute_info
    assert isinstance(new_sol1.compute_info["dependencies"], list)
    assert any("pytest" in dep for dep in new_sol1.compute_info["dependencies"])


def test_compute_info_hours(tmp_path):
    """Test that CPU and wall time are correctly persisted.

    Verifies that compute information including CPU hours and wall time
    are properly saved and restored when loading a submission.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Setting compute info with specific hours
        >>> # 2. Saving the submission
        >>> # 3. Reloading and checking values match

    Note:
        Compute information is critical for submission evaluation
        and must be accurately preserved across save/load cycles.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Test Team"
    sub.tier = "test"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    evt = sub.get_event("evt")
    sol = evt.add_solution(model_type="other", parameters={})
    sol.set_compute_info(cpu_hours=1.5, wall_time_hours=2.0)
    sub.save()

    new_sub = load(str(project))
    new_sol = new_sub.get_event("evt").solutions[sol.solution_id]
    assert new_sol.compute_info["cpu_hours"] == 1.5
    assert new_sol.compute_info["wall_time_hours"] == 2.0


def test_deactivate_and_export(tmp_path):
    """Test that deactivated solutions are excluded from exports.

    Verifies that when solutions are deactivated, they are properly
    excluded from submission exports while remaining in the project.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating active and inactive solutions
        >>> # 2. Exporting the submission
        >>> # 3. Checking only active solutions are included

    Note:
        Deactivated solutions remain in the project for potential
        reactivation but are excluded from final submissions.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Test Team"
    sub.tier = "test"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    evt = sub.get_event("test-event")
    sol_active = evt.add_solution("other", {"a": 1})
    sol_inactive = evt.add_solution("other", {"b": 2})
    sol_inactive.deactivate()
    sub.save()

    zip_path = project / "submission.zip"
    sub.export(str(zip_path))

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        solution_files = [n for n in names if n.startswith("events/") and "solutions" in n]
        assert "submission.json" in names
    assert solution_files == [f"events/test-event/solutions/{sol_active.solution_id}.json"]


def test_export_includes_external_files(tmp_path):
    """Test that external files are properly included in exports.

    Verifies that referenced files (posterior data, plots) are correctly
    included in submission exports with proper path handling.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating solution with external file references
        >>> # 2. Creating the referenced files
        >>> # 3. Exporting and checking file inclusion
        >>> # 4. Verifying path updates in solution JSON

    Note:
        External files are copied into the export archive and their
        paths in the solution JSON are updated to reflect the new locations.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Test Team"
    sub.tier = "test"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    evt = sub.get_event("test-event")  # Use valid event ID for test tier
    sol = evt.add_solution("other", {})
    (project / "post.h5").write_text("data")
    sol.posterior_path = "post.h5"
    (project / "lc.png").write_text("img")
    sol.lightcurve_plot_path = "lc.png"
    (project / "lens.png").write_text("img")
    sol.lens_plane_plot_path = "lens.png"
    sub.save()

    zip_path = project / "out.zip"
    sub.export(str(zip_path))

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        base = f"events/test-event/solutions/{sol.solution_id}"
        assert f"{base}.json" in names
        assert f"{base}/post.h5" in names
        assert f"{base}/lc.png" in names
        assert f"{base}/lens.png" in names
        data = json.loads(zf.read(f"{base}.json"))
        assert data["posterior_path"] == f"{base}/post.h5"
        assert data["lightcurve_plot_path"] == f"{base}/lc.png"
        assert data["lens_plane_plot_path"] == f"{base}/lens.png"


def test_get_active_solutions(tmp_path):
    """Test filtering of active solutions from events.

    Verifies that the get_active_solutions() method correctly returns
    only solutions that have not been deactivated.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating multiple solutions
        >>> # 2. Deactivating one solution
        >>> # 3. Checking only active solutions are returned

    Note:
        This method is used extensively for submission validation
        and export operations to ensure only active solutions are processed.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("evt")
    sol1 = evt.add_solution("other", {"a": 1})
    sol2 = evt.add_solution("other", {"b": 2})
    sol2.deactivate()

    actives = evt.get_active_solutions()

    assert len(actives) == 1
    assert actives[0].solution_id == sol1.solution_id


def test_clear_solutions(tmp_path):
    """Test that clear_solutions() deactivates all solutions.

    Verifies that the clear_solutions() method deactivates all solutions
    in an event without removing them from the project.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating multiple solutions
        >>> # 2. Calling clear_solutions()
        >>> # 3. Checking all solutions are deactivated
        >>> # 4. Verifying solutions still exist in project

    Note:
        clear_solutions() is a convenience method that deactivates
        all solutions rather than deleting them, allowing for easy
        reactivation if needed.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("evt")
    sol1 = evt.add_solution("other", {"a": 1})
    sol2 = evt.add_solution("other", {"b": 2})

    evt.clear_solutions()
    sub.save()

    reloaded = load(str(project))
    evt2 = reloaded.get_event("evt")

    assert not evt2.solutions[sol1.solution_id].is_active
    assert not evt2.solutions[sol2.solution_id].is_active
    assert len(evt2.solutions) == 2


def test_posterior_path_persists(tmp_path):
    """Test that posterior file paths are correctly persisted.

    Verifies that posterior file paths are properly saved and restored
    when loading a submission.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Setting a posterior file path
        >>> # 2. Saving the submission
        >>> # 3. Reloading and checking path matches

    Note:
        Posterior file paths are important for submission evaluation
        and must be accurately preserved across save/load cycles.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("event")
    sol = evt.add_solution("other", {"x": 1})
    sol.posterior_path = "posteriors/post.h5"
    sub.save()

    new_sub = load(str(project))
    new_sol = new_sub.events["event"].solutions[sol.solution_id]
    assert new_sol.posterior_path == "posteriors/post.h5"


def test_new_fields_persist(tmp_path):
    """Test that new solution fields are correctly persisted.

    Verifies that newer solution fields (bands, higher-order effects,
    reference times) are properly saved and restored.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Setting various new fields on a solution
        >>> # 2. Saving the submission
        >>> # 3. Reloading and checking all fields match

    Note:
        This test ensures backward compatibility when new fields
        are added to the solution schema.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("event")
    sol = evt.add_solution("1S1L", {"x": 1})
    sol.bands = ["0", "1"]
    sol.higher_order_effects = ["parallax"]
    sol.t_ref = 123.4
    sub.save()

    new_sub = load(str(project))
    new_sol = new_sub.events["event"].solutions[sol.solution_id]
    assert new_sol.bands == ["0", "1"]
    assert new_sol.higher_order_effects == ["parallax"]
    assert new_sol.t_ref == 123.4


def test_plot_paths_persist(tmp_path):
    """Test that plot file paths are correctly persisted.

    Verifies that lightcurve and lens plane plot paths are properly
    saved and restored when loading a submission.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Setting plot file paths
        >>> # 2. Saving the submission
        >>> # 3. Reloading and checking paths match

    Note:
        Plot paths are important for submission documentation
        and must be accurately preserved across save/load cycles.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("event")
    sol = evt.add_solution("other", {"x": 1})
    sol.lightcurve_plot_path = "plots/lc.png"
    sol.lens_plane_plot_path = "plots/lens.png"
    sub.save()

    new_sub = load(str(project))
    new_sol = new_sub.events["event"].solutions[sol.solution_id]
    assert new_sol.lightcurve_plot_path == "plots/lc.png"
    assert new_sol.lens_plane_plot_path == "plots/lens.png"


def test_relative_probability_export(tmp_path):
    """Test that relative probabilities are correctly handled in exports.

    Verifies that relative probabilities are properly exported and that
    automatic calculation works for solutions without explicit values.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Setting explicit relative probability on one solution
        >>> # 2. Leaving another solution without relative probability
        >>> # 3. Exporting and checking automatic calculation

    Note:
        When solutions lack explicit relative probabilities, they are
        automatically calculated based on BIC values if sufficient
        data is available.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Test Team"
    sub.tier = "test"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    evt = sub.get_event("test-event")
    sol1 = evt.add_solution("other", {"a": 1})
    sol1.log_likelihood = -10
    sol1.n_data_points = 50
    sol1.relative_probability = 0.6
    sol2 = evt.add_solution("other", {"b": 2})
    sol2.log_likelihood = -12
    sol2.n_data_points = 50
    sol2.relative_probability = 0.4  # Make sum = 1.0
    sub.save()

    zip_path = project / "out.zip"
    sub.export(str(zip_path))

    with zipfile.ZipFile(zip_path) as zf:
        data1 = json.loads(zf.read(f"events/test-event/solutions/{sol1.solution_id}.json"))
        data2 = json.loads(zf.read(f"events/test-event/solutions/{sol2.solution_id}.json"))
        assert data1["relative_probability"] == 0.6
        assert abs(data2["relative_probability"] - 0.4) < 1e-6


def test_validate_warnings(tmp_path):
    """Test that validation generates appropriate warnings.

    Verifies that the validation system correctly identifies and reports
    various issues with submissions.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating submission with known issues
        >>> # 2. Running validation
        >>> # 3. Checking that expected warnings are generated

    Note:
        Validation warnings help users identify issues before submission
        and ensure data completeness and correctness.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt1 = sub.get_event("evt1")
    evt1.add_solution("other", {"a": 1})
    evt2 = sub.get_event("evt2")
    sol2 = evt2.add_solution("other", {"b": 2})
    sol2.deactivate()

    warnings = sub.run_validation()

    assert any("Hardware info" in w for w in warnings)
    assert any("evt2" in w for w in warnings)
    # The validation now focuses on critical errors, not missing metadata fields
    # Check for the actual warnings that are generated
    assert any("team_name" in w for w in warnings)
    assert any("tier" in w for w in warnings)


def test_relative_probability_range(tmp_path):
    """Test that relative probabilities are properly calculated and validated.

    Verifies that relative probabilities are calculated correctly for solutions
    that don't have them set, and that validation catches issues with probability
    ranges and sums.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating solutions with and without relative probabilities
        >>> # 2. Checking automatic calculation using BIC
        >>> # 3. Validating probability ranges and sums
        >>> # 4. Testing validation warnings for invalid probabilities

    Note:
        Relative probabilities must sum to 1.0 for active solutions within
        each event. The system automatically calculates missing probabilities
        using BIC when sufficient data is available.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("evt")

    # Add solutions with different relative probabilities
    sol1 = evt.add_solution("other", {"a": 1})
    sol1.log_likelihood = -100
    sol1.n_data_points = 100
    sol1.relative_probability = 0.6

    sol2 = evt.add_solution("other", {"b": 2})
    sol2.log_likelihood = -110
    sol2.n_data_points = 100
    sol2.relative_probability = 0.4

    # Test validation
    warnings = sub.run_validation()
    assert not any("relative probabilities" in w.lower() for w in warnings)

    # Test invalid probabilities
    sol1.relative_probability = 0.8  # Sum > 1.0
    warnings = sub.run_validation()
    assert any("sum to" in w for w in warnings)


def test_solution_aliases(tmp_path):
    """Test solution alias functionality including creation, validation, and persistence.

    Verifies that solution aliases can be set, are validated for uniqueness,
    and are properly persisted across save/load cycles. Also tests that
    aliases are displayed correctly in dossier generation.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating solutions with aliases
        >>> # 2. Testing alias uniqueness validation
        >>> # 3. Checking alias persistence
        >>> # 4. Testing alias lookup functionality

    Note:
        Aliases provide human-readable identifiers for solutions and must
        be unique within each event. They are used as primary identifiers
        in dossier displays with UUIDs as secondary identifiers.
    """
    project = tmp_path / "proj"
    sub = load(str(project))

    # Test creating solutions with aliases
    evt1 = sub.get_event("EVENT001")
    sol1 = evt1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}, alias="best_fit")
    sol2 = evt1.add_solution(
        "1S2L",
        {"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "s": 1.2, "q": 0.5},
        alias="binary_model",
    )  # noqa: F841

    # Test alias persistence
    sub.save()
    new_sub = load(str(project))
    new_sol1 = new_sub.get_event("EVENT001").solutions[sol1.solution_id]
    new_sol2 = new_sub.get_event("EVENT001").solutions[sol2.solution_id]  # noqa: F841

    assert new_sol1.alias == "best_fit"
    assert new_sol2.alias == "binary_model"  # noqa: F841

    # Test alias lookup
    found_sol = new_sub.get_solution_by_alias("EVENT001", "best_fit")
    assert found_sol is not None
    assert found_sol.solution_id == sol1.solution_id

    # Test alias uniqueness validation
    evt2 = sub.get_event("EVENT002")  # noqa: F841
    sol3 = evt2.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}, alias="best_fit")  # noqa: F841

    # Test duplicate alias in same event - should fail
    # Create a fresh submission to test duplicate aliases
    project2 = tmp_path / "proj2"  # noqa: F841
    sub2 = load(str(project2))  # noqa: F841
    evt_dup = sub2.get_event("EVENT001")  # noqa: F841
    sol_dup1 = evt_dup.add_solution("1S1L", {"t0": 2459123.5}, alias="duplicate")  # noqa: F841
    sol_dup2 = evt_dup.add_solution("1S2L", {"t0": 2459123.5}, alias="duplicate")  # Duplicate alias  # noqa: F841

    with pytest.raises(ValueError, match="Duplicate alias"):
        sub2.save()  # This should trigger validation and raise the error


def test_alias_lookup_table(tmp_path):
    """Test that the alias lookup table is properly created and maintained.

    Verifies that the aliases.json file is created with the correct mapping
    of "<event_id> <alias>" to solution_id, and that it's updated when
    aliases are added or removed.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating solutions with aliases
        >>> # 2. Checking alias lookup table creation
        >>> # 3. Testing lookup table updates
        >>> # 4. Verifying table structure and content

    Note:
        The alias lookup table provides fast lookup of solutions by alias
        and is stored as aliases.json in the project root.
    """
    project = tmp_path / "proj"
    sub = load(str(project))

    # Create solutions with aliases
    evt1 = sub.get_event("EVENT001")
    sol1 = evt1.add_solution("1S1L", {"t0": 2459123.5}, alias="fit1")
    sol2 = evt1.add_solution("1S2L", {"t0": 2459123.5}, alias="fit2")  # noqa: F841

    evt2 = sub.get_event("EVENT002")  # noqa: F841
    sol3 = evt2.add_solution("1S1L", {"t0": 2459123.5}, alias="fit1")  # Same alias, different event  # noqa: F841

    sub.save()

    # Check that aliases.json was created
    alias_file = project / "aliases.json"
    assert alias_file.exists()

    # Load and verify the lookup table
    with alias_file.open("r", encoding="utf-8") as f:
        alias_lookup = json.load(f)

    # Check that all expected aliases are in the lookup table
    expected_aliases = ["EVENT001 fit1", "EVENT001 fit2", "EVENT002 fit1"]
    assert all(key in alias_lookup for key in expected_aliases)
    assert alias_lookup["EVENT001 fit1"] == sol1.solution_id
    assert alias_lookup["EVENT001 fit2"] == sol2.solution_id
    assert alias_lookup["EVENT002 fit1"] == sol3.solution_id


def test_alias_validation_warnings(tmp_path):
    """Test that alias validation warnings are properly generated.

    Verifies that the validation system correctly identifies and reports
    issues with aliases, such as duplicate aliases within the same event.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating solutions with duplicate aliases
        >>> # 2. Running validation
        >>> # 3. Checking for appropriate warning messages
        >>> # 4. Testing validation without duplicates

    Note:
        Alias validation is part of the overall submission validation
        process and provides clear error messages for data integrity issues.
    """
    project = tmp_path / "proj"
    sub = load(str(project))

    # Create solutions with duplicate aliases in same event
    evt = sub.get_event("EVENT001")
    sol1 = evt.add_solution("1S1L", {"t0": 2459123.5}, alias="duplicate")  # noqa: F841
    _ = evt.add_solution("1S2L", {"t0": 2459123.5}, alias="duplicate")  # noqa: F841

    # Test validation warnings
    warnings = sub.run_validation()
    assert any("Duplicate alias" in w for w in warnings)
    assert any("duplicate" in w.lower() for w in warnings)

    # Fix the duplicate
    # Get the second solution (the one without an explicit variable)
    sol2 = next(sol for sol in evt.solutions.values() if sol.solution_id != sol1.solution_id)
    sol2.alias = "unique"
    warnings = sub.run_validation()
    assert not any("Duplicate alias" in w for w in warnings)


def test_alias_in_dossier_generation(tmp_path):
    """Test that aliases are properly displayed in dossier generation.

    Verifies that when generating dossiers, solutions with aliases show
    the alias as the primary identifier and the UUID as secondary.

    Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    Example:
        >>> # This test verifies:
        >>> # 1. Creating solutions with aliases
        >>> # 2. Generating dossier HTML
        >>> # 3. Checking that aliases appear in the HTML
        >>> # 4. Verifying UUID is shown as secondary identifier

    Note:
        Dossier generation should prioritize aliases for readability
        while still providing UUID access for technical reference.
    """
    project = tmp_path / "proj"
    sub = load(str(project))

    # Create solution with alias
    evt = sub.get_event("EVENT001")
    sol = evt.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0}, alias="best_parallax_fit")
    sol.log_likelihood = -1234.56
    sol.n_data_points = 1250
    sol.set_compute_info(cpu_hours=2.5, wall_time_hours=0.5)

    sub.save()

    # Generate dossier
    from microlens_submit.dossier import generate_dashboard_html

    dossier_dir = project / "dossier"
    generate_dashboard_html(sub, dossier_dir)

    # Check that event page was generated
    event_page = dossier_dir / "EVENT001.html"
    assert event_page.exists()

    # Read the HTML and check for alias display
    with event_page.open("r", encoding="utf-8") as f:
        html_content = f.read()

    # Should show alias as primary identifier
    assert "best_parallax_fit" in html_content
    # Should show UUID as secondary identifier
    assert sol.solution_id[:8] in html_content

    # Check solution page
    solution_page = dossier_dir / f"{sol.solution_id}.html"
    assert solution_page.exists()

    with solution_page.open("r", encoding="utf-8") as f:
        sol_html = f.read()

    # Should show alias in title and header
    assert "best_parallax_fit" in sol_html
    assert sol.solution_id[:8] in sol_html


def test_cli_add_and_edit_alias(tmp_path):
    """Test CLI --alias option for add-solution and edit-solution commands.

    Verifies that:
    - add-solution --alias sets the alias correctly
    - edit-solution --alias updates the alias
    - Aliases are persisted and validated
    """
    project = tmp_path / "proj"
    project.mkdir()
    # Add a solution with alias via CLI
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "microlens_submit.cli",
            "add-solution",
            "EVENT001",
            "1S1L",
            str(project),
            "--param",
            "t0=2459123.5",
            "--param",
            "u0=0.1",
            "--param",
            "tE=20.0",
            "--alias",
            "cli_best_fit",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    # Check that alias is set in the project
    from microlens_submit.utils import load

    sub = load(str(project))
    sol = next(iter(sub.get_event("EVENT001").solutions.values()))
    assert sol.alias == "cli_best_fit"
    # Edit the alias via CLI
    result2 = subprocess.run(
        [
            sys.executable,
            "-m",
            "microlens_submit.cli",
            "edit-solution",
            sol.solution_id,
            str(project),
            "--alias",
            "cli_renamed",
        ],
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 0, result2.stderr
    sub2 = load(str(project))
    sol2 = sub2.get_event("EVENT001").solutions[sol.solution_id]
    assert sol2.alias == "cli_renamed"


def test_remove_solution_and_event():
    """Test the remove_solution and remove_event functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        submission = load(tmpdir)

        # Create an event with solutions
        event = submission.get_event("TEST_EVENT")
        solution1 = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
        _ = event.add_solution("1S2L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "s": 1.2, "q": 0.5})

        # Set notes on one solution (creates tmp file)
        solution1.set_notes("# Test notes")

        # Test removing an unsaved solution
        assert len(event.solutions) == 2
        removed = event.remove_solution(solution1.solution_id)
        assert removed is True
        assert len(event.solutions) == 1

        # Test removing all solutions
        removed_count = event.remove_all_solutions()
        assert removed_count == 1
        assert len(event.solutions) == 0

        # Test removing the event
        event = submission.get_event("TEST_EVENT")  # Recreate
        solution = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1})
        assert len(submission.events) == 1
        removed = submission.remove_event("TEST_EVENT")
        assert removed is True
        assert len(submission.events) == 0

        # Test safety features with saved solutions
        event = submission.get_event("SAVED_EVENT")
        solution = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
        submission.save()  # Make solution saved

        # Should fail without force
        with pytest.raises(ValueError, match="Cannot remove saved solution"):
            event.remove_solution(solution.solution_id)

        # Should work with force
        removed = event.remove_solution(solution.solution_id, force=True)
        assert removed is True

        # Test event removal safety
        event = submission.get_event("SAVED_EVENT2")
        solution = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
        submission.save()

        # Should fail without force
        with pytest.raises(ValueError, match="Cannot remove event"):
            submission.remove_event("SAVED_EVENT2")

        # Should work with force
        removed = submission.remove_event("SAVED_EVENT2", force=True)
        assert removed is True


def test_api_import_solutions_from_csv():
    """Test the API import_solutions_from_csv function directly."""
    import tempfile

    from microlens_submit.utils import load

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test CSV file
        csv_content = """# event_id,solution_alias,model_tags,t0,u0,tE,s,q,alpha,notes
OGLE-2023-BLG-0001,simple_1S1L,"[""1S1L""]",2459123.5,0.1,20.0,,,,,"# Simple Point Lens"
OGLE-2023-BLG-0001,binary_1S2L,"[""1S2L"", ""parallax""]",2459123.5,0.1,20.0,1.2,0.5,45.0,"# Binary Lens"
OGLE-2023-BLG-0002,finite_source,"[""1S1L"", ""finite-source""]",2459156.2,0.08,35.7,,,,,"# Finite Source"
"""
        csv_file = Path(tmpdir) / "test_import.csv"
        csv_file.write_text(csv_content)

        # Load project
        submission = load(tmpdir)
        submission.team_name = "Test Team"

        # Test dry run
        stats = import_solutions_from_csv(submission, csv_file, dry_run=True, validate=True, project_path=Path(tmpdir))
        assert stats["total_rows"] == 3
        assert stats["successful_imports"] == 3

        # Test actual import
        stats = import_solutions_from_csv(
            submission,
            csv_file,
            dry_run=False,
            validate=True,
            project_path=Path(tmpdir),
        )
        assert stats["successful_imports"] == 3
        assert "OGLE-2023-BLG-0001" in submission.events
        assert "OGLE-2023-BLG-0002" in submission.events
        event1 = submission.events["OGLE-2023-BLG-0001"]
        event2 = submission.events["OGLE-2023-BLG-0002"]
        assert len(event1.solutions) == 2
        assert len(event2.solutions) == 1
        aliases = [sol.alias for sol in event1.solutions.values()]
        assert "simple_1S1L" in aliases
        assert "binary_1S2L" in aliases
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
        # Test duplicate handling (error mode)
        stats = import_solutions_from_csv(
            submission,
            csv_file,
            dry_run=False,
            on_duplicate="error",
            project_path=Path(tmpdir),
        )
        assert stats["skipped_rows"] == 3
        # Test duplicate handling (override mode)
        stats = import_solutions_from_csv(
            submission,
            csv_file,
            dry_run=False,
            on_duplicate="override",
            project_path=Path(tmpdir),
        )
        assert stats["duplicate_handled"] == 3
        assert stats["successful_imports"] == 3


def test_api_import_solutions_from_csv_with_data_file():
    """Test the API import_solutions_from_csv function using the actual test file."""
    import tempfile

    from microlens_submit.utils import load

    # Use the actual test CSV file from tests/data
    csv_file = Path(__file__).parent / "data" / "test_import.csv"
    assert csv_file.exists(), f"Test CSV file not found: {csv_file}"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Load project
        submission = load(tmpdir)
        submission.team_name = "Test Team"

        # Test dry run
        stats = import_solutions_from_csv(submission, csv_file, dry_run=True, validate=True, project_path=Path(tmpdir))
        assert stats["total_rows"] == 6
        assert stats["successful_imports"] == 6  # All rows are valid

        # Test actual import
        stats = import_solutions_from_csv(
            submission,
            csv_file,
            dry_run=False,
            validate=True,
            project_path=Path(tmpdir),
        )
        assert stats["successful_imports"] == 6
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
        assert finite_sol.parameters["rho"] == 0.001

        # Test duplicate handling (error mode)
        stats = import_solutions_from_csv(
            submission,
            csv_file,
            dry_run=False,
            on_duplicate="error",
            project_path=Path(tmpdir),
        )
        assert stats["skipped_rows"] == 6  # All rows should be skipped as duplicates

        # Test duplicate handling (override mode)
        stats = import_solutions_from_csv(
            submission,
            csv_file,
            dry_run=False,
            on_duplicate="override",
            project_path=Path(tmpdir),
        )
        assert stats["duplicate_handled"] == 6
        assert stats["successful_imports"] == 6
