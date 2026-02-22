import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Azerbaijan News | Latest Headlines',
  description: 'Stay updated with the latest news from Azerbaijan - covering Sonxeber, APA, Report, Modern, and Axar news sources',
  keywords: 'azerbaijan news, xəbərlər, news aggregator, sonxeber, apa, report, modern, axar',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="az">
      <body>
        <div className="min-h-screen flex flex-col">
          <header className="bg-white shadow-sm sticky top-0 z-50">
            <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
              <div className="flex items-center justify-between">
                <a href="/" className="flex items-center space-x-2">
                  <svg className="w-8 h-8 text-primary-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
                  </svg>
                  <span className="text-2xl font-bold text-gray-900">
                    AZ <span className="text-primary-600">News</span>
                  </span>
                </a>

                <div className="flex items-center space-x-4">
                  <a href="/" className="text-gray-700 hover:text-primary-600 font-medium transition-colors">
                    Ana səhifə
                  </a>
                  <a href="/#sources" className="text-gray-700 hover:text-primary-600 font-medium transition-colors">
                    Mənbələr
                  </a>
                </div>
              </div>
            </nav>
          </header>

          <main className="flex-1">
            {children}
          </main>

          <footer className="bg-gray-900 text-gray-300 mt-16">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <h3 className="text-white font-bold text-lg mb-4">AZ News</h3>
                  <p className="text-sm">
                    Azərbaycanın aparıcı xəbər mənbələrindən ən son xəbərlər
                  </p>
                </div>

                <div>
                  <h3 className="text-white font-bold text-lg mb-4">Mənbələr</h3>
                  <ul className="space-y-2 text-sm">
                    <li><a href="https://sonxeber.az" target="_blank" rel="noopener" className="hover:text-white transition-colors">Sonxeber.az</a></li>
                    <li><a href="https://apa.az" target="_blank" rel="noopener" className="hover:text-white transition-colors">APA.az</a></li>
                    <li><a href="https://report.az" target="_blank" rel="noopener" className="hover:text-white transition-colors">Report.az</a></li>
                    <li><a href="https://modern.az" target="_blank" rel="noopener" className="hover:text-white transition-colors">Modern.az</a></li>
                    <li><a href="https://axar.az" target="_blank" rel="noopener" className="hover:text-white transition-colors">Axar.az</a></li>
                  </ul>
                </div>

                <div>
                  <h3 className="text-white font-bold text-lg mb-4">Haqqında</h3>
                  <p className="text-sm">
                    Avtomatik yenilənən xəbər aqreqatoru.
                    Bütün xəbərlər mənbələrindən toplanır və sizə təqdim olunur.
                  </p>
                </div>
              </div>

              <div className="mt-8 pt-8 border-t border-gray-800 text-center text-sm">
                <p>&copy; {new Date().getFullYear()} AZ News. Bütün hüquqlar qorunur.</p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
