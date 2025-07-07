"""
Utility functions for dossier generation.

This module contains shared utility functions used across the dossier
generation package, including hardware formatting, GitHub URL parsing,
and other helper functions.
"""

import re
from typing import Dict, Any, Optional


def format_hardware_info(hardware_info: Optional[Dict[str, Any]]) -> str:
    """Format hardware information for display in the dashboard.

    Converts hardware information dictionary into a human-readable string
    suitable for display in the dashboard. Handles various hardware info
    formats and provides fallbacks for missing information.

    Args:
        hardware_info: Dictionary containing hardware information. Can include
            keys like 'cpu_details', 'cpu', 'memory_gb', 'ram_gb', 'nexus_image'.
            If None or empty, returns "Not specified".

    Returns:
        str: Formatted hardware information string for display.

    Example:
        >>> hardware_info = {
        ...     'cpu_details': 'Intel Xeon E5-2680 v4',
        ...     'memory_gb': 64,
        ...     'nexus_image': 'roman-science-platform:latest'
        ... }
        >>> format_hardware_info(hardware_info)
        'CPU: Intel Xeon E5-2680 v4, RAM: 64GB, Platform: Roman Nexus'

        >>> format_hardware_info(None)
        'Not specified'

        >>> format_hardware_info({'custom_field': 'custom_value'})
        'custom_field: custom_value'

    Note:
        This function handles multiple hardware info formats for compatibility
        with different submission sources. It prioritizes detailed CPU info
        over basic CPU info and provides fallbacks for missing data.
    """
    if not hardware_info:
        return "Not specified"

    parts = []

    # Common hardware fields
    if "cpu_details" in hardware_info:
        parts.append(f"CPU: {hardware_info['cpu_details']}")
    elif "cpu" in hardware_info:
        parts.append(f"CPU: {hardware_info['cpu']}")

    if "memory_gb" in hardware_info:
        parts.append(f"RAM: {hardware_info['memory_gb']}GB")
    elif "ram_gb" in hardware_info:
        parts.append(f"RAM: {hardware_info['ram_gb']}GB")

    if "nexus_image" in hardware_info:
        parts.append(f"Platform: Roman Nexus")

    if parts:
        return ", ".join(parts)
    else:
        # Fallback: show any available info
        return ", ".join(f"{k}: {v}" for k, v in hardware_info.items() if v is not None)


def extract_github_repo_name(repo_url: str) -> str:
    """Extract owner/repo name from a GitHub URL.

    Parses GitHub repository URLs to extract the owner and repository name
    in a display-friendly format. Handles various GitHub URL formats including
    HTTPS, SSH, and URLs with .git extension.

    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/owner/repo,
            git@github.com:owner/repo.git, etc.)

    Returns:
        str: Repository name in "owner/repo" format, or the original URL
            if parsing fails.

    Example:
        >>> extract_github_repo_name("https://github.com/username/microlens-submit")
        'username/microlens-submit'

        >>> extract_github_repo_name("git@github.com:username/microlens-submit.git")
        'username/microlens-submit'

        >>> extract_github_repo_name("https://github.com/org/repo-name")
        'org/repo-name'

        >>> extract_github_repo_name("invalid-url")
        'invalid-url'

    Note:
        This function uses regex to parse GitHub URLs and handles common
        variations. If the URL doesn't match expected patterns, it returns
        the original URL unchanged.
    """
    match = re.search(r"github\.com[:/]+([\w.-]+)/([\w.-]+)", repo_url)
    if match:
        return f"{match.group(1)}/{match.group(2).replace('.git','')}"
    return repo_url 