Getting Started: A Step-by-Step Tutorial
=======================================

This quick guide walks you through the typical workflow using the ``microlens-submit`` CLI.

If your terminal does not support ANSI escape codes, add ``--no-color`` to disable colored output.

1. **Initialize your project**

   .. code-block:: bash

      microlens-submit init --team-name "Your Team" --tier "standard" /path/to/project

2. **Add your first solution**

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S2L \
          --param t0=555.5 --param u0=0.1 --param tE=25.0 \
          --lightcurve-plot-path plots/event123_lc.png \
          --lens-plane-plot-path plots/event123_lens.png \
          --notes "Initial fit"

   You can also load parameters from a JSON file instead of listing them on the
   command line. Create ``params.json`` containing your values and run:

   .. code-block:: bash

     microlens-submit add-solution EVENT123 1S2L \
          --params-file params.json \
          --lightcurve-plot-path plots/event123_lc.png \
          --lens-plane-plot-path plots/event123_lens.png \
          --notes "Initial fit"

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

9. **Export the final package**

   .. code-block:: bash

      microlens-submit export submission.zip


