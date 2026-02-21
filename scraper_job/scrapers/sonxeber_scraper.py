"""
Sonxeber.az News Scraper

Website structure:
- URL Pattern: /{article_id}/{slug-title}
- Pagination: ?start=2 (incremental)
- Date Format: "21 fevral"
- Image Path: /uploads/ss_{ID}_{hash}.jpg
"""

import re
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url, parse_azerbaijani_date
)


class SonxeberScraper(BaseScraper):
    """Scraper for sonxeber.az"""

    def __init__(self):
        super().__init__(source_domain='sonxeber.az')

    def get_listing_url(self, page_number: int = 1) -> str:
        """Generate listing URL for Sonxeber"""
        if page_number == 1:
            return f"{self.base_url}/xeberler/"
        else:
            return f"{self.base_url}/xeberler/?start={page_number}"

    def extract_article_id(self, url: str) -> Optional[str]:
        """
        Extract article ID from URL
        Example: /388358/gurcustan-azerbaycandan... -> 388358
        """
        match = re.search(r'/(\d+)/', url)
        return match.group(1) if match else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        """Parse article listing page"""
        articles = []

        # Collect all links and filter by URL pattern /{number}/{slug}
        # Some pages use non-ASCII slugs or wrap titles outside <a>, so be flexible.
        article_links = []
        for link in soup.find_all('a', href=True):
            href = extract_attribute(link, 'href')
            if not href:
                continue
            if re.search(r'/\d+/', href):
                article_links.append(link)

        seen_ids = set()

        for link in article_links:
            try:
                url = extract_attribute(link, 'href')
                if not url:
                    continue

                # Normalize URL
                full_url = normalize_url(url, self.base_url)

                # Extract article ID
                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue

                seen_ids.add(article_id)

                # Extract title (from link text, title attribute, or nearby heading)
                title = extract_text(link)
                if not title:
                    title = extract_attribute(link, 'title')

                if not title or len(title) < 5:
                    # Try to find title in parent or nearby elements
                    parent = link.find_parent(['h1', 'h2', 'h3', 'h4', 'div', 'li', 'section', 'article'])
                    if parent:
                        heading = parent.find(['h1', 'h2', 'h3', 'h4'])
                        if heading:
                            title = extract_text(heading)
                        if not title:
                            title = extract_text(parent)

                if not title or len(title) < 5:
                    continue

                # Find image (usually nearby the link)
                image_url = None
                # Try to find img in parent container
                container = link.find_parent(['div', 'article', 'li', 'section'])
                if container:
                    img = container.find('img')
                    if img:
                        image_url = extract_attribute(img, 'src')
                        if image_url:
                            image_url = normalize_url(image_url, self.base_url)

                # Find date (look for date pattern nearby)
                date_elem = None
                published_at = None
                if container:
                    # Look for date in various possible formats
                    date_candidates = container.find_all(
                        text=re.compile(
                            r'\d+\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)',
                            re.IGNORECASE
                        )
                    )
                    if date_candidates:
                        date_str = date_candidates[0].strip()
                        # Add current year if not present
                        if len(date_str.split()) == 2:
                            from datetime import datetime
                            date_str = f"{date_str} {datetime.now().year}"
                        published_at = parse_azerbaijani_date(date_str)

                article = {
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': full_url,
                    'image_url': image_url,
                    'published_at': published_at,
                    'excerpt': None,  # Not available on listing page
                    'slug': url.strip('/').split('/')[-1] if '/' in url else None
                }

                articles.append(article)
                logger.debug(f"Extracted article: {title[:50]}...")

            except Exception as e:
                logger.warning(f"Error parsing article link: {e}")
                continue

        return articles

    def parse_article_detail(self, soup, article_url: str) -> Optional[Dict]:
        """Parse article detail page"""
        try:
            # Find main content area
            # Try different possible content selectors
            content_selectors = [
                'div.article-content',
                'div.content',
                'div.news-content',
                'article',
                'div[itemprop="articleBody"]'
            ]

            content = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Extract text from paragraphs
                    paragraphs = content_elem.find_all(['p', 'div'])
                    content_parts = [extract_text(p) for p in paragraphs if extract_text(p)]
                    content = '\n\n'.join(content_parts)
                    if content:
                        break

            # If still no content, try to find all paragraphs in main area
            if not content:
                main = soup.find('main') or soup.find('div', class_=re.compile(r'main|content'))
                if main:
                    paragraphs = main.find_all('p')
                    content_parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 20]
                    content = '\n\n'.join(content_parts)

            # Find publication date - look for "Tarix: {date}" pattern
            published_at = None
            date_pattern = re.compile(r'Tarix:\s*(.+)', re.IGNORECASE)
            date_text = soup.find(text=date_pattern)
            if date_text:
                match = date_pattern.search(date_text)
                if match:
                    date_str = match.group(1).strip()
                    # Add current year if not present
                    if len(date_str.split()) == 2:
                        from datetime import datetime
                        date_str = f"{date_str} {datetime.now().year}"
                    published_at = parse_azerbaijani_date(date_str)

            # Find author
            author = None
            author_elem = soup.find(['span', 'div', 'p'], class_=re.compile(r'author|writer|muellif'))
            if author_elem:
                author = extract_text(author_elem)

            # Find category
            category = None
            category_elem = soup.find(['a', 'span'], class_=re.compile(r'category|kataqoriya'))
            if category_elem:
                category = extract_text(category_elem)

            result = {
                'content': content,
                'author': author,
                'metadata': {
                    'category': category
                }
            }

            # Add published_at if found
            if published_at:
                result['published_at'] = published_at

            return result

        except Exception as e:
            logger.error(f"Error parsing article detail: {e}")
            return None


# For backwards compatibility with old file structure
if __name__ == "__main__":
    scraper = SonxeberScraper()
    print(f"Sonxeber scraper initialized for: {scraper.source_name}")
