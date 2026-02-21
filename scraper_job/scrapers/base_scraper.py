"""
Base scraper class
All news source scrapers inherit from this class
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from scraper_job.utils.database import DatabaseManager
from scraper_job.utils.helpers import fetch_page, parse_html
from scraper_job.config import MAX_PAGES_PER_RUN


class BaseScraper(ABC):
    """
    Abstract base class for all news scrapers

    Subclasses must implement:
        - parse_article_list(): Extract article links from listing page
        - parse_article_detail(): Extract full article content from detail page
    """

    def __init__(self, source_domain: str):
        """
        Initialize scraper

        Args:
            source_domain: Domain name of the news source (e.g., 'sonxeber.az')
        """
        self.source_domain = source_domain
        self.db = DatabaseManager()

        # Load source configuration from database
        self.source_config = self.db.get_news_source(source_domain)
        if not self.source_config:
            raise ValueError(f"News source '{source_domain}' not found in database")

        self.source_id = self.source_config['id']
        self.source_name = self.source_config['name']
        self.base_url = self.source_config['base_url']
        self.scraper_config = self.source_config.get('scraper_config', {})
        self.pagination_type = self.source_config.get('pagination_type', 'query_param')

        logger.info(f"Initialized scraper for {self.source_name} ({self.source_domain})")

    @abstractmethod
    def parse_article_list(self, soup, page_number: int = 1) -> List[Dict]:
        """
        Parse article listing page and extract article metadata

        Args:
            soup: BeautifulSoup object of the listing page
            page_number: Current page number

        Returns:
            List of article dictionaries with at minimum:
                - source_article_id: Unique ID from source
                - title: Article title
                - url: Full URL to article
                - published_at: Publication datetime (can be None)
                - image_url: Image URL (can be None)
                - excerpt: Short description (can be None)
        """
        pass

    @abstractmethod
    def parse_article_detail(self, soup, article_url: str) -> Optional[Dict]:
        """
        Parse article detail page and extract full content

        Args:
            soup: BeautifulSoup object of the article detail page
            article_url: URL of the article

        Returns:
            Dictionary with:
                - content: Full article text content
                - author: Article author (can be None)
                - category: Article category (can be None)
                - Any other metadata specific to this source
        """
        pass

    def get_listing_url(self, page_number: int = 1) -> str:
        """
        Generate URL for article listing page

        Args:
            page_number: Page number to fetch

        Returns:
            Full URL for the listing page
        """
        if page_number == 1:
            # First page is usually the homepage or main listing
            return self.base_url

        # Handle different pagination types
        if self.pagination_type == 'query_param':
            param_name = self.scraper_config.get('pagination_param', 'page')

            if param_name == 'start':
                # Some sites use ?start=2, ?start=3, etc.
                param_value = page_number
            else:
                # Most use ?page=2, ?page=3, etc.
                param_value = page_number

            return f"{self.base_url}?{param_name}={param_value}"

        elif self.pagination_type == 'path_based':
            # e.g., /page/2/, /page/3/
            return f"{self.base_url}/page/{page_number}/"

        else:
            # Default to query param
            return f"{self.base_url}?page={page_number}"

    def scrape_list_page(self, page_number: int = 1) -> List[Dict]:
        """
        Scrape a single listing page

        Args:
            page_number: Page number to scrape

        Returns:
            List of article dictionaries
        """
        url = self.get_listing_url(page_number)
        logger.info(f"Scraping list page {page_number}: {url}")

        # Fetch page
        response = fetch_page(url)
        if not response:
            logger.error(f"Failed to fetch listing page: {url}")
            return []

        # Parse HTML
        soup = parse_html(response.text)
        if not soup:
            logger.error(f"Failed to parse HTML for: {url}")
            return []

        # Extract articles using subclass implementation
        try:
            articles = self.parse_article_list(soup, page_number)
            logger.info(f"Found {len(articles)} articles on page {page_number}")
            return articles
        except Exception as e:
            logger.error(f"Error parsing article list from {url}: {e}")
            return []

    def scrape_article_detail(self, article_url: str) -> Optional[Dict]:
        """
        Scrape full article content from detail page

        Args:
            article_url: URL of the article detail page

        Returns:
            Dictionary with article content or None if failed
        """
        logger.debug(f"Scraping article detail: {article_url}")

        # Fetch page
        response = fetch_page(article_url)
        if not response:
            return None

        # Parse HTML
        soup = parse_html(response.text)
        if not soup:
            return None

        # Extract content using subclass implementation
        try:
            content = self.parse_article_detail(soup, article_url)
            return content
        except Exception as e:
            logger.error(f"Error parsing article detail from {article_url}: {e}")
            return None

    def run(
        self,
        max_pages: int = MAX_PAGES_PER_RUN,
        scrape_details: bool = False,
        job_type: str = 'incremental',
        triggered_by: str = 'manual'
    ) -> Dict:
        """
        Run the scraper

        Args:
            max_pages: Maximum number of listing pages to scrape
            scrape_details: Whether to scrape full article content
            job_type: Type of scraping job
            triggered_by: What triggered this scrape

        Returns:
            Dictionary with scraping statistics
        """
        logger.info(f"Starting scrape job for {self.source_name}")
        logger.info(f"Max pages: {max_pages}, Scrape details: {scrape_details}")

        # Create scrape job in database
        job_id = self.db.create_scrape_job(
            source_id=self.source_id,
            job_type=job_type,
            triggered_by=triggered_by
        )

        stats = {
            'job_id': job_id,
            'articles_found': 0,
            'articles_new': 0,
            'articles_updated': 0,
            'articles_failed': 0,
            'pages_scraped': 0
        }

        try:
            # Scrape listing pages
            for page_num in range(1, max_pages + 1):
                articles = self.scrape_list_page(page_num)

                if not articles:
                    logger.info(f"No articles found on page {page_num}, stopping")
                    break

                stats['pages_scraped'] = page_num
                stats['articles_found'] += len(articles)

                # Save articles to database
                for article in articles:
                    try:
                        # Add source_id
                        article['source_id'] = self.source_id

                        # Scrape detail page if requested
                        if scrape_details and not article.get('content'):
                            detail_data = self.scrape_article_detail(article['url'])
                            if detail_data:
                                article.update(detail_data)
                                article['is_processed'] = True

                        # Insert into database
                        article_id = self.db.insert_article(article)

                        if article_id:
                            stats['articles_new'] += 1
                        else:
                            # Article already exists
                            pass

                    except Exception as e:
                        logger.error(f"Error saving article {article.get('url')}: {e}")
                        stats['articles_failed'] += 1
                        self.db.log_scrape_error(
                            job_id=job_id,
                            source_id=self.source_id,
                            url=article.get('url', ''),
                            error_type='save_error',
                            error_message=str(e)
                        )

            # Update job status
            self.db.update_scrape_job(
                job_id=job_id,
                status='completed',
                articles_found=stats['articles_found'],
                articles_new=stats['articles_new'],
                articles_updated=stats['articles_updated'],
                articles_failed=stats['articles_failed']
            )

            logger.info(f"Scrape job completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Scrape job failed: {e}")
            self.db.update_scrape_job(
                job_id=job_id,
                status='failed',
                articles_found=stats['articles_found'],
                articles_new=stats['articles_new'],
                articles_failed=stats['articles_failed'],
                error_message=str(e)
            )
            raise
