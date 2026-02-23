"""
Banker.az News Scraper

Website structure:
- URL Pattern: /{slug}/ (WordPress-based)
- Listing: /category/xYbYrlYr/ with path-based pagination /page/N/
- Date Format: ISO datetime in <time datetime="...">
- Content: .tdb_single_content .tdb-block-inner
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

CATEGORY_PATH = '/category/xYbYrlYr'


class BankerScraper(BaseScraper):
    """Scraper for banker.az"""

    def __init__(self):
        super().__init__(source_domain='banker.az')

    def get_listing_url(self, page_number: int = 1) -> str:
        if page_number == 1:
            return f"{self.base_url}{CATEGORY_PATH}/"
        return f"{self.base_url}{CATEGORY_PATH}/page/{page_number}/"

    def extract_article_id(self, url: str) -> Optional[str]:
        """Extract slug from URL: https://banker.az/some-slug/ -> some-slug"""
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        articles = []
        seen_ids = set()

        containers = soup.select('.td_module_wrap')
        for container in containers:
            try:
                title_link = container.select_one('h3.entry-title a')
                if not title_link:
                    continue

                url = extract_attribute(title_link, 'href')
                if not url:
                    continue

                full_url = normalize_url(url, self.base_url)
                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)

                title = extract_text(title_link)
                if not title or len(title) < 5:
                    continue

                # Image
                image_url = None
                img = container.select_one('img')
                if img:
                    image_url = extract_attribute(img, 'src') or extract_attribute(img, 'data-src')
                    if image_url:
                        image_url = normalize_url(image_url, self.base_url)

                # Date
                published_at = None
                date_elem = container.select_one('time.entry-date')
                if date_elem and date_elem.get('datetime'):
                    try:
                        published_at = datetime.fromisoformat(
                            date_elem['datetime'].replace('+04:00', '+00:00')
                        ).replace(tzinfo=None)
                    except Exception:
                        pass

                articles.append({
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': full_url,
                    'image_url': image_url,
                    'published_at': published_at,
                    'excerpt': None,
                    'slug': article_id,
                })
                logger.debug(f"Extracted: {title[:50]}...")

            except Exception as e:
                logger.warning(f"Error parsing banker.az article: {e}")
                continue

        return articles

    def parse_article_detail(self, soup, article_url: str) -> Optional[Dict]:
        try:
            content = None
            for selector in [
                'div.tdb_single_content .tdb-block-inner',
                'div.tdb_single_content',
                'article .entry-content',
                'div.td-post-content',
            ]:
                elem = soup.select_one(selector)
                if elem:
                    paragraphs = elem.find_all('p')
                    parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 10]
                    content = '\n\n'.join(parts)
                    if content:
                        break

            published_at = None
            date_elem = soup.select_one('time.entry-date')
            if date_elem and date_elem.get('datetime'):
                try:
                    published_at = datetime.fromisoformat(
                        date_elem['datetime'].replace('+04:00', '+00:00')
                    ).replace(tzinfo=None)
                except Exception:
                    pass

            result = {'content': content, 'author': None, 'metadata': {}}
            if published_at:
                result['published_at'] = published_at
            return result

        except Exception as e:
            logger.error(f"Error parsing banker.az detail: {e}")
            return None


if __name__ == "__main__":
    scraper = BankerScraper()
    print(f"Banker scraper initialized for: {scraper.source_name}")
