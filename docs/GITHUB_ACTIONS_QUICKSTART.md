# GitHub Actions Quick Start

**5-minute setup guide for automated news scraping**

## Step 1: Add Secrets (2 minutes)

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 2 secrets:

### Secret 1: DATABASE_URL
```
Name: DATABASE_URL
Value: postgresql://user:password@host.region.provider.tech/database?sslmode=require
```

**Get from**: Your PostgreSQL provider (Neon, Supabase, etc.)

### Secret 2: GEMINI_API_KEY
```
Name: GEMINI_API_KEY
Value: your_gemini_api_key_here
```

**Get from**: https://makersuite.google.com/app/apikey

**⚠️ CRITICAL**: These are placeholders - use YOUR actual credentials!

## Step 2: Enable Actions (30 seconds)

1. Go to **Actions** tab in your repository
2. If disabled, click **"I understand my workflows, go ahead and enable them"**
3. You should see: **Scrape News Articles** workflow

## Step 3: Test Manual Run (1 minute)

1. Click on **Scrape News Articles** workflow
2. Click **Run workflow** button (top right)
3. Leave defaults:
   - Max pages: `3`
   - Scrape details: `false`
4. Click green **Run workflow** button
5. Refresh page to see the running job

## Step 4: Monitor First Run (2 minutes)

1. Click on the running workflow (yellow dot)
2. Click on **scrape** job
3. Watch the steps execute
4. Wait for completion (green checkmark)

**Expected result:**
```
✅ Scraping completed
   Pages scraped: 3
   Articles found: ~120-150
   New articles: ~120-150
   Failed: 0
```

## Step 5: Verify Database (30 seconds)

Check that articles were saved:

```bash
python -m scraper_job.run_scraper stats
```

You should see articles from **Sonxeber** and **Metbuat**.

## That's It! ✅

Your scraper is now running automatically **3 times daily**:
- **09:00 UTC** (12:00 Baku)
- **13:00 UTC** (16:00 Baku)
- **18:00 UTC** (21:00 Baku)

---

## What Happens Now?

### Automatic Scraping
Every day at scheduled times:
1. GitHub Actions spins up a fresh Ubuntu server
2. Installs Python and dependencies
3. Runs scrapers for all news sources (3 pages each)
4. Saves articles to your PostgreSQL database
5. Uploads logs for 7 days
6. Shuts down the server

### Cost
**$0.00** - Completely free on GitHub's free tier!
- 2,000 minutes/month for public repos
- Each run uses ~5 minutes
- 3 runs/day × 30 days = 450 minutes/month

---

## Common Issues

### "Secrets not found"
→ Double-check secret names are exactly: `DATABASE_URL` and `GEMINI_API_KEY`

### "Database connection failed"
→ Verify your database allows connections from any IP (or GitHub IPs)

### "Workflow not running"
→ Make sure you pushed to the `main` branch (scheduled workflows only run on default branch)

### "No articles scraped"
→ Check the website structure hasn't changed, review logs in Actions

---

## Next Steps

### Add More Scrapers
Implement additional news sources:
- Azertag.az
- APA.az
- Report.az

See: [Development Guide](README.md#development)

### Implement AI Summarization
Generate article summaries with Gemini API (coming in Phase 3)

### Build Frontend
Create a Next.js app to display articles and summaries

### Deploy to Vercel
Host the frontend for free on Vercel

---

## Advanced Configuration

### Change Schedule

Edit `.github/workflows/scrape-news.yml`:

```yaml
schedule:
  - cron: '0 6 * * *'   # 06:00 UTC
  - cron: '0 12 * * *'  # 12:00 UTC
  - cron: '0 20 * * *'  # 20:00 UTC
```

### Scrape More Pages

Change default in workflow file:

```yaml
--pages ${{ github.event.inputs.max_pages || '5' }}  # Change to 5
```

### Enable Full Content Scraping

Add `--details` flag in workflow:

```yaml
python -m scraper_job.run_scraper run-all \
  --pages 3 \
  --details \
  --triggered-by github_action
```

---

## Monitoring

### View Logs
**Actions** tab → Click on workflow run → Click **scrape** job → Expand steps

### Download Logs
Scroll to bottom of workflow run → **Artifacts** → Download `scraper-logs-XXX.zip`

### Email Notifications
GitHub **Settings** → **Notifications** → Enable **Actions** notifications

---

## Full Documentation

For detailed information, see:
- [GitHub Actions Setup Guide](.github/SETUP.md) - Complete setup instructions
- [README.md](README.md) - Full project documentation
- [SCRAPER_STATUS.md](SCRAPER_STATUS.md) - Implementation status

---

**Ready to go!** Your news scraper is now running on autopilot. 🚀
