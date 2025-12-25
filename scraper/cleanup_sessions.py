"""
Cleanup script to delete the last N scraping sessions

Usage:
    # Using environment variable
    export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
    python cleanup_sessions.py 9

    # Or pass directly (not recommended for security)
    DATABASE_URL="postgresql://..." python cleanup_sessions.py 9
"""

import sys
import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import pathlib

# Try to load environment variables from .env.local
env_path = pathlib.Path(__file__).parent.parent / '.env.local'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[INFO] Loaded environment from {env_path}")

def delete_last_sessions(num_sessions: int = 9):
    """
    Delete the last N scraping sessions and their related articles

    Args:
        num_sessions: Number of sessions to delete (default 9)
    """
    connection_string = os.getenv('DATABASE_URL')

    if not connection_string:
        print("[ERROR] DATABASE_URL not found in environment")
        print("[INFO] Please set DATABASE_URL environment variable or create .env.local file")
        print("[INFO] Example: export DATABASE_URL='postgresql://user:pass@host:5432/dbname'")
        print("[INFO] Or use the cleanup_last_9_sessions.sql file to run manually")
        return False

    try:
        # Connect to database
        conn = psycopg2.connect(connection_string, client_encoding='UTF8')
        cursor = conn.cursor()

        print(f"[INFO] Finding last {num_sessions} scraping sessions...")

        # Get the IDs of the last N sessions
        cursor.execute("""
            SELECT id, created_at, summary, new_articles_count
            FROM news.scraping_summaries
            ORDER BY id DESC
            LIMIT %s
        """, (num_sessions,))

        sessions = cursor.fetchall()

        if not sessions:
            print("[INFO] No sessions found to delete")
            return True

        session_ids = [session[0] for session in sessions]

        print(f"\n[INFO] Sessions to delete:")
        for session in sessions:
            session_id, created_at, summary, new_count = session
            summary_preview = summary[:50] if summary else "None"
            print(f"  - ID: {session_id}, Created: {created_at}, New Articles: {new_count}")
            print(f"    Summary: {summary_preview}...")

        # Ask for confirmation
        print(f"\n[WARNING] This will delete {len(session_ids)} sessions and all their related articles!")
        confirm = input("Type 'yes' to confirm: ")

        if confirm.lower() != 'yes':
            print("[INFO] Operation cancelled")
            return False

        # Delete articles related to these sessions
        print(f"\n[INFO] Deleting articles from these sessions...")
        cursor.execute("""
            DELETE FROM news.articles
            WHERE scraping_session_id = ANY(%s)
        """, (session_ids,))

        deleted_articles = cursor.rowcount
        print(f"[SUCCESS] Deleted {deleted_articles} articles")

        # Delete the scraping summaries
        print(f"[INFO] Deleting scraping summaries...")
        cursor.execute("""
            DELETE FROM news.scraping_summaries
            WHERE id = ANY(%s)
        """, (session_ids,))

        deleted_summaries = cursor.rowcount
        print(f"[SUCCESS] Deleted {deleted_summaries} scraping summaries")

        # Commit the transaction
        conn.commit()

        print(f"\n[SUCCESS] Cleanup completed!")
        print(f"  - Deleted {deleted_summaries} sessions")
        print(f"  - Deleted {deleted_articles} articles")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")
        if 'conn' in locals() and conn and not conn.closed:
            conn.rollback()
        return False

if __name__ == "__main__":
    num_sessions = 9

    if len(sys.argv) > 1:
        try:
            num_sessions = int(sys.argv[1])
        except ValueError:
            print(f"[ERROR] Invalid number: {sys.argv[1]}")
            sys.exit(1)

    success = delete_last_sessions(num_sessions)
    sys.exit(0 if success else 1)
