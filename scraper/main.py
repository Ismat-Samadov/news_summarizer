"""
Async main scraper script - REFACTORED for transactional DB saves
Runs all news source scrapers asynchronously and ONLY saves if everything succeeds
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, List

# Fix encoding for Azerbaijani characters on Windows
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import io
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import Database
from sources.banker_az import BankerAzScraper
from sources.marja_az import MarjaAzScraper
from sources.report_az import ReportAzScraper
from sources.fed_az import FedAzScraper
from sources.sonxeber_az import SonxeberAzScraper
from sources.iqtisadiyyat_az import IqtisadiyyatAzScraper
from sources.trend_az import TrendAzScraper
from sources.apa_az import ApaAzScraper
from sources.qafqazinfo_az import QafqazinfoAzScraper
from sources.oxu_az import OxuAzScraper
from telegram import TelegramReporter
from summarizer import GeminiSummarizer


async def scrape_source(scraper_class, source_name: str, db: Database, num_pages: int) -> Dict:
    """
    Generic scraper function that collects articles without saving to DB

    Args:
        scraper_class: Scraper class to use
        source_name: Name of the source
        db: Database instance (for duplicate checking)
        num_pages: Number of pages to scrape

    Returns:
        Dictionary with scraping statistics and collected articles
    """
    print("\n" + "=" * 60)
    print(f"SCRAPING {source_name.upper()}")
    print("=" * 60)

    new_articles = []

    async with scraper_class() as scraper:
        articles = await scraper.scrape_all(num_pages=num_pages, batch_size=10)

        total_found = len(articles)
        total_skipped = 0

        # Check for duplicates but don't save yet
        for article in articles:
            if db.article_exists(article['url']):
                total_skipped += 1
                continue
            new_articles.append(article)

    print("\n" + "=" * 60)
    print(f"{source_name.upper()} SUMMARY")
    print(f"Total found: {total_found}")
    print(f"New articles: {len(new_articles)}")
    print(f"Duplicates skipped: {total_skipped}")
    print("=" * 60)

    return {
        'name': source_name,
        'total': total_found,
        'scraped': total_found,
        'saved': len(new_articles),
        'skipped': total_skipped,
        'new_articles': new_articles
    }


async def main():
    """Main async function to run all scrapers with transactional DB saves"""
    print("\n" + "=" * 60)
    print("ASYNC NEWS SCRAPER STARTED (TRANSACTIONAL MODE)")
    print("=" * 60)

    # Initialize Telegram reporter and summarizer
    telegram = TelegramReporter()
    summarizer = GeminiSummarizer()

    # Track overall statistics
    start_time = datetime.now(timezone.utc)
    sources_stats = []
    all_new_articles = []
    errors = []
    end_time = None

    # Initialize database connection
    db = Database()

    if not db.connect():
        error_msg = "Failed to connect to database"
        print(f"[ERROR] {error_msg}")
        telegram.send_error_alert(error_msg)
        return

    try:
        print("\n[INFO] PHASE 1: SCRAPING ALL SOURCES (no DB saves yet)...")

        # Scrape all sources (without saving to DB)
        sources_stats.append(await scrape_source(BankerAzScraper, "Banker.az", db, num_pages=2))
        sources_stats.append(await scrape_source(MarjaAzScraper, "Marja.az", db, num_pages=2))
        sources_stats.append(await scrape_source(ReportAzScraper, "Report.az", db, num_pages=1))
        sources_stats.append(await scrape_source(FedAzScraper, "Fed.az", db, num_pages=2))
        sources_stats.append(await scrape_source(SonxeberAzScraper, "Sonxeber.az", db, num_pages=2))
        sources_stats.append(await scrape_source(IqtisadiyyatAzScraper, "Iqtisadiyyat.az", db, num_pages=2))
        sources_stats.append(await scrape_source(TrendAzScraper, "Trend.az", db, num_pages=1))
        sources_stats.append(await scrape_source(ApaAzScraper, "APA.az", db, num_pages=2))
        sources_stats.append(await scrape_source(QafqazinfoAzScraper, "Qafqazinfo.az", db, num_pages=2))
        sources_stats.append(await scrape_source(OxuAzScraper, "Oxu.az", db, num_pages=2))

        # Collect all new articles
        for stats in sources_stats:
            all_new_articles.extend(stats.get('new_articles', []))

        print("\n" + "=" * 60)
        print("SCRAPING PHASE COMPLETED")
        print("=" * 60)

        # Calculate totals
        total_found = sum(s['total'] for s in sources_stats)
        total_saved = sum(s['saved'] for s in sources_stats)

        print(f"Total articles found: {total_found}")
        print(f"Total new articles: {total_saved}")

        # Check if we have new articles
        if not all_new_articles:
            print("\n[WARNING] No new articles found - aborting (nothing to save)")
            end_time = datetime.now(timezone.utc)
            errors.append("No new articles found")
            return

        print(f"\n[INFO] PHASE 2: CREATING AI SUMMARY for {len(all_new_articles)} articles...")

        # Create AI summary
        session_summary = summarizer.create_session_summary(all_new_articles, sources_stats)

        if not session_summary:
            print("\n[ERROR] AI summary creation FAILED - aborting (nothing saved to DB)")
            end_time = datetime.now(timezone.utc)
            errors.append("AI summary creation failed - Gemini error or quota exhausted")
            telegram.send_error_alert("Scraping failed: AI summary creation failed")
            return

        # Check if summary indicates failure (insufficient banking news)
        failure_keywords = [
            "kifayət qədər xəbər tapılmadı",
            "heç bir xəbər tapılmadı",
            "No new articles",
            "Məlumat yoxdur"
        ]

        if any(keyword in session_summary for keyword in failure_keywords):
            print("\n[WARNING] AI summary indicates insufficient banking news - aborting")
            end_time = datetime.now(timezone.utc)
            errors.append("Insufficient banking-relevant articles")
            return

        print("[SUCCESS] AI summary created successfully")

        print(f"\n[INFO] PHASE 3: SAVING TO DATABASE (transactional)...")

        # Calculate duration
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        # Prepare summary data
        summary_data = {
            'summary': session_summary,
            'articles_count': total_found,
            'sources_count': len(sources_stats),
            'new_articles_count': total_saved,
            'scraping_duration_seconds': duration
        }

        # Save everything in one transaction
        session_id = db.save_complete_session(all_new_articles, summary_data)

        if not session_id:
            print("\n[ERROR] Database save FAILED - all changes rolled back")
            errors.append("Database transaction failed - rolled back")
            telegram.send_error_alert("Scraping failed: Database save failed (rolled back)")
            return

        print(f"\n[SUCCESS] ✅ Complete session saved to DB (Session ID: {session_id})")
        print(f"  - {len(all_new_articles)} articles saved")
        print(f"  - AI summary created and saved")
        print(f"  - Duration: {duration:.1f}s")

    except KeyboardInterrupt:
        print("\n\n[INFO] Scraping interrupted by user")
        errors.append("Scraping interrupted by user")
        end_time = datetime.now(timezone.utc)

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"\n[ERROR] {error_msg}")
        errors.append(error_msg)
        telegram.send_error_alert(error_msg)
        import traceback
        traceback.print_exc()
        end_time = datetime.now(timezone.utc)

    finally:
        # Close database connection
        db.close()

        # Ensure end_time is set
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Calculate totals (even if scraping failed)
        total_found = sum(s['total'] for s in sources_stats) if sources_stats else 0
        total_scraped = sum(s['scraped'] for s in sources_stats) if sources_stats else 0
        total_saved = sum(s['saved'] for s in sources_stats) if sources_stats else 0
        total_skipped = sum(s['skipped'] for s in sources_stats) if sources_stats else 0

        # Send Telegram report
        report_stats = {
            'start_time': start_time,
            'end_time': end_time,
            'sources': sources_stats,
            'total_found': total_found,
            'total_scraped': total_scraped,
            'total_saved': total_saved,
            'total_skipped': total_skipped,
            'session_summary': session_summary if 'session_summary' in locals() else None,
            'errors': errors
        }

        telegram.send_scraping_report(report_stats)


if __name__ == "__main__":
    asyncio.run(main())
