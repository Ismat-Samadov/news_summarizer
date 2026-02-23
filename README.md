# birnews — Bir mənbə, bütün xəbərlər

Automated news aggregator for Azerbaijani news websites. Scrapes articles from 11 sources and presents them through a Next.js frontend.

**Automated scraping**: 3 times daily at 09:00, 13:00, and 18:00 UTC via GitHub Actions.

**Snapshot-based storage**: Each scrape deletes old articles before inserting new ones, maintaining only the latest snapshot. This prevents database growth and ensures zero storage costs.

---

## System Architecture

```mermaid
graph TB
    subgraph CI["GitHub Actions (3x daily)"]
        GH[run_scraper.py]
    end

    subgraph Scrapers["scraper_job/scrapers/"]
        S1[sonxeber_scraper.py]
        S2[apa_scraper.py]
        S3[report_scraper.py]
        S4[modern_scraper.py]
        S5[axar_scraper.py]
        S6[banker_scraper.py]
        S7[fed_scraper.py]
        S8[marja_scraper.py]
        S9[oxu_scraper.py]
        S10[qafqazinfo_scraper.py]
        S11[trend_scraper.py]
    end

    subgraph DB["Neon PostgreSQL (news schema)"]
        T1[(news_sources)]
        T2[(articles)]
        T3[(scrape_jobs)]
        T4[(scrape_errors)]
    end

    subgraph Frontend["Next.js App (Vercel)"]
        F1[Home Page]
        F2[Article Detail]
        F3[Search]
    end

    GH --> Scrapers
    Scrapers --> DB
    DB --> Frontend
    Users((Users)) --> Frontend
```

---

## Scraping Flow

```mermaid
flowchart TD
    A([GitHub Actions Trigger]) --> B[run_scraper.py run-all]
    B --> C{For each source}
    C --> D[Initialize BaseScraper subclass]
    D --> E[DELETE old articles for source]
    E --> F[CREATE scrape_job record]
    F --> G{For each page 1..N}
    G --> H[Fetch listing page via Playwright/requests]
    H --> I[parse_article_list → article URLs + metadata]
    I --> J{For each article}
    J --> K{scrape_details?}
    K -- yes --> L[Fetch detail page]
    L --> M[parse_article_detail → content + author]
    K -- no --> N[Skip detail fetch]
    M --> O[INSERT article into DB]
    N --> O
    O --> P{More articles?}
    P -- yes --> J
    P -- no --> Q{More pages?}
    Q -- yes --> G
    Q -- no --> R[UPDATE scrape_job with stats]
    R --> S[Cleanup: delete jobs/errors > 7 days]
    S --> T{More sources?}
    T -- yes --> C
    T -- no --> U([Done — upload logs as artifact])
```

---

## Database Schema

```mermaid
erDiagram
    news_sources {
        int id PK
        varchar name
        varchar domain
        varchar base_url
        varchar language
        bool is_active
        varchar pagination_type
        jsonb scraper_config
        timestamp created_at
    }

    articles {
        uuid id PK
        int source_id FK
        varchar title
        text url
        text excerpt
        text content
        varchar image_url
        varchar author
        timestamp published_at
        timestamp scraped_at
        int view_count
        varchar content_hash
    }

    scrape_jobs {
        int id PK
        int source_id FK
        varchar job_type
        varchar status
        varchar triggered_by
        int articles_new
        int articles_updated
        int articles_deleted
        int errors_count
        timestamp started_at
        timestamp completed_at
    }

    scrape_errors {
        int id PK
        int job_id FK
        varchar error_type
        text message
        text url
        timestamp created_at
    }

    news_sources ||--o{ articles : "has"
    news_sources ||--o{ scrape_jobs : "tracks"
    scrape_jobs ||--o{ scrape_errors : "logs"
```

---

## CI/CD Pipeline

```mermaid
flowchart LR
    subgraph Schedule["Cron Schedule (UTC)"]
        C1["09:00 — morning"]
        C2["13:00 — afternoon"]
        C3["18:00 — evening"]
    end

    subgraph Workflow["GitHub Actions Job"]
        W1[Checkout repo]
        W2[Setup Python 3.11]
        W3[pip install requirements]
        W4[playwright install chromium]
        W5[python -m scraper_job.run_scraper run-all]
        W6[Display statistics]
        W7[Upload logs artifact]
        W8{Success?}
        W9[Fail with error]
    end

    subgraph Secrets["Repository Secrets"]
        S1[DATABASE — Neon connection string]
    end

    Schedule --> W1
    manual([workflow_dispatch]) --> W1
    W1 --> W2 --> W3 --> W4 --> W5 --> W6 --> W7 --> W8
    W8 -- no --> W9
    Secrets --> W5
```

---

## Project Structure

```
birnews/
├── scraper_job/
│   ├── scrapers/               # 11 news source scrapers
│   │   ├── base_scraper.py     # Abstract base class
│   │   ├── sonxeber_scraper.py
│   │   ├── apa_scraper.py
│   │   ├── report_scraper.py
│   │   ├── modern_scraper.py
│   │   ├── axar_scraper.py
│   │   ├── banker_scraper.py
│   │   ├── fed_scraper.py
│   │   ├── marja_scraper.py
│   │   ├── oxu_scraper.py
│   │   ├── qafqazinfo_scraper.py
│   │   └── trend_scraper.py
│   ├── utils/
│   │   ├── database.py         # DB operations (insert, delete, upsert)
│   │   └── helpers.py          # HTTP fetch, text extraction, date parsing
│   ├── scripts/
│   │   ├── schema.sql          # Full DB schema + seed data
│   │   ├── analyse.sql         # 20+ analysis queries
│   │   └── db_commands.md      # psql command reference
│   ├── config.py               # Rate limits, timeouts, schema name
│   └── run_scraper.py          # CLI entrypoint + SCRAPERS registry
├── news-app/                   # Next.js 14 frontend
│   ├── app/
│   │   ├── page.tsx            # Home — article grid + filters + search
│   │   ├── article/[id]/       # Article detail page
│   │   └── layout.tsx          # Shell, header, footer
│   ├── components/
│   │   ├── ArticleCard.tsx
│   │   ├── Pagination.tsx
│   │   └── SearchBar.tsx
│   └── lib/
│       └── db.ts               # Neon PostgreSQL queries (pg pool)
├── .github/
│   └── workflows/
│       └── scrape-news.yml     # Automated scraping workflow
├── requirements.txt
└── README.md
```

---

## News Sources

11 active scrapers:

| # | Source | Domain | Notes |
|---|--------|--------|-------|
| 1 | **Sonxeber.az** | sonxeber.az | ✅ |
| 2 | **APA.az** | apa.az | ✅ Azerbaijan Press Agency |
| 3 | **Report.az** | report.az | ✅ |
| 4 | **Modern.az** | modern.az | ✅ |
| 5 | **Axar.az** | axar.az | ✅ |
| 6 | **Banker.az** | banker.az | ✅ Financial news |
| 7 | **Fed.az** | fed.az | ✅ |
| 8 | **Marja.az** | marja.az | ✅ |
| 9 | **Oxu.az** | oxu.az | ✅ Economy category |
| 10 | **Qafqazinfo.az** | qafqazinfo.az | ✅ |
| 11 | **Trend.az** | az.trend.az | ✅ Business section |

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```env
DATABASE=postgresql://user:password@host/database
DATABASE_URL=postgresql://user:password@host/database
```

### 3. Initialize Database

```bash
psql "$DATABASE" -f scraper_job/scripts/schema.sql
```

### 4. GitHub Actions Secrets

Add one repository secret:

| Secret | Value |
|--------|-------|
| `DATABASE` | Neon PostgreSQL connection string |

---

## Usage

### Scraping Commands

```bash
# Run all scrapers (3 pages each)
python -m scraper_job.run_scraper run-all -p 3

# Run a single source
python -m scraper_job.run_scraper run -s banker.az -p 3

# Scrape with full article content
python -m scraper_job.run_scraper run -s apa.az -p 2 --details

# Show database statistics
python -m scraper_job.run_scraper stats

# List available scrapers
python -m scraper_job.run_scraper list
```

### Command Options

- `run` — single source
  - `-s, --source` — source domain (required)
  - `-p, --pages` — max pages (default: 3)
  - `-d, --details` — scrape full article content
  - `--triggered-by` — label for job tracking

- `run-all` — all registered scrapers
  - `-p, --pages` — max pages per source
  - `-d, --details` — scrape full article content

- `stats` — print DB statistics
- `list` — list registered scrapers

---

## Frontend

The Next.js frontend is deployed on Vercel and reads directly from Neon PostgreSQL.

**Features:**
- Article grid with source filter tabs (dynamic from DB)
- Full-text search across title, excerpt, and content
- Pagination (24 articles/page)
- Article detail page with view count tracking
- Responsive layout

---

## Adding a New Scraper

1. Create `scraper_job/scrapers/mysource_scraper.py`:

```python
from scraper_job.scrapers.base_scraper import BaseScraper

class MySourceScraper(BaseScraper):
    def __init__(self):
        super().__init__(source_domain='mysource.az')

    def parse_article_list(self, soup, page_number=1):
        articles = []
        for item in soup.select('div.article-item'):
            link = item.select_one('a')
            if not link:
                continue
            articles.append({
                'url': link['href'],
                'title': link.get_text(strip=True),
                'published_at': None,
                'image_url': None,
            })
        return articles

    def parse_article_detail(self, soup, article_url):
        return {
            'content': soup.select_one('div.content').get_text(strip=True),
            'author': None,
        }
```

2. Register in `run_scraper.py`:

```python
from scraper_job.scrapers.mysource_scraper import MySourceScraper

SCRAPERS = {
    ...
    'mysource.az': MySourceScraper,
}
```

3. Insert DB record:

```sql
INSERT INTO news.news_sources (name, domain, base_url, language, is_active)
VALUES ('MySource.az', 'mysource.az', 'https://mysource.az', 'az', TRUE)
ON CONFLICT (domain) DO NOTHING;
```

4. Test:

```bash
python -m scraper_job.run_scraper run -s mysource.az -p 1
```

---

## Features

- ✅ 11 active news sources
- ✅ Snapshot-based storage (zero storage growth)
- ✅ JavaScript rendering via Playwright
- ✅ Deduplication by content hash
- ✅ Job tracking and error logging (auto-cleanup after 7 days)
- ✅ GitHub Actions automation (3x daily)
- ✅ Next.js frontend with search, filters, and pagination
- ✅ Deployed on Vercel + Neon (fully serverless)
- ✅ Configurable rate limiting and retries

---

## JavaScript Rendering (Playwright)

Many Azerbaijani news sites serve skeleton HTML to crawlers. Playwright renders pages with a headless Chromium browser before extraction.

```bash
# Enable locally
export USE_PLAYWRIGHT=true
python -m scraper_job.run_scraper run -s sonxeber.az -p 3
```

Playwright is always enabled in GitHub Actions (`USE_PLAYWRIGHT=true` in workflow env).

---

## License

MIT
