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
- beginner: Beginner challenge tier with limited event set
- experienced: Experienced challenge tier with full event set
- test: Testing tier for development
- 2018-test: 2018 test events tier
- None: No validation tier (skips event validation)

Example:
    >>> from microlens_submit.tier_validation import validate_event_id, TIER_DEFINITIONS
    >>>
    >>> # Check if an event is valid for a tier
    >>> is_valid = validate_event_id("EVENT001", "beginner")
    >>> if is_valid:
    ...     print("Event is valid for beginner tier")
    ... else:
    ...     print("Event is not valid for beginner tier")

    >>> # Get available tiers
    >>> print("Available tiers:", list(TIER_DEFINITIONS.keys()))

Note:
    All validation functions return boolean values and provide human-readable
    error messages for invalid events. The "None" tier skips all validation.
"""

from typing import Dict, List, Optional, Set, Union

# Tier definitions with their associated event lists and model type constraints
# --- BEGIN AUTO-GENERATED: TIER_DEFINITIONS ---
TIER_DEFINITIONS = {
    "beginner": {
        "description": "Beginner challenge tier with limited event set",
        "event_prefix": "rmdc26_",
        "event_range": [1, 188],
        "allowed_model_types": ["1S1L", "1S2L", "2S1L", "2S2L", "other"],
        "allowed_higher_order_effects": ["parallax", "finite-source"],
    },
    "experienced": {
        "description": "Experienced challenge tier with full event set",
        "event_prefix": "rmdc26_",
        "event_range": [1, 2288],
        "allowed_model_types": ["1S1L", "1S2L", "2S1L", "2S2L", "1S3L", "2S3L", "1S4L", "2S4L", "other"],
        "allowed_higher_order_effects": "all",
    },
    "test": {
        "description": "Testing tier for development",
        "event_list": [
            "evt",
            "test-event",
            "EVENT001",
            "EVENT002",
            "EVENT003",
            "EVENT004",
            "EVENT005",
            "EVENT006",
            "EVENT007",
            "data_challenge_0_129_335",
        ],
        "allowed_model_types": "all",
        "allowed_higher_order_effects": "all",
    },
    "2018-test": {
        "description": "2018 test events tier",
        "event_prefix": "ulwdc1_",
        "event_range": [0, 293],
        "event_format": "{prefix}{index:03d}",
        "event_list": ["2018-EVENT-001", "2018-EVENT-002"],
        "allowed_model_types": "all",
        "allowed_higher_order_effects": "all",
    },
    "None": {
        "description": "No validation tier (skips event validation)",
        "event_list": [],
        "allowed_model_types": "all",
        "allowed_higher_order_effects": "all",
    },
}
# --- END AUTO-GENERATED: TIER_DEFINITIONS ---

# Cache for event lists to avoid repeated list creation
_EVENT_LIST_CACHE: Dict[str, Set[str]] = {}


def get_tier_event_list(tier: str) -> Set[str]:
    """Get the set of valid event IDs for a given tier.

    Args:
        tier: The challenge tier name.

    Returns:
        Set[str]: Set of valid event IDs for the tier (normalized to lowercase).

    Raises:
        ValueError: If the tier is not defined.

    Example:
        >>> events = get_tier_event_list("beginner")
        >>> print(f"Beginner tier has {len(events)} events")
        >>> print("event001" in events)
    """
    if tier not in TIER_DEFINITIONS:
        raise ValueError(f"Unknown tier: {tier}. Available tiers: {list(TIER_DEFINITIONS.keys())}")

    # Use cache for performance
    if tier not in _EVENT_LIST_CACHE:
        event_list = list(TIER_DEFINITIONS[tier].get("event_list", []))
        if "event_prefix" in TIER_DEFINITIONS[tier] and "event_range" in TIER_DEFINITIONS[tier]:
            event_prefix = str(TIER_DEFINITIONS[tier]["event_prefix"])
            event_range = tuple(TIER_DEFINITIONS[tier]["event_range"])
            event_format = str(TIER_DEFINITIONS[tier].get("event_format", "{prefix}{index:06d}"))
            for i in range(event_range[0], event_range[1] + 1):
                event_list.append(event_format.format(prefix=event_prefix, index=i))

        # Normalize all event IDs to lowercase for case-insensitive comparison
        _EVENT_LIST_CACHE[tier] = set(event_id.lower() for event_id in event_list)

    return _EVENT_LIST_CACHE[tier]


def validate_event_id(event_id: str, tier: str) -> bool:
    """Validate if an event ID is valid for a given tier.

    Args:
        event_id: The event ID to validate (case-insensitive).
        tier: The challenge tier to validate against.

    Returns:
        bool: True if the event ID is valid for the tier, False otherwise.

    Example:
        >>> is_valid = validate_event_id("rmdc26_000001", "beginner")
        >>> if is_valid:
        ...     print("Event is valid for beginner tier")
        >>> else:
        ...     print("Event is not valid for beginner tier")
    """
    # Skip validation for "None" tier or if tier is not defined
    if tier == "None" or tier not in TIER_DEFINITIONS:
        return True

    valid_events = get_tier_event_list(tier)
    return event_id.lower() in valid_events


def get_event_validation_error(event_id: str, tier: str) -> Optional[str]:
    """Get a human-readable error message for an invalid event ID.

    Args:
        event_id: The event ID that failed validation.
        tier: The challenge tier that was validated against.

    Returns:
        Optional[str]: Error message if the event is invalid, None if valid.

    Example:
        >>> error = get_event_validation_error("INVALID_EVENT", "beginner")
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


def get_allowed_model_types(tier: str) -> Union[List[str], str]:
    """Get the list of allowed model types for a given tier.

    Args:
        tier: The challenge tier name.

    Returns:
        List[str] | str: List of allowed model type names. Returns "all" if all
                         model types are allowed for this tier.

    Raises:
        ValueError: If the tier is not defined.

    Example:
        >>> allowed = get_allowed_model_types("beginner")
        >>> print(f"Beginner tier allows: {allowed}")
        >>> if "2S2L" in allowed:
        ...     print("Binary source, binary lens is allowed in beginner tier")
    """
    if tier not in TIER_DEFINITIONS:
        raise ValueError(f"Unknown tier: {tier}. Available tiers: {get_available_tiers()}")

    allowed = TIER_DEFINITIONS[tier].get("allowed_model_types", "all")
    # Always treat "all" as a special case; otherwise return the list
    return allowed


def get_tier_description(tier: str) -> str:
    """Get the description for a given tier.

    Args:
        tier: The tier name.

    Returns:
        str: Description of the tier.

    Raises:
        ValueError: If the tier is not defined.

    Example:
        >>> desc = get_tier_description("beginner")
        >>> print(f"Beginner tier: {desc}")
    """
    if tier not in TIER_DEFINITIONS:
        raise ValueError(f"Unknown tier: {tier}. Available tiers: {list(TIER_DEFINITIONS.keys())}")

    return TIER_DEFINITIONS[tier]["description"]
