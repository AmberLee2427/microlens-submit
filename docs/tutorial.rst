Getting Started: A Step-by-Step Tutorial
=======================================

This comprehensive guide walks you through the complete workflow using the ``microlens-submit`` CLI, from initial project setup to final submission export.

**Prerequisites**
~~~~~~~~~~~~~~~~~

- Python 3.8 or higher
- ``microlens-submit`` installed (``pip install microlens-submit``)
- Basic familiarity with command-line interfaces
- Understanding of microlensing parameters and models

**Workflow Overview**
~~~~~~~~~~~~~~~~~~~~~

The typical workflow consists of these main steps:

1. **Project Initialization**: Set up your submission project structure
2. **Solution Addition**: Add microlensing solutions with parameters and metadata
3. **Bulk Importing Solutions from CSV**
4. **Validation**: Check your solutions for completeness and consistency
5. **Documentation**: Add notes and generate review materials
6. **Export**: Create the final submission package

**Step-by-Step Guide**
~~~~~~~~~~~~~~~~~~~~~~

If your terminal does not support ANSI escape codes, add ``--no-color`` to disable colored output.

1. **Initialize your project**

   Start by creating a new submission project with your team information:

   .. code-block:: bash

      microlens-submit init --team-name "Your Team" --tier "beginner" /path/to/project

   .. note::
      If you need to update your team name, tier, or other top-level submission info later, you can simply re-run ``microlens-submit init`` in the same project directory. This will overwrite the ``submission.json`` metadata with your new values, but will not affect your events or solutions. It's a quick way to fix mistakes without editing the JSON file directly.

   This creates the project directory structure and initializes the submission metadata.

   **Options:**
   - ``--team-name``: Your team's name (required)
   - ``--tier``: Challenge tier ("beginner" or "experienced")
   - Project path: Where to create the project directory

2. **Record repository and hardware info**

   Before validation and export, set your repository URL and hardware details.
   GPU information is optional (Roman Nexus nodes are CPU-only), so omit it if
   not applicable.

   .. code-block:: bash

      microlens-submit set-repo-url https://github.com/team/microlens-analysis /path/to/project

      microlens-submit set-hardware-info \
          --cpu-details "Intel Xeon Gold 6248" \
          --ram-gb 128 \
          --gpu "NVIDIA A100" \
          --gpu-count 1 \
          --gpu-memory-gb 40 \
          /path/to/project

3. **Add your first solution**

   Add a microlensing solution with all required parameters:

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S1L \
          --param t0=555.5 --param u0=0.1 --param tE=25.0 \
          --log-likelihood -1234.56 \
          --n-data-points 1250 \
          --cpu-hours 15.2 \
          --wall-time-hours 3.8 \
          --lightcurve-plot-path plots/event123_lc.png \
          --lens-plane-plot-path plots/event123_lens.png \
          --notes "Initial fit" \
          --higher-order-effect parallax,finite-source

   **Required Parameters:**
   - Event ID: Unique identifier for the microlensing event
   - Model type: Microlensing model (1S1L, 1S2L, 2S1L, etc.)
   - Model parameters: Specific to the model type

   **Optional Metadata:**
   - Log-likelihood and data points for statistical analysis
   - Compute information for resource tracking
   - Plot paths for visualization files
   - Notes for documentation
   - Higher-order effects for advanced models

   **Note:**
   The notes for each solution are always stored as a Markdown file, and the path is tracked in the solution JSON. You can:
   - Use ``--notes-file <path>`` to specify an existing Markdown file (the path is stored as-is).
   - Use ``--notes <string>`` to create a canonical notes file at ``events/<event_id>/solutions/<solution_id>.md`` (the path is stored automatically).
   - If neither is provided, an empty canonical notes file is created.

   You can append to notes later with:

   .. code-block:: bash

     microlens-submit edit-solution <solution_id> --append-notes "More details after review."

   Or open the notes file in your editor (using $EDITOR, nano, or vi):

   .. code-block:: bash

     microlens-submit notes <solution_id>

   **Tip:**
   - Notes support full Markdown formatting (headers, lists, code, tables, links, etc.).
   - The notes file is included in the exported zip and rendered in the HTML dossier.

   **Quick Notes Editing:**

   The ``microlens-submit notes <solution_id>`` command is a convenient way to quickly edit solution notes:

   .. code-block:: bash

     # Open notes in your default editor
     microlens-submit notes <solution_id>

     # This will:
     # - Open the notes file in your $EDITOR environment variable
     # - If $EDITOR is not set, it will try nano, then vi
     # - Save changes automatically when you exit the editor
     # - Validate the markdown formatting

   **Editor Configuration:**

   You can set your preferred editor by setting the $EDITOR environment variable:

   .. code-block:: bash

     # Set VS Code as your default editor
     export EDITOR="code --wait"

     # Set Vim as your default editor
     export EDITOR="vim"

     # Set Emacs as your default editor
     export EDITOR="emacs"

     # Then use the notes command
     microlens-submit notes <solution_id>

   **Alternative Editing Methods:**

   You can also edit notes directly or use the append method:

   .. code-block:: bash

     # Method 1: Direct file editing (if you know the path)
     nano events/EVENT123/solutions/<solution_id>.md

     # Method 2: Append to existing notes
     microlens-submit edit-solution <solution_id> \
          --append-notes "Additional analysis results..."

     # Method 3: Replace notes entirely
     microlens-submit edit-solution <solution_id> \
          --notes "Complete replacement of notes content"

   **Rich Documentation with Markdown Notes:**

   The notes field supports **full Markdown formatting**, allowing you to create rich, structured documentation for your solutions. This is particularly valuable for creating detailed submission dossiers for evaluators.

   **Example: Comprehensive Solution Documentation**

   Create detailed notes with markdown formatting:

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S2L \
          --param t0=2459123.5 --param u0=0.12 --param tE=22.1 \
          --param q=0.001 --param s=1.15 --param alpha=45.2 \
          --alias "binary_planetary" \
          --notes "# Binary Lens Solution for EVENT123

   ## Model Overview
   This solution represents a **binary lens** with a planetary companion (q = 0.001).

   ## Fitting Strategy
   - **Sampling Method:** MCMC with 1000 walkers
   - **Chain Length:** 50,000 steps per walker
   - **Burn-in:** First 10,000 steps discarded
   - **Convergence:** Gelman-Rubin statistic < 1.01 for all parameters

   ## Key Findings
   1. **Planetary Signal:** Clear detection of a planetary companion
   2. **Caustic Crossing:** Source crosses the planetary caustic
   3. **Finite Source Effects:** ρ = 0.001 indicates significant finite source effects

   ## Physical Parameters
   | Parameter | Value | Units |
   |-----------|-------|-------|
   | M_L | 0.45 ± 0.05 | M☉ |
   | D_L | 6.2 ± 0.3 | kpc |
   | M_planet | 1.5 ± 0.2 | M⊕ |
   | a | 2.8 ± 0.4 | AU |

   ## Model Comparison
   - **Single Lens:** Δχ² = 156.7 (rejected)
   - **Binary Lens:** Best fit with ΔBIC = 23.4

   ## Code Reference
   ```python
   # Fitting code snippet
   import emcee
   sampler = emcee.EnsembleSampler(nwalkers=1000, ndim=8, log_prob_fn=log_probability)
   sampler.run_mcmc(initial_state, 50000)
   ```

   ## References
   - [Gould & Loeb 1992](https://ui.adsabs.harvard.edu/abs/1992ApJ...396..104G)
   - [Mao & Paczynski 1991](https://ui.adsabs.harvard.edu/abs/1991ApJ...374L..37M)

   ---
   *Last updated: 2025-01-15*"

   **Markdown Features Supported:**
   - **Headers** (##, ###, etc.) for section organization
   - **Bold** and *italic* text for emphasis
   - **Lists** (numbered and bulleted) for structured information
   - **Tables** for parameter comparisons and data presentation
   - **Code blocks** for algorithm snippets and examples
   - **Links** to external references and documentation
   - **Images** (if referenced files exist in your project)
   - **Mathematical expressions** using LaTeX syntax

   **Appending to Existing Notes:**

   You can build up detailed documentation over time:

   .. code-block:: bash

     # Add initial notes
     microlens-submit add-solution EVENT123 1S1L \
          --param t0=2459123.5 --param u0=0.15 --param tE=20.5 \
          --notes "# Initial Single Lens Fit

   Basic point-source point-lens model as starting point."

     # Later, append additional analysis
     microlens-submit edit-solution <solution_id> \
          --append-notes "

   ## Follow-up Analysis

   After reviewing the residuals, we identified systematic deviations
   that suggest a more complex model is needed. The binary lens model
   provides a significantly better fit (Δχ² = 156.7).

   ### Residual Analysis
   - Peak deviation: 0.15 magnitudes
   - Systematic pattern suggests caustic crossing
   - Finite source effects may be important"

   **Solution Aliases:**

   You can assign human-readable aliases to your solutions for easier identification:

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S1L \
          --param t0=555.5 --param u0=0.1 --param tE=25.0 \
          --alias "best_fit" \
          --notes "Initial fit"

   **Alias Features:**
   - Aliases must be unique within each event (e.g., you can't have two solutions with alias "best_fit" in EVENT123)
   - Aliases are displayed as primary identifiers in dossier generation, with UUIDs as secondary
   - In the full dossier report, solutions are titled as "Solution: <event_id> <alias>" with UUID as subtitle
   - Aliases can be edited later using the edit-solution command
   - Solutions without aliases fall back to UUID-based identification

   **Edit solution aliases:**

   .. code-block:: bash

     microlens-submit edit-solution <solution_id> --alias "updated_best_fit"

   **Parameter File Support:**

   You can also load parameters from a JSON or YAML file instead of listing them on the
   command line. Create ``params.json`` containing your values and run:

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S2L \
          --params-file params.json \
          --lightcurve-plot-path plots/event123_lc.png \
          --lens-plane-plot-path plots/event123_lens.png \
          --notes "Initial fit" \
          --higher-order-effect parallax,finite-source

   **Parameter File Formats:**

   **Simple format (parameters only):**

   .. code-block:: json

     {
       "t0": 555.5,
       "u0": 0.1,
       "tE": 25.0
     }

   Or in YAML:

   .. code-block:: yaml

     t0: 555.5
     u0: 0.1
     tE: 25.0

   **Structured format (parameters + uncertainties):**

   .. code-block:: json

     {
       "parameters": {
         "t0": 555.5,
         "u0": 0.1,
         "tE": 25.0
       },
       "uncertainties": {
         "t0": [0.1, 0.1],
         "u0": 0.02,
         "tE": [0.3, 0.4]
       }
     }

   Or in YAML:

   .. code-block:: yaml

     parameters:
       t0: 555.5
       u0: 0.1
       tE: 25.0
     uncertainties:
       t0: [0.1, 0.1]
       u0: 0.02
       tE: [0.3, 0.4]

   Uncertainties can be single values (symmetric) or [lower, upper] arrays (asymmetric).
   Both JSON and YAML formats are supported with the same structure.

3. **Bulk Importing Solutions from CSV**

   You can import multiple solutions at once from a CSV file using the bulk import command. This is especially useful for large teams or automated pipelines.

   .. code-block:: bash

      microlens-submit import-solutions path/to/your_solutions.csv

   **Features:**
   - Supports individual parameter columns or a JSON parameters column
   - Handles solution aliases, notes, and higher-order effects
   - Duplicate handling: error (default), override, or ignore
   - Supports dry-run and validation options
   - File paths are resolved relative to the current working directory or with --project-path

   **Example CSV:**
   See `tests/data/test_import.csv` in the repository for a comprehensive example covering all features and edge cases. You can use this file as a template for your own imports.

   **Basic CSV format:**
   .. code-block:: csv

      # event_id,solution_alias,model_tags,t0,u0,tE,s,q,alpha,notes
      OGLE-2023-BLG-0001,simple_1S1L,"[""1S1L""]",2459123.5,0.1,20.0,,,,,"# Simple Point Lens"
      OGLE-2023-BLG-0001,binary_1S2L,"[""1S2L""]",2459123.5,0.1,20.0,1.2,0.5,45.0,"# Binary Lens"
      OGLE-2023-BLG-0002,finite_source,"[""1S1L"", ""finite-source""]",2459156.2,0.08,35.7,,,,,"# Finite Source"

   **Options:**
   - `--on-duplicate [error|override|ignore]`: How to handle duplicate aliases/IDs
   - `--dry-run`: Preview what would be imported without saving
   - `--validate`: Run validation on each imported solution
   - `--project-path <dir>`: Set the project root for file resolution

   **Test Data:**
   The file `tests/data/test_import.csv` is used in the test suite and can be copied or adapted for your own bulk imports.

4. **Validate without saving**

   Test your solution before committing it to disk:

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S2L \
          --param t0=555.5 --param u0=0.1 --param tE=25.0 \
          --dry-run

   This prints the parsed input, resulting schema output, and validation results
   without writing anything to disk. Any parameter validation warnings will be
   displayed. This is especially useful for checking relative probability
   assignments before saving.

5. **Validate existing solutions**

   Check your solutions for completeness and consistency:

   .. code-block:: bash

      # Validate a specific solution
      microlens-submit validate-solution <solution_id>

      # Validate all solutions for an event
      microlens-submit validate-event EVENT123

      # Validate the entire submission
      microlens-submit validate-submission

   These commands check parameter completeness, types, and physical consistency
   based on the model type and higher-order effects. They also validate that
   relative probabilities for active solutions in each event sum to 1.0.

6. **Attach a posterior file (optional)**

   After generating a posterior sample (e.g., an MCMC chain), store the file
   within your project and record its relative path using the Python API::

      >>> sub = microlens_submit.load("/path/to/project")
      >>> evt = sub.get_event("EVENT123")
      >>> sol = next(iter(evt.solutions.values()))
      >>> sol.posterior_path = "posteriors/chain.h5"
      >>> sol.lightcurve_plot_path = "plots/event123_lc.png"
      >>> sol.lens_plane_plot_path = "plots/event123_lens.png"
      >>> sub.save()

7. **Add a competing solution**

   Add alternative models for comparison:

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S1L \
          --param t0=556.0 --param u0=0.2 --param tE=24.5

8. **List your solutions**

   Review all solutions for an event:

   .. code-block:: bash

      microlens-submit list-solutions EVENT123

9. **Deactivate the less-good solution**

   Mark solutions as inactive (they remain in the project but aren't exported):

   .. code-block:: bash

      microlens-submit deactivate <solution_id>

   **Note:** Deactivated solutions are kept in the project but excluded from exports.
   Use this when you want to keep the solution data for reference but don't want
   it in your final submission.

10. **Remove mistakes (optional)**

   Completely remove solutions or events that were created by mistake:

   .. code-block:: bash

      # Remove a saved solution (requires --force for safety)
      microlens-submit remove-solution <solution_id> --force

      # Remove an entire event and all its solutions (requires --force for safety)
      microlens-submit remove-event <event_id> --force

   **CLI vs Python API:**

   - The CLI always operates on saved (on-disk) solutions and events. There is no concept of an "unsaved" solution in the CLI (except when using --dry-run, which does not persist anything).
   - In the Python API, you can create solutions/events in memory and remove them before saving. In the CLI, every change is immediately saved to disk.

   **What happens if you forget --force?**

   If you try to remove a saved solution or event without --force, you'll get a helpful error message and nothing will be deleted. For example:

   .. code-block:: text

      $ microlens-submit remove-solution 12345678-1234-1234-1234-123456789abc
      Error: Cannot remove saved solution 12345678... without force=True. Use solution.deactivate() to exclude from exports instead, or call remove_solution(solution_id, force=True) to force removal.
      💡 Use --force to override safety checks, or use deactivate to keep the solution

   **When to use removal vs deactivation:**

   - **Use deactivate()** when you want to keep the solution data but exclude it from exports
   - **Use remove_solution()** when you made a mistake and want to completely clean up (requires --force in the CLI)
   - **Use remove_event()** when you created an event by accident and want to start over (requires --force in the CLI)

   **Safety features:**

   - Saved solutions/events require ``--force`` to prevent accidental data loss
   - Removal cannot be undone - use deactivate() if you're unsure
   - Temporary files (notes in tmp/) are automatically cleaned up

11. **Edit solution attributes (optional)**

   After creating solutions, you can modify their attributes:

   .. code-block:: bash

     # Update relative probability
     microlens-submit edit-solution <solution_id> --relative-probability 0.7

     # Append to notes
     microlens-submit edit-solution <solution_id> --append-notes "Updated after model comparison"

     # Update compute info
     microlens-submit edit-solution <solution_id> --cpu-hours 25.5 --wall-time-hours 6.2

     # Fix a parameter typo
     microlens-submit edit-solution <solution_id> --param t0=2459123.6

     # Update an uncertainty
     microlens-submit edit-solution <solution_id> --param-uncertainty t0=[0.05,0.05]

     # Add higher-order effects
     microlens-submit edit-solution <solution_id> --higher-order-effect parallax,finite-source

     # Clear an attribute
     microlens-submit edit-solution <solution_id> --clear-relative-probability

     # See what would change without saving
     microlens-submit edit-solution <solution_id> --relative-probability 0.8 --dry-run

12. **Export the final package**

    Create the submission package for upload:

    .. code-block:: bash

       microlens-submit export submission.zip

    This creates a zip file containing all active solutions and associated files,
    ready for submission to the challenge organizers.

13. **Preview your submission dossier**

    Generate a human-readable HTML dashboard for review:

    .. code-block:: bash

       microlens-submit generate-dossier

    This will create a human-readable HTML dashboard at ``dossier/index.html`` inside your project directory. Open this file in your web browser to preview your submission as evaluators will see it.

    You can also serve the dossier with a simple local server:

    .. code-block:: bash

       cd dossier
       python3 -m http.server

    Then open ``http://localhost:8000`` in your browser.

    The dossier includes:
    - Team and submission metadata
    - Solution summaries and statistics
    - Progress bar and compute time
    - Event table and parameter distribution placeholders

    **Note:** The dossier is for your review only and is not included in the exported submission zip.

**Advanced Features**
~~~~~~~~~~~~~~~~~~~~

**GitHub Integration:**

Set your repository URL for automatic linking in the dossier:

.. code-block:: bash

   microlens-submit set-repo-url https://github.com/your-team/microlens-analysis.git

**Solution Comparison:**

Compare solutions using BIC-based relative probabilities:

.. code-block:: bash

   microlens-submit compare-solutions EVENT123

**Advanced Solution Comparison Workflow:**

When you have multiple solutions for the same event, it's crucial to manage them effectively and specify how they should be weighted. Here's a comprehensive workflow:

**1. Add Multiple Solutions for Comparison:**

.. code-block:: bash

   # Add a simple single-lens solution
   microlens-submit add-solution EVENT123 1S1L \
        --param t0=2459123.5 --param u0=0.15 --param tE=20.5 \
        --alias "simple_1S1L" \
        --log-likelihood -1234.56 --n-data-points 1250 \
        --notes "Initial single-lens fit using MCMC sampling"

   # Add a more complex binary-lens solution
   microlens-submit add-solution EVENT123 1S2L \
        --param t0=2459123.5 --param u0=0.12 --param tE=22.1 \
        --param q=0.001 --param s=1.15 --param alpha=45.2 \
        --alias "binary_1S2L" \
        --log-likelihood -1189.34 --n-data-points 1250 \
        --notes "Binary-lens fit with planetary companion. MCMC with 1000 walkers."

   # Add a third alternative solution
   microlens-submit add-solution EVENT123 1S2L \
        --param t0=2459123.8 --param u0=0.18 --param tE=19.8 \
        --param q=0.002 --param s=0.95 --param alpha=32.1 \
        --alias "alternative_1S2L" \
        --log-likelihood -1201.45 --n-data-points 1250 \
        --notes "Alternative binary solution with different parameter space."

**2. Compare Solutions with Detailed Analysis:**

.. code-block:: bash

   # View comparison table
   microlens-submit compare-solutions EVENT123

   # This will show:
   # - Model types and parameter counts
   # - Log-likelihood values
   # - BIC scores (calculated automatically)
   # - Relative probabilities (calculated automatically)
   # - Higher-order effects used

**3. Set Explicit Relative Probabilities:**

If you want to override the automatic BIC-based calculation:

.. code-block:: bash

   # Set explicit probabilities based on your analysis
   microlens-submit edit-solution <solution_id_1> --relative-probability 0.1
   microlens-submit edit-solution <solution_id_2> --relative-probability 0.7
   microlens-submit edit-solution <solution_id_3> --relative-probability 0.2

   # Verify probabilities sum to 1.0
   microlens-submit compare-solutions EVENT123

**4. Manage Solution States:**

.. code-block:: bash

   # Deactivate the worst solution (keeps it for reference)
   microlens-submit deactivate <solution_id_3>

   # Re-activate if needed later
   microlens-submit activate <solution_id_3>

   # Remove completely if it was a mistake
   microlens-submit remove-solution <solution_id_3> --force

**5. Update Solutions Based on Comparison:**

.. code-block:: bash

   # Refine the best solution with additional analysis
   microlens-submit edit-solution <solution_id_2> \
        --append-notes "

   ## Model Comparison Results

   After comparing all three solutions:
   - **Simple 1S1L:** Δχ² = 156.7 vs binary models (rejected)
   - **Binary 1S2L (primary):** Best fit with ΔBIC = 23.4
   - **Binary 1S2L (alternative):** ΔBIC = 11.2 vs primary

   The primary binary solution is clearly preferred, with the
   alternative binary solution having some merit but lower probability."

**6. Validate Your Final Solution Set:**

.. code-block:: bash

   # Check that everything is valid
   microlens-submit validate-event EVENT123

   # Ensure relative probabilities sum to 1.0 for active solutions
   microlens-submit validate-submission

**Solution Comparison Best Practices:**

1. **Start Simple:** Always begin with a single-lens model as baseline
2. **Document Decisions:** Use notes to explain why you prefer certain solutions
3. **Use Aliases:** Give meaningful names to solutions for easier management
4. **Keep History:** Use deactivate() rather than remove() to preserve analysis history
5. **Validate Regularly:** Check that relative probabilities sum to 1.0
6. **Consider Uncertainties:** Include parameter uncertainties when available
7. **Record Compute Time:** Track computational resources for each solution

**Relative Probability Guidelines:**

- **Sum to 1.0:** All active solutions in an event must have probabilities summing to 1.0
- **Automatic Calculation:** If you provide log-likelihood and n_data_points, BIC-based probabilities are calculated automatically
- **Manual Override:** You can set explicit probabilities based on your analysis
- **Single Solution:** If only one active solution exists, its probability should be 1.0 or None
- **Validation:** The system will warn you if probabilities don't sum correctly

**Parameter File Management:**

Use structured parameter files for complex models:

.. code-block:: bash

   # Create a parameter file with uncertainties
   cat > params.yaml << EOF
   parameters:
     t0: 2459123.5
     u0: 0.15
     tE: 20.5
     q: 0.001
     s: 1.15
     alpha: 45.2
   uncertainties:
     t0: [0.1, 0.1]
     u0: 0.02
     tE: [0.3, 0.4]
     q: 0.0001
     s: 0.05
     alpha: 2.0
   EOF

   # Use the parameter file
   microlens-submit add-solution EVENT123 1S2L --params-file params.yaml

**Project Management:**

Manage multiple events and solutions efficiently:

.. code-block:: bash

   # List all events
   ls events/

   # Check project status
   microlens-submit validate-submission

   # View project structure
   tree -I '*.pyc|__pycache__'

**Troubleshooting**
~~~~~~~~~~~~~~~~~~

**Common Issues and Solutions:**

1. **Validation Errors:**
   - Check that all required parameters are provided for your model type
   - Ensure relative probabilities sum to 1.0 for active solutions
   - Verify parameter types (numbers vs strings)

2. **File Path Issues:**
   - Use relative paths from the project root
   - Ensure referenced files exist before adding solutions
   - Check file permissions for reading/writing

3. **Model Type Errors:**
   - Verify model type spelling (1S1L, 1S2L, 2S1L, etc.)
   - Check that parameters match the model type requirements
   - Ensure higher-order effects are compatible with the model

4. **Export Problems:**
   - Make sure at least one solution is active per event
   - Check that all referenced files exist
   - Verify the export path is writable

**Getting Help**
~~~~~~~~~~~~~~~

- **Documentation**: This tutorial and the API reference
- **Jupyter Notebooks**: Interactive examples in the docs directory
- **GitHub Issues**: Report bugs or request features
- **Validation Messages**: Read the detailed error messages for guidance

**Best Practices**
~~~~~~~~~~~~~~~~~

1. **Use dry-run**: Always test with ``--dry-run`` before saving
2. **Validate regularly**: Check your submission frequently during development
3. **Document thoroughly**: Add detailed notes to explain your analysis
4. **Version control**: Use git to track changes to your project
5. **Backup regularly**: Keep copies of your project directory
6. **Test export**: Verify your submission package before final submission

**Comprehensive Best Practices Guide**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Reproducibility:**

- **Always use `--cpu-hours` and `--wall-time-hours`** to record computational details
- **Include version information** for key dependencies in your notes
- **Use descriptive notes** for each solution explaining your methodology
- **Record your analysis pipeline** with code snippets and parameter choices
- **Document data preprocessing** steps and quality cuts applied

.. code-block:: bash

   # Example of comprehensive compute info
   microlens-submit add-solution EVENT123 1S1L \
        --param t0=2459123.5 --param u0=0.15 --param tE=20.5 \
        --cpu-hours 15.2 --wall-time-hours 3.8 \
        --notes "# Single Lens Analysis

   ## Analysis Pipeline
   - **Data Source:** Roman DC2 2018-test tier
   - **Preprocessing:** 3σ outlier removal, band-specific calibration
   - **Fitting Method:** MCMC with 500 walkers, 20,000 steps
   - **Software Versions:** MulensModel 2.8.1, emcee 3.1.4
   - **Hardware:** 16-core Intel Xeon, 64GB RAM

   ## Quality Cuts
   - Removed data points with mag_err > 0.1
   - Applied systematic error floor of 0.02 mag
   - Used only I-band data for final fit

   ## Convergence Criteria
   - Gelman-Rubin statistic < 1.01 for all parameters
   - Effective sample size > 1000 for all parameters
   - Visual inspection of chain traces"

**Workflow Management:**

- **Save frequently** with regular validation checks
- **Use `deactivate()` instead of deleting solutions** to preserve analysis history
- **Keep multiple solutions** for comparison and model selection
- **Use meaningful aliases** for easier solution identification
- **Organize your project structure** with clear file naming conventions

.. code-block:: bash

   # Example workflow with multiple solutions
   microlens-submit add-solution EVENT123 1S1L \
        --alias "baseline_1S1L" --notes "Baseline single-lens model"

   microlens-submit add-solution EVENT123 1S2L \
        --alias "planetary_1S2L" --notes "Planetary companion model"

   # Compare and document your decision
   microlens-submit compare-solutions EVENT123

   # Deactivate the worse solution but keep for reference
   microlens-submit deactivate <baseline_solution_id>

   # Update the preferred solution with comparison results
   microlens-submit edit-solution <planetary_solution_id> \
        --append-notes "Selected over single-lens model: Δχ² = 156.7"

**Data Quality:**

- **Validate your parameters** before adding solutions
- **Include uncertainties** when available for better statistical analysis
- **Record the number of data points** used in each fit
- **Document data quality cuts** and preprocessing steps
- **Check for systematic errors** and include them in your analysis

.. code-block:: bash

   # Example with comprehensive data quality info
   microlens-submit add-solution EVENT123 1S2L \
        --param t0=2459123.5 --param u0=0.12 --param tE=22.1 \
        --param q=0.001 --param s=1.15 --param alpha=45.2 \
        --param-uncertainty t0=[0.1,0.1] --param-uncertainty u0=0.02 \
        --param-uncertainty tE=[0.3,0.4] --param-uncertainty q=0.0001 \
        --n-data-points 1250 \
        --notes "# High-Quality Binary Lens Fit

   ## Data Quality Assessment
   - **Total data points:** 1,450 (raw)
   - **Points used in fit:** 1,250 (after quality cuts)
   - **Systematic error floor:** 0.02 mag applied
   - **Band coverage:** I-band primary, V-band secondary
   - **Temporal coverage:** 2459120-2459130 (10 days)

   ## Uncertainty Analysis
   - Parameter uncertainties from MCMC posterior distributions
   - Asymmetric uncertainties for t0 and tE due to light curve asymmetry
   - Systematic uncertainties included in error budget"

**Performance Optimization:**

- **The tool is designed for long-term projects** with efficient handling of large numbers of solutions
- **Export only when ready** for final submission to avoid unnecessary processing
- **Use bulk import** for large datasets to save time
- **Organize your file structure** efficiently with clear naming conventions
- **Monitor disk space** for large posterior files and plots

.. code-block:: bash

   # Example of efficient bulk processing
   # Create a CSV file with all your solutions
   cat > solutions.csv << EOF
   event_id,solution_alias,model_tags,t0,u0,tE,log_likelihood,n_data_points,notes
   EVENT123,baseline,["1S1L"],2459123.5,0.15,20.5,-1234.56,1250,"Baseline model"
   EVENT123,planetary,["1S2L"],2459123.5,0.12,22.1,-1189.34,1250,"Planetary model"
   EVENT124,simple,["1S1L"],2459156.2,0.08,35.7,-2156.78,2100,"Simple fit"
   EOF

   # Bulk import all solutions at once
   microlens-submit import-solutions solutions.csv --validate

   # Generate dossier for review
   microlens-submit generate-dossier

   # Export only when ready for submission
   microlens-submit export final_submission.zip
