# GitHub Actions Setup Guide

This guide explains how to set up GitHub Actions for automated news scraping.

## Prerequisites

1. GitHub repository with this code
2. PostgreSQL database (Neon, Supabase, or any PostgreSQL provider)
3. Google Gemini API key (for AI summarization)

## Workflow Schedule

The scraper runs **3 times daily** at:
- **09:00 UTC** (12:00 Baku time)
- **13:00 UTC** (16:00 Baku time)
- **18:00 UTC** (21:00 Baku time)

Each run scrapes **3 pages** from each news source.

## Setup Instructions

### Step 1: Configure GitHub Secrets

GitHub Actions needs access to your database and API keys. These must be stored as encrypted secrets.

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

#### Required Secrets

| Secret Name      | Description                          | Example Value                                    |
|------------------|--------------------------------------|--------------------------------------------------|
| `DATABASE_URL`   | PostgreSQL connection string         | `postgresql://user:pass@host/db?sslmode=require` |
| `GEMINI_API_KEY` | Google Gemini API key (for summaries)| `AIzaSy...`                                      |

**Important**: Never commit these values to your repository!

### Step 2: Add Secrets

#### DATABASE_URL

```
Secret name: DATABASE_URL
Secret value: postgresql://user:password@host.region.provider.tech/database?sslmode=require
```

**Example format**:
```
postgresql://neondb_owner:YOUR_PASSWORD@ep-xxxxx.region.aws.neon.tech/neondb?sslmode=require
```

**Note**: Use your actual database connection string from Neon/Supabase.

#### GEMINI_API_KEY

```
Secret name: GEMINI_API_KEY
Secret value: your_gemini_api_key_here
```

**Example format**:
```
AIzaSy...your_actual_key_here
```

**Note**: Get your API key from https://makersuite.google.com/app/apikey

### Step 3: Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. If Actions are disabled, click **"I understand my workflows, go ahead and enable them"**
3. You should see the workflows:
   - **Scrape News Articles** (runs 3x daily)
   - **Generate AI Summaries** (runs 3x daily, 30 min after scraping)

### Step 4: Test the Workflow Manually

Before waiting for the scheduled run, test it manually:

1. Go to **Actions** tab
2. Click **Scrape News Articles** workflow
3. Click **Run workflow** dropdown
4. Adjust parameters if needed:
   - Max pages: `3` (default)
   - Scrape details: `false` (default)
5. Click **Run workflow** button

### Step 5: Monitor the First Run

1. Click on the running workflow
2. Click on the **scrape** job
3. Watch the logs in real-time
4. Check for errors

Expected output:
```
Run scraper for all sources
Running all scrapers (2 sources)
Sonxeber: 45 new / 45 found
Metbuat: 38 new / 38 found
```

### Step 6: Verify Database

After the workflow completes, check your database:

```sql
-- Connect to your database
SET search_path TO news, public;

-- Check articles
SELECT * FROM article_stats;

-- Check recent scraping jobs
SELECT
    ns.name,
    sj.started_at,
    sj.articles_new,
    sj.status
FROM scrape_jobs sj
JOIN news_sources ns ON sj.source_id = ns.id
ORDER BY sj.started_at DESC
LIMIT 10;
```

## Workflow Configuration

### Scrape News Articles (`scrape-news.yml`)

**Triggers:**
- Scheduled: 09:00, 13:00, 18:00 UTC daily
- Manual: Via "Run workflow" button

**Parameters (manual runs only):**
- `max_pages`: Number of pages per source (default: 3)
- `scrape_details`: Scrape full article content (default: false)

**What it does:**
1. Scrapes 3 pages from each news source
2. Saves articles to database
3. Displays statistics
4. Uploads logs as artifacts

### Generate AI Summaries (`summarize-news.yml`)

**Triggers:**
- Scheduled: 09:30, 13:30, 18:30 UTC daily (30 min after scraping)
- Manual: Via "Run workflow" button

**Parameters:**
- `batch_size`: Number of articles to summarize (default: 100)

**Status:** Placeholder (will be implemented in Phase 3)

## Customizing the Schedule

To change when the scraper runs, edit `.github/workflows/scrape-news.yml`:

```yaml
schedule:
  - cron: '0 6 * * *'   # 06:00 UTC
  - cron: '0 12 * * *'  # 12:00 UTC
  - cron: '0 20 * * *'  # 20:00 UTC
```

**Cron syntax:**
```
 ┌───────────── minute (0 - 59)
 │ ┌───────────── hour (0 - 23)
 │ │ ┌───────────── day of month (1 - 31)
 │ │ │ ┌───────────── month (1 - 12)
 │ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
 │ │ │ │ │
 * * * * *
```

**Examples:**
- `0 * * * *` - Every hour at minute 0
- `0 */6 * * *` - Every 6 hours
- `0 9,18 * * *` - At 09:00 and 18:00 only
- `0 9 * * 1-5` - At 09:00 on weekdays only

## Adjusting Scraping Settings

### Change Number of Pages

Edit the workflow file to change default pages:

```yaml
--pages ${{ github.event.inputs.max_pages || '5' }}  # Change 3 to 5
```

Or pass it when running manually.

### Enable Full Article Scraping

To scrape full article content by default:

```yaml
--pages 3 \
--details \  # Add this line
--triggered-by github_action
```

**Warning**: This makes scraping slower and may trigger rate limits.

## Monitoring and Logs

### View Logs

1. Go to **Actions** tab
2. Click on a workflow run
3. Click on the **scrape** job
4. Expand steps to see logs

### Download Log Artifacts

1. Scroll to bottom of workflow run page
2. Find **Artifacts** section
3. Download `scraper-logs-{run_number}.zip`
4. Extract and view detailed logs

### Set Up Notifications

To receive notifications on failure:

1. Go to your GitHub profile
2. **Settings** → **Notifications**
3. Enable **Actions** notifications

Or add email notifications in the workflow:

```yaml
- name: Send failure notification
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: News Scraper Failed
    body: Check logs at ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
    to: your-email@example.com
    from: GitHub Actions
```

## Troubleshooting

### Workflow Not Running

**Problem**: Workflow doesn't run at scheduled time

**Solutions**:
1. Check if Actions are enabled (Settings → Actions)
2. Scheduled workflows only run on the default branch (usually `main`)
3. GitHub may delay scheduled runs by up to 15 minutes during high load
4. Push a commit to trigger workflow validation

### Database Connection Failed

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
1. Verify `DATABASE_URL` secret is correct
2. Check database allows connections from GitHub IPs
3. Test connection string locally first
4. Ensure database is running

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'scraper_job'`

**Solutions**:
1. Verify `requirements.txt` is correct
2. Check Python version matches (3.11)
3. Clear pip cache and reinstall

### Rate Limiting

**Problem**: Too many requests, getting 429 errors

**Solutions**:
1. Reduce number of pages: `--pages 2`
2. Increase delays in `config.py`
3. Don't scrape details on every run
4. Spread out scheduled runs more

## Cost Considerations

### GitHub Actions

- **Free tier**: 2,000 minutes/month for public repos
- **Free tier**: 500 minutes/month for private repos
- This workflow uses ~5 minutes per run
- 3 runs/day × 30 days = 90 runs/month = ~450 minutes/month

**Conclusion**: Well within free tier limits!

### Database

- **Neon Free Tier**: 0.5 GB storage, 100 hours compute/month
- Each article ~1-5 KB
- 100 articles/day × 30 days = 3,000 articles ≈ 15 MB/month

**Conclusion**: Plenty of space on free tier!

### Gemini API

- **Free tier**: 60 requests/minute, 1,500 requests/day
- Summarizing 100 articles = 100 requests
- 3 runs/day × 100 articles = 300 requests/day

**Conclusion**: Within free tier limits!

## Security Best Practices

1. ✅ **Never commit secrets** - Use GitHub Secrets
2. ✅ **Use environment variables** - Don't hardcode credentials
3. ✅ **Limit secret access** - Only give secrets to workflows that need them
4. ✅ **Rotate secrets regularly** - Change database passwords periodically
5. ✅ **Monitor usage** - Check Actions tab for unusual activity
6. ✅ **Enable 2FA** - Protect your GitHub account

## Next Steps

After setting up GitHub Actions:

1. ✅ Monitor first few runs
2. ✅ Verify data in database
3. ⏳ Implement AI summarization
4. ⏳ Build frontend to display articles
5. ⏳ Deploy frontend to Vercel
6. ⏳ Add more scrapers

## Support

If you encounter issues:

1. Check workflow logs
2. Review this setup guide
3. Test scraper locally first
4. Create a GitHub issue with error details
