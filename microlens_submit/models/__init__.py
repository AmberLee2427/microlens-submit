"""
Data models for microlens-submit.

This package contains the core data models for managing microlensing challenge submissions:
- Solution: Individual model fit with parameters and metadata
- Event: Container for solutions to a single microlensing event
- Submission: Top-level container for a submission project

Example:
    >>> from microlens_submit.models import Solution, Event, Submission
    >>> 
    >>> # Create a submission
    >>> submission = Submission()
    >>> submission.team_name = "Team Alpha"
    >>> 
    >>> # Add an event and solution
    >>> event = submission.get_event("EVENT001")
    >>> solution = event.add_solution("1S1L", {"t0": 2459123.5, "u0": 0.1, "tE": 20.0})
"""

from .solution import Solution
from .event import Event
from .submission import Submission

__all__ = ["Solution", "Event", "Submission"] 