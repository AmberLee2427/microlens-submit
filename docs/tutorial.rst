Getting Started: A Step-by-Step Tutorial
=======================================

This quick guide walks you through the typical workflow using the ``microlens-submit`` CLI.

If your terminal does not support ANSI escape codes, add ``--no-color`` to disable colored output.

1. **Initialize your project**

   .. code-block:: bash

      microlens-submit init --team-name "Your Team" --tier "standard" /path/to/project

2. **Add your first solution**

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

   **Note:** The ``--notes`` field supports Markdown formatting, allowing you to create rich documentation with headers, lists, code blocks, and links. This is especially useful for creating detailed submission dossiers for evaluators.

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

3. **Validate without saving**

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S2L \
          --param t0=555.5 --param u0=0.1 --param tE=25.0 \
          --dry-run

   This prints the parsed input, resulting schema output, and validation results
   without writing anything to disk. Any parameter validation warnings will be
   displayed. This is especially useful for checking relative probability
   assignments before saving.

4. **Validate existing solutions**

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

5. **Attach a posterior file (optional)**

   After generating a posterior sample (e.g., an MCMC chain), store the file
   within your project and record its relative path using the Python API::

      >>> sub = microlens_submit.load("/path/to/project")
      >>> evt = sub.get_event("EVENT123")
      >>> sol = next(iter(evt.solutions.values()))
      >>> sol.posterior_path = "posteriors/chain.h5"
      >>> sol.lightcurve_plot_path = "plots/event123_lc.png"
      >>> sol.lens_plane_plot_path = "plots/event123_lens.png"
      >>> sub.save()

6. **Add a competing solution**

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S1L \
          --param t0=556.0 --param u0=0.2 --param tE=24.5

7. **List your solutions**

   .. code-block:: bash

      microlens-submit list-solutions EVENT123

8. **Deactivate the less-good solution**

   .. code-block:: bash

      microlens-submit deactivate <solution_id>

9. **Edit solution attributes (optional)**

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

10. **Export the final package**

   .. code-block:: bash

      microlens-submit export submission.zip


