"""
Qafqazinfo.az News Scraper

Website structure:
- Listing: /news/category/iqtisadiyyat-4 with query-param pagination ?page=N
- Date Format: "09.11.2025 | 10:59"
- Content: .panel-body.news_text
"""

import re
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url, parse_azerbaijani_date
)

CATEGORY_PATH = '/news/category/iqtisadiyyat-4'


class QafqazinfoScraper(BaseScraper):
    """Scraper for qafqazinfo.az"""

    def __init__(self):
        super().__init__(source_domain='qafqazinfo.az')

    def get_listing_url(self, page_number: int = 1) -> str:
        if page_number == 1:
            return f"{self.base_url}{CATEGORY_PATH}"
        return f"{self.base_url}{CATEGORY_PATH}?page={page_number}"

    def extract_article_id(self, url: str) -> Optional[str]:
        """Extract numeric ID from /news/detail/{id}-slug"""
        match = re.search(r'/news/detail/(\d+)', url)
        if match:
            return match.group(1)
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        articles = []
        seen_ids = set()

        article_links = soup.select('a[href*="/news/detail/"]')
        for link in article_links:
            try:
                url = link.get('href', '')
                if not url:
                    continue

                if url.startswith('/'):
                    url = self.base_url + url
                if not url.startswith('https://qafqazinfo.az/news/detail/'):
                    continue

                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)

                # Title: link text or nearby heading
                title = extract_text(link)
                if not title or len(title) < 5:
                    parent = link.find_parent(['div', 'article', 'li'])
                    if parent:
                        heading = parent.find(['h2', 'h3', 'h4'])
                        title = extract_text(heading) if heading else title

                if not title or len(title) < 5:
                    continue

                # Image
                image_url = None
                container = link.find_parent(['div', 'article', 'li'])
                if container:
                    img = container.find('img')
                    if img:
                        image_url = extract_attribute(img, 'src') or extract_attribute(img, 'data-src')
                        if image_url:
                            image_url = normalize_url(image_url, self.base_url)

                articles.append({
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': url,
                    'image_url': image_url,
                    'published_at': None,
                    'excerpt': None,
                    'slug': article_id,
                })
                logger.debug(f"Extracted: {title[:50]}...")

            except Exception as e:
                logger.warning(f"Error parsing qafqazinfo.az article: {e}")
                continue

        return articles

    def parse_date(self, date_str: str) -> Optional[object]:
        """Parse 'DD.MM.YYYY | HH:MM' format"""
        from datetime import datetime
        try:
            date_str = date_str.strip().replace('|', '').strip()
            parts = date_str.split()
            if len(parts) >= 1:
                date_parts = parts[0].split('.')
                if len(date_parts) == 3:
                    day, month, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
                    hour, minute = 0, 0
                    if len(parts) >= 2:
                        time_parts = parts[1].split(':')
                        if len(time_parts) >= 2:
                            hour, minute = int(time_parts[0]), int(time_parts[1])
                    return datetime(year, month, day, hour, minute)
        except Exception as e:
            logger.warning(f"Could not parse qafqazinfo.az date '{date_str}': {e}")
        return None

    def parse_article_detail(self, soup, article_url: str) -> Optional[Dict]:
        try:
            # Date
            published_at = None
            date_elem = soup.select_one('time[datetime]')
            if date_elem:
                date_text = extract_text(date_elem)
                published_at = self.parse_date(date_text)

            # Content
            content = None
            content_elem = soup.select_one('.panel-body.news_text')
            if content_elem:
                for unwanted in content_elem.select('script, style, .rek_banner'):
                    unwanted.decompose()
                paragraphs = content_elem.find_all('p')
                parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 10]
                content = '\n\n'.join(parts)

            if not content:
                all_paragraphs = soup.find_all('p')
                parts = [extract_text(p) for p in all_paragraphs if len(extract_text(p)) > 20]
                content = '\n\n'.join(parts)

            # Title (also strip media suffix)
            title_elem = soup.select_one('.panel-body h1[style*="font-size: 32px"]')
            if not title_elem:
                title_elem = soup.select_one('.panel.panel-default.news .panel-body h1')

            result = {'content': content, 'author': None, 'metadata': {}}
            if published_at:
                result['published_at'] = published_at
            return result

        except Exception as e:
            logger.error(f"Error parsing qafqazinfo.az detail: {e}")
            return None


if __name__ == "__main__":
    scraper = QafqazinfoScraper()
    print(f"Qafqazinfo scraper initialized for: {scraper.source_name}")
