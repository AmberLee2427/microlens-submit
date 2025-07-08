"""
Tier validation module for microlens-submit.

This module provides centralized validation logic for challenge tiers and their
associated event lists. It validates event IDs against tier-specific event lists
and provides tier definitions for the microlensing data challenge.

The module defines:
- Tier definitions with associated event lists
- Event ID validation functions
- Tier-specific validation logic

**Supported Tiers:**
- basic: Basic challenge tier with limited event set
- standard: Standard challenge tier with full event set
- advanced: Advanced challenge tier with all events
- test: Testing tier for development
- 2018-test: 2018 test events tier
- None: No validation tier (skips event validation)

Example:
    >>> from microlens_submit.tier_validation import validate_event_id, TIER_DEFINITIONS
    >>>
    >>> # Check if an event is valid for a tier
    >>> is_valid = validate_event_id("EVENT001", "standard")
    >>> if is_valid:
    ...     print("Event is valid for standard tier")
    >>> else:
    ...     print("Event is not valid for standard tier")

    >>> # Get available tiers
    >>> print("Available tiers:", list(TIER_DEFINITIONS.keys()))

Note:
    All validation functions return boolean values and provide human-readable
    error messages for invalid events. The "None" tier skips all validation.
"""

from typing import Dict, List, Optional, Set

# Tier definitions with their associated event lists
TIER_DEFINITIONS = {
    "standard": {
        "description": "Standard challenge tier with limited event set",
        "event_list": [
            # Add standard tier events here
            "EVENT001",
            "EVENT002",
            "EVENT003",
        ],
    },
    "advanced": {
        "description": "Advanced challenge tier with full event set",
        "event_list": [
            # Add advanced tier events here
            "EVENT001",
            "EVENT002",
            "EVENT003",
            "EVENT004",
            "EVENT005",
            "EVENT006",
            "EVENT007",
        ],
    },
    "test": {
        "description": "Testing tier for development",
        "event_list": [
            # Add test events here
            "evt",
            "test-event",
        ],
    },
    "2018-test": {
        "description": "2018 test events tier",
        "event_list": [
            # Add 2018 test events here
            "2018-EVENT-001",
            "2018-EVENT-002",
        ],
    },
    "None": {
        "description": "No validation tier (skips event validation)",
        "event_list": [],  # Empty list means no validation
    },
}

# Cache for event lists to avoid repeated list creation
_EVENT_LIST_CACHE: Dict[str, Set[str]] = {}


def get_tier_event_list(tier: str) -> Set[str]:
    """Get the set of valid event IDs for a given tier.

    Args:
        tier: The challenge tier name.

    Returns:
        Set[str]: Set of valid event IDs for the tier.

    Raises:
        ValueError: If the tier is not defined.

    Example:
        >>> events = get_tier_event_list("standard")
        >>> print(f"Standard tier has {len(events)} events")
        >>> print("EVENT001" in events)
    """
    if tier not in TIER_DEFINITIONS:
        raise ValueError(f"Unknown tier: {tier}. Available tiers: {list(TIER_DEFINITIONS.keys())}")

    # Use cache for performance
    if tier not in _EVENT_LIST_CACHE:
        _EVENT_LIST_CACHE[tier] = set(TIER_DEFINITIONS[tier]["event_list"])

    return _EVENT_LIST_CACHE[tier]


def validate_event_id(event_id: str, tier: str) -> bool:
    """Validate if an event ID is valid for a given tier.

    Args:
        event_id: The event ID to validate.
        tier: The challenge tier to validate against.

    Returns:
        bool: True if the event ID is valid for the tier, False otherwise.

    Example:
        >>> is_valid = validate_event_id("EVENT001", "standard")
        >>> if is_valid:
        ...     print("Event is valid for standard tier")
        >>> else:
        ...     print("Event is not valid for standard tier")
    """
    # Skip validation for "None" tier or if tier is not defined
    if tier == "None" or tier not in TIER_DEFINITIONS:
        return True

    valid_events = get_tier_event_list(tier)
    return event_id in valid_events


def get_event_validation_error(event_id: str, tier: str) -> Optional[str]:
    """Get a human-readable error message for an invalid event ID.

    Args:
        event_id: The event ID that failed validation.
        tier: The challenge tier that was validated against.

    Returns:
        Optional[str]: Error message if the event is invalid, None if valid.

    Example:
        >>> error = get_event_validation_error("INVALID_EVENT", "standard")
        >>> if error:
        ...     print(f"Validation error: {error}")
        >>> else:
        ...     print("Event is valid")
    """
    if validate_event_id(event_id, tier):
        return None

    # No error for "None" tier or undefined tiers
    if tier == "None" or tier not in TIER_DEFINITIONS:
        return None

    valid_events = get_tier_event_list(tier)
    tier_desc = TIER_DEFINITIONS[tier]["description"]

    return (
        f"Event '{event_id}' is not valid for tier '{tier}' ({tier_desc}). "
        f"Valid events for this tier: {sorted(valid_events)}"
    )


def get_available_tiers() -> List[str]:
    """Get a list of all available tiers.

    Returns:
        List[str]: List of all available tier names.

    Example:
        >>> tiers = get_available_tiers()
        >>> print(f"Available tiers: {tiers}")
    """
    return list(TIER_DEFINITIONS.keys())


def get_tier_description(tier: str) -> str:
    """Get the description for a given tier.

    Args:
        tier: The tier name.

    Returns:
        str: Description of the tier.

    Raises:
        ValueError: If the tier is not defined.

    Example:
        >>> desc = get_tier_description("standard")
        >>> print(f"Standard tier: {desc}")
    """
    if tier not in TIER_DEFINITIONS:
        raise ValueError(f"Unknown tier: {tier}. Available tiers: {list(TIER_DEFINITIONS.keys())}")

    return TIER_DEFINITIONS[tier]["description"]
