'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';

interface SearchBarProps {
  initialQuery?: string;
  sourceId?: number;
}

export default function SearchBar({ initialQuery = '', sourceId }: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);
  const router = useRouter();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      // If empty, redirect to home or current source
      router.push(sourceId ? `/?source=${sourceId}` : '/');
      return;
    }

    // Build URL with search and optional source filter
    const params = new URLSearchParams();
    params.set('q', query.trim());
    if (sourceId) {
      params.set('source', sourceId.toString());
    }

    router.push(`/?${params.toString()}`);
  };

  const handleClear = () => {
    setQuery('');
    router.push(sourceId ? `/?source=${sourceId}` : '/');
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto mb-8">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Xəbərlərdə axtar..."
          className="w-full px-6 py-4 pr-32 rounded-full text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/50 shadow-lg"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-2">
          {query && (
            <button
              type="button"
              onClick={handleClear}
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
          <button
            type="submit"
            className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-full transition-colors font-medium"
          >
            Axtar
          </button>
        </div>
      </div>
    </form>
  );
}
