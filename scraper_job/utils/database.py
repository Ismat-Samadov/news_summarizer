"""
Database utility module
Handles all database operations for the news scraper
"""

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from typing import List, Dict, Optional, Any
from datetime import datetime
from contextlib import contextmanager
import hashlib
import json
from loguru import logger

from scraper_job.config import DATABASE_URL, DB_SCHEMA


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.schema = DB_SCHEMA

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(self.database_url)
            # Set search path to news schema
            with conn.cursor() as cur:
                cur.execute(f"SET search_path TO {self.schema}, public;")
            conn.commit()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_news_source(self, domain: str) -> Optional[Dict]:
        """Get news source by domain"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM news_sources WHERE domain = %s",
                    (domain,)
                )
                return dict(cur.fetchone()) if cur.rowcount > 0 else None

    def get_all_active_sources(self) -> List[Dict]:
        """Get all active news sources"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM news_sources WHERE is_active = TRUE ORDER BY id"
                )
                return [dict(row) for row in cur.fetchall()]

    def create_scrape_job(
        self,
        source_id: int,
        job_type: str = 'incremental',
        triggered_by: str = 'manual'
    ) -> str:
        """Create a new scrape job and return its ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scrape_jobs (
                        source_id, job_type, status, started_at, triggered_by
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (source_id, job_type, 'running', datetime.now(), triggered_by)
                )
                job_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Created scrape job {job_id} for source {source_id}")
                return job_id

    def update_scrape_job(
        self,
        job_id: str,
        status: str,
        articles_found: int = 0,
        articles_new: int = 0,
        articles_updated: int = 0,
        articles_failed: int = 0,
        error_message: Optional[str] = None,
        error_details: Optional[Dict] = None
    ):
        """Update scrape job with results"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE scrape_jobs
                    SET status = %s,
                        completed_at = %s,
                        duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)),
                        articles_found = %s,
                        articles_new = %s,
                        articles_updated = %s,
                        articles_failed = %s,
                        error_message = %s,
                        error_details = %s
                    WHERE id = %s
                    """,
                    (
                        status, datetime.now(), articles_found, articles_new,
                        articles_updated, articles_failed, error_message,
                        json.dumps(error_details) if error_details else None,
                        job_id
                    )
                )
                conn.commit()
                logger.info(f"Updated scrape job {job_id}: {status}")

    def log_scrape_error(
        self,
        job_id: str,
        source_id: int,
        url: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None
    ):
        """Log a scraping error"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO scrape_errors (
                        job_id, source_id, url, error_type, error_message, stack_trace
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (job_id, source_id, url, error_type, error_message, stack_trace)
                )
                conn.commit()

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """Generate SHA-256 hash of content for deduplication"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def article_exists(self, source_id: int, source_article_id: str) -> bool:
        """Check if article already exists in database"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1 FROM articles
                    WHERE source_id = %s AND source_article_id = %s
                    LIMIT 1
                    """,
                    (source_id, source_article_id)
                )
                return cur.rowcount > 0

    def insert_article(self, article_data: Dict) -> Optional[str]:
        """
        Insert a new article into the database
        Returns article UUID if successful, None if duplicate
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Generate content hash if content provided
                    content_hash = None
                    if article_data.get('content'):
                        content_hash = self.generate_content_hash(article_data['content'])

                    cur.execute(
                        """
                        INSERT INTO articles (
                            source_id, source_article_id, title, url, slug,
                            category_id, content, excerpt, image_url,
                            author, published_at, view_count, is_processed,
                            content_hash, metadata
                        ) VALUES (
                            %(source_id)s, %(source_article_id)s, %(title)s, %(url)s, %(slug)s,
                            %(category_id)s, %(content)s, %(excerpt)s, %(image_url)s,
                            %(author)s, %(published_at)s, %(view_count)s, %(is_processed)s,
                            %(content_hash)s, %(metadata)s
                        )
                        ON CONFLICT (source_id, source_article_id) DO NOTHING
                        RETURNING id
                        """,
                        {
                            'source_id': article_data['source_id'],
                            'source_article_id': article_data.get('source_article_id'),
                            'title': article_data['title'],
                            'url': article_data['url'],
                            'slug': article_data.get('slug'),
                            'category_id': article_data.get('category_id'),
                            'content': article_data.get('content'),
                            'excerpt': article_data.get('excerpt'),
                            'image_url': article_data.get('image_url'),
                            'author': article_data.get('author'),
                            'published_at': article_data.get('published_at'),
                            'view_count': article_data.get('view_count', 0),
                            'is_processed': article_data.get('is_processed', False),
                            'content_hash': content_hash,
                            'metadata': json.dumps(article_data.get('metadata', {}))
                        }
                    )

                    if cur.rowcount > 0:
                        article_id = cur.fetchone()[0]
                        conn.commit()
                        logger.debug(f"Inserted article: {article_data['title'][:50]}...")
                        return article_id
                    else:
                        logger.debug(f"Article already exists: {article_data.get('source_article_id')}")
                        return None

        except psycopg2.IntegrityError as e:
            logger.warning(f"Duplicate article URL: {article_data['url']}")
            return None
        except Exception as e:
            logger.error(f"Error inserting article: {e}")
            raise

    def bulk_insert_articles(self, articles: List[Dict]) -> int:
        """
        Bulk insert articles into database
        Returns count of successfully inserted articles
        """
        inserted_count = 0
        for article in articles:
            if self.insert_article(article):
                inserted_count += 1
        return inserted_count

    def get_or_create_category(self, source_id: int, name: str, slug: str) -> int:
        """Get category ID or create if doesn't exist"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Try to get existing category
                cur.execute(
                    "SELECT id FROM categories WHERE source_id = %s AND slug = %s",
                    (source_id, slug)
                )
                result = cur.fetchone()

                if result:
                    return result[0]

                # Create new category
                cur.execute(
                    """
                    INSERT INTO categories (name, slug, source_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (slug, source_id) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (name, slug, source_id)
                )
                category_id = cur.fetchone()[0]
                conn.commit()
                logger.debug(f"Created category: {name} (ID: {category_id})")
                return category_id

    def get_articles_for_summarization(self, limit: int = 100) -> List[Dict]:
        """Get articles that need AI summarization"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT a.*, ns.name as source_name
                    FROM articles a
                    JOIN news_sources ns ON a.source_id = ns.id
                    WHERE a.is_processed = TRUE
                      AND a.is_summarized = FALSE
                      AND a.content IS NOT NULL
                    ORDER BY a.published_at DESC
                    LIMIT %s
                    """,
                    (limit,)
                )
                return [dict(row) for row in cur.fetchall()]

    def insert_summary(self, summary_data: Dict) -> Optional[str]:
        """
        Insert a new summary into the database
        Returns summary UUID if successful, None if failed
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO summaries (
                            article_id, summary_short, summary_medium, summary_long,
                            key_points, entities, topics, sentiment,
                            model_used, model_version, confidence_score
                        ) VALUES (
                            %(article_id)s, %(summary_short)s, %(summary_medium)s, %(summary_long)s,
                            %(key_points)s, %(entities)s, %(topics)s, %(sentiment)s,
                            %(model_used)s, %(model_version)s, %(confidence_score)s
                        )
                        ON CONFLICT (article_id) DO UPDATE SET
                            summary_short = EXCLUDED.summary_short,
                            summary_medium = EXCLUDED.summary_medium,
                            summary_long = EXCLUDED.summary_long,
                            key_points = EXCLUDED.key_points,
                            entities = EXCLUDED.entities,
                            topics = EXCLUDED.topics,
                            sentiment = EXCLUDED.sentiment,
                            model_used = EXCLUDED.model_used,
                            model_version = EXCLUDED.model_version,
                            confidence_score = EXCLUDED.confidence_score,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                        """,
                        {
                            'article_id': summary_data['article_id'],
                            'summary_short': summary_data.get('summary_short'),
                            'summary_medium': summary_data.get('summary_medium'),
                            'summary_long': summary_data.get('summary_long'),
                            'key_points': json.dumps(summary_data.get('key_points', [])),
                            'entities': json.dumps(summary_data.get('entities', {})),
                            'topics': json.dumps(summary_data.get('topics', [])),
                            'sentiment': summary_data.get('sentiment'),
                            'model_used': summary_data.get('model_used'),
                            'model_version': summary_data.get('model_version'),
                            'confidence_score': summary_data.get('confidence_score')
                        }
                    )

                    summary_id = cur.fetchone()[0]
                    conn.commit()
                    logger.debug(f"Inserted summary for article {summary_data['article_id']}")
                    return summary_id

        except Exception as e:
            logger.error(f"Error inserting summary: {e}")
            return None

    def mark_article_summarized(self, article_id: str):
        """Mark an article as summarized"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE articles SET is_summarized = TRUE WHERE id = %s",
                    (article_id,)
                )
                conn.commit()

    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM article_stats")
                article_stats = [dict(row) for row in cur.fetchall()]

                cur.execute("SELECT * FROM scrape_job_stats")
                job_stats = [dict(row) for row in cur.fetchall()]

                return {
                    'article_stats': article_stats,
                    'job_stats': job_stats
                }
