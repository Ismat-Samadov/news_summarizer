"""
Metbuat.az News Scraper

Website structure:
- URL Pattern: /news/{id}/{slug}.html
- Pagination: ?page=2&per-page=39
- Date Format: "21 Fevral 2026 12:06" (full timestamp)
- Image Path: /images/metbuat/images_t/{ID}.jpg
"""

import re
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url, parse_azerbaijani_date
)


class MetbuatScraper(BaseScraper):
    """Scraper for metbuat.az"""

    def __init__(self):
        super().__init__(source_domain='metbuat.az')
        self.per_page = self.scraper_config.get('per_page', 39)

    def get_listing_url(self, page_number: int = 1) -> str:
        """Generate listing URL for Metbuat"""
        if page_number == 1:
            return self.base_url
        else:
            return f"{self.base_url}/?page={page_number}&per-page={self.per_page}"

    def extract_article_id(self, url: str) -> Optional[str]:
        """
        Extract article ID from URL
        Example: /news/1547127/ilham-eliyev-serencam-imzaladi.html -> 1547127
        """
        match = re.search(r'/news/(\d+)/', url)
        return match.group(1) if match else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        """Parse article listing page"""
        articles = []

        # Find all article links with the pattern /news/{id}/{slug}.html
        article_links = soup.find_all('a', href=re.compile(r'/news/\d+/[\w-]+\.html'))

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

                # Extract title
                title = extract_text(link)
                if not title or len(title) < 10:
                    # Try to find in parent heading
                    parent = link.find_parent(['h1', 'h2', 'h3', 'h4', 'div', 'article'])
                    if parent:
                        heading = parent.find(['h1', 'h2', 'h3', 'h4'])
                        if heading:
                            title = extract_text(heading)

                if not title or len(title) < 10:
                    continue

                # Find image
                image_url = None
                container = link.find_parent(['div', 'article', 'li', 'section'])
                if container:
                    img = container.find('img')
                    if img:
                        # Try src first, then data-src for lazy loading
                        image_url = extract_attribute(img, 'src') or extract_attribute(img, 'data-src')
                        if image_url:
                            image_url = normalize_url(image_url, self.base_url)

                # Find date - Metbuat uses format "21 Fevral 2026 12:06"
                published_at = None
                if container:
                    # Look for date pattern
                    date_candidates = container.find_all(
                        text=re.compile(
                            r'\d+\s+(Yanvar|Fevral|Mart|Aprel|May|İyun|İyul|Avqust|Sentyabr|Oktyabr|Noyabr|Dekabr)\s+\d{4}',
                            re.IGNORECASE
                        )
                    )
                    if date_candidates:
                        date_str = date_candidates[0].strip()
                        published_at = parse_azerbaijani_date(date_str)

                # Extract excerpt if available
                excerpt = None
                if container:
                    excerpt_elem = container.find(['p', 'div'], class_=re.compile(r'excerpt|description|summary'))
                    if excerpt_elem:
                        excerpt = extract_text(excerpt_elem)

                article = {
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': full_url,
                    'image_url': image_url,
                    'published_at': published_at,
                    'excerpt': excerpt,
                    'slug': url.strip('/').split('/')[-1].replace('.html', '') if '/' in url else None
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
            content_selectors = [
                'div.news-content',
                'div.article-content',
                'div.content',
                'div[itemprop="articleBody"]',
                'article'
            ]

            content = None
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Extract text from paragraphs
                    paragraphs = content_elem.find_all('p')
                    content_parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 20]
                    content = '\n\n'.join(content_parts)
                    if content:
                        break

            # Fallback: find all paragraphs in main area
            if not content:
                main = soup.find('main') or soup.find('div', id=re.compile(r'content|main'))
                if main:
                    paragraphs = main.find_all('p')
                    content_parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 20]
                    content = '\n\n'.join(content_parts)

            # Find author
            author = None
            author_selectors = [
                ['span', {'class': re.compile(r'author')}],
                ['div', {'class': re.compile(r'author')}],
                ['a', {'class': re.compile(r'author')}],
                ['span', {'itemprop': 'author'}]
            ]
            for selector in author_selectors:
                author_elem = soup.find(*selector)
                if author_elem:
                    author = extract_text(author_elem)
                    break

            # Find category
            category = None
            # Category is usually in breadcrumbs or as a link
            breadcrumb = soup.find(['nav', 'div'], class_=re.compile(r'breadcrumb'))
            if breadcrumb:
                category_links = breadcrumb.find_all('a')
                if len(category_links) > 1:
                    # Usually the second or third link is the category
                    category = extract_text(category_links[-2] if len(category_links) > 2 else category_links[-1])

            if not category:
                category_elem = soup.find(['a', 'span'], class_=re.compile(r'category'))
                if category_elem:
                    category = extract_text(category_elem)

            # Find view count if available
            view_count = 0
            views_elem = soup.find(text=re.compile(r'baxış|views', re.IGNORECASE))
            if views_elem:
                # Extract number from text
                numbers = re.findall(r'\d+', views_elem)
                if numbers:
                    view_count = int(numbers[0])

            return {
                'content': content,
                'author': author,
                'view_count': view_count,
                'metadata': {
                    'category': category
                }
            }

        except Exception as e:
            logger.error(f"Error parsing article detail: {e}")
            return None


# For backwards compatibility
if __name__ == "__main__":
    scraper = MetbuatScraper()
    print(f"Metbuat scraper initialized for: {scraper.source_name}")
