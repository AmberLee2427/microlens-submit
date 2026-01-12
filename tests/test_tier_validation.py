"""Tests for tier validation functionality."""

import pydantic
import pytest

from microlens_submit import load
from microlens_submit.tier_validation import (
    get_available_tiers,
    get_event_validation_error,
    get_tier_description,
    get_tier_event_list,
    validate_event_id,
)


def test_get_available_tiers():
    """Test getting available tiers."""
    tiers = get_available_tiers()
    assert isinstance(tiers, list)
    assert len(tiers) > 0
    assert "beginner" in tiers
    assert "experienced" in tiers
    assert "test" in tiers
    assert "2018-test" in tiers
    assert "None" in tiers


def test_get_tier_description():
    """Test getting tier descriptions."""
    desc = get_tier_description("beginner")
    assert isinstance(desc, str)
    assert "Beginner challenge tier" in desc

    desc = get_tier_description("None")
    assert "No validation tier" in desc

    with pytest.raises(ValueError):
        get_tier_description("invalid-tier")


def test_get_tier_event_list():
    """Test getting event lists for tiers."""
    events = get_tier_event_list("beginner")
    assert isinstance(events, set)
    assert "rmdc26_0000" in events
    assert "rmdc26_0001" in events
    assert "rmdc26_0200" in events

    events = get_tier_event_list("None")
    assert isinstance(events, set)
    assert len(events) == 0

    with pytest.raises(ValueError):
        get_tier_event_list("invalid-tier")


def test_validate_event_id():
    """Test event ID validation."""
    # Test valid events
    assert validate_event_id("rmdc26_0000", "beginner")
    assert validate_event_id("rmdc26_0000", "experienced")
    assert validate_event_id("evt", "test")
    assert validate_event_id("2018-EVENT-001", "2018-test")
    assert validate_event_id("ulwdc1_293", "2018-test")

    # Test invalid events
    assert not validate_event_id("INVALID_EVENT", "beginner")
    assert not validate_event_id("rmdc26_2001", "experienced")

    # Test None tier and invalid tiers (should always return True)
    assert validate_event_id("ANY_EVENT", "None")
    assert validate_event_id("INVALID_EVENT", "None")
    assert validate_event_id("ANY_EVENT", "invalid-tier")
    assert validate_event_id("INVALID_EVENT", "invalid-tier")


def test_get_event_validation_error():
    """Test getting validation error messages."""
    # Test valid events (should return None)
    assert get_event_validation_error("rmdc26_0000", "beginner") is None
    assert get_event_validation_error("ANY_EVENT", "None") is None
    assert get_event_validation_error("ANY_EVENT", "invalid-tier") is None

    # Test invalid events
    error = get_event_validation_error("INVALID_EVENT", "beginner")
    assert isinstance(error, str)
    assert "INVALID_EVENT" in error
    assert "beginner" in error
    assert "Beginner challenge tier" in error
    assert "rmdc26_0000" in error  # Should list valid events

    error = get_event_validation_error("rmdc26_2001", "experienced")
    assert isinstance(error, str)
    assert "rmdc26_2001" in error
    assert "experienced" in error
    assert "Experienced challenge tier" in error


def test_tier_hierarchy():
    """Test that higher tiers include events from lower tiers."""
    standard_events = get_tier_event_list("beginner")
    advanced_events = get_tier_event_list("experienced")

    # Beginner events should be in experienced
    for event in standard_events:
        assert event in advanced_events

    # Experienced should have more events than beginner
    assert len(advanced_events) >= len(standard_events)


def test_test_tier_events():
    """Test that test tier has appropriate test events."""
    test_events = get_tier_event_list("test")
    assert "evt" in test_events
    assert "test-event" in test_events


def test_2018_test_tier_events():
    """Test that 2018-test tier has appropriate events."""
    events = get_tier_event_list("2018-test")
    assert "2018-EVENT-001" in events
    assert "2018-EVENT-002" in events


def test_submission_validation_with_invalid_events(tmp_path):
    """Test that submission validation detects invalid events for the tier."""
    project = tmp_path / "proj"
    sub = load(str(project))

    # Set tier to beginner
    sub.tier = "beginner"
    sub.team_name = "Test Team"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    # Add a valid event
    evt1 = sub.get_event("rmdc26_0000")
    evt1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Add an invalid event (not in beginner tier)
    evt2 = sub.get_event("rmdc26_9999")
    evt2.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Run validation - should catch the invalid event
    warnings = sub.run_validation()

    # Should have a warning about the invalid event
    invalid_event_warnings = [w for w in warnings if "rmdc26_9999" in w and "not valid for tier" in w]
    assert len(invalid_event_warnings) > 0, f"Expected validation warning for invalid event, got: {warnings}"

    # Should not have warnings about the valid event being invalid for tier
    # The warning message mentions rmdc26_0000 in the list of valid events, but rmdc26_0000 itself is not the
    # subject of the warning
    # So we should check that there are no warnings that start with "Event 'rmdc26_0000'"
    event001_as_subject_warnings = [w for w in warnings if w.startswith("Event 'rmdc26_0000'")]
    assert (
        len(event001_as_subject_warnings) == 0
    ), f"Should not have tier validation warning for valid event rmdc26_0000, got: {warnings}"


def test_submission_validation_with_valid_events(tmp_path):
    """Test that submission validation passes when all events are valid for the tier."""
    project = tmp_path / "proj"
    sub = load(str(project))

    # Set tier to beginner
    sub.tier = "beginner"
    sub.team_name = "Test Team"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    # Add only valid events for beginner tier
    evt1 = sub.get_event("rmdc26_0000")
    evt1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    evt2 = sub.get_event("rmdc26_0001")
    evt2.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    evt3 = sub.get_event("rmdc26_0002")
    evt3.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Run validation - should not have tier validation warnings
    warnings = sub.run_validation()

    # Should not have any tier validation warnings
    tier_validation_warnings = [w for w in warnings if "not valid for tier" in w]
    assert (
        len(tier_validation_warnings) == 0
    ), f"Should not have tier validation warnings for valid events, got: {warnings}"


def test_submission_validation_with_none_tier(tmp_path):
    """Test that submission validation skips event validation when tier is 'None'."""
    project = tmp_path / "proj"
    sub = load(str(project))

    # Set tier to None (should skip validation)
    sub.tier = "None"
    sub.team_name = "Test Team"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    # Add events that would be invalid for other tiers
    evt1 = sub.get_event("INVALID_EVENT_1")
    evt1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    evt2 = sub.get_event("INVALID_EVENT_2")
    evt2.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Run validation - should not have tier validation warnings
    warnings = sub.run_validation()

    # Should not have any tier validation warnings
    tier_validation_warnings = [w for w in warnings if "not valid for tier" in w]
    assert (
        len(tier_validation_warnings) == 0
    ), f"Should not have tier validation warnings for 'None' tier, got: {warnings}"


def test_submission_validation_with_invalid_tier(tmp_path):
    """Test that submission validation automatically changes invalid tier names to 'None'."""
    project = tmp_path / "proj"
    sub = load(str(project))

    # Set tier to an invalid value
    sub.tier = "invalid-tier"
    sub.team_name = "Test Team"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    # Add any events
    evt1 = sub.get_event("rmdc26_0000")
    evt1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Run validation - should change tier to "None" and warn about the change
    warnings = sub.run_validation()

    # Should have a warning about the invalid tier being changed
    invalid_tier_warnings = [w for w in warnings if "Invalid tier 'invalid-tier' changed to 'None'" in w]
    assert len(invalid_tier_warnings) > 0, f"Expected validation warning about tier change, got: {warnings}"

    # Should not have any event validation warnings since tier is now "None"
    event_validation_warnings = [w for w in warnings if "not valid for tier" in w]
    assert len(event_validation_warnings) == 0, f"Should skip event validation for 'None' tier, got: {warnings}"

    # The tier should have been changed to "None"
    assert sub.tier == "None"


def test_export_with_invalid_events_should_fail(tmp_path):
    """Test that export fails when there are invalid events for the tier."""
    project = tmp_path / "proj"
    sub = load(str(project))

    # Set tier to beginner
    sub.tier = "beginner"
    sub.team_name = "Test Team"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    # Add a valid event
    evt1 = sub.get_event("rmdc26_0000")
    evt1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Add an invalid event
    evt2 = sub.get_event("rmdc26_9999")
    evt2.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Save the submission first
    sub.save()

    # Try to export - should fail due to validation
    with pytest.raises(ValueError, match="not valid for tier"):
        sub.export("test_export.zip")


def test_save_with_invalid_events_should_warn(tmp_path):
    """Test that save warns when there are invalid events for the tier but still saves."""
    project = tmp_path / "proj"
    sub = load(str(project))

    # Set tier to beginner
    sub.tier = "beginner"
    sub.team_name = "Test Team"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    # Add a valid event
    evt1 = sub.get_event("rmdc26_0000")
    evt1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Add an invalid event
    evt2 = sub.get_event("rmdc26_9999")
    evt2.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Try to save - should warn but not fail due to validation
    # Capture the output to check for warnings
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        sub.save()

    output = f.getvalue()

    # Should have a warning about the invalid event
    assert "rmdc26_9999" in output
    assert "not valid for tier" in output
    assert "Save completed with validation warnings" in output


def test_export_with_valid_events_should_succeed(tmp_path):
    """Test that export succeeds when all events are valid for the tier."""
    project = tmp_path / "proj"
    sub = load(str(project))

    # Set tier to beginner
    sub.tier = "beginner"
    sub.team_name = "Test Team"
    sub.repo_url = "https://github.com/test/team"
    sub.hardware_info = {"cpu": "test"}

    # Add only valid events for beginner tier
    evt1 = sub.get_event("rmdc26_0000")
    evt1.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    evt2 = sub.get_event("rmdc26_0001")
    evt2.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})

    # Save the submission
    sub.save()

    # Export should succeed
    export_path = tmp_path / "test_export.zip"
    sub.export(str(export_path))

    # Verify the export file was created
    assert export_path.exists()


def test_pydantic_validation_at_creation():
    """Test that Pydantic validation warns about parameter issues at solution creation time."""
    import warnings

    from microlens_submit.models.solution import Solution

    # Test valid solution creation
    valid_solution = Solution(
        solution_id="test-123", model_type="1S1L", parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0}
    )
    assert valid_solution.model_type == "1S1L"
    assert valid_solution.parameters["t0"] == 2459123.5

    # Test 1: Missing required parameter - should warn but not error
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        solution_with_missing = Solution(
            solution_id="test-456", model_type="1S1L", parameters={"t0": 2459123.5, "u0": 0.1}  # Missing tE
        )
        # Should have a warning about missing parameters
        assert len(w) > 0
        assert any("Solution created with potential issues" in str(warning.message) for warning in w)
        assert any("Missing required parameters" in str(warning.message) for warning in w)
        # Verify the solution was still created
        assert solution_with_missing.model_type == "1S1L"

    # Test 2: Invalid parameter type - should warn but not error
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        solution_with_wrong_type = Solution(
            solution_id="test-789",
            model_type="1S1L",
            parameters={"t0": "not_a_number", "u0": 0.1, "tE": 20.0},  # t0 is string
        )
        # Should have a warning about invalid parameter
        assert len(w) > 0
        assert any("Solution created with potential issues" in str(warning.message) for warning in w)
        assert any("must be numeric" in str(warning.message) for warning in w)
        # Verify the solution was still created
        assert solution_with_wrong_type.model_type == "1S1L"

    # Test 3: Invalid parameter for model type (1S1L shouldn't have 's' parameter) - should warn
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        solution_with_invalid_param = Solution(
            solution_id="test-101",
            model_type="1S1L",
            parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "s": 1.2},  # 's' not valid for 1S1L
        )
        # Should have a warning about invalid parameter
        assert len(w) > 0
        assert any("Solution created with potential issues" in str(warning.message) for warning in w)
        assert any("Invalid parameter 's' for model type '1S1L'" in str(warning.message) for warning in w)
        # Verify the solution was still created
        assert solution_with_invalid_param.model_type == "1S1L"

    # Test 4: t_ref provided when not needed - should warn
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        solution_with_unneeded_tref = Solution(
            solution_id="test-102",
            model_type="1S1L",
            parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0},
            t_ref=2459123.0,  # Not needed for 1S1L with no effects
        )
        # Should have a warning about t_ref
        assert len(w) > 0
        assert any("Solution created with potential issues" in str(warning.message) for warning in w)
        assert any("t_ref provided but not required" in str(warning.message) for warning in w)
        # Verify the solution was still created
        assert solution_with_unneeded_tref.model_type == "1S1L"

    # Test 5: t_ref wrong type - should raise ValueError (basic type error)
    with pytest.raises(ValueError, match="t_ref must be numeric"):
        Solution(
            solution_id="test-103",
            model_type="1S1L",
            parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0},
            t_ref="not_a_number",
        )

    # Test 6: bands wrong type - should raise ValueError (basic type error)
    with pytest.raises(ValueError, match="bands must be a list"):
        Solution(
            solution_id="test-104",
            model_type="1S1L",
            parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0},
            bands="not_a_list",  # Should be a list
        )

    # Test 7: bands with non-string elements - should raise ValidationError (Pydantic type error)
    with pytest.raises(pydantic.ValidationError) as excinfo:
        Solution(
            solution_id="test-105",
            model_type="1S1L",
            parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0},
            bands=[123, "1"],  # First element should be string
        )
    assert "bands.0" in str(excinfo.value)
    assert "Input should be a valid string" in str(excinfo.value)

    # Test 8: Missing flux parameters for bands - should warn
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        solution_with_missing_flux = Solution(
            solution_id="test-106",
            model_type="1S1L",
            parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0},
            bands=["0", "1"],  # Need flux parameters for each band
        )
        # Should have a warning about missing flux parameters
        assert len(w) > 0
        assert any("Solution created with potential issues" in str(warning.message) for warning in w)
        assert any("Missing required flux parameters" in str(warning.message) for warning in w)
        # Verify the solution was still created
        assert solution_with_missing_flux.model_type == "1S1L"

    # Test 9: Valid solution with parallax (t_ref required and provided)
    valid_parallax_solution = Solution(
        solution_id="test-107",
        model_type="1S1L",
        parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "piEN": 0.1, "piEE": 0.05},
        higher_order_effects=["parallax"],
        t_ref=2459123.0,  # Required for parallax
    )
    assert valid_parallax_solution.higher_order_effects == ["parallax"]

    # Test 10: Parallax without t_ref (should warn)
    solution_without_tref = Solution(
        solution_id="test-108",
        model_type="1S1L",
        parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "piEN": 0.1, "piEE": 0.05},
        higher_order_effects=["parallax"],
        # Missing t_ref
    )
    # Should have a validation message about missing t_ref
    validation_messages = solution_without_tref.run_validation()
    assert len(validation_messages) > 0
    assert any("Reference time (t_ref) required for effect 'parallax'" in msg for msg in validation_messages)

    # Test 11: Valid 1S2L solution
    valid_binary_solution = Solution(
        solution_id="test-109",
        model_type="1S2L",
        parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "s": 1.2, "q": 0.5, "alpha": 45.0},
    )
    assert valid_binary_solution.model_type == "1S2L"

    # Test 12: 1S2L missing required parameters (should warn)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        solution_missing_binary_params = Solution(
            solution_id="test-110",
            model_type="1S2L",
            parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0},  # Missing s, q, alpha
        )
        # Should have a warning about missing parameters
        assert len(w) > 0
        assert any("Solution created with potential issues" in str(warning.message) for warning in w)
        assert any("Missing required parameters" in str(warning.message) for warning in w)
        # Verify the solution was still created
        assert solution_missing_binary_params.model_type == "1S2L"

    # Test 13: "other" model type allows unknown parameters
    other_solution = Solution(
        solution_id="test-111", model_type="other", parameters={"custom_param": "value", "another_param": 123.45}
    )
    assert other_solution.model_type == "other"

    # Test 14: "other" higher-order effect allows unknown parameters
    other_effect_solution = Solution(
        solution_id="test-112",
        model_type="1S1L",
        parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "custom_effect_param": 42.0},
        higher_order_effects=["other"],
    )
    assert "other" in other_effect_solution.higher_order_effects
