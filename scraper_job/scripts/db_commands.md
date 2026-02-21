# Database Commands Reference

## Connection String
```bash
# Set your database URL from .env file
export DATABASE_URL="your_database_url_from_env_file"

# Or load from .env
export $(cat .env | grep DATABASE | xargs)
```

## Quick Connect
```bash
# Connect using environment variable
psql "$DATABASE_URL"

# Or use connection string from .env file
# Replace with YOUR actual connection string
psql "postgresql://user:password@host.region.provider.tech/database?sslmode=require"
```

## Schema Commands

### Set Search Path (Run this first in each session)
```sql
SET search_path TO news, public;
```

### View Schema Structure
```sql
-- List all schemas
\dn

-- List tables in news schema
\dt news.*

-- List views in news schema
\dv news.*

-- List indexes in news schema
\di news.*

-- Describe a specific table
\d news.articles
\d news.news_sources
\d news.summaries

-- Show table sizes
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('news.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'news'
ORDER BY pg_total_relation_size('news.'||tablename) DESC;
```

## Common Queries

### Check News Sources
```sql
SET search_path TO news, public;
SELECT id, name, domain, pagination_type, is_active FROM news_sources;
```

### View Article Statistics
```sql
SET search_path TO news, public;
SELECT * FROM article_stats;
```

### View Scraping Job Statistics
```sql
SET search_path TO news, public;
SELECT * FROM scrape_job_stats;
```

### Recent Articles
```sql
SET search_path TO news, public;
SELECT
    a.title,
    ns.name as source,
    a.published_at,
    a.url
FROM articles a
JOIN news_sources ns ON a.source_id = ns.id
ORDER BY a.published_at DESC
LIMIT 20;
```

### Articles Pending Summary
```sql
SET search_path TO news, public;
SELECT
    COUNT(*) as pending_count,
    ns.name as source
FROM articles a
JOIN news_sources ns ON a.source_id = ns.id
WHERE a.is_processed = TRUE AND a.is_summarized = FALSE
GROUP BY ns.name;
```

## Run Analysis Queries
```bash
# Run all analysis queries
psql "$DATABASE_URL" -f /Users/ismatsamadov/news_summarizer/scraper_job/scripts/analyse.sql

# Or run specific query
psql "$DATABASE_URL" << 'EOF'
SET search_path TO news, public;
-- Your query here
SELECT * FROM news_sources;
EOF
```

## Backup & Restore

### Backup News Schema
```bash
pg_dump "$DATABASE_URL" -n news -f backup_news_schema.sql

# Backup with data
pg_dump "$DATABASE_URL" -n news --data-only -f backup_news_data.sql
```

### Restore Schema
```bash
psql "$DATABASE_URL" -f backup_news_schema.sql
```

## Python Connection

### Using psycopg2
```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load from .env file
load_dotenv()
database_url = os.getenv('DATABASE')

conn = psycopg2.connect(database_url)

# Set search path
with conn.cursor() as cur:
    cur.execute("SET search_path TO news, public;")

    # Query news sources
    cur.execute("SELECT * FROM news_sources;")
    sources = cur.fetchall()
    print(sources)

conn.close()
```

### Using SQLAlchemy
```python
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load from .env file
load_dotenv()
database_url = os.getenv('DATABASE')

engine = create_engine(
    database_url,
    connect_args={"options": "-csearch_path=news,public"}
)

with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM news_sources"))
    for row in result:
        print(row)
```

## Maintenance Commands

### Vacuum and Analyze
```sql
SET search_path TO news, public;

-- Vacuum all tables
VACUUM ANALYZE news.articles;
VACUUM ANALYZE news.summaries;
VACUUM ANALYZE news.news_sources;
```

### Check Dead Tuples
```sql
SELECT
    schemaname,
    relname,
    n_dead_tup,
    n_live_tup,
    round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_percentage
FROM pg_stat_user_tables
WHERE schemaname = 'news'
ORDER BY n_dead_tup DESC;
```

### Refresh Views (if materialized)
```sql
-- Currently using regular views, but for future materialized views:
-- REFRESH MATERIALIZED VIEW news.article_stats;
```

## Troubleshooting

### Check Active Connections
```sql
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'neondb';
```

### Check Locks
```sql
SELECT
    locktype,
    relation::regclass,
    mode,
    granted
FROM pg_locks
WHERE database = (SELECT oid FROM pg_database WHERE datname = 'neondb');
```

### Kill Hanging Query
```sql
-- Find the PID from pg_stat_activity, then:
SELECT pg_terminate_backend(PID_NUMBER);
```

## Quick Tests

### Insert Test Article
```sql
SET search_path TO news, public;

INSERT INTO articles (
    source_id,
    source_article_id,
    title,
    url,
    published_at
) VALUES (
    1,  -- Sonxeber
    'test-123',
    'Test Article Title',
    'https://sonxeber.az/test-123/test-article',
    NOW()
) RETURNING id, title;
```

### Delete Test Data
```sql
SET search_path TO news, public;

DELETE FROM articles WHERE source_article_id LIKE 'test-%';
```

## Schema Information

**Database**: neondb
**Schema**: news
**Owner**: neondb_owner

**Tables**: 6
- news_sources (10 sources configured)
- articles
- categories
- summaries
- scrape_jobs
- scrape_errors

**Views**: 2
- article_stats
- scrape_job_stats

**Indexes**: 26 (optimized for common queries)

**Functions**: 1
- update_updated_at_column() - Auto-updates timestamps
