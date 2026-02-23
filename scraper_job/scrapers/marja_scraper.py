"""
Marja.az News Scraper

Website structure:
- Listing: /bank-kredit/12 with query-param pagination ?page=N
- Date Format: DD.MM.YYYY and HH:MM (separate small elements)
- Content: div.content-news
"""

from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url
)

CATEGORY_PATH = '/bank-kredit/12'


class MarjaScraper(BaseScraper):
    """Scraper for marja.az"""

    def __init__(self):
        super().__init__(source_domain='marja.az')

    def get_listing_url(self, page_number: int = 1) -> str:
        if page_number == 1:
            return f"{self.base_url}{CATEGORY_PATH}"
        return f"{self.base_url}{CATEGORY_PATH}?page={page_number}"

    def extract_article_id(self, url: str) -> Optional[str]:
        """Extract numeric ID or last segment from URL"""
        import re
        match = re.search(r'/(\d+)(?:[/-]|$)', url.rstrip('/'))
        if match:
            return match.group(1)
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else None

    def parse_date(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse DD.MM.YYYY and HH:MM"""
        try:
            return datetime.strptime(f"{date_str.strip()} {time_str.strip()}", "%d.%m.%Y %H:%M")
        except Exception:
            return None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        articles = []
        seen_ids = set()

        containers = soup.select('figure.snip1208')
        for container in containers:
            try:
                link = container.find('a')
                if not link or not link.get('href'):
                    continue

                url = link['href']
                if not url.startswith('http'):
                    url = self.base_url + url
                full_url = url

                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)

                # Title: figcaption, heading, or link text
                title = ''
                figcaption = container.find('figcaption')
                if figcaption:
                    heading = figcaption.find(['h2', 'h3', 'h4'])
                    title = extract_text(heading) if heading else extract_text(figcaption)
                if not title or len(title) < 5:
                    title = extract_text(link)

                if not title or len(title) < 5:
                    continue

                # Image
                image_url = None
                img = container.find('img')
                if img:
                    image_url = extract_attribute(img, 'src') or extract_attribute(img, 'data-src')
                    if image_url:
                        image_url = normalize_url(image_url, self.base_url)

                articles.append({
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': full_url,
                    'image_url': image_url,
                    'published_at': None,
                    'excerpt': None,
                    'slug': article_id,
                })
                logger.debug(f"Extracted: {title[:50]}...")

            except Exception as e:
                logger.warning(f"Error parsing marja.az article: {e}")
                continue

        return articles

    def parse_article_detail(self, soup, article_url: str) -> Optional[Dict]:
        try:
            # Date: two <small> elements inside div.news-date
            published_at = None
            date_elems = soup.select('div.news-date small')
            if len(date_elems) >= 2:
                date_text = date_elems[0].get_text().strip()
                time_text = date_elems[1].get_text().strip()
                # Strip icon characters (non-ASCII prefix)
                import re
                date_text = re.sub(r'^[^\d]+', '', date_text).strip()
                time_text = re.sub(r'^[^\d]+', '', time_text).strip()
                published_at = self.parse_date(date_text, time_text)

            # Content
            content = None
            content_elem = soup.select_one('div.content-news')
            if content_elem:
                for unwanted in content_elem.select('script, style, iframe, .middle-single, a.text-link-underline'):
                    unwanted.decompose()
                paragraphs = content_elem.find_all('p')
                parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 10]
                content = '\n\n'.join(parts)

            result = {'content': content, 'author': None, 'metadata': {}}
            if published_at:
                result['published_at'] = published_at
            return result

        except Exception as e:
            logger.error(f"Error parsing marja.az detail: {e}")
            return None


if __name__ == "__main__":
    scraper = MarjaScraper()
    print(f"Marja scraper initialized for: {scraper.source_name}")
