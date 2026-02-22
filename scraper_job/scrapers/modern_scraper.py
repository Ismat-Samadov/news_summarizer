"""
Modern.az News Scraper

Website structure:
- URL Pattern: /az/{category}/{id}/{slug}/
- Date Format: "HH:MM, Bu gün" (Today) or "HH:MM, DD Month YYYY"
- Images: Lazy loaded with data-src attribute
- Unique ID: Numeric ID in URL path
"""

import re
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url, parse_azerbaijani_date
)


class ModernScraper(BaseScraper):
    """Scraper for modern.az"""

    def __init__(self):
        super().__init__(source_domain='modern.az')

    def extract_article_id(self, url: str) -> Optional[str]:
        """
        Extract article ID from URL
        Example: /az/idman/571636/ulviyye-feteliyeva/ -> 571636
        """
        match = re.search(r'/(\d+)/', url)
        return match.group(1) if match else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        """Parse article listing page"""
        articles = []

        # Find all article links - Modern uses /az/{category}/{id}/{slug}/ pattern
        # Can be relative (/az/...) or absolute (https://modern.az/az/...)
        # Skip static pages
        skip_patterns = ['/haqqinda', '/elaqe', '/reklam', '/login', '/qeydiyyat', '/arxiv']

        article_links = soup.find_all('a', href=re.compile(r'(/az/[^/]+/\d+/|^https://modern\.az/az/[^/]+/\d+/)'))

        seen_ids = set()

        for link in article_links:
            try:
                url = extract_attribute(link, 'href')
                if not url:
                    continue

                # Skip non-article pages
                if any(skip in url for skip in skip_patterns):
                    continue

                # Normalize URL
                full_url = normalize_url(url, self.base_url)

                # Extract article ID
                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue

                seen_ids.add(article_id)

                # Extract title
                title = None
                # Try <strong> tag first (common in Modern.az)
                strong = link.find('strong')
                if strong:
                    title = extract_text(strong)

                # Try <h3> tag
                if not title:
                    h3 = link.find('h3')
                    if h3:
                        title = extract_text(h3)

                # Try link text directly
                if not title:
                    title = extract_text(link)

                # Try parent container
                if not title or len(title) < 10:
                    parent = link.find_parent(['div', 'article', 'li'])
                    if parent:
                        for heading in parent.find_all(['h1', 'h2', 'h3', 'h4', 'strong']):
                            heading_text = extract_text(heading)
                            if heading_text and len(heading_text) >= 10:
                                title = heading_text
                                break

                if not title or len(title) < 10:
                    continue

                # Find container for metadata
                container = link.find_parent(['div', 'article', 'li'])

                # Find image (Modern.az uses lazy loading with data-src)
                image_url = None
                if container:
                    img = container.find('img')
                    if img:
                        # Try data-src first (lazy loading)
                        image_url = extract_attribute(img, 'data-src') or extract_attribute(img, 'src')
                        if image_url:
                            # Handle protocol-relative URLs
                            if image_url.startswith('//'):
                                image_url = 'https:' + image_url
                            else:
                                image_url = normalize_url(image_url, self.base_url)

                # Find date and time
                # Modern.az uses formats like:
                # - "18:28, Bu gün" (Today)
                # - "18:28, 22 fevral 2026"
                published_at = None
                if container:
                    # Look for time pattern followed by date
                    time_date_pattern = re.compile(
                        r'(\d{1,2}:\d{2}),\s*(Bu gün|Dünən|\d+\s+(?:yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+\d{4})',
                        re.IGNORECASE
                    )

                    time_date_text = container.find(text=time_date_pattern)
                    if time_date_text:
                        match = time_date_pattern.search(time_date_text)
                        if match:
                            time_str = match.group(1)
                            date_str = match.group(2)

                            # Handle "Bu gün" (Today) and "Dünən" (Yesterday)
                            now = datetime.now()
                            if date_str.lower() == 'bu gün':
                                date_str = now.strftime('%d %B %Y')
                            elif date_str.lower() == 'dünən':
                                from datetime import timedelta
                                yesterday = now - timedelta(days=1)
                                date_str = yesterday.strftime('%d %B %Y')

                            # Combine time and date
                            full_date_str = f"{date_str} {time_str}"
                            published_at = parse_azerbaijani_date(full_date_str)

                # Extract category from URL
                category_match = re.search(r'/az/([^/]+)/', url)
                category = category_match.group(1) if category_match else None

                article = {
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': full_url,
                    'image_url': image_url,
                    'published_at': published_at,
                    'excerpt': None,
                    'slug': None,
                    'metadata': {
                        'category': category
                    }
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
            # Find main content
            content = None
            content_selectors = [
                'div.article-content',
                'div.news-content',
                'div[itemprop="articleBody"]',
                'div.content',
                'article'
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    paragraphs = content_elem.find_all('p')
                    content_parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 20]
                    content = '\n\n'.join(content_parts)
                    if content:
                        break

            # Fallback: get all paragraphs
            if not content:
                all_paragraphs = soup.find_all('p')
                content_parts = [extract_text(p) for p in all_paragraphs if len(extract_text(p)) > 20]
                content = '\n\n'.join(content_parts)

            # Find publication date from detail page
            published_at = None
            all_text = soup.get_text()

            # Look for time and date pattern
            time_date_pattern = re.compile(
                r'(\d{1,2}:\d{2}),?\s*(\d+\s+(?:yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+\d{4})',
                re.IGNORECASE
            )

            match = time_date_pattern.search(all_text)
            if match:
                time_str = match.group(1)
                date_str = match.group(2)
                full_date_str = f"{date_str} {time_str}"
                published_at = parse_azerbaijani_date(full_date_str)

            # Find author
            author = None
            author_elem = soup.find(['span', 'div', 'p'], class_=re.compile(r'author|muellif|yazar'))
            if author_elem:
                author = extract_text(author_elem)

            # Find category from breadcrumb
            category = None
            breadcrumb = soup.find(['nav', 'div'], class_=re.compile(r'breadcrumb'))
            if breadcrumb:
                links = breadcrumb.find_all('a')
                if len(links) > 1:
                    category = extract_text(links[-1])

            result = {
                'content': content,
                'author': author,
                'metadata': {
                    'category': category
                }
            }

            if published_at:
                result['published_at'] = published_at

            return result

        except Exception as e:
            logger.error(f"Error parsing article detail: {e}")
            return None


# For backwards compatibility
if __name__ == "__main__":
    scraper = ModernScraper()
    print(f"Modern scraper initialized for: {scraper.source_name}")
