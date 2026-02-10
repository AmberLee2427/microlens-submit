from microlens_submit.validate_parameters import validate_parameter_uncertainties


def test_uncertainty_mixture_error_message():
    """Test that mixing physical parameter uncertainties into parameter_uncertainties gives a helpful error."""
    # Setup: parameters has t0, physical_parameters has Mtot
    parameters = {"t0": 100.0}
    physical_parameters = {"Mtot": 0.5}

    # User accidentally puts Mtot uncertainty in parameter_uncertainties
    uncertainties = {"t0": 1.0, "Mtot": 0.5}  # This causes "Uncertainty provided for unknown parameter" if not handled

    # Run validation
    messages = validate_parameter_uncertainties(parameters, uncertainties, physical_parameters)

    # Check if we get the BETTER error message
    expected_error = (
        "Physical parameter 'Mtot' found in parameter_uncertainties. Move it to physical_parameter_uncertainties."
    )
    assert expected_error in messages
