Microlensing Data Challenge Submission Toolkit
=============================================

Welcome to the official documentation for ``microlens-submit``, a comprehensive toolkit for managing and submitting microlensing data challenge solutions.

**What is microlens-submit?**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During the 2018 Data Challenge, teams mailed in spreadsheets and wrote pages of answers by hand. That process was tedious and error-prone. For Data Challenge 2, we provide this tool to automate everything from project setup to the final submission package.

``microlens-submit`` is a **stateful submission toolkit** that provides:

- **Project Management**: Initialize and organize your submission project
- **Solution Tracking**: Add, edit, and manage microlensing solutions
- **Validation**: Comprehensive parameter and submission validation
- **Export**: Generate submission packages ready for upload
- **Documentation**: Create HTML dossiers for review and presentation
- **CLI & API**: Both command-line and programmatic interfaces

**Key Features**
~~~~~~~~~~~~~~~~

- **Complete Workflow**: From initial project setup to final submission
- **Parameter Validation**: Automatic checking of model parameters and uncertainties
- **Multiple Model Types**: Support for 1S1L, 1S2L, 2S1L, and other microlensing models
- **Higher-Order Effects**: Parallax, finite source, limb darkening, and more
- **Rich Documentation**: Markdown notes with syntax highlighting
- **HTML Dossiers**: Beautiful, printable reports for submission review
- **GitHub Integration**: Automatic repository linking and commit tracking
- **Compute Tracking**: CPU and wall time monitoring for resource usage

**Quick Start**
~~~~~~~~~~~~~~

.. code-block:: bash

   # Install the toolkit
   pip install microlens-submit
   
   # Initialize your project
   microlens-submit init --team-name "Your Team" --tier "standard" ./my_submission
   
   # Add your first solution
   microlens-submit add-solution EVENT123 1S1L \
        --param t0=2459123.5 --param u0=0.15 --param tE=20.5 \
        --log-likelihood -1234.56 --n-data-points 1250
   
   # Generate a dossier for review
   microlens-submit generate-dossier
   
   # Export your submission
   microlens-submit export submission.zip

**Documentation Sections**
~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tutorial
   usage_examples
   api

**Additional Resources**
~~~~~~~~~~~~~~~~~~~~~~~

- **Tutorial**: Complete step-by-step guide to using microlens-submit
- **API Reference**: Detailed documentation of the Python API
- **Jupyter Notebooks**: Interactive tutorials in the docs directory
- **Manual Submission**: For those who prefer to build packages by hand, see `SUBMISSION_MANUAL.md <https://github.com/AmberLee2427/microlens-submit/blob/main/SUBMISSION_MANUAL.md>`_

**Getting Help**
~~~~~~~~~~~~~~~

- **GitHub Issues**: Report bugs or request features on the `GitHub repository <https://github.com/AmberLee2427/microlens-submit>`_
- **Documentation**: This site contains comprehensive guides and examples
- **Examples**: Check the Jupyter notebooks in the docs directory for detailed examples

**Why Use microlens-submit?**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using ``microlens-submit`` is **strongly recommended** for packaging your results because it:

- **Reduces Errors**: Automatic validation catches common mistakes
- **Saves Time**: Automated workflow eliminates manual steps
- **Ensures Consistency**: Standardized format across all submissions
- **Provides Documentation**: Rich HTML dossiers for review
- **Supports Collaboration**: Version control friendly project structure
