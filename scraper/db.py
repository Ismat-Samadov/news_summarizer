"""
Database utilities for news scraper
Handles PostgreSQL connections with proper UTF-8 encoding for Azerbaijani characters
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from datetime import datetime
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Fix encoding for Azerbaijani characters on Windows
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import io
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment variables from parent directory
import pathlib
env_path = pathlib.Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

class Database:
    def __init__(self):
        self.connection_string = os.getenv('DATABASE_URL')
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection with UTF-8 encoding"""
        try:
            self.conn = psycopg2.connect(
                self.connection_string,
                client_encoding='UTF8',
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            print("[SUCCESS] Database connected successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False

    def ensure_connection(self):
        """Ensure database connection is active, reconnect if needed"""
        try:
            if self.conn is None or self.conn.closed:
                print("[INFO] Database connection lost, reconnecting...")
                return self.connect()

            # Test connection with a simple query
            self.cursor.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"[WARNING] Connection test failed: {e}, reconnecting...")
            try:
                self.close()
            except:
                pass
            return self.connect()

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("[SUCCESS] Database connection closed")

    def insert_article(self, article: Dict, scraping_session_id: Optional[int] = None) -> Optional[int]:
        """
        Insert a news article into the database

        Args:
            article: Dictionary with keys: title, content, source, url, published_date
            scraping_session_id: Optional ID of the scraping session that collected this article

        Returns:
            Article ID if successful, None otherwise
        """
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                print("[ERROR] Failed to establish database connection")
                return None

            query = sql.SQL("""
                INSERT INTO news.articles (title, content, source, url, published_date, language, scraping_session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE
                SET title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    published_date = EXCLUDED.published_date,
                    scraping_session_id = EXCLUDED.scraping_session_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """)

            self.cursor.execute(query, (
                article.get('title'),
                article.get('content'),
                article.get('source'),
                article.get('url'),
                article.get('published_date'),
                article.get('language', 'az'),
                scraping_session_id
            ))

            result = self.cursor.fetchone()
            self.conn.commit()

            article_id = result['id'] if result else None

            # Try to print with title, fallback if console encoding fails
            try:
                print(f"[SUCCESS] Article saved: {article.get('title')[:50]}... (ID: {article_id})")
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"[SUCCESS] Article saved (ID: {article_id})")

            return article_id

        except Exception as e:
            try:
                print(f"[ERROR] Error inserting article: {e}")
            except UnicodeEncodeError:
                print(f"[ERROR] Error inserting article (encoding error in message)")
            if self.conn and not self.conn.closed:
                self.conn.rollback()
            return None

    def bulk_insert_articles(self, articles: List[Dict], scraping_session_id: Optional[int] = None) -> int:
        """
        Insert multiple articles in a single transaction

        Args:
            articles: List of article dictionaries
            scraping_session_id: Optional ID of the scraping session

        Returns:
            Number of articles successfully inserted
        """
        inserted_count = 0
        for article in articles:
            if self.insert_article(article, scraping_session_id):
                inserted_count += 1
        return inserted_count

    def save_complete_session(self, articles: List[Dict], summary_data: Dict) -> Optional[int]:
        """
        Save a complete scraping session (summary + articles) in a single transaction.
        If anything fails, everything is rolled back.

        Args:
            articles: List of article dictionaries to save
            summary_data: Dictionary with summary data:
                - summary: str (comprehensive summary text)
                - articles_count: int (total articles found)
                - sources_count: int (number of sources)
                - new_articles_count: int (new articles saved)
                - scraping_duration_seconds: float (optional)

        Returns:
            Session ID if successful, None if anything failed (with full rollback)
        """
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                print("[ERROR] Failed to establish database connection")
                return None

            # Start transaction
            print("[INFO] Starting database transaction...")

            # Step 1: Create scraping session
            query = sql.SQL("""
                INSERT INTO news.scraping_summaries
                (summary, articles_count, sources_count, new_articles_count, scraping_duration_seconds)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """)

            self.cursor.execute(query, (
                summary_data.get('summary'),
                summary_data.get('articles_count'),
                summary_data.get('sources_count'),
                summary_data.get('new_articles_count'),
                summary_data.get('scraping_duration_seconds')
            ))

            result = self.cursor.fetchone()
            session_id = result['id'] if result else None

            if not session_id:
                print("[ERROR] Failed to create session, rolling back...")
                self.conn.rollback()
                return None

            print(f"[SUCCESS] Created scraping session (ID: {session_id})")

            # Step 2: Insert all articles with session ID
            articles_saved = 0
            article_query = sql.SQL("""
                INSERT INTO news.articles (title, content, source, url, published_date, language, scraping_session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE
                SET title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    published_date = EXCLUDED.published_date,
                    scraping_session_id = EXCLUDED.scraping_session_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """)

            for article in articles:
                self.cursor.execute(article_query, (
                    article.get('title'),
                    article.get('content'),
                    article.get('source'),
                    article.get('url'),
                    article.get('published_date'),
                    article.get('language', 'az'),
                    session_id
                ))
                articles_saved += 1

            print(f"[SUCCESS] Inserted {articles_saved} articles")

            # Commit transaction
            self.conn.commit()
            print(f"[SUCCESS] Transaction committed - session {session_id} saved successfully")

            return session_id

        except Exception as e:
            print(f"[ERROR] Failed to save session: {e}")
            if self.conn and not self.conn.closed:
                print("[WARNING] Rolling back transaction...")
                self.conn.rollback()
            return None

    def article_exists(self, url: str) -> bool:
        """Check if an article with the given URL already exists"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return False

            query = sql.SQL("SELECT id FROM news.articles WHERE url = %s")
            self.cursor.execute(query, (url,))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"[ERROR] Error checking article existence: {e}")
            return False

    def insert_scraping_summary(self, summary_data: Dict) -> Optional[int]:
        """
        Insert a scraping session summary

        Args:
            summary_data: Dictionary with keys:
                - summary: str (comprehensive summary text)
                - articles_count: int (total articles found)
                - sources_count: int (number of sources)
                - new_articles_count: int (new articles saved)
                - scraping_duration_seconds: float (optional)

        Returns:
            Summary ID if successful, None otherwise
        """
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                print("[ERROR] Failed to establish database connection")
                return None

            query = sql.SQL("""
                INSERT INTO news.scraping_summaries
                (summary, articles_count, sources_count, new_articles_count, scraping_duration_seconds)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """)

            self.cursor.execute(query, (
                summary_data.get('summary'),
                summary_data.get('articles_count'),
                summary_data.get('sources_count'),
                summary_data.get('new_articles_count'),
                summary_data.get('scraping_duration_seconds')
            ))

            result = self.cursor.fetchone()
            self.conn.commit()

            summary_id = result['id'] if result else None
            print(f"[SUCCESS] Scraping summary saved (ID: {summary_id})")

            return summary_id

        except Exception as e:
            print(f"[ERROR] Error inserting scraping summary: {e}")
            if self.conn and not self.conn.closed:
                self.conn.rollback()
            return None

    def update_scraping_summary(self, summary_id: int, summary_data: Dict) -> bool:
        """
        Update an existing scraping session summary

        Args:
            summary_id: ID of the summary to update
            summary_data: Dictionary with keys to update:
                - summary: str (comprehensive summary text)
                - articles_count: int (total articles found)
                - new_articles_count: int (new articles saved)
                - scraping_duration_seconds: float

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                print("[ERROR] Failed to establish database connection")
                return False

            query = sql.SQL("""
                UPDATE news.scraping_summaries
                SET summary = %s,
                    articles_count = %s,
                    new_articles_count = %s,
                    scraping_duration_seconds = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """)

            self.cursor.execute(query, (
                summary_data.get('summary'),
                summary_data.get('articles_count'),
                summary_data.get('new_articles_count'),
                summary_data.get('scraping_duration_seconds'),
                summary_id
            ))

            self.conn.commit()
            print(f"[SUCCESS] Scraping summary updated (ID: {summary_id})")
            return True

        except Exception as e:
            print(f"[ERROR] Error updating scraping summary: {e}")
            if self.conn and not self.conn.closed:
                self.conn.rollback()
            return False

    def get_articles_by_source(self, source: str, limit: int = 10) -> List[Dict]:
        """Retrieve articles from a specific source"""
        try:
            # Ensure connection is alive
            if not self.ensure_connection():
                return []

            query = sql.SQL("""
                SELECT * FROM news.articles
                WHERE source = %s
                ORDER BY published_date DESC
                LIMIT %s
            """)
            self.cursor.execute(query, (source, limit))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"[ERROR] Error retrieving articles: {e}")
            return []
