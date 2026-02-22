-- News Summarizer Database Schema
-- PostgreSQL database for storing scraped news articles and AI summaries

-- Create dedicated schema for this project
CREATE SCHEMA IF NOT EXISTS news;

-- Set search path to use news schema
SET search_path TO news, public;

-- Enable UUID extension for unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA public;

-- Table: news_sources
-- Stores information about each news website being scraped
CREATE TABLE news_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    domain VARCHAR(255) NOT NULL UNIQUE,
    base_url VARCHAR(500) NOT NULL,
    language VARCHAR(10) DEFAULT 'az',
    is_active BOOLEAN DEFAULT TRUE,
    supports_pagination BOOLEAN DEFAULT TRUE,
    pagination_type VARCHAR(50), -- 'query_param', 'infinite_scroll', 'path_based'
    scraper_config JSONB, -- Store source-specific scraping configuration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: categories
-- News categories across all sources
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(255) NOT NULL, -- Increased from 100 for long category slugs
    source_id INTEGER REFERENCES news_sources(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(slug, source_id)
);

-- Table: articles
-- Main table for storing scraped news articles
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id INTEGER NOT NULL REFERENCES news_sources(id) ON DELETE CASCADE,
    source_article_id VARCHAR(255), -- Original article ID from the source website (increased from 100 for long slugs)
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    slug TEXT,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,

    -- Content fields
    content TEXT, -- Full article content if scraped
    excerpt TEXT, -- Short excerpt/description

    -- Media
    image_url TEXT,
    image_local_path TEXT, -- Path to locally stored image

    -- Metadata
    author VARCHAR(255),
    published_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Engagement metrics (if available)
    view_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,

    -- Article status
    is_processed BOOLEAN DEFAULT FALSE, -- Whether article content has been fully scraped
    is_summarized BOOLEAN DEFAULT FALSE, -- Whether AI summary has been generated

    -- Deduplication
    content_hash VARCHAR(64), -- SHA-256 hash of content for deduplication

    -- Additional metadata from source
    metadata JSONB, -- Store any source-specific metadata

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    CONSTRAINT unique_source_article UNIQUE(source_id, source_article_id)
);

-- Table: summaries
-- AI-generated summaries of articles
CREATE TABLE summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,

    -- Summary content
    summary_short TEXT, -- 1-2 sentence summary
    summary_medium TEXT, -- 1 paragraph summary
    summary_long TEXT, -- Multi-paragraph detailed summary

    -- Key information extraction
    key_points JSONB, -- Array of key points/bullet points
    entities JSONB, -- Named entities (people, places, organizations)
    topics JSONB, -- Main topics/tags
    sentiment VARCHAR(50), -- 'positive', 'negative', 'neutral'

    -- AI model information
    model_used VARCHAR(100), -- e.g., 'gemini-pro', 'gpt-4'
    model_version VARCHAR(50),

    -- Quality metrics
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure one summary per article
    UNIQUE(article_id)
);

-- Table: scrape_jobs
-- Track scraping job execution and status
CREATE TABLE scrape_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id INTEGER REFERENCES news_sources(id) ON DELETE CASCADE,

    -- Job details
    job_type VARCHAR(50) NOT NULL, -- 'full_scrape', 'incremental', 'detail_scrape'
    status VARCHAR(50) NOT NULL, -- 'running', 'completed', 'failed', 'partial'

    -- Execution info
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Results
    articles_found INTEGER DEFAULT 0,
    articles_new INTEGER DEFAULT 0,
    articles_updated INTEGER DEFAULT 0,
    articles_failed INTEGER DEFAULT 0,

    -- Error tracking
    error_message TEXT,
    error_details JSONB,

    -- Metadata
    triggered_by VARCHAR(50), -- 'github_action', 'manual', 'scheduled'
    metadata JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: scrape_errors
-- Detailed error logging for individual article scraping failures
CREATE TABLE scrape_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES scrape_jobs(id) ON DELETE CASCADE,
    source_id INTEGER REFERENCES news_sources(id) ON DELETE CASCADE,

    -- Error details
    url TEXT,
    error_type VARCHAR(100), -- 'network_error', 'parse_error', 'validation_error'
    error_message TEXT,
    stack_trace TEXT,

    -- Context
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_articles_source_id ON articles(source_id);
CREATE INDEX idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX idx_articles_scraped_at ON articles(scraped_at DESC);
CREATE INDEX idx_articles_is_processed ON articles(is_processed);
CREATE INDEX idx_articles_is_summarized ON articles(is_summarized);
CREATE INDEX idx_articles_content_hash ON articles(content_hash);
CREATE INDEX idx_articles_category_id ON articles(category_id);

CREATE INDEX idx_summaries_article_id ON summaries(article_id);
CREATE INDEX idx_summaries_created_at ON summaries(created_at DESC);

CREATE INDEX idx_scrape_jobs_source_id ON scrape_jobs(source_id);
CREATE INDEX idx_scrape_jobs_status ON scrape_jobs(status);
CREATE INDEX idx_scrape_jobs_started_at ON scrape_jobs(started_at DESC);

CREATE INDEX idx_categories_source_id ON categories(source_id);
CREATE INDEX idx_categories_slug ON categories(slug);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_news_sources_updated_at BEFORE UPDATE ON news_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_summaries_updated_at BEFORE UPDATE ON summaries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial news sources based on GitHub issues
INSERT INTO news_sources (name, domain, base_url, language, pagination_type, scraper_config) VALUES
('Sonxeber', 'sonxeber.az', 'https://sonxeber.az', 'az', 'query_param', '{"pagination_param": "start", "pagination_increment": 1}'),
('Metbuat', 'metbuat.az', 'https://metbuat.az', 'az', 'query_param', '{"pagination_param": "page", "per_page": 39}'),
('Axar', 'axar.az', 'https://axar.az', 'az', 'infinite_scroll', '{"use_infinite_scroll": true}'),
('Milli', 'news.milli.az', 'https://news.milli.az', 'az', 'infinite_scroll', '{"ajax_endpoint": "/latest.php"}'),
('Azertag', 'azertag.az', 'https://azertag.az', 'az', 'query_param', '{"pagination_param": "page", "multilingual": true}'),
('APA', 'apa.az', 'https://apa.az', 'az', 'query_param', '{"pagination_param": "page", "multilingual": true}'),
('Oxu', 'oxu.az', 'https://oxu.az', 'az', 'query_param', '{"anti_scraping": true, "requires_headers": true}'),
('Report', 'report.az', 'https://report.az', 'az', 'query_param', '{"pagination_param": "page", "multilingual": true}'),
('Xezer Xeber', 'xezerxeber.az', 'https://www.xezerxeber.az', 'az', 'infinite_scroll', '{"use_infinite_scroll": true}'),
('Modern', 'modern.az', 'https://modern.az', 'az', 'query_param', '{"pagination_param": "page", "multilingual": true, "languages": ["az", "en", "ru", "tr", "fa"]}');

-- Create view for article statistics
CREATE OR REPLACE VIEW article_stats AS
SELECT
    ns.name as source_name,
    COUNT(a.id) as total_articles,
    COUNT(CASE WHEN a.is_processed THEN 1 END) as processed_articles,
    MAX(a.published_at) as latest_article_date,
    MAX(a.scraped_at) as last_scrape_time
FROM news_sources ns
LEFT JOIN articles a ON ns.id = a.source_id
GROUP BY ns.id, ns.name;

-- Create view for scraping job statistics
CREATE OR REPLACE VIEW scrape_job_stats AS
SELECT
    ns.name as source_name,
    COUNT(sj.id) as total_jobs,
    COUNT(CASE WHEN sj.status = 'completed' THEN 1 END) as completed_jobs,
    COUNT(CASE WHEN sj.status = 'failed' THEN 1 END) as failed_jobs,
    AVG(sj.duration_seconds) as avg_duration_seconds,
    MAX(sj.started_at) as last_job_time
FROM news_sources ns
LEFT JOIN scrape_jobs sj ON ns.id = sj.source_id
GROUP BY ns.id, ns.name;
