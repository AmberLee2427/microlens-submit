from microlens_submit.validate_parameters import validate_physical_parameters


def test_mass_consistency():
    # Valid case
    params = {"M1": 0.5, "M2": 0.3, "Mtot": 0.8}
    assert not validate_physical_parameters(params)

    # Invalid case
    params = {"M1": 0.5, "M2": 0.3, "Mtot": 1.0}
    msgs = validate_physical_parameters(params)
    assert len(msgs) == 1
    assert "Mtot (1.0) does not match" in msgs[0]


def test_vector_consistency():
    # Valid case (3-4-5 triangle)
    params = {"piE_N": 0.3, "piE_E": 0.4, "piE": 0.5}
    assert not validate_physical_parameters(params)

    # Invalid case
    params = {"piE_N": 0.3, "piE_E": 0.4, "piE": 0.6}
    msgs = validate_physical_parameters(params)
    assert len(msgs) == 1
    assert "piE magnitude" in msgs[0]


def test_distance_checks():
    # Valid
    params = {"D_L": 4.0, "D_S": 8.0}
    assert not validate_physical_parameters(params)

    # D_L > D_S
    params = {"D_L": 9.0, "D_S": 8.0}
    msgs = validate_physical_parameters(params)
    assert len(msgs) == 1
    assert "Lens distance D_L" in msgs[0]

    # Large distance warning
    params = {"D_L": 30.0}
    msgs = validate_physical_parameters(params)
    assert len(msgs) == 1
    assert "unusually large" in msgs[0]


def test_mass_magnitude_warning():
    # Valid
    params = {"M1": 1.0}
    assert not validate_physical_parameters(params)

    # Too large
    params = {"M1": 100.0}
    msgs = validate_physical_parameters(params)
    assert len(msgs) == 1
    assert "very large" in msgs[0]
