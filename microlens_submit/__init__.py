"""microlens-submit: A stateful submission toolkit for the Microlensing Data Challenge.

This package provides a comprehensive toolkit for managing and submitting microlensing
data challenge solutions. It offers both programmatic API access and command-line
interface for creating, validating, and exporting microlensing submissions.

**Core Features:**
- Project initialization and management
- Solution creation and parameter validation
- Submission validation and completeness checking
- HTML dossier generation with rich visualizations
- Export functionality for challenge submission
- Command-line interface for all operations

**Main Components:**
- Submission: Top-level container for all submission data
- Event: Container for microlensing events and their solutions
- Solution: Individual microlensing solutions with parameters and metadata
- Validation: Comprehensive parameter and submission validation
- Dossier: HTML report generation with Tailwind CSS styling

**Quick Start:**
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
    ...     parameters={"t0": 2459123.5, "u0": 0.1, "tE": 20.0}
    ... )
    >>> solution.log_likelihood = -1234.56
    >>> solution.cpu_hours = 2.5
    >>> submission.save()

**Command Line Usage:**
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

**Supported Model Types:**
- 1S1L: Point Source, Single Point Lens (standard microlensing)
- 1S2L: Point Source, Binary Point Lens
- 2S1L: Binary Source, Single Point Lens
- 2S2L: Binary Source, Binary Point Lens
- 1S3L: Point Source, Triple Point Lens
- 2S3L: Binary Source, Triple Point Lens

**Higher-Order Effects:**
- parallax: Microlens parallax effect
- finite-source: Finite source size effect
- lens-orbital-motion: Orbital motion of lens components
- xallarap: Source orbital motion
- gaussian-process: Gaussian process noise modeling
- stellar-rotation: Stellar rotation effects
- fitted-limb-darkening: Fitted limb darkening coefficients

Example:
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

Note:
    This package is designed for the Microlensing Data Challenge and provides
    comprehensive tools for managing submission data. All data is stored in
    JSON format for portability and human readability. The package includes
    extensive validation to ensure submission completeness and correctness.
    The HTML dossier generation creates professional, printable reports with
    Tailwind CSS styling and syntax-highlighted markdown notes.
"""

__version__ = "0.12.2"

from .api import Event, Solution, Submission, load

__all__ = ["Event", "Solution", "Submission", "load"]
