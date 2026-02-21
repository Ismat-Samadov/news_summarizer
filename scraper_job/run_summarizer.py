"""
AI Summarization Runner
Generates AI summaries for scraped news articles using Google Gemini
"""

import sys
import argparse
from datetime import datetime
from loguru import logger

from scraper_job.config import LOG_LEVEL, LOG_FORMAT
from scraper_job.utils.database import DatabaseManager
from scraper_job.utils.summarizer import NewsSummarizer

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level=LOG_LEVEL
)
logger.add(
    "logs/summarizer_{time}.log",
    rotation="1 day",
    retention="30 days",
    format=LOG_FORMAT,
    level="DEBUG"
)


def summarize_articles(
    batch_size: int = 100,
    source_filter: str = None,
    triggered_by: str = 'manual'
):
    """
    Generate summaries for articles that haven't been summarized yet

    Args:
        batch_size: Number of articles to summarize in one run
        source_filter: Optional source domain to filter articles
        triggered_by: What triggered this summarization
    """
    logger.info(f"{'='*60}")
    logger.info(f"Starting AI Summarization")
    logger.info(f"Batch size: {batch_size}, Triggered by: {triggered_by}")
    logger.info(f"{'='*60}")

    # Initialize database and summarizer
    db = DatabaseManager()
    summarizer = NewsSummarizer()

    # Test Gemini connection
    logger.info("Testing Gemini API connection...")
    if not summarizer.test_connection():
        logger.error("Failed to connect to Gemini API. Check your GEMINI_API_KEY")
        return {
            'success': False,
            'error': 'Gemini API connection failed'
        }

    logger.success("Gemini API connection successful")

    # Get articles that need summarization
    logger.info(f"Fetching up to {batch_size} articles for summarization...")

    articles = db.get_articles_for_summarization(limit=batch_size)

    if not articles:
        logger.warning("No articles found that need summarization")
        return {
            'success': True,
            'articles_processed': 0,
            'articles_summarized': 0,
            'articles_failed': 0
        }

    logger.info(f"Found {len(articles)} articles to summarize")

    # Filter by source if specified
    if source_filter:
        articles = [a for a in articles if a.get('source_name', '').lower() == source_filter.lower()]
        logger.info(f"Filtered to {len(articles)} articles from source: {source_filter}")

    # Generate summaries
    results = summarizer.batch_summarize(articles, max_articles=batch_size)

    # Save summaries to database
    logger.info("Saving summaries to database...")

    summarized_count = 0
    failed_count = 0

    for result in results:
        if result['success'] and result['summary']:
            try:
                # Prepare summary data for database
                summary_data = {
                    'article_id': result['article_id'],
                    'summary_short': result['summary'].get('summary_short'),
                    'summary_medium': result['summary'].get('summary_medium'),
                    'summary_long': result['summary'].get('summary_long'),
                    'key_points': result['summary'].get('key_points'),
                    'entities': result['summary'].get('entities'),
                    'topics': result['summary'].get('topics'),
                    'sentiment': result['summary'].get('sentiment'),
                    'model_used': result['summary'].get('model_used'),
                    'model_version': result['summary'].get('model_version'),
                    'confidence_score': result['summary'].get('confidence_score')
                }

                # Insert summary into database
                summary_id = db.insert_summary(summary_data)

                if summary_id:
                    # Mark article as summarized
                    db.mark_article_summarized(result['article_id'])
                    summarized_count += 1
                    logger.debug(f"Saved summary for article {result['article_id']}")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to save summary for article {result['article_id']}")

            except Exception as e:
                logger.error(f"Error saving summary for article {result['article_id']}: {e}")
                failed_count += 1
        else:
            failed_count += 1

    # Print summary statistics
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARIZATION COMPLETED")
    logger.info(f"{'='*60}")
    logger.info(f"Articles processed: {len(results)}")
    logger.info(f"Successfully summarized: {summarized_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"{'='*60}\n")

    return {
        'success': True,
        'articles_processed': len(results),
        'articles_summarized': summarized_count,
        'articles_failed': failed_count
    }


def test_summarizer():
    """Test the summarizer with a sample article"""
    logger.info("Testing summarizer with sample article...")

    db = DatabaseManager()

    # Get one article for testing
    articles = db.get_articles_for_summarization(limit=1)

    if not articles:
        logger.error("No articles available for testing. Please scrape some articles first.")
        return False

    article = articles[0]
    logger.info(f"Testing with article: {article['title'][:50]}...")

    # Initialize summarizer
    summarizer = NewsSummarizer()

    # Test connection
    if not summarizer.test_connection():
        logger.error("Gemini API connection test failed")
        return False

    # Generate summary
    summary = summarizer.summarize_article(article)

    if summary:
        logger.success("Summary generation successful!")
        logger.info(f"\nShort Summary:\n{summary.get('summary_short', 'N/A')}\n")
        logger.info(f"Key Points: {summary.get('key_points', [])}")
        logger.info(f"Sentiment: {summary.get('sentiment', 'N/A')}")
        logger.info(f"Confidence: {summary.get('confidence_score', 0):.2f}")
        return True
    else:
        logger.error("Summary generation failed")
        return False


def show_summary_stats():
    """Display summary statistics"""
    db = DatabaseManager()

    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY STATISTICS")
    logger.info(f"{'='*60}\n")

    stats = db.get_stats()

    for source_stat in stats['article_stats']:
        if source_stat['total_articles'] > 0:
            logger.info(f"{source_stat['source_name']}:")
            logger.info(f"  Total articles: {source_stat['total_articles']}")
            logger.info(f"  Summarized: {source_stat['summarized_articles']}")

            if source_stat['total_articles'] > 0:
                percentage = (source_stat['summarized_articles'] / source_stat['total_articles']) * 100
                logger.info(f"  Percentage: {percentage:.1f}%\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI News Summarizer using Google Gemini')

    parser.add_argument(
        'command',
        choices=['run', 'test', 'stats'],
        help='Command to execute'
    )

    parser.add_argument(
        '-b', '--batch-size',
        type=int,
        default=100,
        help='Number of articles to summarize (default: 100)'
    )

    parser.add_argument(
        '-s', '--source',
        help='Filter articles by source domain'
    )

    parser.add_argument(
        '--triggered-by',
        default='manual',
        help='What triggered this summarization (manual, github_action, scheduled)'
    )

    args = parser.parse_args()

    # Create logs directory if it doesn't exist
    import os
    os.makedirs('logs', exist_ok=True)

    if args.command == 'test':
        success = test_summarizer()
        sys.exit(0 if success else 1)

    elif args.command == 'stats':
        show_summary_stats()

    elif args.command == 'run':
        result = summarize_articles(
            batch_size=args.batch_size,
            source_filter=args.source,
            triggered_by=args.triggered_by
        )

        if result['success']:
            logger.success(f"Summarization completed: {result['articles_summarized']} articles summarized")
            sys.exit(0)
        else:
            logger.error("Summarization failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
