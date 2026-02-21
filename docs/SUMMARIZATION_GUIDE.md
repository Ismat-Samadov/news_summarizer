# AI Summarization Guide

Complete guide to using Google Gemini AI for automatic news summarization.

## Overview

The news summarizer uses **Google Gemini 2.0 Flash Exp** to automatically generate comprehensive summaries of scraped articles in Azerbaijani language.

### What It Does

- Generates 3 levels of summaries (short, medium, long)
- Extracts key points (bullet points)
- Identifies named entities (people, places, organizations)
- Classifies topics and themes
- Performs sentiment analysis
- Provides quality confidence scores
- **All outputs in Azerbaijani language**

---

## Quick Start

### 1. Scrape Articles with Content

**Important**: Articles must have full content to be summarized.

```bash
# Scrape with --details flag to get full content
python -m scraper_job.run_scraper run -s sonxeber.az -p 2 --details
```

### 2. Generate Summaries

```bash
# Summarize all unsummarized articles
python -m scraper_job.run_summarizer run

# Limit to 50 articles
python -m scraper_job.run_summarizer run --batch-size 50
```

### 3. Check Results

```bash
# View summarization statistics
python -m scraper_job.run_summarizer stats
```

---

## Commands

### Run Summarization

```bash
python -m scraper_job.run_summarizer run [OPTIONS]
```

**Options:**
- `--batch-size N` - Number of articles to summarize (default: 100)
- `--source DOMAIN` - Filter by source domain (e.g., sonxeber.az)
- `--triggered-by TYPE` - Source: manual, github_action, scheduled

**Examples:**
```bash
# Summarize 100 articles
python -m scraper_job.run_summarizer run

# Summarize 50 articles from specific source
python -m scraper_job.run_summarizer run --batch-size 50 --source sonxeber.az

# Triggered by GitHub Actions
python -m scraper_job.run_summarizer run --batch-size 100 --triggered-by github_action
```

### Test Summarizer

```bash
python -m scraper_job.run_summarizer test
```

Tests the summarizer with one article and displays results.

### View Statistics

```bash
python -m scraper_job.run_summarizer stats
```

Shows summarization progress for each news source.

---

## Gemini API Setup

### Get API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with Google account
3. Click **Get API Key**
4. Click **Create API key in new project**
5. Copy the API key

### Add to .env

```env
GEMINI_API_KEY=your_actual_api_key_here
```

### Verify Connection

```bash
python -m scraper_job.run_summarizer test
```

---

## Summary Structure

### Example Output

```json
{
  "summary_short": "Britaniyada qadın texniki səhv nəticəsində İlon Maskdan 100 dəfə zəngin oldu.",

  "summary_medium": "Britaniyada yaşayan 53 yaşlı Theresa Rowley bank səhvi nəticəsində 10 milyard funt sterlinq alıb. Bu məbləğ İlon Maskın sərvətindən 100 dəfə çoxdur. Qadın pulları xeyriyyə məqsədləri üçün istifadə etmək istəyir.",

  "summary_long": "Britaniyada 53 yaşlı Theresa Rowley adlı qadının bank hesabına səhvən 10 milyard funt sterlinq (təxminən 12,5 milyard dollar) köçürülüb. Bu məbləğ dünyanın ən varlı insanlarından biri olan İlon Maskın sərvətindən təxminən 100 dəfə çoxdur...",

  "key_points": [
    "Bank səhvi nəticəsində 10 milyard funt hesaba köçürülüb",
    "Qadın pulu xeyriyyə üçün istifadə etmək istəyir",
    "Bank səhvi aşkar edərək məbləği geri götürüb"
  ],

  "entities": {
    "people": ["Theresa Rowley", "İlon Mask"],
    "organizations": ["Britaniya bankı"],
    "locations": ["Britaniya"]
  },

  "topics": ["maliyyə", "bank səhvi", "xeyriyyə"],

  "sentiment": "neutral",

  "confidence_score": 0.92,

  "model_used": "gemini-2.0-flash-exp",
  "model_version": "2.0-flash-exp"
}
```

### Field Descriptions

| Field | Description | Language |
|-------|-------------|----------|
| `summary_short` | 1-2 sentence summary (≤50 words) | Azerbaijani |
| `summary_medium` | 1 paragraph summary (≤150 words) | Azerbaijani |
| `summary_long` | Detailed multi-paragraph (≤500 words) | Azerbaijani |
| `key_points` | 3-5 main points as bullet list | Azerbaijani |
| `entities.people` | Names of people mentioned | Original |
| `entities.organizations` | Organizations mentioned | Original |
| `entities.locations` | Places mentioned | Original |
| `topics` | Main topics/themes (2-5) | Azerbaijani |
| `sentiment` | positive / negative / neutral | English |
| `confidence_score` | Quality score (0.0 - 1.0) | Number |

---

## Free Tier Limits

### Gemini 2.0 Flash Exp

**Daily Limits:**
- **Requests**: 1,000 requests per day
- **Tokens**: 250,000 tokens per minute
- **Context Window**: 1 million tokens
- **Cost**: $0.00 (completely free)

**Reset**: Midnight Pacific Time daily

### Our Usage

**Per Summary:**
- Input: ~500-2000 tokens (article content)
- Output: ~300-800 tokens (summary)
- Total: ~1,000-3,000 tokens per article

**Daily Capacity:**
- 1,000 requests/day = 1,000 articles/day
- More than enough for 3 scraping runs/day (300 articles)

### Rate Limiting

The system includes built-in handling for rate limits:
- Automatic retry with exponential backoff
- Error logging for failed summaries
- Continue processing remaining articles if one fails

---

## Database Schema

### summaries Table

```sql
CREATE TABLE summaries (
    id UUID PRIMARY KEY,
    article_id UUID REFERENCES articles(id),

    -- Summaries
    summary_short TEXT,
    summary_medium TEXT,
    summary_long TEXT,

    -- Extracted Information
    key_points JSONB,
    entities JSONB,
    topics JSONB,
    sentiment VARCHAR(50),

    -- Metadata
    model_used VARCHAR(100),
    model_version VARCHAR(50),
    confidence_score DECIMAL(3,2),

    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    UNIQUE(article_id)
);
```

### Query Examples

```sql
-- Get articles with summaries
SELECT
    a.title,
    s.summary_short,
    s.sentiment,
    s.confidence_score
FROM articles a
JOIN summaries s ON a.id = s.article_id
ORDER BY a.published_at DESC
LIMIT 10;

-- Find high-confidence summaries
SELECT
    a.title,
    s.summary_medium,
    s.confidence_score
FROM articles a
JOIN summaries s ON a.id = s.article_id
WHERE s.confidence_score >= 0.8
ORDER BY s.confidence_score DESC;

-- Get summaries by sentiment
SELECT
    sentiment,
    COUNT(*) as count
FROM summaries
GROUP BY sentiment;

-- Extract topics across all summaries
SELECT
    jsonb_array_elements_text(topics) as topic,
    COUNT(*) as frequency
FROM summaries
GROUP BY topic
ORDER BY frequency DESC
LIMIT 20;
```

---

## Workflow Integration

### Automated GitHub Actions

Summarization runs automatically 30 minutes after each scraping job:

**Schedule:**
- 09:30 UTC (after 09:00 scraping)
- 13:30 UTC (after 13:00 scraping)
- 18:30 UTC (after 18:00 scraping)

**Process:**
1. Scraper runs and saves articles
2. Wait 30 minutes (for scraping to complete)
3. Summarizer queries unsummarized articles
4. Generates summaries via Gemini API
5. Saves summaries to database
6. Marks articles as summarized

### Manual Workflow

```bash
# 1. Scrape with content
python -m scraper_job.run_scraper run -s sonxeber.az -p 2 --details

# 2. Generate summaries
python -m scraper_job.run_summarizer run

# 3. Check results
python -m scraper_job.run_summarizer stats
```

---

## Troubleshooting

### No Articles to Summarize

**Problem**: "No articles found that need summarization"

**Solutions:**
1. Scrape articles with `--details` flag to get full content
2. Check that articles have `is_processed = TRUE`
3. Verify articles aren't already summarized

```bash
# Scrape with full content
python -m scraper_job.run_scraper run -s sonxeber.az -p 2 --details
```

### Gemini API Connection Failed

**Problem**: "Failed to connect to Gemini API"

**Solutions:**
1. Verify `GEMINI_API_KEY` is set in `.env`
2. Check API key is valid (test at [Google AI Studio](https://makersuite.google.com))
3. Ensure no billing issues (free tier should work)
4. Check internet connection

```bash
# Test connection
python -m scraper_job.run_summarizer test
```

### Rate Limit Exceeded

**Problem**: "429 Too Many Requests"

**Solutions:**
1. Wait until midnight Pacific Time (daily reset)
2. Reduce `--batch-size` to stay under 1,000/day
3. Space out summarization runs throughout the day

```bash
# Use smaller batches
python -m scraper_job.run_summarizer run --batch-size 50
```

### Low Confidence Scores

**Problem**: Summaries have low confidence (<0.6)

**Possible Causes:**
1. Article content is too short or incomplete
2. Article is in mixed languages
3. Content quality is poor
4. Parsing issues

**Solutions:**
1. Review article content quality
2. Improve content extraction in scraper
3. Filter out low-quality articles

```sql
-- Find low-confidence summaries
SELECT a.title, s.confidence_score, a.url
FROM articles a
JOIN summaries s ON a.id = s.article_id
WHERE s.confidence_score < 0.6
ORDER BY s.confidence_score ASC;
```

---

## Best Practices

### 1. Scrape with Full Content

Always use `--details` flag when you want to summarize:

```bash
python -m scraper_job.run_scraper run -s sonxeber.az -p 3 --details
```

### 2. Batch Processing

Process in batches to avoid rate limits:

```bash
# Morning batch
python -m scraper_job.run_summarizer run --batch-size 300

# Evening batch (after reset)
python -m scraper_job.run_summarizer run --batch-size 300
```

### 3. Monitor Quality

Check confidence scores regularly:

```sql
SELECT
    AVG(confidence_score) as avg_confidence,
    MIN(confidence_score) as min_confidence,
    MAX(confidence_score) as max_confidence
FROM summaries
WHERE created_at >= CURRENT_DATE;
```

### 4. Handle Failures Gracefully

The system continues processing even if individual summaries fail:
- Check logs for failed articles
- Retry failed articles later
- Review error patterns

---

## Advanced Usage

### Custom Prompts

Modify the prompt in `utils/summarizer.py` to customize summary style:

```python
def create_summary_prompt(self, article: Dict) -> str:
    # Customize prompt here
    prompt = f"""...your custom prompt..."""
    return prompt
```

### Confidence Scoring

Adjust confidence calculation in `calculate_confidence()`:

```python
def calculate_confidence(self, summary: Dict) -> float:
    # Custom confidence logic
    score = 0.0
    # Add your criteria
    return min(score, 1.0)
```

### Batch Size Optimization

Find optimal batch size based on your needs:

```bash
# Small batches (safer, slower)
python -m scraper_job.run_summarizer run --batch-size 50

# Medium batches (balanced)
python -m scraper_job.run_summarizer run --batch-size 100

# Large batches (faster, riskier)
python -m scraper_job.run_summarizer run --batch-size 300
```

---

## API Reference

### NewsSummarizer Class

```python
from scraper_job.utils.summarizer import NewsSummarizer

# Initialize
summarizer = NewsSummarizer(api_key="your_key")

# Test connection
summarizer.test_connection()

# Summarize one article
summary = summarizer.summarize_article(article_dict)

# Batch summarize
results = summarizer.batch_summarize(articles_list, max_articles=100)
```

### Database Methods

```python
from scraper_job.utils.database import DatabaseManager

db = DatabaseManager()

# Get articles needing summarization
articles = db.get_articles_for_summarization(limit=100)

# Insert summary
summary_id = db.insert_summary(summary_data)

# Mark as summarized
db.mark_article_summarized(article_id)
```

---

## Performance Tips

1. **Use Gemini 2.0 Flash Exp**: Fastest, free tier
2. **Batch Process**: Process multiple articles in one run
3. **Parallel Processing**: (Future) Implement async requests
4. **Cache Responses**: (Future) Cache common summaries
5. **Monitor Quota**: Track daily usage

---

## Future Enhancements

### Planned Features
- ⏳ Async summarization for faster processing
- ⏳ Multi-language support (Russian, English)
- ⏳ Custom summary templates
- ⏳ Summary comparison and validation
- ⏳ Automatic quality improvement
- ⏳ Summary caching and deduplication

---

## Resources

- [Google Gemini API Docs](https://ai.google.dev/docs)
- [Get API Key](https://makersuite.google.com/app/apikey)
- [Rate Limits Info](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Python SDK](https://github.com/google/generative-ai-python)

---

**Last Updated**: 2026-02-21
**Version**: 1.0
**Status**: ✅ Fully Implemented
