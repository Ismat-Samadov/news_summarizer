"""
Axar.az News Scraper

Website structure:
- URL Pattern: /news/{category}/{id}.html
- Date Format: "21 Fevral 23:50" or "18:59"
- Unique ID: Numeric ID in URL
- Note: Only scrapes static content from initial page load (no infinite scroll)
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


class AxarScraper(BaseScraper):
    """Scraper for axar.az"""

    def __init__(self):
        super().__init__(source_domain='axar.az')

    def extract_article_id(self, url: str) -> Optional[str]:
        """
        Extract article ID from URL
        Example: /news/planet/1064588.html -> 1064588
        """
        match = re.search(r'/(\d+)\.html', url)
        return match.group(1) if match else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        """Parse article listing page"""
        articles = []

        # Find all article links - Axar uses /news/{category}/{id}.html pattern
        article_links = soup.find_all('a', href=re.compile(r'/news/[^/]+/\d+\.html'))

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
                title = None
                # Try <strong> tag first
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

                # Find image
                image_url = None
                if container:
                    img = container.find('img')
                    if img:
                        image_url = extract_attribute(img, 'src') or extract_attribute(img, 'data-src')
                        if image_url:
                            image_url = normalize_url(image_url, self.base_url)

                # Find date and time
                # Axar.az uses formats like "21 Fevral 23:50" or "18:59"
                published_at = None
                if container:
                    # Look for date/time pattern
                    date_time_pattern = re.compile(
                        r'(\d{1,2}\s+(?:yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+\d{1,2}:\d{2}|\d{1,2}:\d{2})',
                        re.IGNORECASE
                    )

                    # Search in all text nodes
                    all_text = container.get_text()
                    match = date_time_pattern.search(all_text)
                    if match:
                        date_str = match.group(0).strip()

                        # If only time (e.g., "18:59"), assume today
                        if re.match(r'^\d{1,2}:\d{2}$', date_str):
                            now = datetime.now()
                            date_str = f"{now.day} {now.strftime('%B')} {date_str}".lower()

                        published_at = parse_azerbaijani_date(date_str)

                # Extract category from URL
                category_match = re.search(r'/news/([^/]+)/', url)
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

            # Look for full date pattern
            date_pattern = re.compile(
                r'\d{1,2}\s+(?:yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+\d{4}\s+\d{1,2}:\d{2}',
                re.IGNORECASE
            )

            match = date_pattern.search(all_text)
            if match:
                date_str = match.group(0)
                published_at = parse_azerbaijani_date(date_str)

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
    scraper = AxarScraper()
    print(f"Axar scraper initialized for: {scraper.source_name}")
