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

      microlens-submit init --team-name "Your Team" --tier "standard" /path/to/project

   This creates the project directory structure and initializes the submission metadata.

   **Options:**
   - ``--team-name``: Your team's name (required)
   - ``--tier``: Challenge tier ("standard" or "advanced")
   - Project path: Where to create the project directory

2. **Add your first solution**

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


