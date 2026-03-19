import { useState } from 'react'
import { Search, Plus, Minus } from 'lucide-react'
import { cn } from '../lib/utils'

interface Props {
  onSubmit: (urls: string[], maxPages: number, probe: boolean) => Promise<void>
  loading?: boolean
}

export function ScanForm({ onSubmit, loading }: Props) {
  const [url, setUrl] = useState('')
  const [bulkMode, setBulkMode] = useState(false)
  const [bulkUrls, setBulkUrls] = useState('')
  const [maxPages, setMaxPages] = useState(10)
  const [probe, setProbe] = useState(true)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const urls = bulkMode
      ? bulkUrls.split('\n').map(u => u.trim()).filter(Boolean)
      : [url.trim()]

    if (urls.length === 0) {
      setError('Enter at least one URL')
      return
    }

    try {
      await onSubmit(urls, maxPages, probe)
      setUrl('')
      setBulkUrls('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit scan')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-gray-700">
          {bulkMode ? 'Retailer URLs (one per line)' : 'Retailer URL'}
        </label>
        <button
          type="button"
          onClick={() => setBulkMode(b => !b)}
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
        >
          {bulkMode ? <Minus className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
          {bulkMode ? 'Single URL' : 'Bulk mode'}
        </button>
      </div>

      {bulkMode ? (
        <textarea
          value={bulkUrls}
          onChange={e => setBulkUrls(e.target.value)}
          placeholder={'https://www.kmart.com.au\nhttps://www.target.com\nhttps://www.walmart.com'}
          rows={5}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
          disabled={loading}
        />
      ) : (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://www.kmart.com.au"
            className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
        </div>
      )}

      {/* Options row */}
      <div className="flex items-center gap-4 text-sm text-gray-600">
        <label className="flex items-center gap-2 cursor-pointer">
          <span>Max pages:</span>
          <select
            value={maxPages}
            onChange={e => setMaxPages(Number(e.target.value))}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
            disabled={loading}
          >
            {[5, 10, 15, 20, 30].map(n => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={probe}
            onChange={e => setProbe(e.target.checked)}
            className="rounded border-gray-300 text-blue-600"
            disabled={loading}
          />
          <span>Probe APIs</span>
        </label>
      </div>

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      <button
        type="submit"
        disabled={loading}
        className={cn(
          'w-full rounded-lg py-2.5 px-4 text-sm font-semibold text-white transition-colors',
          loading
            ? 'bg-blue-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
        )}
      >
        {loading ? 'Submitting…' : bulkMode ? 'Scan all URLs' : 'Scan'}
      </button>
    </form>
  )
}
