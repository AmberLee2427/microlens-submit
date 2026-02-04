"""Tests for BIC calculation with proper parameter counting."""

import math
import tempfile
from pathlib import Path

from microlens_submit.models.submission import Submission
from microlens_submit.validate_parameters import count_model_parameters


def test_count_model_parameters():
    """Test that count_model_parameters correctly excludes metadata and physical parameters."""
    # Model parameters only
    params_basic = {
        "t0": 2459123.5,
        "u0": 0.1,
        "tE": 20.0,
        "F0_S": 1000.0,
        "F0_B": 500.0,
    }
    assert count_model_parameters(params_basic) == 5

    # Add metadata (should not be counted)
    params_with_metadata = params_basic.copy()
    params_with_metadata["t_ref"] = 2459123.0
    params_with_metadata["limb_darkening_coeffs"] = {"I": [0.5, 0.2]}
    assert count_model_parameters(params_with_metadata) == 5  # Same as before

    # Add physical parameters (should not be counted)
    params_with_physical = params_basic.copy()
    params_with_physical["Mtot"] = 0.45
    params_with_physical["D_L"] = 5.2
    params_with_physical["D_S"] = 8.1
    params_with_physical["thetaE"] = 0.52
    assert count_model_parameters(params_with_physical) == 5  # Same as before

    # Add higher-order effect parameters (should be counted)
    params_with_parallax = params_basic.copy()
    params_with_parallax["piEN"] = 0.1
    params_with_parallax["piEE"] = 0.05
    assert count_model_parameters(params_with_parallax) == 7  # +2 for parallax

    # Add everything together
    params_complete = {
        # Core parameters (3)
        "t0": 2459123.5,
        "u0": 0.1,
        "tE": 20.0,
        # Binary parameters (3)
        "s": 1.2,
        "q": 0.5,
        "alpha": 45.0,
        # Higher-order parameters (2)
        "piEN": 0.1,
        "piEE": 0.05,
        # Flux parameters (2)
        "F0_S": 1000.0,
        "F0_B": 500.0,
        # Limb darkening parameter (1)
        "u_0": 0.6,
        # Metadata (NOT counted)
        "t_ref": 2459123.0,
        # Physical parameters (NOT counted)
        "Mtot": 0.45,
        "D_L": 5.2,
        "D_S": 8.1,
        "thetaE": 0.52,
    }
    # Should count: 3 core + 3 binary + 2 parallax + 2 flux + 1 LD = 11
    assert count_model_parameters(params_complete) == 11


def test_bic_calculation_excludes_metadata():
    """Test that BIC calculation uses count_model_parameters and excludes metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create submission
        sub = Submission()
        sub.project_path = tmpdir
        sub.team_name = "Test Team"
        sub.tier = "None"  # Skip event validation
        sub.repo_url = "https://github.com/test/test"
        sub.hardware_info = {"cpu_details": "Test CPU"}

        # Add event
        event = sub.get_event("TEST001")

        # Solution 1: Simple 1S1L (5 model parameters)
        sol1 = event.add_solution(
            model_type="1S1L",
            parameters={
                "t0": 2459123.5,
                "u0": 0.1,
                "tE": 20.0,
                "F0_S": 1000.0,
                "F0_B": 500.0,
            },
        )
        sol1.log_likelihood = -1234.56
        sol1.n_data_points = 1250
        sol1.bands = ["0"]

        # Solution 2: 1S2L with parallax + metadata (10 model parameters)
        sol2 = event.add_solution(
            model_type="1S2L",
            parameters={
                "t0": 2459123.5,
                "u0": 0.08,
                "tE": 22.1,
                "s": 1.15,
                "q": 0.001,
                "alpha": 45.2,
                "piEN": 0.1,
                "piEE": 0.05,
                "F0_S": 1000.0,
                "F0_B": 500.0,
                # Add metadata (should NOT be counted)
                "t_ref": 2459123.0,
                # Add physical parameters (should NOT be counted)
                "Mtot": 0.45,
                "D_L": 5.2,
                "D_S": 8.1,
            },
        )
        sol2.log_likelihood = -1189.34
        sol2.n_data_points = 1250
        sol2.higher_order_effects = ["parallax"]
        sol2.t_ref = 2459123.0
        sol2.bands = ["0"]

        # Verify parameter counts
        k1 = count_model_parameters(sol1.parameters)
        k2 = count_model_parameters(sol2.parameters)

        assert k1 == 5, f"Expected 5 model parameters for sol1, got {k1}"
        assert k2 == 10, f"Expected 10 model parameters for sol2, got {k2}"

        # Calculate expected BIC values
        n = 1250
        bic1_expected = k1 * math.log(n) - 2 * sol1.log_likelihood
        bic2_expected = k2 * math.log(n) - 2 * sol2.log_likelihood

        # Verify BIC calculation logic
        # sol2 has better log-likelihood despite more parameters
        # BIC penalizes complexity, but sol2 should still be favored
        assert sol2.log_likelihood > sol1.log_likelihood  # Less negative = better

        # The solution with better fit (after BIC penalty) should have lower BIC
        # BIC = k*ln(n) - 2*log_likelihood
        # Lower BIC = better model
        assert bic2_expected < bic1_expected

        # Verify export works without errors (rel prob calculated internally)
        sub.save()
        zip_path = Path(tmpdir) / "test_submission.zip"
        sub.export(str(zip_path))

        # Verify the zip was created
        assert Path(zip_path).exists()


def test_bic_with_physical_parameters_only():
    """Test that solutions with only physical parameters don't count them in BIC."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sub = Submission()
        sub.project_path = tmpdir
        sub.team_name = "Test Team"
        sub.tier = "None"  # Skip event validation
        sub.repo_url = "https://github.com/test/test"
        sub.hardware_info = {"cpu_details": "Test CPU"}

        event = sub.get_event("TEST002")

        # Solution with model parameters
        sol1 = event.add_solution(
            model_type="1S1L",
            parameters={
                "t0": 2459123.5,
                "u0": 0.1,
                "tE": 20.0,
                "F0_S": 1000.0,
                "F0_B": 500.0,
            },
        )
        sol1.log_likelihood = -1234.56
        sol1.n_data_points = 1250
        sol1.bands = ["0"]

        # Solution with model parameters + physical parameters
        sol2 = event.add_solution(
            model_type="1S1L",
            parameters={
                "t0": 2459125.0,
                "u0": 0.12,
                "tE": 21.0,
                "F0_S": 950.0,
                "F0_B": 520.0,
                # Physical parameters (NOT counted)
                "Mtot": 0.45,
                "M1": 0.45,
                "D_L": 5.2,
                "D_S": 8.1,
                "thetaE": 0.52,
                "piE": 0.11,
                "piE_N": 0.1,
                "piE_E": 0.05,
                "mu_rel": 5.3,
                "mu_rel_N": 4.2,
                "mu_rel_E": 3.1,
                "phi": 0.78,
            },
        )
        sol2.log_likelihood = -1235.12
        sol2.n_data_points = 1250
        sol2.bands = ["0"]

        # Both should have same parameter count for BIC
        k1 = count_model_parameters(sol1.parameters)
        k2 = count_model_parameters(sol2.parameters)

        assert k1 == 5
        assert k2 == 5  # Physical parameters not counted!

        # BIC values should be very close (same k, similar log_likelihood)
        bic1 = k1 * math.log(1250) - 2 * sol1.log_likelihood
        bic2 = k2 * math.log(1250) - 2 * sol2.log_likelihood

        # sol1 has slightly better log_likelihood, so should have slightly lower BIC
        assert bic1 < bic2


if __name__ == "__main__":
    test_count_model_parameters()
    test_bic_calculation_excludes_metadata()
    test_bic_with_physical_parameters_only()
    print("✅ All BIC calculation tests passed!")
