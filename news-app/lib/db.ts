import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false
  }
});

export interface Article {
  id: string;
  source_id: number;
  source_name?: string;
  title: string;
  url: string;
  excerpt: string | null;
  image_url: string | null;
  author: string | null;
  published_at: Date | null;
  scraped_at: Date;
  view_count: number;
}

export interface NewsSource {
  id: number;
  name: string;
  domain: string;
  base_url: string;
  language: string;
  is_active: boolean;
}

export async function getArticles(limit: number = 20, offset: number = 0, sourceId?: number) {
  const client = await pool.connect();
  try {
    let query = `
      SELECT
        a.id, a.source_id, a.title, a.url, a.excerpt,
        a.image_url, a.author, a.published_at, a.scraped_at, a.view_count,
        ns.name as source_name
      FROM news.articles a
      LEFT JOIN news.news_sources ns ON a.source_id = ns.id
    `;

    const params: any[] = [];
    if (sourceId) {
      query += ` WHERE a.source_id = $1`;
      params.push(sourceId);
      query += ` ORDER BY a.published_at DESC NULLS LAST, a.scraped_at DESC LIMIT $2 OFFSET $3`;
      params.push(limit, offset);
    } else {
      query += ` ORDER BY a.published_at DESC NULLS LAST, a.scraped_at DESC LIMIT $1 OFFSET $2`;
      params.push(limit, offset);
    }

    const result = await client.query<Article>(query, params);
    return result.rows;
  } finally {
    client.release();
  }
}

export async function getArticleById(id: string) {
  const client = await pool.connect();
  try {
    const query = `
      SELECT
        a.*, ns.name as source_name, ns.domain as source_domain
      FROM news.articles a
      LEFT JOIN news.news_sources ns ON a.source_id = ns.id
      WHERE a.id = $1
    `;
    const result = await client.query(query, [id]);
    return result.rows[0] || null;
  } finally {
    client.release();
  }
}

export async function getNewsSources() {
  const client = await pool.connect();
  try {
    const query = `
      SELECT * FROM news.news_sources
      WHERE is_active = TRUE
      ORDER BY name
    `;
    const result = await client.query<NewsSource>(query);
    return result.rows;
  } finally {
    client.release();
  }
}

export async function isValidSourceId(sourceId: number) {
  const client = await pool.connect();
  try {
    const query = `
      SELECT EXISTS(
        SELECT 1 FROM news.news_sources
        WHERE id = $1 AND is_active = TRUE
      ) as exists
    `;
    const result = await client.query(query, [sourceId]);
    return result.rows[0].exists;
  } finally {
    client.release();
  }
}

export async function getArticleCount(sourceId?: number) {
  const client = await pool.connect();
  try {
    let query = `SELECT COUNT(*) as count FROM news.articles`;
    const params: any[] = [];

    if (sourceId) {
      query += ` WHERE source_id = $1`;
      params.push(sourceId);
    }

    const result = await client.query(query, params);
    return parseInt(result.rows[0].count);
  } finally {
    client.release();
  }
}

export async function searchArticles(searchTerm: string, limit: number = 20, offset: number = 0, sourceId?: number) {
  const client = await pool.connect();
  try {
    let query = `
      SELECT
        a.id, a.source_id, a.title, a.url, a.excerpt,
        a.image_url, a.author, a.published_at, a.scraped_at, a.view_count,
        ns.name as source_name
      FROM news.articles a
      LEFT JOIN news.news_sources ns ON a.source_id = ns.id
      WHERE (a.title ILIKE $1 OR a.excerpt ILIKE $1 OR a.content ILIKE $1)
    `;

    const params: any[] = [`%${searchTerm}%`];

    if (sourceId) {
      query += ` AND a.source_id = $${params.length + 1}`;
      params.push(sourceId);
    }

    query += ` ORDER BY a.published_at DESC NULLS LAST, a.scraped_at DESC LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    params.push(limit, offset);

    const result = await client.query<Article>(query, params);
    return result.rows;
  } finally {
    client.release();
  }
}

export async function getSearchCount(searchTerm: string, sourceId?: number) {
  const client = await pool.connect();
  try {
    let query = `
      SELECT COUNT(*) as count
      FROM news.articles
      WHERE (title ILIKE $1 OR excerpt ILIKE $1 OR content ILIKE $1)
    `;

    const params: any[] = [`%${searchTerm}%`];

    if (sourceId) {
      query += ` AND source_id = $${params.length + 1}`;
      params.push(sourceId);
    }

    const result = await client.query(query, params);
    return parseInt(result.rows[0].count);
  } finally {
    client.release();
  }
}
