-- Analysis Queries for News Summarizer Database
-- Use these queries to analyze scraped data, monitor performance, and generate insights

-- Set search path to use news schema
SET search_path TO news, public;

-- ============================================
-- ARTICLE ANALYTICS
-- ============================================

-- 1. Get total articles by source
SELECT
    ns.name as source,
    COUNT(a.id) as total_articles,
    COUNT(CASE WHEN a.is_processed THEN 1 END) as processed,
    COUNT(CASE WHEN a.is_summarized THEN 1 END) as summarized,
    ROUND(COUNT(CASE WHEN a.is_summarized THEN 1 END)::DECIMAL / NULLIF(COUNT(a.id), 0) * 100, 2) as summarization_rate
FROM news_sources ns
LEFT JOIN articles a ON ns.id = a.source_id
GROUP BY ns.id, ns.name
ORDER BY total_articles DESC;

-- 2. Articles scraped in the last 24 hours
SELECT
    ns.name as source,
    COUNT(a.id) as articles_last_24h,
    MIN(a.published_at) as oldest_article,
    MAX(a.published_at) as newest_article
FROM articles a
JOIN news_sources ns ON a.source_id = ns.id
WHERE a.scraped_at >= NOW() - INTERVAL '24 hours'
GROUP BY ns.name
ORDER BY articles_last_24h DESC;

-- 3. Most popular categories
SELECT
    c.name as category,
    ns.name as source,
    COUNT(a.id) as article_count,
    AVG(a.view_count) as avg_views
FROM categories c
JOIN articles a ON c.id = a.category_id
JOIN news_sources ns ON c.source_id = ns.id
GROUP BY c.name, ns.name
ORDER BY article_count DESC
LIMIT 20;

-- 4. Articles without summaries (need processing)
SELECT
    ns.name as source,
    a.title,
    a.url,
    a.published_at,
    a.scraped_at
FROM articles a
JOIN news_sources ns ON a.source_id = ns.id
WHERE a.is_summarized = FALSE
ORDER BY a.published_at DESC
LIMIT 100;

-- 5. Duplicate detection - articles with same content hash
SELECT
    content_hash,
    COUNT(*) as duplicate_count,
    STRING_AGG(DISTINCT ns.name, ', ') as sources,
    MIN(a.title) as sample_title
FROM articles a
JOIN news_sources ns ON a.source_id = ns.id
WHERE content_hash IS NOT NULL
GROUP BY content_hash
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- 6. Daily article volume trend (last 30 days)
SELECT
    DATE(published_at) as publish_date,
    COUNT(*) as articles_published,
    COUNT(DISTINCT source_id) as active_sources
FROM articles
WHERE published_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(published_at)
ORDER BY publish_date DESC;

-- 7. Articles by hour of day (find peak publishing times)
SELECT
    EXTRACT(HOUR FROM published_at) as hour_of_day,
    COUNT(*) as article_count,
    ROUND(AVG(view_count), 0) as avg_views
FROM articles
WHERE published_at IS NOT NULL
GROUP BY hour_of_day
ORDER BY hour_of_day;

-- ============================================
-- SCRAPING JOB ANALYTICS
-- ============================================

-- 8. Recent scraping job performance
SELECT
    ns.name as source,
    sj.status,
    sj.started_at,
    sj.duration_seconds,
    sj.articles_found,
    sj.articles_new,
    sj.articles_failed,
    ROUND((sj.articles_new::DECIMAL / NULLIF(sj.articles_found, 0)) * 100, 2) as new_article_rate
FROM scrape_jobs sj
JOIN news_sources ns ON sj.source_id = ns.id
ORDER BY sj.started_at DESC
LIMIT 50;

-- 9. Scraping success rate by source
SELECT
    ns.name as source,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN sj.status = 'completed' THEN 1 END) as successful,
    COUNT(CASE WHEN sj.status = 'failed' THEN 1 END) as failed,
    ROUND(COUNT(CASE WHEN sj.status = 'completed' THEN 1 END)::DECIMAL / COUNT(*) * 100, 2) as success_rate,
    ROUND(AVG(sj.duration_seconds), 2) as avg_duration_sec,
    SUM(sj.articles_new) as total_new_articles
FROM scrape_jobs sj
JOIN news_sources ns ON sj.source_id = ns.id
GROUP BY ns.name
ORDER BY success_rate DESC;

-- 10. Most common scraping errors
SELECT
    ns.name as source,
    se.error_type,
    COUNT(*) as error_count,
    STRING_AGG(DISTINCT se.error_message, ' | ') as sample_errors
FROM scrape_errors se
JOIN news_sources ns ON se.source_id = ns.id
WHERE se.created_at >= NOW() - INTERVAL '7 days'
GROUP BY ns.name, se.error_type
ORDER BY error_count DESC
LIMIT 20;

-- 11. Failed URLs that need retry
SELECT
    se.url,
    ns.name as source,
    se.error_type,
    se.retry_count,
    se.last_retry_at,
    se.created_at
FROM scrape_errors se
JOIN news_sources ns ON se.source_id = ns.id
WHERE se.retry_count < 3
ORDER BY se.created_at DESC
LIMIT 100;

-- ============================================
-- SUMMARY ANALYTICS
-- ============================================

-- 12. Summary quality metrics
SELECT
    ns.name as source,
    COUNT(s.id) as summaries_generated,
    ROUND(AVG(s.confidence_score), 2) as avg_confidence,
    COUNT(CASE WHEN s.confidence_score >= 0.8 THEN 1 END) as high_quality_summaries,
    s.model_used,
    MIN(s.created_at) as first_summary,
    MAX(s.created_at) as latest_summary
FROM summaries s
JOIN articles a ON s.article_id = a.id
JOIN news_sources ns ON a.source_id = ns.id
GROUP BY ns.name, s.model_used
ORDER BY summaries_generated DESC;

-- 13. Sentiment distribution
SELECT
    ns.name as source,
    s.sentiment,
    COUNT(*) as count,
    ROUND(COUNT(*)::DECIMAL / SUM(COUNT(*)) OVER (PARTITION BY ns.name) * 100, 2) as percentage
FROM summaries s
JOIN articles a ON s.article_id = a.id
JOIN news_sources ns ON a.source_id = ns.id
WHERE s.sentiment IS NOT NULL
GROUP BY ns.name, s.sentiment
ORDER BY ns.name, count DESC;

-- 14. Most common topics/entities
SELECT
    jsonb_array_elements_text(s.topics) as topic,
    COUNT(*) as frequency,
    STRING_AGG(DISTINCT ns.name, ', ') as sources
FROM summaries s
JOIN articles a ON s.article_id = a.id
JOIN news_sources ns ON a.source_id = ns.id
WHERE s.topics IS NOT NULL
GROUP BY topic
ORDER BY frequency DESC
LIMIT 30;

-- 15. Articles needing summary regeneration (low confidence)
SELECT
    a.title,
    ns.name as source,
    s.confidence_score,
    s.model_used,
    a.url,
    s.created_at
FROM summaries s
JOIN articles a ON s.article_id = a.id
JOIN news_sources ns ON a.source_id = ns.id
WHERE s.confidence_score < 0.6
ORDER BY s.confidence_score ASC
LIMIT 50;

-- ============================================
-- DATA QUALITY CHECKS
-- ============================================

-- 16. Articles missing critical fields
SELECT
    'Missing Title' as issue,
    COUNT(*) as count
FROM articles WHERE title IS NULL OR title = ''
UNION ALL
SELECT
    'Missing URL' as issue,
    COUNT(*) as count
FROM articles WHERE url IS NULL OR url = ''
UNION ALL
SELECT
    'Missing Published Date' as issue,
    COUNT(*) as count
FROM articles WHERE published_at IS NULL
UNION ALL
SELECT
    'Missing Category' as issue,
    COUNT(*) as count
FROM articles WHERE category_id IS NULL
UNION ALL
SELECT
    'Missing Image' as issue,
    COUNT(*) as count
FROM articles WHERE image_url IS NULL;

-- 17. Sources not scraped recently (potential issues)
SELECT
    ns.name as source,
    MAX(a.scraped_at) as last_scrape,
    NOW() - MAX(a.scraped_at) as time_since_last_scrape,
    ns.is_active
FROM news_sources ns
LEFT JOIN articles a ON ns.id = a.source_id
GROUP BY ns.id, ns.name, ns.is_active
HAVING MAX(a.scraped_at) < NOW() - INTERVAL '2 days' OR MAX(a.scraped_at) IS NULL
ORDER BY last_scrape DESC NULLS LAST;

-- 18. Database storage usage
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'news'
ORDER BY size_bytes DESC;

-- ============================================
-- EXPORT QUERIES FOR DASHBOARDS
-- ============================================

-- 19. Daily summary for dashboard
SELECT
    CURRENT_DATE as report_date,
    COUNT(DISTINCT a.id) as total_articles,
    COUNT(DISTINCT CASE WHEN a.scraped_at >= CURRENT_DATE THEN a.id END) as articles_today,
    COUNT(DISTINCT CASE WHEN a.is_summarized THEN a.id END) as total_summarized,
    COUNT(DISTINCT s.id) FILTER (WHERE s.created_at >= CURRENT_DATE) as summaries_today,
    COUNT(DISTINCT sj.id) FILTER (WHERE sj.started_at >= CURRENT_DATE) as jobs_today,
    COUNT(DISTINCT sj.id) FILTER (WHERE sj.started_at >= CURRENT_DATE AND sj.status = 'failed') as failed_jobs_today
FROM articles a
LEFT JOIN summaries s ON a.id = s.article_id
LEFT JOIN scrape_jobs sj ON TRUE;

-- 20. Source health check
SELECT
    ns.name,
    ns.is_active,
    COUNT(DISTINCT a.id) as total_articles,
    MAX(a.scraped_at) as last_successful_scrape,
    COUNT(DISTINCT sj.id) FILTER (WHERE sj.started_at >= NOW() - INTERVAL '7 days') as jobs_last_week,
    COUNT(DISTINCT sj.id) FILTER (WHERE sj.started_at >= NOW() - INTERVAL '7 days' AND sj.status = 'failed') as failures_last_week,
    CASE
        WHEN MAX(a.scraped_at) < NOW() - INTERVAL '24 hours' THEN 'WARNING'
        WHEN MAX(a.scraped_at) < NOW() - INTERVAL '48 hours' THEN 'CRITICAL'
        ELSE 'OK'
    END as health_status
FROM news_sources ns
LEFT JOIN articles a ON ns.id = a.source_id
LEFT JOIN scrape_jobs sj ON ns.id = sj.source_id
GROUP BY ns.id, ns.name, ns.is_active
ORDER BY health_status DESC, ns.name;
