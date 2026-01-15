"""
LLM Processing module for the Cultural Events Aggregator.

This module provides functionality to communicate with Anthropic's Claude models
to analyze scraped content and extract relevant cultural events based on
user preferences.
"""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import date

import anthropic


class LLMProcessor:
    """
    A processor that uses Anthropic's Claude models to analyze and filter cultural events.
    
    Attributes:
        client: Anthropic client instance.
        model: Name of the Claude model to use.
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        """
        Initialize the LLM processor.
        
        Args:
            api_key: Anthropic API key.
            model: Name of the model to use (default: claude-sonnet-4-20250514).
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for event extraction."""
        return """You are an expert assistant specialized in extracting and filtering cultural event information from raw text scraped from Polish websites.

Your task is to:
1. Analyze the provided text content from multiple event websites
2. Identify cultural events that match the user's preferences
3. Extract structured information about each matching event
4. Return the results in a specific JSON format

IMPORTANT RULES:
- Only include events that clearly match the user's preferences
- Only include events within the specified date range
- Only include events in the specified location
- If the exact time is not available, use "00:00" as a placeholder
- If no matching events are found, return an empty array []
- Ensure all dates are in DD-MM-YYYY format
- Ensure all times are in HH:MM format (24-hour)
- Event descriptions should be concise (max 100 characters)
- Links must be complete, valid URLs

OUTPUT FORMAT:
Return ONLY a valid JSON array with no additional text or explanation.
Each object in the array must have exactly these fields:
{
    "date": "DD-MM-YYYY",
    "time": "HH:MM",
    "event": "Brief description of the event",
    "link": "https://full-url-to-event-page"
}"""
    
    def _build_user_prompt(
        self,
        raw_text: str,
        preferences: str,
        start_date: date,
        end_date: date,
        location: str,
        available_links: List[str],
    ) -> str:
        """
        Build the user prompt with context and scraped content.
        
        Args:
            raw_text: Aggregated text from scraped websites.
            preferences: User's event preferences.
            start_date: Start of the date range.
            end_date: End of the date range.
            location: Target location for events.
            available_links: List of event URLs found during scraping.
            
        Returns:
            Formatted user prompt.
        """
        start_str = start_date.strftime("%d-%m-%Y")
        end_str = end_date.strftime("%d-%m-%Y")
        
        links_text = "\n".join(available_links[:50])  # Limit to avoid token overflow
        
        return f"""TASK: Find cultural events matching the criteria below.

USER PREFERENCES: {preferences}

DATE RANGE: {start_str} to {end_str} (inclusive)

LOCATION: {location}

AVAILABLE EVENT LINKS (use these when possible):
{links_text}

SCRAPED CONTENT FROM EVENT WEBSITES:
{raw_text}

---

Based on the above content, extract all events that:
1. Match the user preferences: "{preferences}"
2. Occur between {start_str} and {end_str}
3. Are located in or near {location}

Return the results as a JSON array. If no matching events are found, return []."""
    
    def _parse_response(self, response_text: str) -> List[Dict[str, str]]:
        """
        Parse the LLM response and extract JSON array.
        
        Args:
            response_text: Raw response from the LLM.
            
        Returns:
            List of event dictionaries.
            
        Raises:
            ValueError: If the response cannot be parsed as valid JSON.
        """
        # Try to extract JSON from the response
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            # Remove opening fence
            text = re.sub(r'^```(?:json)?\s*\n?', '', text)
            # Remove closing fence
            text = re.sub(r'\n?```\s*$', '', text)
        
        # Try to parse as JSON
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            else:
                print(f"[WARNING] LLM returned non-array JSON: {type(data)}")
                return []
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse LLM response as JSON: {e}")
            print(f"[DEBUG] Response was: {text[:500]}...")
            return []
    
    def _validate_events(self, events: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Validate and clean extracted events.
        
        Args:
            events: List of event dictionaries from LLM.
            
        Returns:
            List of validated event dictionaries.
        """
        validated = []
        required_fields = {"date", "time", "event", "link"}
        
        for event in events:
            # Check all required fields exist
            if not all(field in event for field in required_fields):
                print(f"[WARNING] Skipping event with missing fields: {event}")
                continue
            
            # Validate date format (DD-MM-YYYY)
            date_pattern = r'^\d{2}-\d{2}-\d{4}$'
            if not re.match(date_pattern, event["date"]):
                print(f"[WARNING] Invalid date format: {event['date']}")
                continue
            
            # Validate time format (HH:MM)
            time_pattern = r'^\d{2}:\d{2}$'
            if not re.match(time_pattern, event["time"]):
                # Try to fix common issues
                if re.match(r'^\d{1}:\d{2}$', event["time"]):
                    event["time"] = "0" + event["time"]
                else:
                    print(f"[WARNING] Invalid time format: {event['time']}, using 00:00")
                    event["time"] = "00:00"
            
            # Validate link
            if not event["link"].startswith(("http://", "https://")):
                print(f"[WARNING] Invalid link format: {event['link']}")
                continue
            
            # Truncate event description if too long
            if len(event["event"]) > 150:
                event["event"] = event["event"][:147] + "..."
            
            validated.append(event)
        
        return validated
    
    def filter_events(
        self,
        raw_text: str,
        preferences: str,
        start_date: date,
        end_date: date,
        location: str,
        available_links: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """
        Analyze scraped content and extract matching events using LLM.
        
        Args:
            raw_text: Aggregated text from scraped websites.
            preferences: User's event preferences.
            start_date: Start of the date range.
            end_date: End of the date range.
            location: Target location for events.
            available_links: List of event URLs found during scraping.
            
        Returns:
            List of validated event dictionaries with keys: date, time, event, link.
        """
        if available_links is None:
            available_links = []
        
        # Truncate text if too long (to avoid token limits)
        max_chars = 100000  # Approximately 25k tokens
        if len(raw_text) > max_chars:
            print(f"[INFO] Truncating text from {len(raw_text)} to {max_chars} characters")
            raw_text = raw_text[:max_chars]
        
        print(f"[INFO] Sending {len(raw_text)} characters to LLM for analysis...")
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            raw_text=raw_text,
            preferences=preferences,
            start_date=start_date,
            end_date=end_date,
            location=location,
            available_links=available_links,
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )
            
            response_text = response.content[0].text
            
            # Parse and validate events
            events = self._parse_response(response_text)
            validated_events = self._validate_events(events)
            
            print(f"[INFO] LLM found {len(events)} events, {len(validated_events)} validated")
            
            return validated_events
            
        except Exception as e:
            print(f"[ERROR] LLM processing failed: {e}")
            return []


if __name__ == "__main__":
    # Test with sample data
    from parameters import get_api_key, LLM_MODEL
    from datetime import timedelta
    
    try:
        api_key = get_api_key()
        processor = LLMProcessor(api_key, LLM_MODEL)
        
        sample_text = """
        Warsztaty plastyczne dla dzieci 4-7 lat
        Data: 18.01.2026, godzina 10:00
        Miejsce: Centrum Kultury, Warszawa
        Bezpłatne zajęcia artystyczne dla najmłodszych.
        Link: https://waw4free.pl/wydarzenie-12345
        
        Koncert rockowy - tylko dla dorosłych
        Data: 19.01.2026, godzina 21:00
        Klub muzyczny, Warszawa
        """
        
        today = date.today()
        events = processor.filter_events(
            raw_text=sample_text,
            preferences="Events for kids in age 5-6 year old",
            start_date=today,
            end_date=today + timedelta(days=7),
            location="Warsaw in Poland",
            available_links=["https://waw4free.pl/wydarzenie-12345"],
        )
        
        print(f"\nFiltered events: {json.dumps(events, indent=2, ensure_ascii=False)}")
        
    except EnvironmentError as e:
        print(f"Setup error: {e}")
