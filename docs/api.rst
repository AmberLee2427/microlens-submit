Python API Reference
====================

For advanced users who prefer integrating ``microlens-submit`` directly into Python scripts, this section documents the public API. The API provides programmatic access to all functionality available through the command-line interface.

**Core Classes**
~~~~~~~~~~~~~~~

The API is built around three main classes that represent the hierarchical structure of microlensing submissions:

- **Submission**: Top-level container for all events and team information
- **Event**: Container for multiple solutions for a single microlensing event
- **Solution**: Individual microlensing model fit with parameters and metadata

**Loading and Saving**
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: microlens_submit.load

**Submission Class**
~~~~~~~~~~~~~~~~~~~

The main container class that represents an entire microlensing challenge submission.

.. autoclass:: microlens_submit.Submission
   :members:
   :special-members: __init__

   **Key Methods:**

   - ``get_event(event_id)``: Retrieve or create an event
   - ``save()``: Persist all changes to disk
   - ``run_validation()``: Check submission completeness and consistency
   - ``export(path)``: Create submission package

   **Example:**

   .. code-block:: python

      >>> from microlens_submit import load
      >>>
      >>> # Load existing submission
      >>> submission = load("./my_project")
      >>>
      >>> # Set team information
      >>> submission.team_name = "Team Alpha"
      >>> submission.tier = "experienced"
      >>> submission.repo_url = "https://github.com/team-alpha/microlens-analysis"
      >>> # GPU info is optional; omit it for CPU-only environments.
      >>> submission.hardware_info = {
      ...     "cpu": "Intel i9",
      ...     "ram_gb": 64,
      ...     "gpu": {"model": "NVIDIA A100", "count": 1, "memory_gb": 40},
      ... }
      >>>
      >>> # Save changes
      >>> submission.save()
      >>>
      >>> # Validate submission
      >>> warnings = submission.run_validation()
      >>> for warning in warnings:
      ...     print(f"Warning: {warning}")

**Event Class**
~~~~~~~~~~~~~~

Represents a microlensing event that can contain multiple solutions.

.. autoclass:: microlens_submit.Event
   :members:
   :special-members: __init__

   **Key Methods:**

   - ``add_solution(model_type, parameters)``: Create and add a new solution
   - ``get_solution(solution_id)``: Retrieve a specific solution
   - ``get_active_solutions()``: Get only active solutions
   - ``clear_solutions()``: Deactivate all solutions

   **Example:**

   .. code-block:: python

      >>> # Get or create an event
      >>> event = submission.get_event("EVENT123")
      >>>
      >>> # Add a solution
      >>> solution = event.add_solution(
      ...     model_type="1S1L",
      ...     parameters={"t0": 2459123.5, "u0": 0.15, "tE": 20.5}
      ... )
      >>>
      >>> # Set solution metadata
      >>> solution.log_likelihood = -1234.56
      >>> solution.n_data_points = 1250
      >>> solution.relative_probability = 1.0
      >>>
      >>> # Save the submission
      >>> submission.save()

**Solution Class**
~~~~~~~~~~~~~~~~~

Represents an individual microlensing model fit with all associated metadata.

.. autoclass:: microlens_submit.Solution
   :members:
   :special-members: __init__

   **Key Methods:**

   - ``set_compute_info()``: Automatically capture compute information
   - ``activate()`` / ``deactivate()``: Control solution status
   - ``get_notes()``: Retrieve solution notes as markdown

   **Example:**

   .. code-block:: python

      >>> # Create a solution with higher-order effects
      >>> solution = event.add_solution(
      ...     model_type="1S2L",
      ...     parameters={
      ...         "t0": 2459123.5,
      ...         "u0": 0.12,
      ...         "tE": 22.1,
      ...         "q": 0.001,
      ...         "s": 1.15,
      ...         "alpha": 45.2
      ...     }
      ... )
      >>>
      >>> # Add higher-order effects
      >>> solution.higher_order_effects = ["parallax", "finite-source"]
      >>> solution.t_ref = 2459123.0
      >>>
      >>> # Set uncertainties
      >>> solution.parameter_uncertainties = {
      ...     "t0": [0.1, 0.1],
      ...     "u0": 0.02,
      ...     "tE": [0.3, 0.4]
      ... }
      >>>
      >>> # Set compute information
      >>> solution.set_compute_info(cpu_hours=15.2, wall_time_hours=3.8)
      >>>
      >>> # Add notes
      >>> solution.notes = "# Binary Lens Solution\n\nThis solution includes parallax and finite source effects."
      >>>
      >>> # Set file paths
      >>> solution.posterior_path = "posteriors/chain.h5"
      >>> solution.lightcurve_plot_path = "plots/event123_lc.png"
      >>> solution.lens_plane_plot_path = "plots/event123_lens.png"

   **Solution Aliases:**

   You can assign human-readable aliases to solutions for easier identification:

   .. code-block:: python

      >>> # Create a solution with an alias
      >>> solution = event.add_solution(
      ...     model_type="1S1L",
      ...     parameters={"t0": 2459123.5, "u0": 0.15, "tE": 20.5}
      ... )
      >>>
      >>> # Set an alias for the solution
      >>> solution.alias = "best_fit"
      >>>
      >>> # Aliases must be unique within each event
      >>> # This would raise an error if another solution in EVENT123 has alias "best_fit"
      >>> submission.save()

   **Alias Features:**
   - Aliases are displayed as primary identifiers in dossier generation
   - In the full dossier report, solutions are titled as "Solution: <event_id> <alias>"
   - The UUID is shown as a subtitle for technical reference
   - Solutions without aliases fall back to UUID-based identification
   - Aliases can be edited later by setting the ``alias`` attribute

**Advanced Usage**
~~~~~~~~~~~~~~~~~

**Working with Multiple Solutions:**

.. code-block:: python

   >>> # Compare solutions using BIC
   >>> from microlens_submit.cli import compare_solutions
   >>>
   >>> # Get all solutions for an event
   >>> event = submission.get_event("EVENT123")
   >>> solutions = list(event.solutions.values())
   >>>
   >>> # Calculate relative probabilities
   >>> for solution in solutions:
   ...     if solution.log_likelihood and solution.n_data_points:
   ...         # BIC calculation would go here
   ...         pass

**Validation and Error Handling:**

.. code-block:: python

   >>> # Comprehensive validation
   >>> warnings = submission.run_validation()
   >>>
   >>> if warnings:
   ...     print("Validation warnings:")
   ...     for warning in warnings:
   ...         print(f"  - {warning}")
   ... else:
   ...     print("Submission is valid!")

**Export and Dossier Generation:**

.. code-block:: python

   >>> # Export submission package
   >>> submission.export("final_submission.zip")
   >>>
   >>> # Generate dossier
   >>> from microlens_submit.dossier import generate_dashboard_html
   >>> from pathlib import Path
   >>>
   >>> generate_dashboard_html(submission, Path("./dossier_output"))

**Best Practices**
~~~~~~~~~~~~~~~~~

1. **Always save after changes**: Call ``submission.save()`` after modifying data
2. **Use validation**: Check ``submission.run_validation()`` before exporting
3. **Handle errors gracefully**: Wrap operations in try/except blocks
4. **Use relative paths**: Keep file paths relative to the project directory
5. **Document solutions**: Add detailed notes to explain your analysis

**Error Handling**
~~~~~~~~~~~~~~~~~

The API raises various exceptions that should be handled appropriately:

.. code-block:: python

   >>> try:
   ...     submission = load("./my_project")
   ... except FileNotFoundError:
   ...     print("Project directory not found")
   ... except ValidationError as e:
   ...     print(f"Validation error: {e}")
   ... except Exception as e:
   ...     print(f"Unexpected error: {e}")
