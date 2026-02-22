"""
Azertag.az News Scraper

Website structure:
- URL Pattern: /xeber/{slug}-{id}
- Pagination: ?page=2
- Date Format: "21.02.2026 [19:22]"
- Image Path: Various CDN paths
"""

import re
from typing import List, Dict, Optional
from loguru import logger

from scraper_job.scrapers.base_scraper import BaseScraper
from scraper_job.utils.helpers import (
    extract_text, extract_attribute,
    normalize_url, parse_azerbaijani_date
)


class AzertagScraper(BaseScraper):
    """Scraper for azertag.az (State News Agency)"""

    def __init__(self):
        super().__init__(source_domain='azertag.az')

    def extract_article_id(self, url: str) -> Optional[str]:
        """
        Extract article ID from URL
        Example: /xeber/sabah-bakida-hava-4034987 -> 4034987
        """
        match = re.search(r'-(\d+)$', url)
        return match.group(1) if match else None

    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        """Parse article listing page"""
        articles = []

        # Find all article links matching pattern /xeber/{slug}-{id}
        article_links = soup.find_all('a', href=re.compile(r'/xeber/[\w_]+-\d+'))

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
                    # Try to find in parent container
                    parent = link.find_parent(['div', 'li', 'article'])
                    if parent:
                        title_elem = parent.find(['h2', 'h3', 'h4', 'a'])
                        if title_elem:
                            title = extract_text(title_elem)

                if not title or len(title) < 10:
                    continue

                # Find image
                image_url = None
                container = link.find_parent(['div', 'article', 'li'])
                if container:
                    img = container.find('img')
                    if img:
                        image_url = extract_attribute(img, 'src') or extract_attribute(img, 'data-src')
                        if image_url:
                            image_url = normalize_url(image_url, self.base_url)

                # Find date - Azertag uses format "21.02.2026 [19:22]"
                published_at = None
                if container:
                    # Look for date pattern DD.MM.YYYY [HH:MM]
                    date_pattern = re.compile(r'\d{2}\.\d{2}\.\d{4}\s*\[\d{2}:\d{2}\]')
                    date_text = container.find(text=date_pattern)
                    if date_text:
                        date_str = date_text.strip()
                        published_at = parse_azerbaijani_date(date_str)

                # Extract slug from URL
                slug_match = re.search(r'/xeber/([\w_]+)-\d+', url)
                slug = slug_match.group(1) if slug_match else None

                article = {
                    'source_article_id': article_id,
                    'title': title.strip(),
                    'url': full_url,
                    'image_url': image_url,
                    'published_at': published_at,
                    'excerpt': None,
                    'slug': slug
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

            # Fallback: find all paragraphs
            if not content:
                all_paragraphs = soup.find_all('p')
                content_parts = [extract_text(p) for p in all_paragraphs if len(extract_text(p)) > 20]
                content = '\n\n'.join(content_parts)

            # Find publication date if not captured in listing
            published_at = None
            date_pattern = re.compile(r'\d{2}\.\d{2}\.\d{4}\s*\[\d{2}:\d{2}\]')
            all_text = soup.get_text()
            match = date_pattern.search(all_text)
            if match:
                published_at = parse_azerbaijani_date(match.group(0))

            # Find author
            author = None
            author_elem = soup.find(['span', 'div'], class_=re.compile(r'author|muellif'))
            if author_elem:
                author = extract_text(author_elem)

            # Find category (usually in breadcrumbs or URL)
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
    scraper = AzertagScraper()
    print(f"Azertag scraper initialized for: {scraper.source_name}")
