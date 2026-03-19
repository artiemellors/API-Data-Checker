import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, ArrowRight } from 'lucide-react'
import { api, type ScanResponse } from '../api/client'
import { ScanStatusBadge } from '../components/ScanStatusBadge'
import { formatDate, formatDuration } from '../lib/utils'

export function ScanList() {
  const [scans, setScans] = useState<ScanResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchScans = async () => {
    try {
      const data = await api.listScans()
      setScans(data)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scans')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchScans()
    // Auto-refresh while there are running scans
    const interval = setInterval(() => {
      fetchScans()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">All Scans</h1>
        <button
          onClick={fetchScans}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm p-3 mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-400">Loading…</div>
      ) : scans.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 mb-4">No scans yet.</p>
          <Link to="/" className="text-blue-600 hover:underline text-sm">
            Start your first scan →
          </Link>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-left">
                <th className="px-4 py-3 font-semibold text-gray-600">Domain</th>
                <th className="px-4 py-3 font-semibold text-gray-600">Status</th>
                <th className="px-4 py-3 font-semibold text-gray-600 text-right">Services</th>
                <th className="px-4 py-3 font-semibold text-gray-600 text-right">Endpoints</th>
                <th className="px-4 py-3 font-semibold text-gray-600">Started</th>
                <th className="px-4 py-3 font-semibold text-gray-600">Duration</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {scans.map((scan, i) => (
                <tr
                  key={scan.scan_id}
                  className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                    i === scans.length - 1 ? 'border-0' : ''
                  }`}
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-gray-900">{scan.domain}</p>
                      <p className="text-xs text-gray-400 truncate max-w-xs" title={scan.url}>
                        {scan.url}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <ScanStatusBadge status={scan.status} />
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">
                    {scan.services_found}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">
                    {scan.endpoints_discovered}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {formatDate(scan.started_at)}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {formatDuration(scan.started_at, scan.completed_at) ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/scans/${scan.scan_id}`}
                      className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 text-xs font-medium"
                    >
                      View
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
