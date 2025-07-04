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
    >>> from microlens_submit.api import load
    >>> 
    >>> # Run a specific test
    >>> def test_basic_functionality(tmp_path):
    ...     project = tmp_path / "test_project"
    ...     sub = load(str(project))
    ...     sub.team_name = "Test Team"
    ...     sub.tier = "test"
    ...     sub.save()
    ...     
    ...     # Verify persistence
    ...     new_sub = load(str(project))
    ...     assert new_sub.team_name == "Test Team"
    ...     assert new_sub.tier == "test"

Note:
    All tests use pytest's tmp_path fixture for isolated testing.
    Tests verify both the API functionality and data persistence.
    The test suite ensures backward compatibility and data integrity.
"""

import zipfile
import json

from microlens_submit.api import load


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
        solution_files = [
            n for n in names if n.startswith("events/") and "solutions" in n
        ]
        assert "submission.json" in names
    assert solution_files == [
        f"events/test-event/solutions/{sol_active.solution_id}.json"
    ]


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
    evt = sub.get_event("event")
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
        base = f"events/event/solutions/{sol.solution_id}"
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
    evt = sub.get_event("evt")
    sol1 = evt.add_solution("other", {"a": 1})
    sol1.log_likelihood = -10
    sol1.n_data_points = 50
    sol1.relative_probability = 0.6
    sol2 = evt.add_solution("other", {"b": 2})
    sol2.log_likelihood = -12
    sol2.n_data_points = 50
    sub.save()

    zip_path = project / "out.zip"
    sub.export(str(zip_path))

    with zipfile.ZipFile(zip_path) as zf:
        data1 = json.loads(zf.read(f"events/evt/solutions/{sol1.solution_id}.json"))
        data2 = json.loads(zf.read(f"events/evt/solutions/{sol2.solution_id}.json"))
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

    warnings = sub.validate()

    assert any("Hardware info" in w for w in warnings)
    assert any("evt2" in w for w in warnings)
    assert any("log_likelihood" in w for w in warnings)
    assert any("lightcurve_plot_path" in w for w in warnings)
    assert any("lens_plane_plot_path" in w for w in warnings)


def test_relative_probability_range(tmp_path):
    """Test that relative probability validation works correctly.
    
    Verifies that the validation system correctly identifies relative
    probability values outside the valid range (0-1).
    
    Args:
        tmp_path: Pytest fixture providing a temporary directory path.
    
    Example:
        >>> # This test verifies:
        >>> # 1. Setting invalid relative probability (>1)
        >>> # 2. Running validation
        >>> # 3. Checking that appropriate warning is generated
    
    Note:
        Relative probabilities must be between 0 and 1, and the sum
        of all relative probabilities for an event should equal 1.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("evt")
    sol = evt.add_solution("other", {"a": 1})
    sol.relative_probability = 1.2

    warnings = sub.validate()

    assert any("between 0 and 1" in w for w in warnings)
