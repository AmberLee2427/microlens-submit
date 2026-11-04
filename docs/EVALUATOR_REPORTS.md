# Evaluator Reports

This workflow generates the evaluator dossiers and cohort-level reports for the RMDC26 beginner and experienced cohorts.

## Required Layout

Keep the submission cohorts and shared evaluator inputs under one `rmdc26_submissions` directory:

```text
rmdc26_submissions/
├── beginner/
│   ├── Team 01/
│   └── Team 02/
├── experienced/
│   ├── Team 01/
│   └── Team 02/
└── evaluator_data/
    ├── beginner/
    │   ├── RMDC26_Beginner_Tier.parquet
    │   ├── RMDC26_Events.out.hdf5
    │   ├── RMDC26_beginner_tier_w_id.txt
    │   ├── beginner_tier_predictions.csv       # optional
    │   └── Original Lightcurves/
    └── experienced/
        ├── RMDC26_Experienced_Tier.parquet
        ├── RMDC26_Experienced_Data_name_manifest.csv
        ├── RMDC26_Experienced_Data_out.hdf
        ├── experienced_tier_predictions.csv    # optional
        └── selected_lc/
```

The `Original Lightcurves/` and `selected_lc/` directories are needed for truth lightcurve overlays. The experienced HDF file may also be named `RMDC26_Experienced_Data_out.hdf5`; both names are supported.

The evaluator data is intentionally kept outside Git because the parquet and lightcurve files are large and contain challenge data. When transferring this work, copy the complete `rmdc26_submissions` directory as a separate data artifact alongside the repository checkout.

## Environment

From the repository checkout, install the package into the evaluator environment:

```bash
/Users/paterson.35/anaconda3/envs/bulge_env/bin/pip install -e .
```

The commands below prepend the environment to `PATH` so the CLI is found by subprocesses and shell scripts:

```bash
export PATH=/Users/paterson.35/anaconda3/envs/bulge_env/bin:$PATH
```

If the checkout or environment is on another machine, replace these absolute paths with that machine's Python environment paths.

## Generate Both Cohorts

The `evaluate-cohort` command infers the tier from `submission.json` and automatically looks for truth data at `<cohort-parent>/evaluator_data/<tier>`.

```bash
microlens-submit evaluate-cohort /Users/paterson.35/Documents/rmdc26_submissions/beginner
microlens-submit evaluate-cohort /Users/paterson.35/Documents/rmdc26_submissions/experienced
```

The default run reuses cached shared lightcurves and event comparison metrics and does not refit every active solution. This keeps the report-generation pass practical for the experienced cohort. To regenerate truth lightcurve metrics, add `--refresh-metrics`. To generate missing MulensModel fit and lens-plane plots as well, add `--generate-solution-plots`; this can take substantially longer.

To use an explicit data path, which is useful if the standard layout is not used:

```bash
microlens-submit evaluate-cohort \
  /Users/paterson.35/Documents/rmdc26_submissions/beginner \
  --data-dir /Users/paterson.35/Documents/rmdc26_submissions/evaluator_data/beginner

microlens-submit evaluate-cohort \
  /Users/paterson.35/Documents/rmdc26_submissions/experienced \
  --data-dir /Users/paterson.35/Documents/rmdc26_submissions/evaluator_data/experienced
```

## Generated Outputs

Each team directory receives or refreshes:

- `dossier/index.html`: evaluator dashboard.
- `dossier/full_dossier_report.html`: printable full report.
- `dossier/<event-id>.html`: event pages.
- `dossier/<solution-id>.html`: solution pages.
- `dossier/assets/`: comparison plots, metrics, and cohort rank assets.

Each cohort directory receives:

- `cohort_analysis/cohort_metrics.json`.
- `cohort_analysis/cohort_confusion_matrix.html`.
- `interactive_plots_<tier>/`: shared interactive lightcurves.

Open a dashboard locally with:

```bash
open /Users/paterson.35/Documents/rmdc26_submissions/beginner/Team\ 01/dossier/index.html
```

## Verification

The evaluator mode uses hidden truth data. For the experienced tier, event-type truth and consensus are intentionally represented as a submitted-event distribution; parameter, physical, and fit-quality comparisons remain visible.

Run the test suite after changing evaluator code:

```bash
PATH=/Users/paterson.35/anaconda3/envs/bulge_env/bin:$PATH \
/Users/paterson.35/anaconda3/envs/bulge_env/bin/pytest
```

Before handing off, confirm that both commands complete without `Invalid ... evaluator data` errors and that each team has a fresh `dossier/index.html` and `dossier/full_dossier_report.html`.
