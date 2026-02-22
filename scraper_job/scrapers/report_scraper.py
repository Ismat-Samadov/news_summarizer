"""
Report.az News Scraper

Website structure:
- URL Pattern: /{category}/{slug} (no numeric ID)
- Pagination: Query param based
- Date Format: "21 fevral, 2026" and "19:22" (separate)
- Unique ID: URL slug itself
"""

import re
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url, parse_azerbaijani_date
)


class ReportScraper(BaseScraper):
    """Scraper for report.az"""

    def __init__(self):
        super().__init__(source_domain='report.az')

    def extract_article_id(self, url: str) -> Optional[str]:
        """
        Extract article ID from URL (use slug as ID since no numeric ID)
        Example: /xarici-siyaset/sefir-ukrayna -> sefir-ukrayna
        """
        # Remove leading slash and split by /
        parts = url.strip('/').split('/')
        if len(parts) >= 2:
            # Return the slug (last part)
            return parts[-1]
        return None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        """Parse article listing page"""
        articles = []

        # Find all article links - Report uses /{category}/{slug} pattern
        # Skip static pages
        skip_patterns = ['/haqqimizda', '/elaqe', '/reklam', '/login', '/register']

        article_links = soup.find_all('a', href=re.compile(r'^/[^/]+/[\w-]+$'))

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

                # Extract article ID (slug)
                article_id = self.extract_article_id(url)
                if not article_id or article_id in seen_ids:
                    continue

                seen_ids.add(article_id)

                # Extract title
                title = extract_text(link)
                if not title or len(title) < 10:
                    # Try parent container
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

                # Find date and time - Report shows them separately
                # Date: "22 fevral, 2026", Time: "16:34"
                published_at = None
                if container:
                    # Look for date pattern with comma
                    date_pattern = re.compile(
                        r'\d+\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr),?\s+\d{4}',
                        re.IGNORECASE
                    )
                    # Look for time pattern
                    time_pattern = re.compile(r'\d{1,2}:\d{2}')

                    date_text = container.find(text=date_pattern)
                    time_text = container.find(text=time_pattern)

                    if date_text:
                        # Remove comma if present
                        date_str = date_text.strip().replace(',', '')
                        time_str = time_text.strip() if time_text else "00:00"

                        # Combine date and time
                        full_date_str = f"{date_str} {time_str}"
                        published_at = parse_azerbaijani_date(full_date_str)

                # Extract category from URL
                category_match = re.search(r'^/([^/]+)/', url)
                category = category_match.group(1) if category_match else None

                article = {
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': full_url,
                    'image_url': image_url,
                    'published_at': published_at,
                    'excerpt': None,
                    'slug': article_id,  # slug is the ID for Report
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

            # Fallback
            if not content:
                all_paragraphs = soup.find_all('p')
                content_parts = [extract_text(p) for p in all_paragraphs if len(extract_text(p)) > 20]
                content = '\n\n'.join(content_parts)

            # Find publication date
            published_at = None
            all_text = soup.get_text()

            date_pattern = re.compile(
                r'\d+\s+(yanvar|fevral|mart|aprel|may|iyun|iyul|avqust|sentyabr|oktyabr|noyabr|dekabr),?\s+\d{4}',
                re.IGNORECASE
            )
            time_pattern = re.compile(r'\d{1,2}:\d{2}')

            date_match = date_pattern.search(all_text)
            time_match = time_pattern.search(all_text)

            if date_match:
                date_str = date_match.group(0).replace(',', '')
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
    scraper = ReportScraper()
    print(f"Report scraper initialized for: {scraper.source_name}")
