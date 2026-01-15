"""
Web scraping module for the Cultural Events Aggregator.

This module provides functionality to scrape cultural event information
from multiple Polish websites including waw4free.pl, bigbookcafe.pl,
and kultura.um.warszawa.pl.
"""

import time
import re
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from parameters import (
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    USER_AGENT,
)


class WebScraper:
    """
    A web scraper for extracting cultural event information from Polish websites.
    
    Attributes:
        session: requests.Session object for making HTTP requests.
        last_request_time: Timestamp of the last request for rate limiting.
    """
    
    def __init__(self) -> None:
        """Initialize the WebScraper with a configured session."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        self.last_request_time: float = 0
    
    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
    
    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """
        Fetch a URL with retry logic.
        
        Args:
            url: The URL to fetch.
            
        Returns:
            The HTML content as a string, or None if all retries failed.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._wait_for_rate_limit()
                
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                
                self.last_request_time = time.time()
                return response.text
                
            except requests.exceptions.RequestException as e:
                print(f"[ERROR] Attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
                if attempt < MAX_RETRIES:
                    wait_time = attempt * 2  # Exponential backoff
                    print(f"[INFO] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
        
        print(f"[ERROR] Failed to fetch {url} after {MAX_RETRIES} attempts. Skipping...")
        return None
    
    def _extract_text(self, html: str, remove_tags: List[str] = None) -> str:
        """
        Extract clean text from HTML content.
        
        Args:
            html: Raw HTML content.
            remove_tags: List of tag names to remove before extraction.
            
        Returns:
            Clean text content.
        """
        if remove_tags is None:
            remove_tags = ["script", "style", "nav", "footer", "header", "aside", "noscript"]
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove unwanted tags
        for tag in remove_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Extract text
        text = soup.get_text(separator=" ", strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _extract_links(self, html: str, base_url: str, pattern: str) -> List[str]:
        """
        Extract links matching a pattern from HTML.
        
        Args:
            html: Raw HTML content.
            base_url: Base URL for resolving relative links.
            pattern: Regex pattern to match in href attributes.
            
        Returns:
            List of absolute URLs matching the pattern.
        """
        soup = BeautifulSoup(html, "html.parser")
        links = []
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if re.search(pattern, href):
                absolute_url = urljoin(base_url, href)
                if absolute_url not in links:
                    links.append(absolute_url)
        
        return links
    
    def scrape_waw4free(self, target_date: date) -> Dict[str, Any]:
        """
        Scrape events from waw4free.pl for a specific date.
        
        Args:
            target_date: The date to search for events.
            
        Returns:
            Dictionary with 'text' (extracted content) and 'links' (event URLs).
        """
        date_str = target_date.strftime("%Y-%m-%d")
        url = f"https://waw4free.pl/szukaj?dzien={date_str}"
        
        print(f"[INFO] Scraping waw4free.pl for {target_date.strftime('%d-%m-%Y')}...")
        
        html = self._fetch_with_retry(url)
        if html is None:
            return {"text": "", "links": [], "source": "waw4free.pl", "date": date_str}
        
        # Extract event links
        links = self._extract_links(html, "https://waw4free.pl", r"/wydarzenie-\d+")
        
        # Extract text content
        text = self._extract_text(html)
        
        return {
            "text": text,
            "links": links,
            "source": "waw4free.pl",
            "date": date_str,
        }
    
    def scrape_waw4free_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Scrape events from waw4free.pl for a date range.
        
        Args:
            start_date: Start of the date range.
            end_date: End of the date range (inclusive).
            
        Returns:
            List of scraping results for each date.
        """
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            result = self.scrape_waw4free(current_date)
            results.append(result)
            current_date += timedelta(days=1)
        
        return results
    
    def scrape_bigbookcafe(self) -> Dict[str, Any]:
        """
        Scrape events from bigbookcafe.pl repertoire page.
        
        Returns:
            Dictionary with 'text' (extracted content) and 'links' (event URLs).
        """
        url = "https://bigbookcafe.pl/repertuar/"
        
        print(f"[INFO] Scraping bigbookcafe.pl/repertuar/...")
        
        html = self._fetch_with_retry(url)
        if html is None:
            return {"text": "", "links": [], "source": "bigbookcafe.pl"}
        
        # Extract event links
        links = self._extract_links(html, "https://bigbookcafe.pl", r"/event/")
        
        # Extract text content
        text = self._extract_text(html)
        
        return {
            "text": text,
            "links": links,
            "source": "bigbookcafe.pl",
        }
    
    def scrape_kultura_um(self, max_pages: int = 5) -> Dict[str, Any]:
        """
        Scrape events from kultura.um.warszawa.pl calendar.
        
        Args:
            max_pages: Maximum number of pages to scrape.
            
        Returns:
            Dictionary with 'text' (extracted content) and 'links' (event URLs).
        """
        base_url = "https://kultura.um.warszawa.pl/kalendarz"
        all_text = []
        all_links = []
        
        for page in range(1, max_pages + 1):
            print(f"[INFO] Scraping kultura.um.warszawa.pl/kalendarz (page {page})...")
            
            # Liferay CMS pagination parameter
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?_event_EVENT_INSTANCE_eventsViewPortlet_cur={page}"
            
            html = self._fetch_with_retry(url)
            if html is None:
                break
            
            # Check if we've reached the end of results
            if page > 1 and "Nie znaleziono" in html:
                break
            
            # Extract event links
            links = self._extract_links(
                html, 
                "https://kultura.um.warszawa.pl", 
                r"kultura\.um\.warszawa\.pl/-/"
            )
            
            # Also try to find links in the format /-/event-slug
            soup = BeautifulSoup(html, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if href.startswith("/-/") and href not in all_links:
                    absolute_url = urljoin("https://kultura.um.warszawa.pl", href)
                    if absolute_url not in all_links:
                        links.append(absolute_url)
            
            all_links.extend([l for l in links if l not in all_links])
            
            # Extract text content
            text = self._extract_text(html)
            all_text.append(text)
            
            # Check if there are more pages (look for pagination indicators)
            if f"cur={page + 1}" not in html and page > 1:
                # No next page link found
                break
        
        return {
            "text": " ".join(all_text),
            "links": all_links,
            "source": "kultura.um.warszawa.pl",
        }
    
    def scrape_all(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Scrape all configured websites for the given date range.
        
        Args:
            start_date: Start of the date range.
            end_date: End of the date range (inclusive).
            
        Returns:
            Dictionary with aggregated text and links from all sources.
        """
        all_results = {
            "sources": [],
            "aggregated_text": "",
            "all_links": [],
        }
        
        # Scrape waw4free.pl for each date
        waw4free_results = self.scrape_waw4free_date_range(start_date, end_date)
        waw4free_text = " ".join([r["text"] for r in waw4free_results if r["text"]])
        waw4free_links = []
        for r in waw4free_results:
            waw4free_links.extend(r["links"])
        
        if waw4free_text:
            all_results["sources"].append({
                "name": "waw4free.pl",
                "text": waw4free_text,
                "links": list(set(waw4free_links)),
            })
        
        # Scrape bigbookcafe.pl
        bigbook_result = self.scrape_bigbookcafe()
        if bigbook_result["text"]:
            all_results["sources"].append({
                "name": "bigbookcafe.pl",
                "text": bigbook_result["text"],
                "links": bigbook_result["links"],
            })
        
        # Scrape kultura.um.warszawa.pl
        kultura_result = self.scrape_kultura_um()
        if kultura_result["text"]:
            all_results["sources"].append({
                "name": "kultura.um.warszawa.pl",
                "text": kultura_result["text"],
                "links": kultura_result["links"],
            })
        
        # Aggregate all text and links
        all_texts = []
        for source in all_results["sources"]:
            all_texts.append(f"\n\n=== SOURCE: {source['name']} ===\n\n{source['text']}")
            all_results["all_links"].extend(source["links"])
        
        all_results["aggregated_text"] = "".join(all_texts)
        all_results["all_links"] = list(set(all_results["all_links"]))
        
        return all_results


if __name__ == "__main__":
    # Test the scraper
    from datetime import date, timedelta
    
    scraper = WebScraper()
    today = date.today()
    end = today + timedelta(days=7)
    
    print(f"Testing scraper from {today} to {end}")
    results = scraper.scrape_all(today, end)
    
    print(f"\nFound {len(results['sources'])} sources")
    print(f"Total text length: {len(results['aggregated_text'])} characters")
    print(f"Total links found: {len(results['all_links'])}")
