Microlensing Submission Format Manual
====================================

.. note::
   **A Note from the Organizers:** We strongly recommend integrating the official ``microlens-submit`` tool into your workflow. It provides immediate solution validation feedback, easy solution comparison, and automated metadata collection. The tool handles all the tedious formatting and metadata generation for you, significantly reducing the risk of submission errors.

   However, if you prefer minimal tool usage or need to build your own submission package programmatically, this document provides the exact specification required. Proceed at your own risk.

Minimal Workflow: Create → Import → (Optional: Generate Dossier) → Export
-------------------------------------------------------------------------

For users who want minimal interaction with the submission tool, here's the simplest workflow:

1. **Create Submission Project**

   .. code-block:: bash

      microlens-submit init --team-name "Your Team Name" --tier "advanced"

   .. note::
      You can re-run ``microlens-submit init`` in the same project directory to quickly update the team name, tier, or other top-level metadata. This will overwrite the ``submission.json`` file with the new values you provide, but will not affect your events or solutions. It's a simple way to fix typos or update your info without manually editing the JSON file.

2. **Import Solutions from CSV**

   .. code-block:: bash

      microlens-submit import-solutions your_solutions.csv --validate

3. **(Optional) Generate Dossier**

   .. code-block:: bash

      microlens-submit generate-dossier

4. **Export Submission**

   .. code-block:: bash

      microlens-submit export-submission

That's it! Your submission has been sent.

CSV Import Format
-----------------

The tool can import solutions from a CSV file with the following columns:

Required Columns
~~~~~~~~~~~~~~~

.. list-table:: Required CSV Columns
   :widths: 25 15 40 20
   :header-rows: 1

   * - Column
     - Type
     - Description
     - Example
   * - ``event_id``
     - string
     - Unique identifier for the microlensing event
     - ``"OGLE-2023-BLG-0001"``
   * - ``solution_alias``
     - string
     - Human-readable name for the solution (must be unique within event)
     - ``"best_fit"`` or ``"parallax_model"``
   * - ``model_tags``
     - JSON array
     - Model type and higher-order effects
     - ``["1S1L"]`` or ``["1S2L", "parallax"]``

Model Types (Required in model_tags)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``1S1L``: Point Source, Single Point Lens (standard microlensing)
- ``1S2L``: Point Source, Binary Point Lens
- ``2S1L``: Binary Source, Single Point Lens
- ``2S2L``: Binary Source, Binary Point Lens
- ``1S3L``: Point Source, Triple Point Lens
- ``2S3L``: Binary Source, Triple Point Lens
- ``other``: Custom model type

Higher-Order Effects (Optional in model_tags)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``parallax``: Microlens parallax effect
- ``finite-source``: Finite source size effect
- ``lens-orbital-motion``: Orbital motion of lens components
- ``xallarap``: Source orbital motion
- ``gaussian-process``: Gaussian process noise modeling
- ``stellar-rotation``: Stellar rotation effects
- ``fitted-limb-darkening``: Fitted limb darkening coefficients
- ``other``: Custom higher-order effect

Parameter Columns
~~~~~~~~~~~~~~~~

You can include model parameters as individual columns. The tool will automatically recognize and validate them:

Core Parameters (Required based on model type)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: Core Model Parameters
   :widths: 20 15 15 40 10
   :header-rows: 1

   * - Parameter
     - Type
     - Units
     - Description
     - Required for
   * - ``t0``
     - float
     - HJD
     - Time of closest approach
     - All models
   * - ``u0``
     - float
     - θE
     - Minimum impact parameter
     - All models
   * - ``tE``
     - float
     - days
     - Einstein radius crossing time
     - All models
   * - ``s``
     - float
     - θE
     - Binary separation scaled by Einstein radius
     - 1S2L, 2S2L
   * - ``q``
     - float
     - mass ratio
     - Mass ratio M2/M1
     - 1S2L, 2S2L
   * - ``alpha``
     - float
     - rad
     - Angle of source trajectory relative to binary axis
     - 1S2L, 2S2L

Higher-Order Effect Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: Higher-Order Effect Parameters
   :widths: 20 15 20 40 20
   :header-rows: 1

   * - Parameter
     - Type
     - Units
     - Description
     - Required for Effect
   * - ``rho``
     - float
     - θE
     - Source radius scaled by Einstein radius
     - ``finite-source``
   * - ``piEN``
     - float
     - Einstein radius
     - Parallax vector component (North)
     - ``parallax``
   * - ``piEE``
     - float
     - Einstein radius
     - Parallax vector component (East)
     - ``parallax``
   * - ``dsdt``
     - float
     - θE/year
     - Rate of change of binary separation
     - ``lens-orbital-motion``
   * - ``dadt``
     - float
     - rad/year
     - Rate of change of binary orientation
     - ``lens-orbital-motion``

Flux Parameters (Required if using bands)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For each photometric band, you need source and blend flux parameters:

- ``F0_S``, ``F0_B``: Source and blend flux for band 0
- ``F1_S``, ``F1_B``: Source and blend flux for band 1
- ``F2_S``, ``F2_B``: Source and blend flux for band 2

For binary source models, use ``F0_S1``, ``F0_S2``, ``F0_B`` etc.

Optional Columns
~~~~~~~~~~~~~~~

.. list-table:: Optional CSV Columns
   :widths: 25 15 40 20
   :header-rows: 1

   * - Column
     - Type
     - Description
     - Example
   * - ``notes``
     - string
     - Solution notes (supports Markdown)
     - ``"# My Solution\n\nThis is a simple fit."``
   * - ``log_likelihood``
     - float
     - Log-likelihood value
     - ``-1234.56``
   * - ``n_data_points``
     - integer
     - Number of data points used
     - ``1250``
   * - ``relative_probability``
     - float
     - Relative probability (0-1)
     - ``0.8``

Example CSV
^^^^^^^^^^

.. code-block:: text

   # event_id,solution_alias,model_tags,t0,u0,tE,s,q,alpha,piEN,piEE,rho,notes
   OGLE-2023-BLG-0001,simple_1S1L,"[""1S1L""]",2459123.5,0.1,20.0,,,,,,,"# Simple Point Lens"
   OGLE-2023-BLG-0001,binary_parallax,"[""1S2L"", ""parallax""]",2459123.5,0.1,20.0,1.2,0.5,45.0,0.1,0.05,,"# Binary Lens with Parallax"
   OGLE-2023-BLG-0002,finite_source,"[""1S1L"", ""finite-source""]",2459156.2,0.08,35.7,,,,,,0.001,"# Finite Source Solution"

Manual Submission Format
-----------------------

If you prefer to create the submission structure manually, here are the specifications:

Directory Structure
~~~~~~~~~~~~~~~~~~

A valid submission is a directory containing a ``submission.json`` file and an ``events/`` subdirectory.

.. code-block:: text

   <submission_dir>/
   ├── submission.json
   └── events/
       └── <event_id>/
           ├── event.json
           └── solutions/
               └── <solution_id>.json

File Schemas
~~~~~~~~~~~

submission.json
^^^^^^^^^^^^^

Global metadata for the entire submission.

.. list-table:: submission.json Fields
   :widths: 25 15 15 45
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Description
   * - ``team_name``
     - string
     - Yes
     - Name of the participant team.
   * - ``tier``
     - string
     - Yes
     - Challenge tier.
   * - ``repo_url``
     - string
     - Yes
     - GitHub repository URL for the team codebase.
   * - ``hardware_info``
     - dict
     - Yes
     - Details about the compute environment.

**Example:**

.. code-block:: json

   {
     "team_name": "Planet Pounders",
     "tier": "advanced",
     "repo_url": "https://github.com/planet-pounders/microlens-analysis",
     "hardware_info": {
       "cpu": "Intel i9",
       "ram_gb": 64
     }
   }

event.json
^^^^^^^^^^

Describes a single event.

.. list-table:: event.json Fields
   :widths: 25 15 15 45
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Description
   * - ``event_id``
     - string
     - Yes
     - Unique identifier for the event.

**Example:**

.. code-block:: json

   {
     "event_id": "KMT-2025-BLG-001",
     "notes_path": "events/KMT-2025-BLG-001/notes.md"
   }

solution.json
^^^^^^^^^^^^

Represents a single model fit.

.. list-table:: solution.json Fields (Part 1: Core Fields)
   :widths: 25 15 15 45
   :header-rows: 1

   * - Field
     - Type
     - Required
     - Description
   * - ``solution_id``
     - string
     - Yes
     - Unique identifier for the solution.
   * - ``model_type``
     - string
     - Yes
     - Must be one of ``1S1L``, ``1S2L``, ``2S1L``, ``2S2L``, ``1S3L``, ``2S3L``, or ``other``.
   * - ``bands``
     - list
     - No
     - Photometric bands used, e.g., ``["0", "1"]``.
   * - ``higher_order_effects``
     - list
     - No
     - Additional effects like ``parallax`` or ``finite-source``.
   * - ``t_ref``
     - float
     - No
     - Reference time for the model.
   * - ``parameters``
     - dict
     - Yes
     - Dictionary of model parameters.
   * - ``is_active``
     - bool
     - No
     - If ``true``, this solution is included in exports. Defaults to ``true``.
   * - ``compute_info``
     - dict
     - No
     - Recorded dependencies and timing information.
   * - ``posterior_path``
     - string
     - No
     - Path to a stored posterior sample file.
   * - ``lightcurve_plot_path``
     - string
     - No
     - Path to the lightcurve plot file.
   * - ``lens_plane_plot_path``
     - string
     - No
     - Path to the lens plane plot file.
   * - ``notes_path``
     - string
     - No
     - Path to the markdown notes file for this solution.
   * - ``used_astrometry``
     - bool
     - No
     - Indicates use of astrometric data. Defaults to ``false``.
   * - ``used_postage_stamps``
     - bool
     - No
     - Indicates use of postage-stamp images. Defaults to ``false``.
   * - ``limb_darkening_model``
     - string
     - No
     - Name of the limb darkening model employed.
   * - ``limb_darkening_coeffs``
     - dict
     - No
     - Mapping of limb darkening coefficients.
   * - ``parameter_uncertainties``
     - dict
     - No
     - Uncertainties for parameters in parameters.
   * - ``physical_parameters``
     - dict
     - No
     - Physical parameters derived from the model.
   * - ``log_likelihood``
     - float
     - No
     - Log-likelihood value of the fit.
   * - ``relative_probability``
     - float
     - No
     - Optional probability of this solution being the best model.
   * - ``n_data_points``
     - integer
     - No
     - Number of data points used in the fit.
   * - ``creation_timestamp``
     - string
     - No
     - ISO timestamp. If omitted, the validator will add a current timestamp.

**Example:**

.. code-block:: json

   {
     "solution_id": "123e4567-e89b-12d3-a456-426614174000",
     "model_type": "1S2L",
     "parameters": {"t0": 555.5, "u0": 0.1, "tE": 25.0},
     "physical_parameters": {"M_L": 0.5, "D_L": 7.8},
     "log_likelihood": -1234.56,
     "is_active": true,
     "creation_timestamp": "2025-07-15T13:45:10Z"
   }

.. note::
   Files referenced by ``posterior_path``, ``lightcurve_plot_path``, and
   ``lens_plane_plot_path`` are automatically included in the exported ``.zip``.

External File Locations
^^^^^^^^^^^^^^^^^^^^^^

These optional files must live *inside* your submission directory, and the
paths stored in each ``solution.json`` should be **relative** to the submission
root. We recommend mirroring the structure that ``microlens-submit`` itself
creates:

.. code-block:: text

   <submission_dir>/
   ├── submission.json
   └── events/
       └── <event_id>/
           ├── event.json
           └── solutions/
               ├── <solution_id>.json
               └── <solution_id>/
                   ├── posterior.h5
                   ├── lightcurve.png
                   └── lens_plane.png

When exported to a ``.zip``, these files are copied into the archive following the
same layout. The ``posterior_path``, ``lightcurve_plot_path``, and
``lens_plane_plot_path`` values inside the ``solution.json`` files in the archive are
rewritten so that they point to their new location relative to the archive root,
e.g. ``events/<event_id>/solutions/<solution_id>/posterior.h5``. Be sure to
extract the archive before running any validation.

Locally, you might reference a posterior file as:

.. code-block:: json

   "posterior_path": "my_runs/posterior.h5"

Inside the exported ``.zip``, the same entry becomes:

.. code-block:: json

   "posterior_path": "events/<event_id>/solutions/<solution_id>/posterior.h5"

Validation
----------

Before submitting, you **must** validate your manually created package using the provided `validate_submission.py <https://github.com/AmberLee2427/microlens-submit/blob/main/validate_submission.py>`_ script. This is your only safety net.

Run the script from your terminal, passing the path to your submission directory:

.. code-block:: bash

   python validate_submission.py /path/to/your/submission_dir

The script will report "Submission is valid" on success or print detailed error messages if it finds any problems with your file structure or JSON formatting. Fix any reported errors before creating your final zip archive.

.. note::
   The ``notes`` field supports Markdown formatting, allowing you to create rich documentation with headers, lists, code blocks, tables, and links. This is particularly useful for creating detailed submission dossiers for evaluators.
