# News Scraper

Automated news scraper for Azerbaijani news websites. Scrapes articles from multiple news sources and stores them in PostgreSQL.

**Automated scraping**: 3 times daily at 09:00, 13:00, and 18:00 UTC via GitHub Actions.

## Project Structure

```
news_summarizer/
├── scraper_job/
│   ├── scrapers/           # News source scrapers
│   │   ├── base_scraper.py
│   │   ├── sonxeber_scraper.py
│   │   ├── metbuat_scraper.py
│   │   └── ...
│   ├── utils/              # Utility modules
│   │   ├── database.py     # Database operations
│   │   └── helpers.py      # Helper functions
│   ├── scripts/            # Database scripts
│   │   ├── schema.sql      # Database schema
│   │   ├── analyse.sql     # Analysis queries
│   │   └── db_commands.md  # Command reference
│   ├── config.py           # Configuration
│   └── run_scraper.py      # Main scraper runner
├── requirements.txt
├── .env
└── README.md
```

## News Sources

Currently implemented scrapers:
1. **Sonxeber.az** ✅
2. **Metbuat.az** ✅
3. **Azertag.az** ✅ (State News Agency)
4. **APA.az** ✅ (Azerbaijan Press Agency)
5. **Report.az** ✅
6. **Modern.az** ✅

Planned implementations:
7. Axar.az (requires infinite scroll handling)
8. News.milli.az (requires AJAX handling)
9. Xezerxeber.az (requires infinite scroll handling)
10. Oxu.az (requires anti-scraping bypass)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
DATABASE=postgresql://user:password@host/database
```

### 3. Initialize Database

The database is already initialized with the `news` schema and all tables. To re-initialize:

```bash
psql "$DATABASE" -f scraper_job/scripts/schema.sql
```

### 4. Set Up GitHub Actions (Optional for Automation)

For automated scraping, see [GitHub Actions Setup Guide](.github/workflows/scrape-news.yml).

**Quick setup:**
1. Add repository secret: `DATABASE_URL`
2. Enable GitHub Actions in your repository
3. Workflows will run automatically 3x daily (09:00, 13:00, 18:00 UTC)

## Usage

### Scraping Commands

```bash
# Run scraper for a specific source
python -m scraper_job.run_scraper run -s sonxeber.az -p 3

# Run all available scrapers
python -m scraper_job.run_scraper run-all -p 3

# Show database statistics
python -m scraper_job.run_scraper stats

# List available scrapers
python -m scraper_job.run_scraper list

# Scrape with full article content
python -m scraper_job.run_scraper run -s metbuat.az -p 2 --details
```

### Command Options

- `run`: Run scraper for a single source
  - `-s, --source`: Source domain (required)
  - `-p, --pages`: Max pages to scrape (default: 3)
  - `-d, --details`: Scrape full article content
  - `--triggered-by`: Source trigger (manual, github_action, scheduled)

- `run-all`: Run all scrapers
  - `-p, --pages`: Max pages per source (default: 3)
  - `-d, --details`: Scrape full article content

- `stats`: Show database statistics
- `list`: List available scrapers

### Python API

```python
from scraper_job.scrapers.sonxeber_scraper import SonxeberScraper

# Initialize scraper
scraper = SonxeberScraper()

# Run scraper
stats = scraper.run(
    max_pages=5,
    scrape_details=True,
    job_type='incremental',
    triggered_by='manual'
)

print(f"Scraped {stats['articles_new']} new articles")
```

## Database Schema

### Core Tables

- `news.news_sources` - News website configurations
- `news.articles` - Scraped articles
- `news.categories` - Article categories
- `news.scrape_jobs` - Job execution tracking
- `news.scrape_errors` - Error logging

### Views

- `news.article_stats` - Article statistics by source
- `news.scrape_job_stats` - Job performance metrics

## Database Queries

```bash
# Connect to database
psql "$DATABASE"

# Set search path
SET search_path TO news, public;

# View sources
SELECT * FROM news_sources;

# View recent articles
SELECT title, published_at FROM articles ORDER BY published_at DESC LIMIT 10;

# View statistics
SELECT * FROM article_stats;
```

See `scraper_job/scripts/analyse.sql` for 20+ pre-built analysis queries.

## GitHub Actions Automation

The project includes automated scraping workflows that run 3 times daily.

### Scheduled Runs

**Scraping Schedule:**
- 09:00 UTC (12:00 Baku time)
- 13:00 UTC (16:00 Baku time)
- 18:00 UTC (21:00 Baku time)

**Each run scrapes:**
- 3 pages from each news source
- Saves all articles to database
- Generates logs and statistics

### Manual Triggers

You can also run scrapers manually via GitHub Actions:

1. Go to **Actions** tab in GitHub
2. Select **Scrape News Articles**
3. Click **Run workflow**
4. Adjust parameters:
   - Max pages (default: 3)
   - Scrape details (default: false)
5. Click **Run workflow** button

### Setup Guide

For detailed setup instructions, see [GitHub Actions Setup Guide](.github/SETUP.md).

**Required secrets:**
- `DATABASE_URL` - PostgreSQL connection string

### Monitoring

- View workflow runs in **Actions** tab
- Download logs as artifacts (retained for 7 days)
- Check database statistics after each run
- Notifications on failure (optional email setup)

## Logging

Logs are stored in `logs/` directory:
- Console output: INFO level
- File logs: DEBUG level
- Rotation: Daily
- Retention: 30 days

## Features

### Current Features
- ✅ Multi-source web scraping (6 news sources)
- ✅ PostgreSQL database storage
- ✅ Deduplication by content hash
- ✅ Job tracking and error logging
- ✅ Configurable scraping limits
- ✅ Respectful rate limiting
- ✅ Comprehensive logging
- ✅ **GitHub Actions automation (3x daily)**
- ✅ **Automated workflows with scheduled runs**

### Upcoming Features
- ⏳ Additional news sources (4 more planned)
- ⏳ Next.js frontend
- ⏳ Vercel deployment
- ⏳ REST API for article access

## Development

### Adding a New Scraper

1. Create a new file in `scraper_job/scrapers/`:

```python
from scraper_job.scrapers.base_scraper import BaseScraper

class NewSourceScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_domain='newsource.az')

    def parse_article_list(self, soup, page_number=1):
        # Extract article metadata from listing page
        articles = []
        # ... extraction logic ...
        return articles

    def parse_article_detail(self, soup, article_url):
        # Extract full article content
        return {
            'content': '...',
            'author': '...',
        }
```

2. Register scraper in `run_scraper.py`:

```python
from scraper_job.scrapers.newsource_scraper import NewSourceScraper

SCRAPERS = {
    'sonxeber.az': SonxeberScraper,
    'metbuat.az': MetbuatScraper,
    'newsource.az': NewSourceScraper,  # Add here
}
```

3. Test the scraper:

```bash
python -m scraper_job.run_scraper run -s newsource.az -p 1
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

## Architecture

### Scraping Flow

```
1. run_scraper.py
   ├─> Initialize scraper (BaseScraper subclass)
   ├─> Create scrape_job in database
   ├─> For each page:
   │   ├─> Fetch listing page
   │   ├─> Parse article links (parse_article_list)
   │   ├─> For each article:
   │   │   ├─> Check if exists (deduplication)
   │   │   ├─> Fetch detail page (optional)
   │   │   ├─> Parse content (parse_article_detail)
   │   │   └─> Insert into database
   │   └─> Rate limiting delay
   └─> Update scrape_job with results
```

### Database Flow

```
Articles
   ├─> is_processed = FALSE (initial scrape - metadata only)
   └─> is_processed = TRUE  (full content scraped)
```

## Configuration

See `scraper_job/config.py` for all configuration options:

- Request timeout and retries
- Rate limiting delays
- Max pages per run
- User agent rotation
- Database schema name
- Logging configuration

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Submit a pull request

## Support

For issues and feature requests, please create a GitHub issue.
