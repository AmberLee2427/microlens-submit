# Testing the Dossier Generation Feature

This directory contains a test script to demonstrate the new dossier generation feature and batch CSV import functionality in `microlens-submit` v0.14.0.

## Quick Test

To test the dossier generation feature:

```bash
# Make sure you have microlens-submit installed (version>=0.14.0)
pip install microlens-submit

# Run the test script (from project root)
python tests/test_dossier_generation.py

# Or run as a module
python -m tests.test_dossier_generation
```

## What the Test Does

The test script will:

1. **Create a test submission project** with team name "Test Team Alpha"
2. **Add sample solutions** for 3 different events with various model types:
   - EVENT001: 1S1L and 1S2L solutions with different relative probabilities
   - EVENT002: 1S2L solution with parallax effects
   - EVENT003: 2S1L solution (binary source)
3. **Demonstrate batch CSV import** using the comprehensive test data file:
   - Imports multiple solutions from `tests/data/test_import.csv`
   - Shows alias support and uniqueness validation
   - Demonstrates notes handling with literal newline conversion
   - Tests various parameter types and model configurations
4. **Validate the submission** to check for any issues
5. **Generate a dossier** using the new `generate-dossier` command
6. **Open the dashboard** in your default web browser

## Test Data File

The script uses `tests/data/test_import.csv` as a comprehensive example for batch import testing. This file includes:

- **Multiple model types**: 1S1L, 1S2L, 2S1L solutions
- **Solution aliases**: Human-readable identifiers like "Best_Fit", "Alternative_Model"
- **Rich notes**: Markdown-formatted notes with literal `\n` characters that get converted to actual newlines
- **Various parameters**: Different parameter combinations and uncertainties
- **Higher-order effects**: Parallax, finite-source, and other effects
- **Edge cases**: Solutions with missing optional fields, different data types

This file serves as both a test fixture and a template for users creating their own CSV imports.

## Expected Output

The script will create (in the project root):
- `test_submission_project/` - The submission project directory
- `test_dossier_output/` - The generated dossier with:
  - `index.html` - Main dashboard
  - `assets/` - Directory for images and other assets
  - `events/` - Directory for future event-specific pages

## Viewing the Dashboard

The generated `index.html` file is a **static HTML file** that you can open directly in any web browser. No web server is required because:

- Tailwind CSS is loaded from CDN
- All styling is self-contained
- No server-side processing is needed

## Features to Test

When you open the dashboard, you should see:

✅ **Header Section**
- RGES-PIT logo (if available)
- Team name and tier information

✅ **Submission Overview**
- Total events submitted (3+ imported events)
- Total active solutions (4+ imported solutions)
- Hardware information

✅ **Progress Tracking**
- Progress bar showing events processed
- Total CPU and wall time hours

✅ **Events Table**
- List of all events with active solution counts
- Model types for each event
- Links to event-specific pages (placeholders for now)

✅ **Solution Aliases**
- Human-readable solution identifiers displayed prominently
- UUID fallbacks for solutions without aliases

✅ **Parameter Distribution Placeholders**
- Placeholder plots for tE, u0, M_L, and D_L distributions
- Professional styling with custom color palette

✅ **Responsive Design**
- Works on desktop and mobile devices
- Modern, professional appearance

## Batch Import Features Demonstrated

The test script showcases several key batch import capabilities:

✅ **CSV Import Process**
- Dry-run validation before actual import
- Column mapping and parameter extraction
- Duplicate handling and validation

✅ **Solution Aliases**
- Human-readable identifiers for solutions
- Uniqueness validation within events
- Display in dossier generation

✅ **Notes Handling**
- Conversion of literal `\n` characters to actual newlines
- Markdown rendering in dossier output
- Proper HTML formatting

✅ **Validation Integration**
- Built-in parameter validation during import
- Error reporting and handling
- Integration with existing validation system

## Cleanup

To remove the test files:

```bash
rm -rf test_submission_project test_dossier_output
```