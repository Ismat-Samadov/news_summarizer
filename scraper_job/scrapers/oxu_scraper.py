"""
Oxu.az News Scraper

Website structure:
- Listing: /iqtisadiyyat with path-based pagination /iqtisadiyyat/page/N
- Date Format: "15 noyabr, 2025 / 19:44", "Bu gün / 12:18", "Dünən / 22:30"
- Content: .post-detail-content-inner.resize-area
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url
)

CATEGORY_PATH = '/iqtisadiyyat'


class OxuScraper(BaseScraper):
    """Scraper for oxu.az"""

    def __init__(self):
        super().__init__(source_domain='oxu.az')
        self.months = {
            'yanvar': 1, 'yan': 1,
            'fevral': 2, 'fev': 2,
            'mart': 3, 'mar': 3,
            'aprel': 4, 'apr': 4,
            'may': 5,
            'iyun': 6, 'iyn': 6,
            'iyul': 7, 'iyl': 7,
            'avqust': 8, 'avq': 8,
            'sentyabr': 9, 'sen': 9,
            'oktyabr': 10, 'okt': 10,
            'noyabr': 11, 'noy': 11,
            'dekabr': 12, 'dek': 12,
        }

    def get_listing_url(self, page_number: int = 1) -> str:
        if page_number == 1:
            return f"{self.base_url}{CATEGORY_PATH}"
        return f"{self.base_url}{CATEGORY_PATH}/page/{page_number}"

    def extract_article_id(self, url: str) -> Optional[str]:
        """Extract numeric article ID from URL"""
        match = re.search(r'/(\d+)(?:[/-]|$)', url.rstrip('/'))
        if match:
            return match.group(1)
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else None

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse Oxu.az date formats:
        - "15 noyabr, 2025 / 19:44"
        - "Bu gün / 12:18"
        - "Dünən / 22:30"
        """
        try:
            date_str = date_str.strip()
            parts = date_str.split('/')
            if len(parts) < 2:
                return None

            date_part = parts[0].strip().lower()
            time_part = parts[1].strip()

            # Parse time
            time_components = time_part.split(':')
            hour, minute = 0, 0
            if len(time_components) >= 2:
                hour = int(time_components[0])
                minute = int(time_components[1])

            today = datetime.now()

            if date_part in ('bu gün', 'bu gun'):
                return datetime(today.year, today.month, today.day, hour, minute)
            elif date_part in ('dünən', 'dunen', 'dünən'):
                yesterday = today - timedelta(days=1)
                return datetime(yesterday.year, yesterday.month, yesterday.day, hour, minute)

            # "15 noyabr, 2025"
            date_clean = date_part.replace(',', '').split()
            if len(date_clean) >= 3:
                day = int(date_clean[0])
                month = self.months.get(date_clean[1])
                year = int(date_clean[2])
                if month:
                    return datetime(year, month, day, hour, minute)

        except Exception as e:
            logger.warning(f"Could not parse oxu.az date '{date_str}': {e}")

        return None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        articles = []
        seen_ids = set()

        items = soup.select('.post-item.rt-news-item[data-url]')
        for item in items:
            try:
                url = item.get('data-url', '')
                if not url or CATEGORY_PATH not in url:
                    continue
                if not url.startswith('http'):
                    url = self.base_url + url

                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)

                # Title
                title_elem = item.select_one('h2, h3, h4, .title, .post-title')
                if title_elem:
                    title = extract_text(title_elem)
                else:
                    link = item.find('a')
                    title = extract_text(link) if link else ''

                if not title or len(title) < 5:
                    continue

                # Image
                image_url = None
                img = item.find('img')
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
                logger.warning(f"Error parsing oxu.az article: {e}")
                continue

        # Fallback: find article links if data-url items not found
        if not articles:
            article_links = soup.select(f'.post-item a[href*="{CATEGORY_PATH}/"]')
            for link in article_links:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    if href.startswith('/'):
                        href = self.base_url + href

                    article_id = self.extract_article_id(href)
                    if not article_id or article_id in seen_ids:
                        continue
                    seen_ids.add(article_id)

                    title = extract_text(link)
                    if not title or len(title) < 5:
                        continue

                    articles.append({
                        'source_article_id': article_id,
                        'title': title.strip(),
                        'url': href,
                        'image_url': None,
                        'published_at': None,
                        'excerpt': None,
                        'slug': article_id,
                    })
                except Exception as e:
                    logger.warning(f"Error in oxu.az fallback parsing: {e}")

        return articles

    def parse_article_detail(self, soup, article_url: str) -> Optional[Dict]:
        try:
            # Date
            published_at = None
            date_elem = soup.select_one('.post-detail-meta span')
            if date_elem:
                published_at = self.parse_date(extract_text(date_elem))

            # Content
            content = None
            content_elem = soup.select_one('.post-detail-content-inner.resize-area')
            if not content_elem:
                content_elem = soup.select_one('.post-detail-content')
            if content_elem:
                for unwanted in content_elem.select(
                    'script, style, .audio-block, .player-area, .tag-area, '
                    '.social-block2, .subscribe-single-block, .tag-post-list, ins'
                ):
                    unwanted.decompose()
                paragraphs = content_elem.find_all('p')
                parts = [
                    extract_text(p) for p in paragraphs
                    if len(extract_text(p)) > 20
                    and not any(s in extract_text(p).lower() for s in ['newmedia', 'reklam', 'advertisement'])
                ]
                content = '\n\n'.join(parts)

            result = {'content': content, 'author': None, 'metadata': {}}
            if published_at:
                result['published_at'] = published_at
            return result

        except Exception as e:
            logger.error(f"Error parsing oxu.az detail: {e}")
            return None


if __name__ == "__main__":
    scraper = OxuScraper()
    print(f"Oxu scraper initialized for: {scraper.source_name}")
