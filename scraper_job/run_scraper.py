"""
Main scraper runner
Runs news scrapers for all configured sources
"""

import sys
import argparse
from datetime import datetime
from loguru import logger

from scraper_job.config import LOG_LEVEL, LOG_FORMAT
from scraper_job.utils.database import DatabaseManager
from scraper_job.scrapers.sonxeber_scraper import SonxeberScraper
from scraper_job.scrapers.apa_scraper import APAScraper
from scraper_job.scrapers.report_scraper import ReportScraper
from scraper_job.scrapers.modern_scraper import ModernScraper
from scraper_job.scrapers.axar_scraper import AxarScraper
from scraper_job.scrapers.banker_scraper import BankerScraper
from scraper_job.scrapers.fed_scraper import FedScraper
from scraper_job.scrapers.marja_scraper import MarjaScraper
from scraper_job.scrapers.oxu_scraper import OxuScraper
from scraper_job.scrapers.qafqazinfo_scraper import QafqazinfoScraper
from scraper_job.scrapers.trend_scraper import TrendScraper

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level=LOG_LEVEL
)
logger.add(
    "logs/scraper_{time}.log",
    rotation="1 day",
    retention="30 days",
    format=LOG_FORMAT,
    level="DEBUG"
)


# Scraper registry
# Note: metbuat.az and azertag.az removed due to 403 anti-scraping blocks
SCRAPERS = {
    'sonxeber.az': SonxeberScraper,
    'apa.az': APAScraper,
    'report.az': ReportScraper,
    'modern.az': ModernScraper,
    'axar.az': AxarScraper,
    'banker.az': BankerScraper,
    'fed.az': FedScraper,
    'marja.az': MarjaScraper,
    'oxu.az': OxuScraper,
    'qafqazinfo.az': QafqazinfoScraper,
    'trend.az': TrendScraper,
}


def run_scraper(
    source_domain: str,
    max_pages: int = 3,
    scrape_details: bool = False,
    triggered_by: str = 'manual'
):
    """
    Run scraper for a specific news source

    Args:
        source_domain: Domain name of the news source
        max_pages: Maximum number of pages to scrape
        scrape_details: Whether to scrape full article content
        triggered_by: What triggered this scrape
    """
    logger.info(f"{'='*60}")
    logger.info(f"Starting scraper for: {source_domain}")
    logger.info(f"Max pages: {max_pages}, Scrape details: {scrape_details}")
    logger.info(f"{'='*60}")

    try:
        # Get scraper class
        scraper_class = SCRAPERS.get(source_domain)
        if not scraper_class:
            logger.error(f"No scraper found for {source_domain}")
            logger.info(f"Available scrapers: {', '.join(SCRAPERS.keys())}")
            return None

        # Initialize scraper
        scraper = scraper_class()

        # Run scraper
        stats = scraper.run(
            max_pages=max_pages,
            scrape_details=scrape_details,
            job_type='incremental' if max_pages <= 5 else 'full_scrape',
            triggered_by=triggered_by
        )

        logger.success(f"Scraper completed successfully!")
        logger.info(f"Statistics:")
        logger.info(f"  - Old articles deleted: {stats.get('articles_deleted', 0)}")
        logger.info(f"  - Pages scraped: {stats['pages_scraped']}")
        logger.info(f"  - Articles found: {stats['articles_found']}")
        logger.info(f"  - New articles: {stats['articles_new']}")
        logger.info(f"  - Failed: {stats['articles_failed']}")

        return stats

    except Exception as e:
        logger.error(f"Scraper failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def run_all_scrapers(max_pages: int = 3, scrape_details: bool = False):
    """Run all available scrapers"""
    import time

    logger.info(f"Running all scrapers ({len(SCRAPERS)} sources)")

    results = {}
    for i, source_domain in enumerate(SCRAPERS.keys()):
        try:
            # Add delay between scrapers to avoid rate limiting
            if i > 0:
                delay = 5  # 5 seconds between scrapers
                logger.info(f"Waiting {delay} seconds before next scraper...")
                time.sleep(delay)

            stats = run_scraper(
                source_domain=source_domain,
                max_pages=max_pages,
                scrape_details=scrape_details,
                triggered_by='batch'
            )
            results[source_domain] = stats
        except Exception as e:
            logger.error(f"Error running scraper for {source_domain}: {e}")
            results[source_domain] = None

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY - All Scrapers")
    logger.info(f"{'='*60}")

    total_found = 0
    total_new = 0
    total_failed = 0

    for source, stats in results.items():
        if stats:
            logger.info(f"{source}: {stats['articles_new']} new / {stats['articles_found']} found")
            total_found += stats['articles_found']
            total_new += stats['articles_new']
            total_failed += stats['articles_failed']
        else:
            logger.warning(f"{source}: FAILED")

    logger.info(f"\nTotals:")
    logger.info(f"  - Articles found: {total_found}")
    logger.info(f"  - New articles: {total_new}")
    logger.info(f"  - Failed: {total_failed}")

    return results


def show_stats():
    """Display database statistics"""
    db = DatabaseManager()
    stats = db.get_stats()

    logger.info(f"\n{'='*60}")
    logger.info(f"DATABASE STATISTICS")
    logger.info(f"{'='*60}\n")

    logger.info("Article Statistics:")
    for source_stat in stats['article_stats']:
        logger.info(f"  {source_stat['source_name']}:")
        logger.info(f"    - Total articles: {source_stat['total_articles']}")
        logger.info(f"    - Processed: {source_stat['processed_articles']}")
        if source_stat.get('last_scrape_time'):
            logger.info(f"    - Last scrape: {source_stat['last_scrape_time']}")

    logger.info(f"\nJob Statistics:")
    for job_stat in stats['job_stats']:
        if job_stat['total_jobs'] > 0:
            logger.info(f"  {job_stat['source_name']}:")
            logger.info(f"    - Total jobs: {job_stat['total_jobs']}")
            logger.info(f"    - Completed: {job_stat['completed_jobs']}")
            logger.info(f"    - Failed: {job_stat['failed_jobs']}")
            if job_stat['avg_duration_seconds']:
                logger.info(f"    - Avg duration: {job_stat['avg_duration_seconds']:.1f}s")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='News Scraper Runner')

    parser.add_argument(
        'command',
        choices=['run', 'run-all', 'stats', 'list'],
        help='Command to execute'
    )

    parser.add_argument(
        '-s', '--source',
        help='News source domain (e.g., sonxeber.az)'
    )

    parser.add_argument(
        '-p', '--pages',
        type=int,
        default=3,
        help='Maximum number of pages to scrape (default: 3)'
    )

    parser.add_argument(
        '-d', '--details',
        action='store_true',
        help='Scrape full article content (slower)'
    )

    parser.add_argument(
        '--triggered-by',
        default='manual',
        help='What triggered this scrape (manual, github_action, scheduled)'
    )

    args = parser.parse_args()

    # Create logs directory if it doesn't exist
    import os
    os.makedirs('logs', exist_ok=True)

    if args.command == 'list':
        logger.info("Available scrapers:")
        for domain in SCRAPERS.keys():
            logger.info(f"  - {domain}")

    elif args.command == 'stats':
        show_stats()

    elif args.command == 'run':
        if not args.source:
            logger.error("--source is required for 'run' command")
            sys.exit(1)

        run_scraper(
            source_domain=args.source,
            max_pages=args.pages,
            scrape_details=args.details,
            triggered_by=args.triggered_by
        )

    elif args.command == 'run-all':
        run_all_scrapers(
            max_pages=args.pages,
            scrape_details=args.details
        )


if __name__ == "__main__":
    main()
