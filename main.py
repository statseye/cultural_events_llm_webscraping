"""
Cultural Events Aggregator - Main Application Entry Point

This application scrapes cultural event websites, filters events using LLM
based on user preferences, and exports matching events to an Excel file.

Usage:
    python main.py

Requirements:
    - OPENAI_API_KEY environment variable must be set
    - Internet connection for web scraping and LLM API calls
"""

import sys
from datetime import date, timedelta
from typing import Tuple, Optional

from parameters import (
    EVENTS_PREFERENCES,
    LOCATION,
    LLM_MODEL,
    get_api_key,
)
from scraper import WebScraper
from llm_processor import LLMProcessor
from excel_exporter import export_to_excel


def print_banner() -> None:
    """Print the application banner."""
    print("=" * 50)
    print("  Cultural Events Aggregator")
    print("  Powered by Anthropic Claude")
    print("=" * 50)
    print()


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse a date string in DD-MM-YYYY format.
    
    Args:
        date_str: Date string to parse.
        
    Returns:
        date object if valid, None otherwise.
    """
    try:
        parts = date_str.strip().split("-")
        if len(parts) != 3:
            return None
        
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def get_date_range() -> Tuple[date, date]:
    """
    Get date range from user input.
    
    Returns:
        Tuple of (start_date, end_date).
    """
    today = date.today()
    default_end = today + timedelta(days=7)
    
    print("Enter date range (format: DD-MM-YYYY)")
    print("Press Enter for default values.\n")
    
    # Get start date
    default_start_str = today.strftime("%d-%m-%Y")
    start_input = input(f"Start date [{default_start_str}]: ").strip()
    
    if start_input:
        start_date = parse_date(start_input)
        if start_date is None:
            print(f"[WARNING] Invalid date format. Using default: {default_start_str}")
            start_date = today
    else:
        start_date = today
    
    # Get end date
    default_end_str = default_end.strftime("%d-%m-%Y")
    end_input = input(f"End date [{default_end_str}]: ").strip()
    
    if end_input:
        end_date = parse_date(end_input)
        if end_date is None:
            print(f"[WARNING] Invalid date format. Using default: {default_end_str}")
            end_date = default_end
    else:
        end_date = default_end
    
    # Validate date range
    if end_date < start_date:
        print("[WARNING] End date is before start date. Swapping dates.")
        start_date, end_date = end_date, start_date
    
    return start_date, end_date


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        Exit code (0 for success, 1 for error).
    """
    print_banner()
    
    # Check for API key
    try:
        api_key = get_api_key()
    except EnvironmentError as e:
        print(f"[ERROR] {e}")
        return 1
    
    # Get date range from user
    start_date, end_date = get_date_range()
    
    print()
    print("-" * 50)
    print(f"[INFO] Date range: {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}")
    print(f"[INFO] Preferences: {EVENTS_PREFERENCES}")
    print(f"[INFO] Location: {LOCATION}")
    print(f"[INFO] LLM Model: {LLM_MODEL}")
    print("-" * 50)
    print()
    
    # Phase 1: Scraping
    print("=" * 50)
    print("PHASE 1: Scraping Websites")
    print("=" * 50)
    print()
    
    scraper = WebScraper()
    scrape_results = scraper.scrape_all(start_date, end_date)
    
    if not scrape_results["aggregated_text"]:
        print("[ERROR] No content retrieved from any website. Exiting.")
        return 1
    
    print()
    print(f"[INFO] Scraped {len(scrape_results['sources'])} sources")
    print(f"[INFO] Total content: {len(scrape_results['aggregated_text'])} characters")
    print(f"[INFO] Found {len(scrape_results['all_links'])} event links")
    print()
    
    # Phase 2: LLM Processing
    print("=" * 50)
    print("PHASE 2: LLM Analysis")
    print("=" * 50)
    print()
    
    processor = LLMProcessor(api_key, LLM_MODEL)
    
    events = processor.filter_events(
        raw_text=scrape_results["aggregated_text"],
        preferences=EVENTS_PREFERENCES,
        start_date=start_date,
        end_date=end_date,
        location=LOCATION,
        available_links=scrape_results["all_links"],
    )
    
    print()
    
    if not events:
        print("[WARNING] No matching events found for the given criteria.")
        print("[INFO] Try adjusting your preferences or date range.")
        return 0
    
    print(f"[INFO] Found {len(events)} matching events")
    print()
    
    # Phase 3: Export to Excel
    print("=" * 50)
    print("PHASE 3: Export to Excel")
    print("=" * 50)
    print()
    
    output_file = export_to_excel(events)
    
    if output_file:
        print()
        print("=" * 50)
        print(f"[SUCCESS] Saved {len(events)} events to:")
        print(f"          {output_file}")
        print("=" * 50)
    else:
        print("[WARNING] Failed to create Excel file.")
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] Operation cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
