# Microlensing Submission Format Manual

This document describes the required directory layout and JSON schemas for challenge submissions. All file formats mirror the Pydantic models used by the `microlens-submit` library.

```
<submission_dir>/
├── submission.json
└── events/
    └── <event_id>/
        ├── event.json
        └── solutions/
            └── <solution_id>.json
```

Each folder under `events/` corresponds to a single microlensing event. Solutions are stored as separate JSON files inside `solutions/`.

## `submission.json`
Global metadata for the entire submission.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `team_name` | string | No | Name of the participant team. |
| `tier` | string | No | Challenge tier. |
| `hardware_info` | dict | No | Details about the compute environment. |

Example:
```json
{
  "team_name": "Planet Pounders",
  "tier": "advanced",
  "hardware_info": {
    "cpu": "Intel i9",
    "ram_gb": 64
  }
}
```

## `event.json`
Describes a single event. Only the event identifier is stored; solutions are kept separately.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string | Yes | Unique identifier for the event. |

Example:
```json
{
  "event_id": "KMT-2025-BLG-001"
}
```

## `solution.json`
Represents a single model fit. Fields correspond to the `Solution` Pydantic model.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `solution_id` | string | Yes | Unique identifier for the solution. |
| `model_type` | string | Yes | Name of the model used for the fit. |
| `parameters` | dict | Yes | Dictionary of model parameters. |
| `is_active` | bool | No | Whether this solution is included in exports (defaults to `true`). |
| `compute_info` | dict | No | Recorded dependencies and timing information. |
| `posterior_path` | string | No | Path to a stored posterior sample file. |
| `notes` | string | No | Free-form notes about the solution. |
| `used_astrometry` | bool | No | Indicates use of astrometric data. |
| `used_postage_stamps` | bool | No | Indicates use of postage-stamp images. |
| `limb_darkening_model` | string | No | Name of the limb-darkening model. |
| `limb_darkening_coeffs` | dict | No | Coefficients for the limb-darkening model. |
| `parameter_uncertainties` | dict | No | Uncertainties for fitted parameters. |
| `physical_parameters` | dict | No | Physical parameters derived from the fit. |
| `log_likelihood` | float | No | Log-likelihood value for the fit. |
| `log_prior` | float | No | Log-prior value for the fit. |
| `n_data_points` | integer | No | Number of data points used in the fit. |
| `creation_timestamp` | string | No | ISO timestamp when the solution was created (defaults to now). |

Example:
```json
{
  "solution_id": "123e4567-e89b-12d3-a456-426614174000",
  "model_type": "binary_lens",
  "parameters": {"t0": 555.5, "u0": 0.1, "tE": 25.0},
  "physical_parameters": {"M_L": 0.5, "D_L": 7.8},
  "log_likelihood": -1234.56,
  "posterior_path": "posteriors/posterior_A.h5",
  "notes": "Binary model provides a much better fit.",
  "compute_info": {
    "cpu_hours": 15.5,
    "wall_time_hours": 2.1,
    "dependencies": [
      "numpy==1.21.2",
      "scipy==1.7.1",
      "emcee==3.1.0"
    ],
    "git_info": {
      "commit": "f4ac2a9f...e1",
      "branch": "feature/new-model",
      "is_dirty": true
    }
  },
  "is_active": true,
  "creation_timestamp": "2025-07-15T13:45:10Z"
}
```
