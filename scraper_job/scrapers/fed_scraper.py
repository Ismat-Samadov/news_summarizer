"""
Fed.az News Scraper

Website structure:
- Listing: /az/maliyye with path-based pagination /az/maliyye/2, /az/maliyye/3
- Date Format: "15 Noy 2025 12:44" (abbreviated Azerbaijani months)
- Content: div.news-text[itemprop="articleBody"]
"""

import re
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url, parse_azerbaijani_date
)

CATEGORY_PATH = '/az/maliyye'


class FedScraper(BaseScraper):
    """Scraper for fed.az"""

    def __init__(self):
        super().__init__(source_domain='fed.az')

    def get_listing_url(self, page_number: int = 1) -> str:
        if page_number == 1:
            return f"{self.base_url}{CATEGORY_PATH}"
        return f"{self.base_url}{CATEGORY_PATH}/{page_number}"

    def extract_article_id(self, url: str) -> Optional[str]:
        """Extract last path segment as ID"""
        parts = url.rstrip('/').split('/')
        return parts[-1] if parts else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        articles = []
        seen_ids = set()

        news_containers = soup.select('div.news')
        for container in news_containers:
            try:
                link = container.find('a')
                if not link or not link.get('href'):
                    continue

                url = link['href']
                if not url.startswith('http'):
                    url = self.base_url.rstrip('/') + '/' + url.lstrip('/')
                full_url = url

                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)

                # Title: div.heading inside the link (fed.az card structure)
                heading_elem = link.select_one('div.heading')
                if heading_elem:
                    title = extract_text(heading_elem)
                else:
                    heading = link.find(['h2', 'h3', 'h4'])
                    title = extract_text(heading) if heading else extract_text(link)

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
                logger.warning(f"Error parsing fed.az article: {e}")
                continue

        return articles

    def parse_article_detail(self, soup, article_url: str) -> Optional[Dict]:
        try:
            # Title
            title_elem = soup.select_one('h3.news-head')
            if not title_elem:
                title_elem = soup.find(['h1', 'h2', 'h3'])

            # Date
            published_at = None
            date_container = soup.select_one('div.news-detail')
            if date_container:
                date_elem = date_container.select_one('span.time.date')
                time_elem = date_container.select_one('span.time:not(.date)')
                if date_elem:
                    date_text = date_elem.get_text().strip()
                    # Remove leading icon characters
                    date_text = re.sub(r'^\s*\S+\s+', '', date_text)
                    time_text = ''
                    if time_elem:
                        time_text = time_elem.get_text().strip()
                        time_text = re.sub(r'^\s*\S+\s+', '', time_text)
                    combined = f"{date_text} {time_text}".strip()
                    published_at = parse_azerbaijani_date(combined)

            # Content
            content = None
            content_elem = soup.select_one('div.news-text[itemprop="articleBody"]')
            if not content_elem:
                content_elem = soup.select_one('div.news-text')
            if content_elem:
                for unwanted in content_elem.select('script, style, iframe, ins'):
                    unwanted.decompose()
                paragraphs = content_elem.find_all('p')
                parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 10]
                content = '\n\n'.join(parts)

            result = {'content': content, 'author': None, 'metadata': {}}
            if published_at:
                result['published_at'] = published_at
            return result

        except Exception as e:
            logger.error(f"Error parsing fed.az detail: {e}")
            return None


if __name__ == "__main__":
    scraper = FedScraper()
    print(f"Fed scraper initialized for: {scraper.source_name}")
