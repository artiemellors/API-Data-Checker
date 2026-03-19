import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Activity, List } from 'lucide-react'
import { Home } from './pages/Home'
import { ScanList } from './pages/ScanList'
import { ScanDetail } from './pages/ScanDetail'
import { cn } from './lib/utils'

function NavBar() {
  const { pathname } = useLocation()

  return (
    <nav className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-semibold text-gray-900">
          <Activity className="w-5 h-5 text-blue-600" />
          API Checker
        </Link>

        <div className="flex items-center gap-1">
          <Link
            to="/"
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              pathname === '/'
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            New scan
          </Link>
          <Link
            to="/scans"
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              pathname.startsWith('/scans')
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            <List className="w-4 h-4" />
            All scans
          </Link>
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/scans" element={<ScanList />} />
            <Route path="/scans/:scanId" element={<ScanDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
