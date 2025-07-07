Usage Examples
==============

The examples below demonstrate typical workflows for the Python API and
command line interface.

Quick Start
-----------

.. code-block:: python

    >>> from microlens_submit import load, Submission
    >>>
    >>> # Load an existing project
    >>> submission = load("./my_project")
    >>>
    >>> # Or create a new submission
    >>> submission = Submission()
    >>> submission.team_name = "Team Alpha"
    >>> submission.tier = "advanced"
    >>> submission.save("./my_project")
    >>>
    >>> # Add a solution to an event
    >>> event = submission.get_event("EVENT001")
    >>> solution = event.add_solution(
    ...     model_type="1S1L",
    ...     parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0},
    ... )
    >>> solution.log_likelihood = -1234.56
    >>> solution.cpu_hours = 2.5
    >>> submission.save()

Command Line Usage
------------------

.. code-block:: bash

    # Initialize a new project
    microlens-submit init --team-name "Team Alpha" --tier "advanced" ./project

    # Add a solution
    microlens-submit add-solution EVENT001 1S1L ./project \
        --param t0=2459123.5 --param u0=0.1 --param tE=20.0 \
        --log-likelihood -1234.56 --cpu-hours 2.5

    # Validate and generate dossier
    microlens-submit validate-submission ./project
    microlens-submit generate-dossier ./project

    # Export for submission
    microlens-submit export submission.zip ./project

Supported Model Types
---------------------

- 1S1L: Point Source, Single Point Lens (standard microlensing)
- 1S2L: Point Source, Binary Point Lens
- 2S1L: Binary Source, Single Point Lens
- 2S2L: Binary Source, Binary Point Lens
- 1S3L: Point Source, Triple Point Lens
- 2S3L: Binary Source, Triple Point Lens

Higher-Order Effects
--------------------

- parallax: Microlens parallax effect
- finite-source: Finite source size effect
- lens-orbital-motion: Orbital motion of lens components
- xallarap: Source orbital motion
- gaussian-process: Gaussian process noise modeling
- stellar-rotation: Stellar rotation effects
- fitted-limb-darkening: Fitted limb darkening coefficients

Extended Example
----------------

.. code-block:: python

    >>> from microlens_submit import load, Submission
    >>> from pathlib import Path
    >>>
    >>> # Create a new submission project
    >>> submission = Submission()
    >>> submission.team_name = "Team Alpha"
    >>> submission.tier = "advanced"
    >>> submission.repo_url = "https://github.com/team-alpha/microlens-analysis"
    >>>
    >>> # Add hardware information
    >>> submission.hardware_info = {
    ...     "cpu_details": "Intel Xeon E5-2680 v4",
    ...     "memory_gb": 64,
    ...     "nexus_image": "roman-science-platform:latest"
    ... }
    >>>
    >>> # Create an event and add solutions
    >>> event = submission.get_event("EVENT001")
    >>>
    >>> # Simple 1S1L solution
    >>> solution1 = event.add_solution(
    ...     model_type="1S1L",
    ...     parameters={
    ...         "t0": 2459123.5,
    ...         "u0": 0.1,
    ...         "tE": 20.0,
    ...         "F0_S": 1000.0,
    ...         "F0_B": 500.0
    ...     }
    ... )
    >>> solution1.log_likelihood = -1234.56
    >>> solution1.n_data_points = 1250
    >>> solution1.cpu_hours = 2.5
    >>> solution1.relative_probability = 0.8
    >>> solution1.notes = "# Simple Point Lens Fit\n\nThis is a basic 1S1L solution."
    >>>
    >>> # Binary lens solution with parallax
    >>> solution2 = event.add_solution(
    ...     model_type="1S2L",
    ...     parameters={
    ...         "t0": 2459123.5,
    ...         "u0": 0.08,
    ...         "tE": 22.1,
    ...         "s": 1.15,
    ...         "q": 0.001,
    ...         "alpha": 45.2,
    ...         "piEN": 0.1,
    ...         "piEE": 0.05,
    ...         "F0_S": 1000.0,
    ...         "F0_B": 500.0
    ...     }
    ... )
    >>> solution2.higher_order_effects = ["parallax"]
    >>> solution2.t_ref = 2459123.0
    >>> solution2.log_likelihood = -1189.34
    >>> solution2.cpu_hours = 15.2
    >>> solution2.relative_probability = 0.2
    >>>
    >>> # Save the submission
    >>> submission.save("./my_submission")
    >>>
    >>> # Validate the submission
    >>> warnings = submission.validate()
    >>> if warnings:
    ...     print("Validation warnings:", warnings)
    >>> else:
    ...     print("Submission is valid!")
    >>>
    >>> # Generate dossier
    >>> from microlens_submit.dossier import generate_dashboard_html
    >>> generate_dashboard_html(submission, Path("./my_submission/dossier"))

Dossier Generation Examples
---------------------------

The dossier generation system creates comprehensive HTML reports for reviewing your submission. Here are examples of the different types of pages you can generate:

**Complete Dossier Generation:**

.. code-block:: python

    >>> from microlens_submit import load
    >>> from microlens_submit.dossier import generate_dashboard_html
    >>> from pathlib import Path
    >>>
    >>> # Load your submission
    >>> submission = load("./my_project")
    >>>
    >>> # Generate the complete dossier (dashboard + all event pages + all solution pages)
    >>> generate_dashboard_html(submission, Path("./dossier_output"))
    >>>
    >>> # This creates:
    >>> # - dossier_output/index.html (main dashboard)
    >>> # - dossier_output/EVENT001.html (event page)
    >>> # - dossier_output/solution_uuid.html (solution pages)
    >>> # - dossier_output/full_dossier_report.html (printable version)
    >>> # - dossier_output/assets/ (logos and icons)

**Individual Event Page Generation:**

.. code-block:: python

    >>> from microlens_submit.dossier import generate_event_page
    >>>
    >>> # Generate a single event page
    >>> event = submission.get_event("EVENT001")
    >>> generate_event_page(event, submission, Path("./dossier_output"))
    >>>
    >>> # Creates: dossier_output/EVENT001.html
    >>> # This page shows:
    >>> # - Event overview and metadata
    >>> # - Solutions table with model types, status, and statistics
    >>> # - Navigation links to individual solution pages
    >>> # - Evaluator-only visualization placeholders

**Individual Solution Page Generation:**

.. code-block:: python

    >>> from microlens_submit.dossier import generate_solution_page
    >>>
    >>> # Generate a single solution page
    >>> solution = event.get_solution("solution_uuid_here")
    >>> generate_solution_page(solution, event, submission, Path("./dossier_output"))
    >>>
    >>> # Creates: dossier_output/solution_uuid_here.html
    >>> # This page shows:
    >>> # - Solution header with model type and metadata
    >>> # - Parameter tables with uncertainties
    >>> # - Markdown-rendered notes with syntax highlighting
    >>> # - Plot placeholders and compute statistics
    >>> # - Evaluator-only comparison sections

**Custom Dossier Content Generation:**

.. code-block:: python

    >>> from microlens_submit.dossier import (
    ...     _generate_dashboard_content,
    ...     _generate_event_page_content,
    ...     _generate_solution_page_content
    ... )
    >>>
    >>> # Generate HTML content without saving files
    >>> dashboard_html = _generate_dashboard_content(submission)
    >>> event_html = _generate_event_page_content(event, submission)
    >>> solution_html = _generate_solution_page_content(solution, event, submission)
    >>>
    >>> # Custom processing or integration
    >>> with open("custom_dashboard.html", "w") as f:
    ...     f.write(dashboard_html)

**Full Dossier Report Generation:**

.. code-block:: python

    >>> from microlens_submit.dossier import _generate_full_dossier_report_html
    >>>
    >>> # Generate a comprehensive single-file report
    >>> _generate_full_dossier_report_html(submission, Path("./dossier_output"))
    >>>
    >>> # Creates: dossier_output/full_dossier_report.html
    >>> # This single file contains:
    >>> # - Complete dashboard content
    >>> # - All event pages
    >>> # - All active solution pages
    >>> # - Section dividers and navigation
    >>> # - Print-friendly formatting

**Dossier Features:**

The generated dossier includes:

- **Dashboard**: Overview with submission statistics, progress tracking, and event summaries
- **Event Pages**: Detailed views of each event with solution tables and metadata
- **Solution Pages**: Individual solution details with parameters, notes, and visualizations
- **Navigation**: Links between pages and back to dashboard
- **Styling**: Professional Tailwind CSS design with RGES-PIT branding
- **Notes Rendering**: Markdown support with syntax highlighting for code blocks
- **GitHub Integration**: Commit links when repository information is available
- **Responsive Design**: Works on desktop and mobile devices
- **Print Support**: Optimized for printing and PDF generation

**CLI Dossier Generation:**

.. code-block:: bash

    # Generate complete dossier
    microlens-submit generate-dossier ./my_project
    
    # Generate dossier for specific event only
    microlens-submit generate-dossier ./my_project --event-id EVENT001
    
    # Generate dossier for specific solution only
    microlens-submit generate-dossier ./my_project --solution-id solution_uuid_here
    
    # Generate with priority flags (for advanced users)
    microlens-submit generate-dossier ./my_project --priority-flags

.. note::
   This package stores data in JSON and performs extensive validation to
   ensure correctness. Dossier generation produces printable HTML reports
   with Tailwind CSS styling and syntax highlighted notes.

