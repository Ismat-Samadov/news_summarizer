-- Migration: replace uuid_generate_v4() with gen_random_uuid()
-- gen_random_uuid() is built into PostgreSQL 13+ and needs no extension.
-- Run this once against the production database.

SET search_path TO news, public;

ALTER TABLE articles      ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE scrape_jobs   ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE scrape_errors ALTER COLUMN id SET DEFAULT gen_random_uuid();
