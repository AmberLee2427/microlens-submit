#!/usr/bin/env python
"""Quick test of uncertainty metadata functionality."""

import shutil
import tempfile

from microlens_submit import Submission, load

# Create temp directory
tmpdir = tempfile.mkdtemp()
print(f"Testing in: {tmpdir}")

try:
    # Create submission
    sub = Submission()
    sub.project_path = tmpdir
    sub.team_name = "Test Team"
    sub.tier = "test"

    # Add event
    event = sub.get_event("rmdc26_2001")

    # Add solution with uncertainty metadata
    sol = event.add_solution(
        model_type="1S1L", parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0, "F0_S": 1000.0, "F0_B": 500.0}
    )

    # Set uncertainties and metadata
    sol.parameter_uncertainties = {"t0": 0.01, "u0": [0.005, 0.008], "tE": 0.5}  # asymmetric
    sol.uncertainty_method = "mcmc_posterior"
    sol.confidence_level = 0.68

    # Set physical parameters
    sol.physical_parameters = {"Mtot": 0.45, "D_L": 5.2, "D_S": 8.1}
    sol.physical_parameter_uncertainties = {"Mtot": 0.08, "D_L": 0.3, "D_S": 0.5}

    # Save and reload
    sub.save()
    sub2 = load(tmpdir)

    # Verify - get the first (and only) solution from the dict
    event2 = sub2.get_event("rmdc26_2001")
    sol2 = list(event2.solutions.values())[0]

    print("\n✓ All tests passed!")
    print("\nUncertainty metadata:")
    print(f"  uncertainty_method: {sol2.uncertainty_method}")
    print(f"  confidence_level: {sol2.confidence_level}")
    print("\nParameter uncertainties:")
    for key, val in sol2.parameter_uncertainties.items():
        print(f"  {key}: {val}")
    print("\nPhysical parameter uncertainties:")
    for key, val in sol2.physical_parameter_uncertainties.items():
        print(f"  {key}: {val}")

    assert sol2.uncertainty_method == "mcmc_posterior"
    assert sol2.confidence_level == 0.68
    assert sol2.physical_parameter_uncertainties["Mtot"] == 0.08

finally:
    shutil.rmtree(tmpdir)
    print(f"\nCleaned up: {tmpdir}")
