-- Migration: Add new news sources
-- Run this against the existing database to register new scrapers.
-- Safe to run multiple times (uses ON CONFLICT DO NOTHING).

SET search_path TO news, public;

INSERT INTO news_sources (name, domain, base_url, language, is_active, pagination_type, scraper_config)
VALUES
  ('Banker.az',        'banker.az',        'https://banker.az',        'az', TRUE, 'path_based',  '{"pagination_param": "page"}'),
  ('Fed.az',           'fed.az',           'https://fed.az',           'az', TRUE, 'path_based',  '{}'),
  ('Marja.az',         'marja.az',         'https://marja.az',         'az', TRUE, 'query_param', '{"pagination_param": "page"}'),
  ('Qafqazinfo.az',    'qafqazinfo.az',    'https://qafqazinfo.az',    'az', TRUE, 'query_param', '{"pagination_param": "page"}'),
  ('Trend.az',         'trend.az',         'https://az.trend.az',      'az', TRUE, 'query_param', '{"single_page": true}')
ON CONFLICT (domain) DO NOTHING;
