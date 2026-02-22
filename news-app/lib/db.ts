import { Pool } from 'pg';

if (!process.env.DATABASE_URL) {
  throw new Error('DATABASE_URL environment variable is not set');
}

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false
  },
  max: 20, // Maximum number of clients in the pool
  idleTimeoutMillis: 30000, // Close idle clients after 30 seconds
  connectionTimeoutMillis: 2000, // Timeout after 2 seconds
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

export async function getArticles(limit: number = 20, offset: number = 0, sourceId?: number): Promise<Article[]> {
  let client;
  try {
    client = await pool.connect();
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
  } catch (error) {
    console.error('Error fetching articles:', error);
    throw error; // Re-throw to let Next.js handle it
  } finally {
    if (client) client.release();
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

export async function getNewsSources(): Promise<NewsSource[]> {
  let client;
  try {
    client = await pool.connect();
    const query = `
      SELECT DISTINCT ns.*
      FROM news.news_sources ns
      INNER JOIN news.articles a ON ns.id = a.source_id
      WHERE ns.is_active = TRUE
      ORDER BY ns.name
    `;
    const result = await client.query<NewsSource>(query);
    return result.rows;
  } catch (error) {
    console.error('Error fetching news sources:', error);
    throw error;
  } finally {
    if (client) client.release();
  }
}

export async function isValidSourceId(sourceId: number): Promise<boolean> {
  try {
    const client = await pool.connect();
    try {
      const query = `
        SELECT EXISTS(
          SELECT 1 FROM news.news_sources
          WHERE id = $1 AND is_active = TRUE
        ) as exists
      `;
      const result = await client.query(query, [sourceId]);
      return result.rows[0]?.exists || false;
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Error validating source ID:', error);
    // If validation fails, assume invalid to be safe
    return false;
  }
}

export async function getArticleCount(sourceId?: number): Promise<number> {
  let client;
  try {
    client = await pool.connect();
    let query = `SELECT COUNT(*) as count FROM news.articles`;
    const params: any[] = [];

    if (sourceId) {
      query += ` WHERE source_id = $1`;
      params.push(sourceId);
    }

    const result = await client.query(query, params);
    return parseInt(result.rows[0].count);
  } catch (error) {
    console.error('Error counting articles:', error);
    throw error;
  } finally {
    if (client) client.release();
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
