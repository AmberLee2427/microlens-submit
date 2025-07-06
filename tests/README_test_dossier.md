# Testing the Dossier Generation Feature

This directory contains a test script to demonstrate the new dossier generation feature in `microlens-submit` v0.13.0.

## Quick Test

To test the dossier generation feature:

```bash
# Make sure you have microlens-submit installed
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple microlens-submit==0.12.0-dev

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
3. **Validate the submission** to check for any issues
4. **Generate a dossier** using the new `generate-dossier` command
5. **Open the dashboard** in your default web browser

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
- Total events submitted (3)
- Total active solutions (4)
- Hardware information

✅ **Progress Tracking**
- Progress bar showing 3/293 events (1.0%)
- Total CPU and wall time hours

✅ **Events Table**
- List of all events with active solution counts
- Model types for each event
- Links to event-specific pages (placeholders for now)

✅ **Parameter Distribution Placeholders**
- Placeholder plots for tE, u0, M_L, and D_L distributions
- Professional styling with custom color palette

✅ **Responsive Design**
- Works on desktop and mobile devices
- Modern, professional appearance

## Cleanup

To remove the test files:

```bash
rm -rf test_submission_project test_dossier_output
```

## Troubleshooting

If the script fails:

1. **Check microlens-submit installation:**
   ```bash
   microlens-submit --version
   ```

2. **Verify the command works:**
   ```bash
   microlens-submit --help
   ```

3. **Check for any error messages** in the script output

4. **Manual browser opening:** If the automatic browser opening fails, manually open the `test_dossier_output/index.html` file in your browser

5. **Path issues:** Make sure you're running the script from the project root directory

## Integration with Test Suite

This test script is designed to work alongside the existing test suite:

- **Location:** `tests/test_dossier_generation.py`
- **Compatible with:** `pytest` (though it's primarily a demonstration script)
- **Dependencies:** Requires `microlens-submit` to be installed
- **Output:** Creates test artifacts in project root (not in tests directory)

## Next Steps

This test demonstrates the core dossier generation functionality. Future versions will include:

- Individual event pages with detailed solution information
- Real parameter distribution plots (instead of placeholders)
- Enhanced metadata display
- Export functionality for sharing dossiers 