"""Automated test suite for solution plotting and MulensModel integration."""

import os
from pathlib import Path

import numpy as np
import pytest

from microlens_submit import load
from microlens_submit.dossier.plotting import (
    fit_best_model,
    generate_lightcurve_plot,
    load_event_dataset,
    map_parameters_to_mulens,
)


@pytest.fixture
def mock_1s1l_data(tmp_path) -> Path:
    """Fixture to generate a mock 1S1L point lens lightcurve dataset."""
    data_file = tmp_path / "mock_1s1l.dat"
    np.random.seed(42)
    times = np.linspace(2459100.0, 2459150.0, 100)
    t0, u0, tE = 2459125.0, 0.1, 20.0
    tau = (times - t0) / tE
    u = np.sqrt(tau**2 + u0**2)
    magnification = (u**2 + 2.0) / (u * np.sqrt(u**2 + 4.0))

    F_S, F_B = 1000.0, 100.0
    flux = F_S * magnification + F_B
    mags = 22.0 - 2.5 * np.log10(flux) + np.random.normal(0.0, 0.01, size=len(times))
    errors = np.ones_like(times) * 0.01

    with data_file.open("w", encoding="utf-8") as f:
        f.write("HJD mag mag_err band\n")
        for t, m, e in zip(times, mags, errors):
            f.write(f"{t:.5f} {m:.5f} {e:.5f} I\n")

    return data_file


@pytest.fixture
def mock_1s2l_data(tmp_path) -> Path:
    """Fixture to generate a mock 1S2L binary lens lightcurve dataset."""
    import MulensModel as mm
    data_file = tmp_path / "mock_1s2l.dat"

    np.random.seed(42)
    times = np.linspace(2459100.0, 2459150.0, 100)
    # True binary lens parameters: t0=2459125.0, u0=0.1, tE=20.0, s=1.2, q=0.01, alpha=90.0
    params_true = {
        't_0': 2459125.0, 'u_0': 0.1, 't_E': 20.0,
        's': 1.2, 'q': 0.01, 'alpha': 90.0
    }
    model_true = mm.Model(params_true)

    magnifications = model_true.get_magnification(times)
    flux = 1000.0 * magnifications + 100.0
    mags = 22.0 - 2.5 * np.log10(flux) + np.random.normal(0.0, 0.01, size=len(times))
    errors = np.ones_like(times) * 0.01

    with data_file.open("w", encoding="utf-8") as f:
        f.write("HJD mag mag_err band\n")
        for t, m, e in zip(times, mags, errors):
            f.write(f"{t:.5f} {m:.5f} {e:.5f} I\n")

    return data_file


@pytest.fixture
def mock_lightcurve_data(mock_1s1l_data) -> Path:
    """Fallback fixture mapping to 1S1L data."""
    return mock_1s1l_data


def test_load_event_dataset(mock_lightcurve_data):
    """Test that load_event_dataset robustly loads columns and groups by band."""
    datasets = load_event_dataset(mock_lightcurve_data, bands=["I"])
    assert len(datasets) == 1
    d = datasets[0]
    assert d.bandpass == "I"
    assert hasattr(d, "mag") and d.mag is not None
    assert len(d.time) == 100
    assert np.allclose(d.time[0], 2459100.0)


def test_map_parameters_to_mulens():
    """Test standard and custom mapping of parameters to MulensModel native parameters."""
    params = {
        "t0": 2459125.0,
        "u0": 0.1,
        "tE": 20.0,
        "s": 1.2,
        "q": 0.01,
        "alpha": 1.5708,  # ~90 degrees in radians
        "piEN": 0.1,
        "piEE": 0.05,
        "dsdt": 0.2,
        "dadt": 0.1,
    }

    # Test standard radian mapping
    mm_params = map_parameters_to_mulens(params, t_ref=2459100.0, alpha_in_degrees=False)
    assert mm_params["t_0"] == 2459125.0
    assert mm_params["u_0"] == 0.1
    assert mm_params["t_E"] == 20.0
    assert mm_params["s"] == 1.2
    assert mm_params["q"] == 0.01
    assert np.allclose(mm_params["alpha"], 90.0, atol=1e-2)
    assert mm_params["pi_E_N"] == 0.1
    assert mm_params["pi_E_E"] == 0.05
    assert mm_params["t_0_par"] == 2459100.0
    assert mm_params["d_s_dt"] == 0.2
    assert mm_params["d_alpha_dt"] == 0.1
    assert mm_params["t_0_kep"] == 2459100.0

    # Test sign inversion of u0 and degrees mapping
    mm_params_neg = map_parameters_to_mulens(params, neg_u0=True, alpha_in_degrees=True)
    assert mm_params_neg["u_0"] == -0.1
    assert mm_params_neg["alpha"] == 1.5708


def test_fit_best_model_optimization(mock_lightcurve_data):
    """Test optimization over alpha and u0 sign conventions to find lowest chi2."""
    datasets = load_event_dataset(mock_lightcurve_data, bands=["I"])

    # Case 1: Parameters specified in degrees (standard)
    params_deg = {
        "t0": 2459125.0,
        "u0": 0.1,
        "tE": 20.0,
    }
    event, chi2 = fit_best_model(datasets, params_deg, model_type="1S1L")
    assert chi2 < 200.0  # Chi2 should be small for the correct fit
    assert np.allclose(abs(event.model.parameters.u_0), 0.1)

    # Case 2: Inverted u0 sign convention
    params_inverted = {
        "t0": 2459125.0,
        "u0": -0.1,
        "tE": 20.0,
    }
    event, chi2 = fit_best_model(datasets, params_inverted, model_type="1S1L")
    assert chi2 < 200.0  # Optimizer should detect neg_u0 option and fit correctly
    assert np.allclose(abs(event.model.parameters.u_0), 0.1)


def test_fit_best_model_alpha_gulls_convention(mock_1s2l_data):
    """Test that alpha with 180 degrees shift (Gulls vs Mulens) is optimized properly."""
    datasets = load_event_dataset(mock_1s2l_data, bands=["I"])

    # Fit binary lens model with offset alpha (true alpha = 90 deg / 1.5708 rad)
    # Suppose fitting code used Gulls definition which shifted alpha by 180 deg (270 deg)
    params_gulls = {
        "t0": 2459125.0,
        "u0": 0.1,
        "tE": 20.0,
        "s": 1.2,
        "q": 0.01,
        "alpha": 4.7123,  # 270 degrees in radians (Gulls convention: rotated by 180 deg)
    }
    event, chi2 = fit_best_model(datasets, params_gulls, model_type="1S2L")
    assert chi2 < 3000.0
    # The optimized alpha in degrees should be one of the tried alpha candidates (rotated or standard)
    assert np.allclose(event.model.parameters.alpha % 180.0, 90.0, atol=5.0)


def test_generate_lightcurve_plot(tmp_path, mock_lightcurve_data):
    """Test generating and saving a beautiful two-panel plot of lightcurve fit and residuals."""
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("EVENT001")
    sol = evt.add_solution(
        model_type="1S1L",
        parameters={"t0": 2459125.0, "u0": 0.1, "tE": 20.0},
        alias="best_fit",
        bands=["I"],
    )

    plot_output = tmp_path / "test_lc_plot.png"
    chi2 = generate_lightcurve_plot(
        solution=sol,
        event=evt,
        data_path=mock_lightcurve_data,
        output_path=plot_output,
    )

    assert plot_output.exists()
    assert os.path.getsize(plot_output) > 0
    assert chi2 < 200.0


def test_cli_plot_solution_command(tmp_path, mock_lightcurve_data):
    """Test CLI plot-solution command execution and project updates."""
    # Setup test project
    project = tmp_path / "proj"
    sub = load(str(project))
    sub.team_name = "Space Poachers"
    sub.tier = "test"

    evt = sub.get_event("EVENT001")
    sol = evt.add_solution(
        model_type="1S1L",
        parameters={"t0": 2459125.0, "u0": 0.1, "tE": 20.0},
        alias="prelim_fit",
        bands=["I"],
    )
    sub.save()

    # Run the CLI plot-solution command using Typer runner
    from typer.testing import CliRunner
    from microlens_submit.cli.main import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "plot-solution",
            "prelim_fit",
            "--data",
            str(mock_lightcurve_data),
            "--project",
            str(project),
        ],
    )

    # Assert successful CLI execution
    assert result.exit_code == 0
    assert "Plot successfully generated" in result.output
    assert "Solution updated and saved on disk" in result.output

    # Verify that the solution got updated in the project
    new_sub = load(str(project))
    new_sol = new_sub.get_event("EVENT001").solutions[sol.solution_id]
    assert new_sol.lightcurve_plot_path is not None
    assert "lightcurve.html" in new_sol.lightcurve_plot_path

    # Verify that the physical file actually exists in the solution dir
    assert (project / new_sol.lightcurve_plot_path).exists()
    assert (project / new_sol.lightcurve_plot_path).stat().st_size > 0


@pytest.fixture
def mock_flux_data(tmp_path) -> Path:
    """Fixture to generate a mock 1S1L point lens lightcurve dataset in flux format."""
    data_file = tmp_path / "mock_flux_1s1l.dat"
    np.random.seed(42)
    times = np.linspace(2459100.0, 2459150.0, 100)
    t0, u0, tE = 2459125.0, 0.1, 20.0
    tau = (times - t0) / tE
    u = np.sqrt(tau**2 + u0**2)
    magnification = (u**2 + 2.0) / (u * np.sqrt(u**2 + 4.0))

    F_S, F_B = 1000.0, 100.0
    flux = F_S * magnification + F_B + np.random.normal(0.0, 10.0, size=len(times))
    errors = np.ones_like(times) * 10.0

    with data_file.open("w", encoding="utf-8") as f:
        f.write("HJD flux flux_err band\n")
        for t, fl, e in zip(times, flux, errors):
            f.write(f"{t:.5f} {fl:.5f} {e:.5f} I\n")

    return data_file


def test_generate_lightcurve_plot_flux(tmp_path, mock_flux_data):
    """Test generating a lightcurve plot with a flux-formatted dataset.

    Verifies that the y-axis label is 'Flux' and the data points are plotted as fluxes.
    """
    project = tmp_path / "proj"
    sub = load(str(project))
    evt = sub.get_event("EVENT001")
    sol = evt.add_solution(
        model_type="1S1L",
        parameters={"t0": 2459125.0, "u0": 0.1, "tE": 20.0},
        alias="flux_fit",
        bands=["I"],
    )

    plot_output = tmp_path / "test_lc_plot_flux.html"
    chi2 = generate_lightcurve_plot(
        solution=sol,
        event=evt,
        data_path=mock_flux_data,
        output_path=plot_output,
    )

    assert plot_output.exists()
    assert os.path.getsize(plot_output) > 0
    assert chi2 < 200.0

    # Read HTML content and verify it contains "Flux" and not magnitude formulas for plot coordinates
    content = plot_output.read_text(encoding="utf-8")
    assert "Flux" in content
    assert "residuals" in content.lower()


def test_fit_best_model_with_provided_fluxes(mock_lightcurve_data):
    """Test that fit_best_model uses provided solution fluxes without any actual fitting."""
    datasets = load_event_dataset(mock_lightcurve_data, bands=["I"])

    # Custom, slightly non-optimal fluxes to prove they are used exactly as-is
    params = {
        "t0": 2459125.0,
        "u0": 0.1,
        "tE": 20.0,
        "FI_S": 1050.0,
        "FI_B": 80.0,
    }

    event, chi2 = fit_best_model(datasets, params, model_type="1S1L")
    assert chi2 is not None
    # Verify the fluxes in the event are exactly the locked ones
    d = datasets[0]
    F_S_val, F_B = event.get_flux_for_dataset(d)
    assert np.allclose(F_S_val, 1050.0)
    assert np.allclose(F_B, 80.0)


def test_load_event_dataset_from_parquet(tmp_path):
    """Test loading an event dataset directly from a Parquet file."""
    import pandas as pd
    parquet_file = tmp_path / "mock_dataset.parquet"
    df = pd.DataFrame({
        'name': ['EVENT001', 'EVENT001', 'EVENT002'],
        'bjd': [2459100.0, 2459101.0, 2459102.0],
        'mag': [15.0, 15.1, 16.0],
        'mag_err': [0.01, 0.01, 0.02],
        'filt': ['I', 'I', 'I'],
    })
    df.to_parquet(parquet_file)

    datasets = load_event_dataset(parquet_file, bands=["I"], event_id="EVENT001")
    assert len(datasets) == 1
    d = datasets[0]
    assert d.bandpass == "I"
    assert len(d.time) == 2
    assert np.allclose(d.time, [2459100.0, 2459101.0])
    assert np.allclose(d.mag, [15.0, 15.1])
