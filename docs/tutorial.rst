Getting Started: A Step-by-Step Tutorial
=======================================

This quick guide walks you through the typical workflow using the ``microlens-submit`` CLI.

1. **Initialize your project**

   .. code-block:: bash

      microlens-submit init --team-name "Your Team" --tier "standard" /path/to/project

2. **Add your first solution**

   .. code-block:: bash

      microlens-submit add-solution EVENT123 binary_lens \
          --param t0=555.5 --param u0=0.1 --param tE=25.0 \
          --notes "Initial fit"

3. **Add a competing solution**

   .. code-block:: bash

      microlens-submit add-solution EVENT123 single_lens \
          --param t0=556.0 --param u0=0.2 --param tE=24.5

4. **List your solutions**

   .. code-block:: bash

      microlens-submit list-solutions EVENT123

5. **Deactivate the less-good solution**

   .. code-block:: bash

      microlens-submit deactivate <solution_id>

6. **Export the final package**

   .. code-block:: bash

      microlens-submit export submission.zip


