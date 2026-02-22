# Azerbaijan News Aggregator - Frontend

Beautiful, responsive Next.js TypeScript app for displaying aggregated news from Azerbaijan's top news sources.

## Features

- ✨ Modern, attractive UI with Tailwind CSS
- 📱 Fully responsive (mobile, tablet, desktop)
- ⚡ Server-side rendering with Next.js 14
- 🎯 TypeScript for type safety
- 📰 Real-time news from 5 active sources
- 🔄 Auto-revalidation every 5 minutes

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Database**: PostgreSQL (Neon)
- **Hosting**: Vercel

## Local Development

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables in `.env.local`:
```env
DATABASE_URL=your_postgresql_connection_string
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000)

## Deploy to Vercel

### One-Click Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/news-app)

### Manual Deployment

1. Push code to GitHub repository

2. Import project to Vercel:
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository

3. Configure environment variables:
   - Add `DATABASE_URL` in Vercel project settings

4. Deploy!

## Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string

## Database Schema

The app expects a PostgreSQL database with the `news` schema containing:
- `news.articles` - News articles
- `news.news_sources` - News source configurations

See `../scraper_job/scripts/schema.sql` for full schema.

## Features

### Homepage
- Latest 24 articles from all sources
- Source filter badges
- Live statistics (total articles, active sources)
- Responsive grid layout

### Article Detail Page
- Full article view
- Source attribution
- Published date
- Link to original article
- Mobile-optimized reading experience

### Performance
- Server-side rendering for SEO
- Image optimization with Next.js Image
- Automatic revalidation (5 min cache)
- Fast page loads

## Project Structure

```
news-app/
├── app/                    # Next.js 14 app directory
│   ├── layout.tsx         # Root layout with header/footer
│   ├── page.tsx           # Homepage
│   ├── article/[id]/      # Article detail pages
│   └── globals.css        # Global styles
├── components/            # React components
│   └── ArticleCard.tsx   # Article card component
├── lib/                   # Utilities
│   └── db.ts             # Database functions
└── public/               # Static files
```

## Customization

### Colors
Edit `tailwind.config.ts` to change the primary color scheme.

### Layout
Modify `app/layout.tsx` for header/footer changes.

### Article Display
Customize `components/ArticleCard.tsx` for article card styling.

## License

MIT
