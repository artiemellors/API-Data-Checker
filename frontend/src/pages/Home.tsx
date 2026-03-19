import { useNavigate } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { useState } from 'react'
import { ScanForm } from '../components/ScanForm'
import { api } from '../api/client'

export function Home() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (urls: string[], maxPages: number, probe: boolean) => {
    setLoading(true)
    try {
      if (urls.length === 1) {
        const scan = await api.createScan(urls[0], maxPages, probe)
        navigate(`/scans/${scan.scan_id}`)
      } else {
        const result = await api.createBatchScan(urls, maxPages, probe)
        // Navigate to scan list to see all batch jobs
        navigate('/scans')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-600 mb-4">
          <Activity className="w-7 h-7 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-3">
          Retailer API Checker
        </h1>
        <p className="text-gray-500 text-base max-w-md mx-auto">
          Discover publicly accessible APIs embedded in retailer websites —
          search, reviews, recommendations, loyalty, payments and more.
        </p>
      </div>

      {/* Scan form card */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
        <ScanForm onSubmit={handleSubmit} loading={loading} />
      </div>

      {/* Example hint */}
      <p className="text-center text-xs text-gray-400 mt-5">
        Try{' '}
        {['kmart.com.au', 'target.com', 'walmart.com'].map((d, i, arr) => (
          <span key={d}>
            <button
              className="text-blue-500 hover:underline"
              onClick={() => handleSubmit([`https://www.${d}`], 10, true)}
            >
              {d}
            </button>
            {i < arr.length - 1 && ', '}
          </span>
        ))}
      </p>
    </div>
  )
}
