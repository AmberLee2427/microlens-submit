<p align="center">
  <a href="https://github.com/AmberLee2427/microlens-submit">
    <img src="./assets/rges-pit_logo.png" alt="logo" width="300"/>
  </a>
</p>

# <font face="Helvetica" size="7"> Microlensing Submission Format Manual </font>  

> **A Note from the Organizers:** We strongly recommend using the official `microlens-submit` tool for a validated, error-free experience. It handles all the tedious formatting and metadata generation for you.
> 
> However, if you insist on building your own submission package programmatically, this document provides the exact specification required. Proceed at your own risk.

## 1\. Directory Structure

A valid submission is a directory containing a `submission.json` file and an `events/` subdirectory.

```php-template
<submission_dir>/
├── submission.json
└── events/
    └── <event_id>/
        ├── event.json
        └── solutions/
            └── <solution_id>.json
```

## 2\. File Schemas

The following sections detail the required JSON structure for each file.

### `submission.json`

Global metadata for the entire submission.

|     Field     |  Type  | Required |              Description               |
|---------------|--------|----------|----------------------------------------|
|   `team_name`   | string |    No    |     Name of the participant team.      |
|     `tier`      | string |    No    |            Challenge tier.             |
| `hardware_info` |  dict  |    No    | Details about the compute environment. |

**Example:**

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

### `event.json`

Describes a single event.

|  Field   |  Type  | Required |           Description            |
|----------|--------|----------|----------------------------------|
| `event_id` | string |   Yes    | Unique identifier for the event. |

**Example:**

```json
{
  "event_id": "KMT-2025-BLG-001"
}
```

### `solution.json`

Represents a single model fit.

|          Field          |  Type   | Required |                              Description                               |
|-------------------------|---------|----------|------------------------------------------------------------------------|
|       `solution_id`       | string  |   Yes    |                  Unique identifier for the solution.                   |
|       `model_type`        | string  |   Yes    |                  Name of the model used for the fit.                   |
|       `parameters`        |  dict   |   Yes    |                    Dictionary of model parameters.                     |
|        `is_active`        |  bool   |    No    |    If `true`, this solution is included in exports. Defaults to `true`.    |
|      `compute_info`       |  dict   |    No    |             Recorded dependencies and timing information.              |
|     `posterior_path`      | string  |    No    |                Path to a stored posterior sample file.                 |
|          `notes`          | string  |    No    |                  Free-form notes about the solution.                   |
|     `used_astrometry`     |  bool   |    No    |         Indicates use of astrometric data. Defaults to `false`.          |
|    `used_postage_stamps`    |  bool   |    No    |       Indicates use of postage-stamp images. Defaults to `false`.        |
|   `limb_darkening_model`    | string  |    No    |                   Name of the limb-darkening model.                    |
|   `limb_darkening_coeffs`   |  dict   |    No    |               Coefficients for the limb-darkening model.               |
| `parameter_uncertainties` |  dict   |    No    |                  Uncertainties for fitted parameters.                  |
|   `physical_parameters`   |  dict   |    No    |               Physical parameters derived from the fit.                |
|     `log_likelihood`      |  float  |    No    |                   Log-likelihood value for the fit.                    |
|        `log_prior`        |  float  |    No    |                      Log-prior value for the fit.                      |
|       `n_data_points`       | integer |    No    |                 Number of data points used in the fit.                 |
|   `creation_timestamp`    | string  |    No    | ISO timestamp. If omitted, the validator will add a current timestamp. |

**Example:**

```json
{
  "solution_id": "123e4567-e89b-12d3-a456-426614174000",
  "model_type": "binary_lens",
  "parameters": {"t0": 555.5, "u0": 0.1, "tE": 25.0},
  "physical_parameters": {"M_L": 0.5, "D_L": 7.8},
  "log_likelihood": -1234.56,
  "is_active": true,
  "creation_timestamp": "2025-07-15T13:45:10Z"
}
```

## 3\. Validation

Before submitting, you **must** validate your manually created package using the provided `validate_submission.py` script. This is your only safety net.

Run the script from your terminal, passing the path to your submission directory:

```css
python validate_submission.py /path/to/your/submission_dir
```

The script will report "Submission is valid" on success or print detailed error messages if it finds any problems with your file structure or JSON formatting. Fix any reported errors before creating your final zip archive.
