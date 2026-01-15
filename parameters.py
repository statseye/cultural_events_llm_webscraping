"""
Configuration parameters for the Cultural Events Aggregator application.

This module contains all configurable settings including user preferences,
target websites, API configuration, and scraping parameters.
"""

import os
from typing import List
import urllib3

urllib3.disable_warnings()


# =============================================================================
# USER PREFERENCES
# =============================================================================

EVENTS_PREFERENCES: str = "Events for kids in age 5-6 year old"
"""User preferences for filtering events. Describes what kind of events to look for."""

LOCATION: str = "Warsaw in Poland"
"""Geographic location for the events."""


# =============================================================================
# TARGET WEBSITES
# =============================================================================

WEBPAGES: List[str] = [
    "https://waw4free.pl/szukaj",
    "https://bigbookcafe.pl/repertuar/",
    "https://kultura.um.warszawa.pl/kalendarz",
]
"""List of websites to scrape for cultural events."""


# =============================================================================
# LLM CONFIGURATION
# =============================================================================

LLM_MODEL: str = "claude-sonnet-4-20250514"
"""Anthropic model to use for event filtering and analysis."""


def get_api_key() -> str:
    """
    Retrieve the Anthropic API key from environment variables.
    
    Returns:
        str: The Anthropic API key.
        
    Raises:
        EnvironmentError: If ANTHROPIC_API_KEY is not set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Please set it before running the application.\n"
            "Example: set ANTHROPIC_API_KEY=sk-ant-your-key-here"
        )
    return api_key


# =============================================================================
# SCRAPING CONFIGURATION
# =============================================================================

REQUEST_DELAY: float = 1.5
"""Delay in seconds between page loads to avoid rate limiting."""


# =============================================================================
# OUTPUT CONFIGURATION
# =============================================================================

OUTPUT_DIR: str = "outputs"
"""Directory where Excel files will be saved."""

TIMEZONE: str = "Europe/Warsaw"
"""Timezone for timestamps in output filenames."""
