"""
Trend.az News Scraper

Website structure:
- Listing: /business/ (single page, timestamp-based pagination not supported)
- Date Format: ISO meta tag article:published_time, or "15 Noyabr 10:31 (UTC+04)"
- Content: div.article-content.article-paddings
"""

import re
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url, parse_azerbaijani_date
)

MONTHS = {
    'yanvar': 1, 'fevral': 2, 'mart': 3, 'aprel': 4,
    'may': 5, 'iyun': 6, 'iyul': 7, 'avqust': 8,
    'sentyabr': 9, 'oktyabr': 10, 'noyabr': 11, 'dekabr': 12,
}

LISTING_URL = '/business/'


class TrendScraper(BaseScraper):
    """Scraper for az.trend.az"""

    def __init__(self):
        super().__init__(source_domain='trend.az')

    def get_listing_url(self, page_number: int = 1) -> str:
        # Trend.az uses timestamp-based pagination; only page 1 is supported
        return f"{self.base_url}{LISTING_URL}"

    def extract_article_id(self, url: str) -> Optional[str]:
        """Extract last meaningful path segment"""
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else None

    def parse_listing_date(self, date_str: str) -> Optional[datetime]:
        """Parse 'DD Noyabr HH:MM (UTC+04)' format from listing"""
        try:
            date_str = date_str.replace('(UTC+04)', '').strip()
            parts = date_str.split()
            if len(parts) >= 3:
                day = int(parts[0])
                month = MONTHS.get(parts[1].lower())
                time_parts = parts[2].split(':')
                if month and len(time_parts) >= 2:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    year = datetime.now().year
                    return datetime(year, month, day, hour, minute)
        except Exception as e:
            logger.warning(f"Could not parse trend.az listing date '{date_str}': {e}")
        return None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        articles = []
        seen_ids = set()

        news_list = soup.select_one('ul.news-list.with-images')
        if not news_list:
            logger.warning("trend.az: Could not find news list container")
            return articles

        list_items = news_list.find_all('li')
        for item in list_items:
            try:
                link = item.find('a')
                if not link or not link.get('href'):
                    continue

                url = link['href']
                if not url.startswith('http'):
                    url = self.base_url + url

                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)

                # Title: heading or link text
                heading = item.find(['h2', 'h3', 'h4'])
                title = extract_text(heading) if heading else extract_text(link)
                if not title or len(title) < 5:
                    continue

                # Image
                image_url = None
                img = item.find('img')
                if img:
                    image_url = extract_attribute(img, 'src') or extract_attribute(img, 'data-src')
                    if image_url:
                        image_url = normalize_url(image_url, self.base_url)

                # Date from listing
                published_at = None
                date_elem = item.find(['span', 'time'], class_=re.compile(r'date|time'))
                if date_elem:
                    published_at = self.parse_listing_date(extract_text(date_elem))

                articles.append({
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': url,
                    'image_url': image_url,
                    'published_at': published_at,
                    'excerpt': None,
                    'slug': article_id,
                })
                logger.debug(f"Extracted: {title[:50]}...")

            except Exception as e:
                logger.warning(f"Error parsing trend.az article: {e}")
                continue

        return articles

    def parse_article_detail(self, soup, article_url: str) -> Optional[Dict]:
        try:
            # Date: prefer meta tag
            published_at = None
            date_meta = soup.find('meta', property='article:published_time')
            if date_meta and date_meta.get('content'):
                try:
                    # ISO format: "2025-11-14T17:57:00+04:00"
                    published_at = datetime.fromisoformat(
                        date_meta['content'].replace('+04:00', '+00:00')
                    ).replace(tzinfo=None)
                except Exception:
                    pass

            if not published_at:
                date_elem = soup.select_one('span.date-time')
                if date_elem:
                    published_at = self.parse_listing_date(extract_text(date_elem))

            # Content
            content = None
            content_elem = soup.select_one('div.article-content.article-paddings')
            if content_elem:
                paragraphs = content_elem.find_all('p')
                parts = [
                    extract_text(p) for p in paragraphs
                    if len(extract_text(p)) > 20 and not extract_text(p).startswith('Bakı. Trend:')
                ]
                content = '\n\n'.join(parts)

            if not content:
                all_paragraphs = soup.find_all('p')
                parts = [extract_text(p) for p in all_paragraphs if len(extract_text(p)) > 20]
                content = '\n\n'.join(parts)

            result = {'content': content, 'author': None, 'metadata': {}}
            if published_at:
                result['published_at'] = published_at
            return result

        except Exception as e:
            logger.error(f"Error parsing trend.az detail: {e}")
            return None


if __name__ == "__main__":
    scraper = TrendScraper()
    print(f"Trend scraper initialized for: {scraper.source_name}")
