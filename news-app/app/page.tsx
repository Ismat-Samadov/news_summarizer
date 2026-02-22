import { getArticles, getNewsSources, getArticleCount, searchArticles, getSearchCount, isValidSourceId } from '@/lib/db';
import ArticleCard from '@/components/ArticleCard';
import Pagination from '@/components/Pagination';
import SearchBar from '@/components/SearchBar';
import { redirect } from 'next/navigation';

export const dynamic = 'force-dynamic';
export const revalidate = 300; // Revalidate every 5 minutes

const ARTICLES_PER_PAGE = 24;

interface HomeProps {
  searchParams: { page?: string; source?: string; q?: string };
}

export default async function Home({ searchParams }: HomeProps) {
  const currentPage = parseInt(searchParams.page || '1', 10);
  let sourceId = searchParams.source ? parseInt(searchParams.source, 10) : undefined;
  const searchQuery = searchParams.q?.trim();

  // Validate source ID if provided
  if (sourceId && !isNaN(sourceId)) {
    const isValid = await isValidSourceId(sourceId);
    if (!isValid) {
      // Invalid source ID - redirect to home without source filter
      const params = new URLSearchParams();
      if (searchQuery) params.set('q', searchQuery);
      if (currentPage > 1) params.set('page', currentPage.toString());
      redirect(params.toString() ? `/?${params.toString()}` : '/');
    }
  } else if (sourceId) {
    // NaN source ID - ignore it
    sourceId = undefined;
  }

  const offset = (currentPage - 1) * ARTICLES_PER_PAGE;

  // Use search or regular fetch based on query
  const [articles, sources, totalCount] = await Promise.all([
    searchQuery
      ? searchArticles(searchQuery, ARTICLES_PER_PAGE, offset, sourceId)
      : getArticles(ARTICLES_PER_PAGE, offset, sourceId),
    getNewsSources(),
    searchQuery
      ? getSearchCount(searchQuery, sourceId)
      : getArticleCount(sourceId),
  ]);

  const totalPages = Math.ceil(totalCount / ARTICLES_PER_PAGE);

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-r from-primary-600 to-primary-700 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl font-bold mb-4">
              Azərbaycan Xəbərləri
            </h1>
            <p className="text-xl text-primary-100 mb-8">
              Ən son xəbərlər bir yerdə • {totalCount} xəbər
            </p>

            {/* Search Bar */}
            <SearchBar initialQuery={searchQuery} sourceId={sourceId} />

            <div className="flex flex-wrap justify-center gap-2">
              {/* All filter */}
              <a
                href="/"
                className={`inline-block px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  !sourceId
                    ? 'bg-white text-primary-600 shadow-lg'
                    : 'bg-white/20 backdrop-blur-sm hover:bg-white/30 cursor-pointer'
                }`}
              >
                Hamısı
              </a>

              {/* Source filters */}
              {sources.map((source) => (
                <a
                  key={source.id}
                  href={`/?source=${source.id}`}
                  className={`inline-block px-4 py-2 rounded-full text-sm font-medium transition-all ${
                    sourceId === source.id
                      ? 'bg-white text-primary-600 shadow-lg'
                      : 'bg-white/20 backdrop-blur-sm hover:bg-white/30 cursor-pointer'
                  }`}
                >
                  {source.name}
                </a>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Articles Grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">
              {searchQuery ? 'Axtarış Nəticələri' : 'Son Xəbərlər'}
            </h2>
            {searchQuery && (
              <p className="text-gray-600 mt-2">
                &ldquo;{searchQuery}&rdquo; üçün {totalCount} nəticə tapıldı
              </p>
            )}
          </div>
          <div className="flex items-center text-sm text-gray-500">
            <svg className="w-5 h-5 mr-2 text-green-500 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Avtomatik yenilənir
          </div>
        </div>

        {articles.length === 0 ? (
          <div className="text-center py-16">
            <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">Hələ ki xəbər yoxdur</h3>
            <p className="text-gray-500">Xəbərlər tezliklə yenilənəcək</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {articles.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </div>

            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              baseUrl={(() => {
                const params = new URLSearchParams();
                if (searchQuery) params.set('q', searchQuery);
                if (sourceId) params.set('source', sourceId.toString());
                return params.toString() ? `/?${params.toString()}` : '/';
              })()}
            />
          </>
        )}
      </section>

      {/* Sources Section */}
      <section id="sources" className="bg-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">
            Xəbər Mənbələri
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
            {sources.map((source) => (
              <a
                key={source.id}
                href={source.base_url}
                target="_blank"
                rel="noopener noreferrer"
                className="card p-6 text-center hover:border-primary-500 border-2 border-transparent transition-all"
              >
                <div className="text-primary-600 font-bold text-lg mb-2">
                  {source.name}
                </div>
                <div className="text-gray-500 text-sm">
                  {source.domain}
                </div>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="bg-gray-100 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <div className="text-4xl font-bold text-primary-600 mb-2">{totalCount}</div>
              <div className="text-gray-600">Ümumi Xəbərlər</div>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <div className="text-4xl font-bold text-primary-600 mb-2">{sources.length}</div>
              <div className="text-gray-600">Aktiv Mənbələr</div>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <div className="text-4xl font-bold text-primary-600 mb-2">24/7</div>
              <div className="text-gray-600">Avtomatik Yenilənmə</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
