# Azerbaijan News Scraper

Async news scraper for 8 major Azerbaijani news sources with AI summarization and Telegram reporting.

## 🔗 Live Links

- **🌐 Web Application**: [https://news-summarizer-omega.vercel.app/](https://news-summarizer-omega.vercel.app/)
- **📱 Telegram Channel**: [https://t.me/batimess](https://t.me/batimess)

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Data Flow](#-data-flow)
- [Uniqueness Mechanisms](#-uniqueness-mechanisms)
- [AI Processing Pipeline](#-ai-processing-pipeline)
- [Performance](#-performance)
- [Setup](#-setup)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Automation](#-automation)
- [Configuration](#-configuration)

## 🚀 Features

- **8 News Sources**: Banker.az, Marja.az, Report.az, Fed.az, Sonxeber.az, Iqtisadiyyat.az, Trend.az, APA.az
- **Async Architecture**: 3-4x faster than synchronous scraping
- **AI Summarization**: Google Gemini 2.0 Flash powered article summaries
- **Telegram Reports**: Automatic notifications with summaries
- **PostgreSQL Storage**: Full article database with relationships
- **Concurrent Processing**: Batch scraping with rate limiting
- **Automated Scheduling**: Runs 3x daily via GitHub Actions (12:00, 16:00, 20:00 UTC)
- **Next.js Frontend**: Modern web interface with time-based session differentiation
- **Duplicate Detection**: URL-based uniqueness with database constraints

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Data Sources"
        A1[Banker.az]
        A2[Marja.az]
        A3[Report.az]
        A4[Fed.az]
        A5[Sonxeber.az]
        A6[Iqtisadiyyat.az]
        A7[Trend.az]
        A8[APA.az]
    end

    subgraph "Scraper Layer"
        B1[Async HTTP Client]
        B2[BeautifulSoup Parser]
        B3[Rate Limiter]
        B4[Duplicate Filter]
    end

    subgraph "AI Processing"
        C1[Gemini 2.0 Flash]
        C2[Relevance Filter]
        C3[Summary Generator]
    end

    subgraph "Storage"
        D1[(PostgreSQL)]
        D2[Articles Table]
        D3[Summaries Table]
    end

    subgraph "Distribution"
        E1[Telegram Bot]
        E2[Next.js Frontend]
        E3[Vercel Hosting]
    end

    subgraph "Automation"
        F1[GitHub Actions]
        F2[Cron Schedule]
    end

    A1 & A2 & A3 & A4 & A5 & A6 & A7 & A8 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> D1
    D1 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> D3
    D3 --> E1
    D1 --> E2
    E2 --> E3
    F1 --> F2
    F2 --> B1

    style C1 fill:#4285f4
    style D1 fill:#336791
    style E3 fill:#000000
    style F1 fill:#2088ff
```

## 🔄 Data Flow

```mermaid
sequenceDiagram
    autonumber
    participant GH as GitHub Actions
    participant SC as Scraper
    participant SRC as News Sources
    participant DB as PostgreSQL
    participant AI as Gemini AI
    participant TG as Telegram
    participant FE as Frontend

    GH->>SC: Trigger scrape (3x daily)
    SC->>SRC: Fetch article lists (async)
    SRC-->>SC: Return article URLs
    SC->>SRC: Scrape articles (batches of 10)
    SRC-->>SC: Return article content

    SC->>DB: Check for duplicates (URL)
    DB-->>SC: Return existing URLs
    SC->>SC: Filter new articles

    SC->>DB: Save new articles
    DB-->>SC: Return session ID

    SC->>AI: Send articles for filtering
    AI-->>SC: Return banking-relevant articles

    SC->>AI: Request summary
    AI-->>SC: Return banking intelligence

    SC->>DB: Save summary with session ID
    SC->>TG: Send summary + stats

    FE->>DB: Query summaries
    DB-->>FE: Return data
    FE-->>User: Display summaries
```

## 🔒 Uniqueness Mechanisms

We ensure article uniqueness through multiple layers:

### 1. Database-Level Constraints

```sql
CREATE TABLE news.articles (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,  -- ✅ Database constraint
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    ...
);

CREATE INDEX idx_articles_url ON news.articles(url);
```

### 2. Application-Level Duplicate Detection

```mermaid
flowchart TD
    A[New Article Scraped] --> B{URL exists in DB?}
    B -->|Yes| C[Skip - Log as Duplicate]
    B -->|No| D[Validate Article]
    D --> E{Has Title & Content?}
    E -->|No| F[Skip - Invalid]
    E -->|Yes| G[Save to Database]
    G --> H[Link to Session]
    H --> I[Count as New Article]

    C --> J[Update Stats]
    F --> J
    I --> J
    J --> K[Session Complete]

    style G fill:#4caf50
    style C fill:#ff9800
    style F fill:#f44336
```

### 3. Uniqueness Workflow

```python
# 1. Fetch existing URLs from database
existing_urls = await db.get_existing_urls()

# 2. Filter out duplicates before saving
new_articles = [
    article for article in scraped_articles
    if article['url'] not in existing_urls
]

# 3. PostgreSQL UNIQUE constraint as fallback
# ON CONFLICT DO NOTHING prevents errors
INSERT INTO news.articles (url, title, content, ...)
VALUES (...)
ON CONFLICT (url) DO NOTHING;
```

### 4. Statistics Tracking

Each scraping session tracks:
- **Total Found**: All articles discovered
- **New Articles**: Successfully saved to database
- **Duplicates Skipped**: Articles already in database
- **Errors**: Failed to scrape or parse

## 🤖 AI Processing Pipeline

```mermaid
flowchart LR
    subgraph "Step 1: Filtering"
        A[All Articles] --> B[Gemini API]
        B --> C{Banking Relevant?}
        C -->|Yes| D[Keep Article]
        C -->|No| E[Discard]
    end

    subgraph "Step 2: Summarization"
        D --> F[Prepare Context]
        F --> G[Gemini API]
        G --> H[Banking Intelligence Report]
    end

    subgraph "Step 3: Distribution"
        H --> I[Save to Database]
        I --> J[Send to Telegram]
        I --> K[Display on Frontend]
    end

    style B fill:#4285f4
    style G fill:#4285f4
    style H fill:#34a853
```

### AI Filtering Criteria

**RELEVANT (Banking-Related):**
- Bank and finance sector news
- Macroeconomic indicators (inflation, GDP growth)
- Regulatory and legislative changes
- Credit, mortgage, deposit markets
- Bank capital and financial results
- Fintech and digital banking
- Currency exchange and monetary policy
- International financial organizations (IMF, World Bank)
- Business environment and investment climate

**IRRELEVANT (Filtered Out):**
- International politics and conflicts (unless affecting banks)
- Sports news
- Culture and entertainment
- Technology (unless fintech)
- General infrastructure projects (unless financing aspects)

### Rate Limiting

```python
# Gemini 2.0 Flash Free Tier Limits
requests_per_minute = 15
tokens_per_minute = 1_000_000
requests_per_day = 1_500

# Implementation
- Tracks request timestamps
- Enforces delays when approaching limits
- Falls back gracefully on quota exhaustion
```

## 📊 Performance

- **Speed**: ~0.30 seconds per article
- **Throughput**: ~200 articles in ~1 minute
- **Concurrent Requests**: 5-10 simultaneous
- **Batch Size**: 10 articles per batch
- **Session Duration**: 1-2 minutes average
- **AI Processing**: 2-3 seconds per summary

## 🛠️ Setup

### 1. Install Dependencies

```bash
# Backend (Python)
pip install -r scraper/requirements.txt

# Frontend (Node.js)
cd frontend
npm install
```

### 2. Configure Environment

Create `.env.local` in root:
```env
DATABASE_URL=postgresql://user:password@host:port/dbname
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

Create `frontend/.env.local`:
```env
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### 3. Initialize Database

```bash
python scraper/scripts/init_db.py
```

### 4. Verify Setup

```bash
# Test database connection
python scraper/scripts/verify_db.py

# Test individual scraper
python scraper/scripts/test_banker_az.py
```

## 🚀 Usage

### Run Scraper Manually

```bash
python scraper/main.py
```

### Run Frontend Development Server

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Test Individual Source

```python
import asyncio
from sources.apa_az import ApaAzScraper

async def test():
    async with ApaAzScraper() as scraper:
        articles = await scraper.scrape_all(num_pages=1, batch_size=10)
        print(f"Scraped {len(articles)} articles")

asyncio.run(test())
```

## 📁 Project Structure

```
news_summarizer/
├── scraper/                      # Python backend
│   ├── main.py                   # Main async scraper orchestrator
│   ├── base_scraper.py           # Async base class for all scrapers
│   ├── db.py                     # PostgreSQL operations
│   ├── summarizer.py             # Gemini AI integration
│   ├── telegram.py               # Telegram bot notifications
│   ├── requirements.txt          # Python dependencies
│   ├── sources/                  # Individual news source scrapers
│   │   ├── banker_az.py          # Banker.az scraper
│   │   ├── marja_az.py           # Marja.az scraper
│   │   ├── report_az.py          # Report.az scraper
│   │   ├── fed_az.py             # Fed.az scraper (multi-category)
│   │   ├── sonxeber_az.py        # Sonxeber.az scraper
│   │   ├── iqtisadiyyat_az.py    # Iqtisadiyyat.az scraper
│   │   ├── trend_az.py           # Trend.az scraper
│   │   └── apa_az.py             # APA.az scraper
│   └── scripts/                  # Utility scripts
│       ├── init_db.py            # Database initialization
│       ├── schema.sql            # PostgreSQL schema
│       ├── verify_db.py          # Database verification
│       └── test_*.py             # Individual scraper tests
│
├── frontend/                     # Next.js frontend
│   ├── app/                      # Next.js App Router
│   │   ├── page.tsx              # Homepage (summaries list)
│   │   ├── summary/[id]/         # Summary detail page
│   │   ├── api/                  # API routes
│   │   │   ├── summaries/        # GET /api/summaries
│   │   │   └── stats/            # GET /api/stats
│   │   └── layout.tsx            # Root layout
│   ├── components/               # React components
│   │   ├── SummariesGrid.tsx     # Summary cards with pagination
│   │   ├── ArticlesGrid.tsx      # Article cards with pagination
│   │   └── Pagination.tsx        # Reusable pagination
│   ├── lib/                      # Utilities
│   │   ├── db.ts                 # Database queries
│   │   └── utils.ts              # Helper functions (date formatting, etc)
│   └── types/                    # TypeScript types
│       └── index.ts              # Database model types
│
├── .github/                      # GitHub Actions
│   └── workflows/
│       └── scrape-news.yml       # Automated scraping (3x daily)
│
└── README.md                     # This file
```

## ⏰ Automation

### GitHub Actions Schedule

The scraper runs automatically **3 times daily**:

```yaml
schedule:
  - cron: '0 12 * * *'  # 12:00 UTC (16:00 Azerbaijan)
  - cron: '0 16 * * *'  # 16:00 UTC (20:00 Azerbaijan)
  - cron: '0 20 * * *'  # 20:00 UTC (00:00 Azerbaijan next day)
```

### Workflow Steps

```mermaid
graph LR
    A[GitHub Actions] --> B[Checkout Code]
    B --> C[Setup Python 3.11]
    C --> D[Install Dependencies]
    D --> E[Run Scraper]
    E --> F{Success?}
    F -->|Yes| G[Log Completion]
    F -->|No| H[Log Error]
    G --> I[Finish]
    H --> I

    style E fill:#4285f4
    style G fill:#34a853
    style H fill:#ea4335
```

### Manual Trigger

You can manually trigger the workflow via GitHub Actions UI or:

```bash
gh workflow run scrape-news.yml
```

## 🔧 Configuration

### Scraper Settings

| Source | Pages | Categories | Notes |
|--------|-------|------------|-------|
| Banker.az | 2 | 1 | Banking news |
| Marja.az | 2 | 1 | Economic news |
| Report.az | 1 | 1 | May have bot protection |
| Fed.az | 2 | 2 | Bank + Finance |
| Sonxeber.az | 2 | 1 | Latest news |
| Iqtisadiyyat.az | 2 | 3 | Bank + Business + Finance |
| Trend.az | 1 | 1 | Economic news |
| APA.az | 2 | 1 | Economic news |

### Rate Limiting

```python
# HTTP Requests
max_concurrent_requests = 5    # Semaphore limit
batch_size = 10                # Articles per batch
delay_between_batches = 1      # Seconds

# AI API (Gemini)
requests_per_minute = 15       # Rate limit
requests_per_day = 1500        # Daily quota
```

### Database Schema

```sql
-- Articles table with uniqueness constraint
CREATE TABLE news.articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(100) NOT NULL,
    url TEXT NOT NULL UNIQUE,              -- Ensures uniqueness
    published_date TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    language VARCHAR(10) DEFAULT 'az',
    scraping_session_id INTEGER REFERENCES news.scraping_summaries(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraping summaries table
CREATE TABLE news.scraping_summaries (
    id SERIAL PRIMARY KEY,
    scraping_date DATE NOT NULL DEFAULT CURRENT_DATE,
    summary TEXT NOT NULL,                 -- AI-generated summary
    articles_count INTEGER NOT NULL,       -- Total articles processed
    sources_count INTEGER NOT NULL,        -- Number of sources
    new_articles_count INTEGER NOT NULL,   -- New articles saved
    scraping_duration_seconds NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Used for time differentiation
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📦 Dependencies

### Backend (Python)

- **aiohttp**: Async HTTP client for concurrent requests
- **beautifulsoup4**: HTML parsing and extraction
- **psycopg2-binary**: PostgreSQL database adapter
- **google-genai**: Google Gemini AI SDK (new unified SDK)
- **python-dotenv**: Environment variable management
- **lxml**: Fast HTML/XML parser
- **requests**: HTTP library for synchronous requests

### Frontend (Next.js)

- **Next.js 15**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **pg**: PostgreSQL client for Node.js
- **React 19**: UI library

## 🎯 Output

Each scraping session generates:

### 1. Database Records
- Articles with full metadata
- Session summary with AI analysis
- Relationships between articles and sessions

### 2. AI Summary
- Banking intelligence report
- Trend analysis
- Risk and opportunity identification
- Action items and recommendations

### 3. Telegram Report
```
📊 BANK SEKTORU XÜLASƏSİ
24 Dekabr 2025, 12:00

✅ Yeni xəbərlər: 45
📰 Ümumi xəbərlər: 45
🌐 Mənbələr: 8
⏱ İcra müddəti: 1m 23s

🤖 AI ANALİZ:
[Banking intelligence report...]
```

### 4. Frontend Display
- Homepage with paginated summary cards
- Detail pages with full AI reports
- Time-differentiated sessions (12:00, 16:00, 20:00)
- Article listings with metadata

## 📈 Statistics Tracked

Each session tracks:
- **Total Articles Found**: All articles discovered across sources
- **New Articles Saved**: Articles successfully saved to database
- **Duplicate Articles Skipped**: Articles already in database (by URL)
- **Sources Count**: Number of news sources scraped
- **Scraping Duration**: Total time taken for the session
- **Per-Source Breakdowns**: Statistics for each news source
- **AI Processing Time**: Time spent on filtering and summarization

## 🔍 Monitoring & Debugging

### View Logs

```bash
# GitHub Actions logs
gh run list --workflow=scrape-news.yml
gh run view <run-id> --log

# Local testing
python scraper/main.py 2>&1 | tee scraper.log
```

### Database Queries

```sql
-- Check recent scraping sessions
SELECT id, created_at, new_articles_count, articles_count, sources_count
FROM news.scraping_summaries
ORDER BY created_at DESC
LIMIT 10;

-- Find duplicates (should be 0)
SELECT url, COUNT(*)
FROM news.articles
GROUP BY url
HAVING COUNT(*) > 1;

-- Articles per source
SELECT source, COUNT(*) as count
FROM news.articles
GROUP BY source
ORDER BY count DESC;
```

## 🚨 Troubleshooting

### Common Issues

**1. Quota Exceeded (429 Error)**
```
Error: 429 RESOURCE_EXHAUSTED
Solution: Using gemini-2.0-flash with generous free tier
```

**2. Bot Protection (403 Error)**
```
Error: 403 Forbidden on Report.az, Iqtisadiyyat.az
Solution: Silently handled, these sites use Cloudflare protection
```

**3. Database Connection Failed**
```
Error: connection to server failed
Solution: Check DATABASE_URL in .env.local
```

## 🔄 Backup

Synchronous version backed up as: `scraper/main_sync_backup.py`

## 📝 License

Private project for news aggregation.

---

**Built with ❤️ for Azerbaijan's banking sector**

🤖 Powered by Google Gemini AI | 🗄️ PostgreSQL | ⚡ Next.js | 🐍 Python AsyncIO
