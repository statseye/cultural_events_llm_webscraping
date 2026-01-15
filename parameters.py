"""
Configuration parameters for the Cultural Events Aggregator application.

This module contains all configurable settings including user preferences,
target websites, API configuration, and scraping parameters.
"""

import os
from typing import List


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

LLM_MODEL: str = "gpt-4o"
"""OpenAI model to use for event filtering and analysis."""


def get_api_key() -> str:
    """
    Retrieve the OpenAI API key from environment variables.
    
    Returns:
        str: The OpenAI API key.
        
    Raises:
        EnvironmentError: If OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it before running the application.\n"
            "Example: set OPENAI_API_KEY=sk-your-key-here"
        )
    return api_key


# =============================================================================
# SCRAPING CONFIGURATION
# =============================================================================

REQUEST_DELAY: float = 1.5
"""Delay in seconds between HTTP requests to avoid rate limiting."""

REQUEST_TIMEOUT: int = 30
"""Timeout in seconds for HTTP requests."""

MAX_RETRIES: int = 3
"""Maximum number of retry attempts for failed requests."""

USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
"""User-Agent header for HTTP requests."""


# =============================================================================
# OUTPUT CONFIGURATION
# =============================================================================

OUTPUT_DIR: str = "outputs"
"""Directory where Excel files will be saved."""

TIMEZONE: str = "Europe/Warsaw"
"""Timezone for timestamps in output filenames."""
