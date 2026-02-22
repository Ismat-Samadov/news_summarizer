"""
Helper utilities for web scraping
"""

import time
import random
from typing import Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from loguru import logger
import os

from scraper_job.config import (
    USER_AGENTS, REQUEST_TIMEOUT, REQUEST_DELAY,
    MAX_RETRIES, RETRY_DELAY
)

# Check if we should use Playwright (for JavaScript-rendered sites)
USE_PLAYWRIGHT = os.getenv('USE_PLAYWRIGHT', 'false').lower() == 'true'

if USE_PLAYWRIGHT:
    try:
        from playwright.sync_api import sync_playwright
        PLAYWRIGHT_AVAILABLE = True
        logger.info("Playwright enabled for JavaScript rendering")
    except ImportError:
        PLAYWRIGHT_AVAILABLE = False
        logger.warning("Playwright not available, falling back to requests")
        USE_PLAYWRIGHT = False
else:
    PLAYWRIGHT_AVAILABLE = False


def get_random_user_agent() -> str:
    """Return a random user agent string"""
    return random.choice(USER_AGENTS)


def get_headers() -> dict:
    """Generate request headers with random user agent"""
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'az-AZ,az;q=0.9,en-US;q=0.8,en;q=0.7,tr;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'DNT': '1',
    }


def fetch_page_with_playwright(
    url: str,
    timeout: int = REQUEST_TIMEOUT
) -> Optional[requests.Response]:
    """
    Fetch a web page using Playwright for JavaScript rendering

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Response-like object with rendered HTML or None if failed
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright not available, cannot fetch with JS rendering")
        return None

    try:
        time.sleep(REQUEST_DELAY)  # Be respectful to servers

        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Set user agent
            page.set_extra_http_headers({
                'User-Agent': get_random_user_agent()
            })

            # Navigate and wait for network to be idle
            logger.debug(f"Fetching with Playwright: {url}")
            page.goto(url, timeout=timeout * 1000, wait_until='networkidle')

            # Get rendered HTML
            content = page.content()
            browser.close()

            logger.debug(f"Successfully fetched with Playwright: {url}")

            # Create a requests-like response object
            class PlaywrightResponse:
                def __init__(self, text):
                    self.text = text
                    self.status_code = 200

                def raise_for_status(self):
                    pass

            return PlaywrightResponse(content)

    except Exception as e:
        logger.error(f"Playwright fetch failed for {url}: {e}")
        return None


def fetch_page(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = REQUEST_TIMEOUT,
    retries: int = MAX_RETRIES
) -> Optional[requests.Response]:
    """
    Fetch a web page with retries and error handling

    Args:
        url: URL to fetch
        headers: Optional custom headers
        timeout: Request timeout in seconds
        retries: Number of retry attempts

    Returns:
        Response object or None if failed
    """
    # Use Playwright if enabled (for JavaScript-rendered sites)
    if USE_PLAYWRIGHT and PLAYWRIGHT_AVAILABLE:
        logger.debug(f"Using Playwright for JavaScript rendering: {url}")
        return fetch_page_with_playwright(url, timeout)

    # Fall back to requests for static HTML
    if headers is None:
        headers = get_headers()

    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY)  # Be respectful to servers

            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True
            )

            response.raise_for_status()
            logger.debug(f"Successfully fetched: {url}")
            return response

        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logger.warning(f"Page not found (404): {url}")
                return None
            elif response.status_code == 403:
                logger.warning(f"Access forbidden (403): {url}")
                return None
            else:
                logger.warning(f"HTTP error {response.status_code}: {url}")

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{retries})")

        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error for {url} (attempt {attempt + 1}/{retries})")

        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")

        # Wait before retry
        if attempt < retries - 1:
            time.sleep(RETRY_DELAY)

    logger.error(f"Failed to fetch {url} after {retries} attempts")
    return None


def parse_html(html_content: str, parser: str = 'lxml') -> Optional[BeautifulSoup]:
    """
    Parse HTML content with BeautifulSoup

    Args:
        html_content: Raw HTML string
        parser: Parser to use ('lxml', 'html.parser', etc.)

    Returns:
        BeautifulSoup object or None if parsing failed
    """
    try:
        return BeautifulSoup(html_content, parser)
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return None


def extract_text(element, strip: bool = True) -> str:
    """Safely extract text from BeautifulSoup element"""
    if element is None:
        return ""
    text = element.get_text()
    return text.strip() if strip else text


def extract_attribute(element, attribute: str, default: str = "") -> str:
    """Safely extract attribute from BeautifulSoup element"""
    if element is None:
        return default
    return element.get(attribute, default)


def normalize_url(url: str, base_url: str) -> str:
    """
    Normalize relative URLs to absolute URLs

    Args:
        url: URL to normalize
        base_url: Base URL for relative paths

    Returns:
        Absolute URL
    """
    if url.startswith('http://') or url.startswith('https://'):
        return url
    elif url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        # Remove trailing slash from base_url if present
        base = base_url.rstrip('/')
        return base + url
    else:
        return base_url.rstrip('/') + '/' + url


def parse_azerbaijani_date(date_string: str) -> Optional[datetime]:
    """
    Parse Azerbaijani date strings to datetime objects

    Examples:
        "21 fevral 2026" -> datetime
        "21 Fevral 2026 12:06" -> datetime
        "21.02.2026 [19:22]" -> datetime
    """
    # Month mapping with variations for Turkish/Azerbaijani characters and English
    months_az = {
        'yanvar': 1, 'fevral': 2, 'mart': 3, 'aprel': 4,
        'may': 5, 'mayıs': 5,
        'iyun': 6, 'i̇yun': 6,  # dotted i variations
        'iyul': 7, 'i̇yul': 7,  # dotted i variations
        'avqust': 8, 'ağustos': 8,
        'sentyabr': 9, 'oktyabr': 10, 'noyabr': 11, 'dekabr': 12,
        # English months
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    try:
        # Clean the string
        date_string = date_string.strip().lower()
        # Normalize dotted i character
        date_string = date_string.replace('İ', 'i').replace('ı', 'i')

        # Pattern 1: "21 fevral 2026" or "21 Fevral 2026 12:06" or "21 fevral 18:26"
        for month_name, month_num in months_az.items():
            if month_name in date_string:
                parts = date_string.split()
                day = int(parts[0])

                # Check if parts[2] is a year (4 digits) or time (contains colon)
                if len(parts) >= 3:
                    if ':' in parts[2]:
                        # Format: "21 fevral 18:26" (no year, time is parts[2])
                        time_str = parts[2]
                        hour, minute = map(int, time_str.split(':'))
                        year = datetime.now().year
                        return datetime(year, month_num, day, hour, minute)
                    else:
                        # Format: "21 fevral 2026" or "21 fevral 2026 18:26"
                        year = int(parts[2])
                        if len(parts) >= 4:
                            time_str = parts[3]
                            hour, minute = map(int, time_str.split(':'))
                            return datetime(year, month_num, day, hour, minute)
                        else:
                            return datetime(year, month_num, day)
                else:
                    # Only "day month" - assume current year
                    year = datetime.now().year
                    return datetime(year, month_num, day)

        # Pattern 2: "21.02.2026 [19:22]" or "21.02.2026"
        if '.' in date_string:
            # Remove brackets if present
            date_string = date_string.replace('[', '').replace(']', '')
            parts = date_string.split()

            date_part = parts[0]
            day, month, year = map(int, date_part.split('.'))

            if len(parts) >= 2:
                time_str = parts[1]
                hour, minute = map(int, time_str.split(':'))
                return datetime(year, month, day, hour, minute)
            else:
                return datetime(year, month, day)

        logger.warning(f"Could not parse date: {date_string}")
        return None

    except Exception as e:
        logger.error(f"Error parsing date '{date_string}': {e}")
        return None


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug

    Args:
        text: Text to slugify

    Returns:
        Slugified text
    """
    import re
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')
