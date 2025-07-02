Getting Started: A Step-by-Step Tutorial
=======================================

This quick guide walks you through the typical workflow using the ``microlens-submit`` CLI.

If your terminal does not support ANSI escape codes, add ``--no-color`` to disable colored output.

1. **Initialize your project**

   .. code-block:: bash

      microlens-submit init --team-name "Your Team" --tier "standard" /path/to/project

2. **Add your first solution**

   .. code-block:: bash

      microlens-submit add-solution EVENT123 binary_lens \
          --param t0=555.5 --param u0=0.1 --param tE=25.0 \
          --notes "Initial fit"

   You can also load parameters from a JSON file instead of listing them on the
   command line. Create ``params.json`` containing your values and run:

   .. code-block:: bash

      microlens-submit add-solution EVENT123 binary_lens \
          --params-file params.json --notes "Initial fit"

3. **Attach a posterior file (optional)**

   After generating a posterior sample (e.g., an MCMC chain), store the file
   within your project and record its relative path using the Python API::

      >>> sub = microlens_submit.load("/path/to/project")
      >>> evt = sub.get_event("EVENT123")
      >>> sol = next(iter(evt.solutions.values()))
      >>> sol.posterior_path = "posteriors/chain.h5"
      >>> sub.save()

4. **Add a competing solution**

   .. code-block:: bash

      microlens-submit add-solution EVENT123 single_lens \
          --param t0=556.0 --param u0=0.2 --param tE=24.5

5. **List your solutions**

   .. code-block:: bash

      microlens-submit list-solutions EVENT123

6. **Deactivate the less-good solution**

   .. code-block:: bash

      microlens-submit deactivate <solution_id>

7. **Export the final package**

   .. code-block:: bash

      microlens-submit export submission.zip


