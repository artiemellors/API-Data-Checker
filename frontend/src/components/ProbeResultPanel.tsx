import { useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import type { ProbeResponse } from '../api/client'
import { cn } from '../lib/utils'

interface Props {
  probe: ProbeResponse
}

function statusColor(status: number | null) {
  if (!status) return 'text-gray-400'
  if (status < 300) return 'text-green-600'
  if (status < 400) return 'text-yellow-600'
  return 'text-red-600'
}

export function ProbeResultPanel({ probe }: Props) {
  const [showSamples, setShowSamples] = useState(false)

  return (
    <div className="rounded-lg border border-gray-200 bg-white text-sm overflow-hidden">
      {/* URL bar */}
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 border-b border-gray-200">
        <span className="text-xs font-mono font-semibold text-gray-500">
          {probe.probe_method}
        </span>
        <a
          href={probe.probe_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-xs font-mono text-blue-600 hover:underline truncate"
          title={probe.probe_url}
        >
          {probe.probe_url}
        </a>
        <ExternalLink className="w-3 h-3 text-gray-400 shrink-0" />
        <span className={cn('text-xs font-semibold', statusColor(probe.response_status))}>
          {probe.response_status ?? '—'}
        </span>
      </div>

      {probe.error && (
        <p className="px-3 py-2 text-xs text-red-600">{probe.error}</p>
      )}

      {/* Data fields */}
      {probe.data_fields_found.length > 0 && (
        <div className="px-3 py-2">
          <p className="text-xs font-semibold text-gray-500 mb-1.5">
            Data fields ({probe.data_fields_found.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {probe.data_fields_found.map(f => (
              <span
                key={f}
                className="text-xs bg-blue-50 text-blue-700 rounded px-1.5 py-0.5 font-mono"
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Sample records toggle */}
      {probe.sample_records.length > 0 && (
        <div className="border-t border-gray-100">
          <button
            onClick={() => setShowSamples(s => !s)}
            className="w-full flex items-center justify-between px-3 py-2 text-xs text-gray-500 hover:bg-gray-50"
          >
            <span>Sample records ({probe.sample_records.length})</span>
            {showSamples ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
          {showSamples && (
            <div className="px-3 pb-3 space-y-2">
              {probe.sample_records.map((rec, i) => (
                <pre
                  key={i}
                  className="text-xs bg-gray-900 text-green-400 rounded p-2 overflow-x-auto"
                >
                  {JSON.stringify(rec, null, 2)}
                </pre>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
