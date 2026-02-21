# News Scraper - Website Analysis & Database Design

## Overview
This document provides a comprehensive analysis of 10 Azerbaijani news websites and the database schema design for the news scraping and summarization system.

---

## News Source Analysis

### 1. **Sonxeber.az**
- **Language**: Azerbaijani (Latin script)
- **URL Pattern**: `/{article_id}/{slug-title}`
- **Pagination**: Query param `?start=2` (incremental)
- **Date Format**: "21 fevral"
- **Unique ID**: Numeric article ID (e.g., 388358)
- **Image Path**: `/uploads/ss_{ID}_{hash}.jpg`
- **Categories**: Sosial, İqtisadiyyat, Siyasət, Hadisə, Kriminal
- **Notes**: Standard pagination, easy to scrape

### 2. **Metbuat.az**
- **Language**: Azerbaijani (Cyrillic characters)
- **URL Pattern**: `/news/{id}/{slug}.html`
- **Pagination**: `?page=2&per-page=39`
- **Date Format**: "21 Fevral 2026 12:06" (full timestamp)
- **Unique ID**: Numeric (e.g., 1547127)
- **Image Path**: `/images/metbuat/images_t/{ID}.jpg`
- **Categories**: ÖLKƏ, SİYASƏT, İQTİSADİYYAT
- **Notes**: Grid layout, high page count (2039 pages)

### 3. **Axar.az**
- **Language**: Azerbaijani (Latin script)
- **URL Pattern**: `/news/{category}/{article-id}.html`
- **Pagination**: Infinite scroll (no traditional pagination)
- **Date Format**: "20 Fevral 14:23"
- **Unique ID**: Numeric (e.g., 1064279)
- **Image Sizes**: Multiple (250x, 70x, 660x390)
- **Categories**: gundem, siyaset, planet, toplum, iqtisadiyyat, kult, saghliq, idman
- **Notes**: Modern layout, requires scroll simulation

### 4. **News.milli.az**
- **Language**: Azerbaijani (Latin script)
- **URL Pattern**: `/{category}/{article-id}.html`
- **Pagination**: AJAX infinite scroll via `/latest.php`
- **Date Format**: "19:00" or "20 Fevral 23:30"
- **Unique ID**: Numeric (e.g., 1317167)
- **Engagement**: View counts visible (e.g., "11 806")
- **Categories**: sport, incident, society, world, showbiz, culture, country, politics, health
- **Analytics**: Google Analytics, Yandex Metrica
- **Notes**: AJAX-based loading, engagement metrics available

### 5. **Azertag.az**
- **Language**: Primary Azerbaijani, supports 7 languages (RU, EN, DE, FR, ES, AR, ZH)
- **URL Pattern**: `/xeber/{slug}-{ID}`
- **Pagination**: `?page=2` (21,600 pages!)
- **Date Format**: "21.02.2026 [19:22]"
- **Unique ID**: Numeric (e.g., 4034747)
- **Images**: No thumbnails in listing view
- **Categories**: Politics, Economy, Culture, Society, Sports, World News
- **Notes**: State news agency, massive archive, multilingual

### 6. **APA.az**
- **Language**: Azerbaijani, supports Persian, Russian, English, French
- **URL Pattern**: `/{category}/{slug}-{ID}`
- **Pagination**: `?page=2` (173 pages)
- **Date Format**: Separate time "17:44" and date "21 fevral 2026"
- **Unique ID**: Numeric (e.g., 941075)
- **Image Path**: `/storage/news/`
- **Categories**: hadise, avropa, sosyal, herbi, sahibkarliq, maliyye, infrastruktur, elm-ve-tehsil, ikt
- **Analytics**: Yandex Metrika, Google Analytics
- **Notes**: Professional layout, good structure

### 7. **Oxu.az**
- **Language**: Azerbaijani
- **URL Pattern**: Unknown (403 Forbidden)
- **Pagination**: Query param based
- **Notes**: **Anti-scraping protection detected** - Returns 403 error, will require special headers/user-agents

### 8. **Report.az**
- **Language**: Azerbaijani, Russian, English available
- **URL Pattern**: `/{category}/{article-slug}`
- **Pagination**: Supported (specific pattern not visible)
- **Date Format**: "21 fevral, 2026" and "19:22"
- **Unique ID**: Slug-based (no numeric ID visible)
- **Categories**: Digər ölkələr, Futbol, İnfrastruktur
- **Structured Data**: Schema.org markup for SEO
- **Notes**: Modern site, good semantic markup

### 9. **Xezerxeber.az**
- **Language**: Azerbaijani (Latin script)
- **URL Pattern**: `/news/{category}/{ID}/{slug}`
- **Pagination**: Infinite scroll
- **Date Format**: "18:14" or "20 Fevral 2026"
- **Unique ID**: Numeric (e.g., 450508)
- **Image CDN**: `cdn.xezerxeber.az`
- **Categories**: Veb TV, Gündəm, İqtisadiyyat, Cəmiyyət, Hadisə, Dünya, Şou Biznes, İdman, Mədəniyyət
- **Analytics**: Google Analytics, OneSignal notifications
- **Notes**: Rich category structure, CDN usage

### 10. **Modern.az**
- **Language**: 6 languages (AZ, EN, RU, TR, FA) - highly multilingual
- **URL Pattern**: `/{lang}/{category}/{id}/{slug}/`
- **Pagination**: `?page=2`
- **Date Format**: "21 February 2026, 19:22" (English format when in EN)
- **Unique ID**: Numeric (e.g., 571470)
- **Categories**: World, Country, Culture, Sports
- **Analytics**: Google Analytics, Yandex Metrica, Microsoft Clarity
- **Notes**: International focus, excellent multilingual support

---

## Common Patterns Identified

### URL Structures
1. **Numeric ID + Slug**: Most common (7/10 sites)
2. **Slug Only**: 1 site (report.az)
3. **Numeric ID Only**: Rare

### Pagination Types
- **Query Parameter**: 6 sites (`?page=N`, `?start=N`)
- **Infinite Scroll**: 3 sites (axar.az, milli.az, xezerxeber.az)
- **Protected**: 1 site (oxu.az - 403 error)

### Language Distribution
- **Azerbaijani Only**: 6 sites
- **Multilingual (2-3 languages)**: 2 sites
- **Highly Multilingual (5+ languages)**: 2 sites (azertag.az, modern.az)

### Content Elements Present
| Element | Sites |
|---------|-------|
| Title | 10/10 |
| URL | 10/10 |
| Date/Time | 10/10 |
| Image | 9/10 |
| Category | 10/10 |
| Numeric ID | 9/10 |
| View Count | 1/10 (milli.az) |
| Author | Not visible in listings |

### Challenges Identified
1. **oxu.az**: Anti-scraping protection (403 Forbidden)
2. **Infinite Scroll Sites**: Require Selenium/Playwright for dynamic content
3. **AJAX Loading**: milli.az uses AJAX endpoints
4. **Rate Limiting**: Need to implement delays and respectful scraping
5. **Language Variants**: Multilingual sites need language-specific handling

---

## Database Schema Design

### Core Tables

#### 1. **news_sources**
Stores metadata about each news website.
- Tracks active/inactive sources
- Stores scraper configuration (pagination type, special requirements)
- JSONB field for flexible source-specific config

#### 2. **articles**
Main table for scraped articles.
- UUID primary key for better distribution
- `source_article_id` stores original ID from source
- `content_hash` for deduplication (SHA-256)
- Separate flags for `is_processed` and `is_summarized`
- JSONB `metadata` for source-specific fields
- Unique constraint on `(source_id, source_article_id)`

#### 3. **categories**
News categories per source.
- Source-specific (same category name might mean different things per source)
- Slug for URL-friendly references

#### 4. **summaries**
AI-generated summaries with multiple granularities.
- Three summary lengths (short, medium, long)
- Key points extraction (JSONB array)
- Named entity recognition (people, places, orgs)
- Sentiment analysis
- Confidence scoring
- Model tracking for A/B testing

#### 5. **scrape_jobs**
Track execution of scraping jobs.
- Job type: full_scrape, incremental, detail_scrape
- Performance metrics (duration, articles found/new/failed)
- Error tracking
- Triggered by source (GitHub Actions, manual, scheduled)

#### 6. **scrape_errors**
Detailed error logging for debugging.
- Per-URL error tracking
- Retry count and last retry timestamp
- Stack traces for debugging
- Error type classification

### Design Decisions

#### Why UUID for articles?
- Better for distributed systems
- Prevents ID enumeration
- Good for partitioning/sharding later

#### Why JSONB for metadata?
- Each news source has unique fields
- Flexible schema for experimentation
- Can add new fields without migrations
- Efficient indexing with GIN indexes

#### Why separate summaries table?
- Different lifecycle (articles scraped → summaries generated later)
- Multiple summary attempts possible
- A/B testing different AI models
- Summary regeneration without affecting article data

#### Why content_hash?
- Detect duplicate articles across sources
- Same news story from multiple sources
- Avoid reprocessing identical content

### Performance Optimizations

1. **Indexes on Common Queries**:
   - `articles(source_id)` - filter by source
   - `articles(published_at DESC)` - chronological queries
   - `articles(is_processed)`, `articles(is_summarized)` - find work to do
   - `articles(content_hash)` - duplicate detection

2. **Materialized Views** (Future):
   - Daily statistics
   - Source health metrics
   - Can be refreshed periodically

3. **Partitioning** (Future):
   - Partition `articles` by `published_at` (monthly)
   - Archive old data to cold storage

4. **Auto-updated Timestamps**:
   - Trigger function updates `updated_at` automatically
   - No application logic needed

---

## Scraping Strategy Recommendations

### Priority Tiers

**Tier 1 - Easy (Start Here)**:
- sonxeber.az - Simple pagination
- metbuat.az - Standard structure
- azertag.az - Clear patterns
- apa.az - Well-structured

**Tier 2 - Moderate**:
- report.az - Good markup
- modern.az - Multilingual but structured
- xezerxeber.az - Infinite scroll (manageable)

**Tier 3 - Complex**:
- axar.az - Infinite scroll, dynamic
- milli.az - AJAX loading
- oxu.az - Anti-scraping protection (requires special handling)

### Recommended Tools

1. **For Simple Sites (Tier 1)**:
   - `requests` + `BeautifulSoup4`
   - Fast, low resource usage

2. **For Infinite Scroll (Tier 2-3)**:
   - `Playwright` or `Selenium`
   - Scroll simulation
   - Wait for dynamic content

3. **For Protected Sites (oxu.az)**:
   - Rotating user agents
   - Request headers mimicking browser
   - Rate limiting (delays between requests)
   - Possible proxy rotation

### Scraping Workflow

```
1. List Page Scraping
   ├─> Extract article URLs, titles, dates, categories, images
   ├─> Store in `articles` table (is_processed=FALSE)
   └─> Track in `scrape_jobs`

2. Detail Page Scraping (later/async)
   ├─> Fetch full article content
   ├─> Generate content_hash
   ├─> Update article (is_processed=TRUE)
   └─> Log errors to `scrape_errors`

3. Summarization (async)
   ├─> Query articles where is_summarized=FALSE
   ├─> Generate summaries via Gemini API
   ├─> Store in `summaries` table
   └─> Update article (is_summarized=TRUE)
```

---

## Next Steps

### Phase 1: Foundation (Now)
- ✅ Database schema created
- ✅ News sources analyzed
- ⏳ Initialize database with schema
- ⏳ Create scraper base classes

### Phase 2: Basic Scrapers (Week 1-2)
- Implement Tier 1 scrapers (4 easy sites)
- Test pagination handling
- Implement error handling
- Basic deduplication

### Phase 3: Advanced Scrapers (Week 3)
- Implement Tier 2 scrapers
- Add infinite scroll support
- Handle multilingual sites

### Phase 4: AI Summarization (Week 4)
- Integrate Gemini API
- Implement summary generation
- Add entity extraction
- Sentiment analysis

### Phase 5: Automation (Week 5)
- GitHub Actions workflow
- Scheduled scraping (cron)
- Error notifications
- Data quality monitoring

### Phase 6: Frontend (Week 6+)
- Next.js application
- Article browsing
- Summary display
- Search functionality
- Deploy to Vercel

---

## Database Setup Commands

```bash
# Connect to PostgreSQL
psql $DATABASE_URL

# Run schema
\i /Users/ismatsamadov/news_summarizer/scraper_job/scripts/schema.sql

# Verify tables created
\dt

# Check initial data
SELECT * FROM news_sources;

# Run analysis queries
\i /Users/ismatsamadov/news_summarizer/scraper_job/scripts/analyse.sql
```

---

## Monitoring & Maintenance

### Daily Checks
- Run query #20 (Source health check)
- Check failed jobs
- Review error logs

### Weekly Analysis
- Article volume trends (query #6)
- Scraping success rates (query #9)
- Summary quality metrics (query #12)

### Monthly Maintenance
- Archive old articles (>6 months)
- Vacuum database
- Update source configurations
- Review and optimize slow queries

---

**Generated**: 2026-02-21
**Database Schema Version**: 1.0
**Total News Sources**: 10
