"""
Configuration module for news scraper
Loads environment variables and provides configuration constants
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Database Configuration
# Support both DATABASE and DATABASE_URL for flexibility in environments.
DATABASE_URL = os.getenv('DATABASE') or os.getenv('DATABASE_URL') or ''

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Scraper Configuration
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

# Request Configuration
REQUEST_TIMEOUT = 30  # seconds
REQUEST_DELAY = 1.0  # seconds between requests (be respectful)
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Scraping Limits
MAX_PAGES_PER_RUN = 5  # Limit pages per scrape run to avoid overload
MAX_ARTICLES_PER_PAGE = 50  # Maximum articles to extract per page

# Database Schema
DB_SCHEMA = 'news'

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>'

# Date/Time Configuration
TIMEZONE = 'Asia/Baku'

# Validation
if not DATABASE_URL:
    raise ValueError(
        "Database connection string is missing. Set DATABASE or DATABASE_URL "
        "in the environment or in the .env file."
    )
