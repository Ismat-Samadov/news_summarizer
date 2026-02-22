"""
APA.az News Scraper

Website structure:
- URL Pattern: /{category}/{slug}-{id}
- Pagination: ?page=2
- Date Format: Separate time "17:44" and date "21 fevral 2026"
- Image Path: /storage/news/{year}/{month}/
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


class APAScraper(BaseScraper):
    """Scraper for apa.az (Azerbaijan Press Agency)"""

    def __init__(self):
        super().__init__(source_domain='apa.az')

    def extract_article_id(self, url: str) -> Optional[str]:
        """
        Extract article ID from URL
        Example: /hadise/gencede-xestexana-941123 -> 941123
        """
        match = re.search(r'-(\d+)$', url)
        return match.group(1) if match else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        """Parse article listing page"""
        articles = []

        # Find all article links matching pattern /{category}/{slug}-{id}
        article_links = soup.find_all('a', href=re.compile(r'/[^/]+/[\w-]+-\d+$'))

        seen_ids = set()

        for link in article_links:
            try:
                url = extract_attribute(link, 'href')
                if not url:
                    continue

                # Skip non-article pages (about, contact, etc.)
                if any(skip in url for skip in ['/haqqimizda', '/elaqe', '/reklam']):
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
                    # Try to find in heading within parent
                    parent = link.find_parent(['div', 'article', 'li'])
                    if parent:
                        heading = parent.find(['h2', 'h3', 'h4'])
                        if heading:
                            title = extract_text(heading)

                if not title or len(title) < 10:
                    continue

                # Find container
                container = link.find_parent(['div', 'article', 'li'])

                # Find image
                image_url = None
                if container:
                    img = container.find('img')
                    if img:
                        image_url = extract_attribute(img, 'src') or extract_attribute(img, 'data-src')
                        if image_url:
                            image_url = normalize_url(image_url, self.base_url)

                # Find date and time - APA shows them separately
                published_at = None
                if container:
                    # Look for time pattern (HH:MM)
                    time_pattern = re.compile(r'\d{1,2}:\d{2}')
                    # Look for date pattern (DD month YYYY)
                    date_pattern = re.compile(
                        r'\d+\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+\d{4}',
                        re.IGNORECASE
                    )

                    time_text = container.find(text=time_pattern)
                    date_text = container.find(text=date_pattern)

                    if date_text:
                        date_str = date_text.strip()
                        time_str = time_text.strip() if time_text else "00:00"

                        # Combine date and time
                        full_date_str = f"{date_str} {time_str}"
                        published_at = parse_azerbaijani_date(full_date_str)

                # Extract category and slug
                category_match = re.search(r'/([^/]+)/[\w-]+-\d+$', url)
                category = category_match.group(1) if category_match else None

                slug_match = re.search(r'/([\w-]+)-\d+$', url)
                slug = slug_match.group(1) if slug_match else None

                article = {
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': full_url,
                    'image_url': image_url,
                    'published_at': published_at,
                    'excerpt': None,
                    'slug': slug,
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
                'article.content'
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    paragraphs = content_elem.find_all('p')
                    content_parts = [extract_text(p) for p in paragraphs if len(extract_text(p)) > 20]
                    content = '\n\n'.join(content_parts)
                    if content:
                        break

            # Fallback
            if not content:
                all_paragraphs = soup.find_all('p')
                content_parts = [extract_text(p) for p in all_paragraphs if len(extract_text(p)) > 20]
                content = '\n\n'.join(content_parts)

            # Find publication date if not in listing
            published_at = None
            all_text = soup.get_text()

            # Try to find date + time pattern
            time_pattern = re.compile(r'\d{1,2}:\d{2}')
            date_pattern = re.compile(
                r'\d+\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr)\s+\d{4}',
                re.IGNORECASE
            )

            time_match = time_pattern.search(all_text)
            date_match = date_pattern.search(all_text)

            if date_match:
                date_str = date_match.group(0)
                time_str = time_match.group(0) if time_match else "00:00"
                full_date_str = f"{date_str} {time_str}"
                published_at = parse_azerbaijani_date(full_date_str)

            # Find author
            author = None
            author_elem = soup.find(['span', 'div'], class_=re.compile(r'author|muellif'))
            if author_elem:
                author = extract_text(author_elem)

            # Find category
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
    scraper = APAScraper()
    print(f"APA scraper initialized for: {scraper.source_name}")
