from microlens_submit.validate_parameters import PARAMETER_PROPERTIES


def test_t0_uses_bjd_units():
    assert PARAMETER_PROPERTIES["t0"]["units"] == "BJD"
