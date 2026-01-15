"""
Web scraping module for the Cultural Events Aggregator.

This module provides functionality to scrape cultural event information
from multiple Polish websites using Playwright for browser automation.
Supports dynamic content and precise element selection.
"""

import asyncio
import re
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup

from parameters import REQUEST_DELAY


class WebScraper:
    """
    A web scraper using Playwright for extracting cultural event information.
    
    Uses headless browser to handle JavaScript-rendered content and
    precise CSS selectors to extract only event-related data.
    """
    
    def __init__(self) -> None:
        """Initialize the WebScraper."""
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.delay = REQUEST_DELAY
    
    async def _init_browser(self) -> None:
        """Initialize the Playwright browser."""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            print("[INFO] Browser initialized")
    
    async def _close_browser(self) -> None:
        """Close the Playwright browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def _handle_cookie_consent(self, page: Page) -> None:
        """
        Try to dismiss cookie consent dialogs.
        
        Args:
            page: Playwright page object.
        """
        # Common cookie consent button selectors
        consent_selectors = [
            'button:has-text("Akceptuję")',
            'button:has-text("Zgadzam się")',
            'button:has-text("Accept")',
            'button:has-text("Akceptuj")',
            'button:has-text("OK")',
            '[class*="cookie"] button',
            '[class*="consent"] button',
            '#onetrust-accept-btn-handler',
            '.cmp-button_button',
        ]
        
        for selector in consent_selectors:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=1000):
                    await button.click()
                    await asyncio.sleep(0.5)
                    print("[INFO] Cookie consent dismissed")
                    return
            except Exception:
                continue
    
    async def _extract_events_waw4free(self, page: Page, target_date: date) -> Dict[str, Any]:
        """
        Extract events from waw4free.pl for a specific date.
        
        Args:
            page: Playwright page object.
            target_date: The date to search for events.
            
        Returns:
            Dictionary with extracted event data.
        """
        date_str = target_date.strftime("%Y-%m-%d")
        url = f"https://waw4free.pl/szukaj?dzien={date_str}"
        
        print(f"[INFO] Scraping waw4free.pl for {target_date.strftime('%d-%m-%Y')}...")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._handle_cookie_consent(page)
            await asyncio.sleep(2)  # Wait for dynamic content
            
            # Extract event cards - targeting specific event elements
            events_data = []
            links = []
            
            # Look for event links with pattern /wydarzenie-
            event_links = await page.locator('a[href*="/wydarzenie-"]').all()
            
            for element in event_links[:30]:  # Limit to 30 events
                try:
                    # Get the parent container for more context
                    text = await element.inner_text()
                    if text.strip():
                        events_data.append(text.strip())
                    
                    # Extract link
                    href = await element.get_attribute('href')
                    if href:
                        if not href.startswith('http'):
                            href = f"https://waw4free.pl{href}"
                        links.append(href)
                except Exception:
                    continue
            
            # Get additional context from the page - event details like dates/times
            # Look for date/time patterns in parent elements
            event_containers = await page.locator('.event, .wydarzenie, article, .search-result').all()
            for container in event_containers[:20]:
                try:
                    text = await container.inner_text()
                    if text.strip() and len(text) > 20:
                        events_data.append(text.strip())
                except Exception:
                    continue
            
            # If still no data, get main content area
            if not events_data:
                try:
                    main_content = await page.locator('main, .content, #content').first.inner_text()
                    events_data.append(main_content[:5000])  # Limit size
                except Exception:
                    pass
            
            return {
                "text": "\n\n---\n\n".join(list(set(events_data))),
                "links": list(set(links)),
                "source": "waw4free.pl",
                "date": date_str,
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to scrape waw4free.pl: {e}")
            return {"text": "", "links": [], "source": "waw4free.pl", "date": date_str}
    
    async def _extract_events_bigbookcafe(self, page: Page) -> Dict[str, Any]:
        """
        Extract events from bigbookcafe.pl repertoire page.
        
        Args:
            page: Playwright page object.
            
        Returns:
            Dictionary with extracted event data.
        """
        url = "https://bigbookcafe.pl/repertuar/"
        
        print(f"[INFO] Scraping bigbookcafe.pl/repertuar/...")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._handle_cookie_consent(page)
            await asyncio.sleep(2)
            
            events_data = []
            links = []
            
            # BigBookCafe uses h3 headers for events with links to /event/
            event_headers = await page.locator('h3 a[href*="/event/"]').all()
            
            for header in event_headers[:20]:
                try:
                    text = await header.inner_text()
                    href = await header.get_attribute('href')
                    
                    if text.strip():
                        events_data.append(text.strip())
                    
                    if href:
                        if not href.startswith('http'):
                            href = f"https://bigbookcafe.pl{href}"
                        links.append(href)
                except Exception:
                    continue
            
            # Get event descriptions from articles or content blocks
            articles = await page.locator('article, .event-item, .repertuar-item, .entry-content p').all()
            for article in articles[:20]:
                try:
                    text = await article.inner_text()
                    if text.strip() and len(text) > 30:
                        events_data.append(text.strip())
                except Exception:
                    continue
            
            # Fallback to main content
            if not events_data:
                try:
                    content = await page.locator('.entry-content, main, article').first.inner_text()
                    events_data.append(content[:5000])
                except Exception:
                    pass
            
            return {
                "text": "\n\n---\n\n".join(list(set(events_data))),
                "links": list(set(links)),
                "source": "bigbookcafe.pl",
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to scrape bigbookcafe.pl: {e}")
            return {"text": "", "links": [], "source": "bigbookcafe.pl"}
    
    async def _extract_events_kultura_um(self, page: Page, max_pages: int = 3) -> Dict[str, Any]:
        """
        Extract events from kultura.um.warszawa.pl calendar.
        
        Args:
            page: Playwright page object.
            max_pages: Maximum number of pages to scrape.
            
        Returns:
            Dictionary with extracted event data.
        """
        base_url = "https://kultura.um.warszawa.pl/kalendarz"
        
        all_events = []
        all_links = []
        
        for page_num in range(1, max_pages + 1):
            print(f"[INFO] Scraping kultura.um.warszawa.pl/kalendarz (page {page_num})...")
            
            try:
                if page_num == 1:
                    url = base_url
                else:
                    url = f"{base_url}?_event_EVENT_INSTANCE_eventsViewPortlet_cur={page_num}"
                
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if page_num == 1:
                    await self._handle_cookie_consent(page)
                
                await asyncio.sleep(2)
                
                # Extract event cards - look for titles with links
                title_links = await page.locator('h2 a, h3 a, .asset-title a').all()
                
                for link_el in title_links[:15]:
                    try:
                        title = await link_el.inner_text()
                        href = await link_el.get_attribute('href')
                        
                        if title.strip():
                            # Try to get parent element for date info
                            parent = link_el.locator('..')
                            try:
                                parent_text = await parent.inner_text()
                                all_events.append(f"{title}\n{parent_text}")
                            except Exception:
                                all_events.append(title)
                        
                        if href:
                            if href.startswith('/-/'):
                                href = f"https://kultura.um.warszawa.pl{href}"
                            elif not href.startswith('http'):
                                href = f"https://kultura.um.warszawa.pl{href}"
                            all_links.append(href)
                    except Exception:
                        continue
                
                # Get event cards content
                cards = await page.locator('.asset-entry, .event-card, article.event').all()
                for card in cards[:15]:
                    try:
                        text = await card.inner_text()
                        if text.strip() and len(text) > 30:
                            all_events.append(text.strip())
                    except Exception:
                        continue
                
                # Check if we should continue to next page
                next_link = await page.locator(f'a[href*="cur={page_num + 1}"]').count()
                if next_link == 0 and page_num > 1:
                    break
                    
            except Exception as e:
                print(f"[ERROR] Failed to scrape kultura.um.warszawa.pl page {page_num}: {e}")
                break
            
            await asyncio.sleep(self.delay)
        
        return {
            "text": "\n\n---\n\n".join(list(set(all_events))),
            "links": list(set(all_links)),
            "source": "kultura.um.warszawa.pl",
        }
    
    async def scrape_all_async(self, start_date: date, end_date: date) -> Dict[str, Any]:
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
        
        try:
            await self._init_browser()
            page = await self.browser.new_page()
            
            # Set viewport and user agent
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Scrape waw4free.pl for each date
            waw4free_texts = []
            waw4free_links = []
            
            current_date = start_date
            while current_date <= end_date:
                result = await self._extract_events_waw4free(page, current_date)
                if result["text"]:
                    waw4free_texts.append(result["text"])
                waw4free_links.extend(result["links"])
                current_date += timedelta(days=1)
                await asyncio.sleep(self.delay)
            
            if waw4free_texts:
                all_results["sources"].append({
                    "name": "waw4free.pl",
                    "text": "\n\n".join(waw4free_texts),
                    "links": list(set(waw4free_links)),
                })
            
            # Scrape bigbookcafe.pl
            bigbook_result = await self._extract_events_bigbookcafe(page)
            if bigbook_result["text"]:
                all_results["sources"].append({
                    "name": "bigbookcafe.pl",
                    "text": bigbook_result["text"],
                    "links": bigbook_result["links"],
                })
            await asyncio.sleep(self.delay)
            
            # Scrape kultura.um.warszawa.pl
            kultura_result = await self._extract_events_kultura_um(page)
            if kultura_result["text"]:
                all_results["sources"].append({
                    "name": "kultura.um.warszawa.pl",
                    "text": kultura_result["text"],
                    "links": kultura_result["links"],
                })
            
            await page.close()
            
        except Exception as e:
            print(f"[ERROR] Scraping failed: {e}")
        finally:
            await self._close_browser()
        
        # Aggregate all text and links
        all_texts = []
        for source in all_results["sources"]:
            all_texts.append(f"\n\n=== SOURCE: {source['name']} ===\n\n{source['text']}")
            all_results["all_links"].extend(source["links"])
        
        all_results["aggregated_text"] = "".join(all_texts)
        all_results["all_links"] = list(set(all_results["all_links"]))
        
        return all_results
    
    def scrape_all(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Synchronous wrapper for scrape_all_async.
        
        Args:
            start_date: Start of the date range.
            end_date: End of the date range (inclusive).
            
        Returns:
            Dictionary with aggregated text and links from all sources.
        """
        return asyncio.run(self.scrape_all_async(start_date, end_date))


if __name__ == "__main__":
    # Test the scraper
    from datetime import date, timedelta
    
    scraper = WebScraper()
    today = date.today()
    end = today + timedelta(days=3)
    
    print(f"Testing Playwright scraper from {today} to {end}")
    results = scraper.scrape_all(today, end)
    
    print(f"\nFound {len(results['sources'])} sources")
    print(f"Total text length: {len(results['aggregated_text'])} characters")
    print(f"Total links found: {len(results['all_links'])}")
    
    # Print sample of extracted text
    if results['aggregated_text']:
        print(f"\nSample text (first 1000 chars):\n{results['aggregated_text'][:1000]}")
