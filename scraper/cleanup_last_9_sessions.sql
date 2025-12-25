-- Cleanup script to delete the last 9 scraping sessions
-- Run this in your PostgreSQL client or through psql

-- First, let's see what we're about to delete
SELECT
    id,
    created_at,
    new_articles_count,
    LEFT(summary, 80) as summary_preview
FROM news.scraping_summaries
ORDER BY id DESC
LIMIT 9;

-- If you're satisfied with the above list, uncomment and run the following:

-- Step 1: Delete articles from these sessions
-- DELETE FROM news.articles
-- WHERE scraping_session_id IN (
--     SELECT id
--     FROM news.scraping_summaries
--     ORDER BY id DESC
--     LIMIT 9
-- );

-- Step 2: Delete the scraping summaries
-- DELETE FROM news.scraping_summaries
-- WHERE id IN (
--     SELECT id
--     FROM news.scraping_summaries
--     ORDER BY id DESC
--     LIMIT 9
-- );

-- Verify cleanup
-- SELECT COUNT(*) as remaining_sessions FROM news.scraping_summaries;
-- SELECT COUNT(*) as remaining_articles FROM news.articles;
