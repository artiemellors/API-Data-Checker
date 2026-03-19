import { ChevronDown, ChevronUp, Key, Shield } from 'lucide-react'
import { useState } from 'react'
import type { ProbeResponse, ServiceResponse } from '../api/client'
import { cn, confidenceColor, CATEGORY_COLORS } from '../lib/utils'
import { ProbeResultPanel } from './ProbeResultPanel'

interface Props {
  service: ServiceResponse
  probes: ProbeResponse[]
}

export function ServiceCard({ service, probes }: Props) {
  const [expanded, setExpanded] = useState(false)

  const confColor = confidenceColor(service.confidence)
  const catColor = CATEGORY_COLORS[service.category] ?? 'bg-gray-100 text-gray-800'

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <button
        className="w-full text-left p-4 flex items-start justify-between gap-3 hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-gray-900">{service.service_name}</h3>
            <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', catColor)}>
              {service.category}
            </span>
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full font-medium border',
                confColor
              )}
            >
              {Math.round(service.confidence * 100)}% confidence
            </span>
          </div>

          {/* Extracted keys */}
          {Object.keys(service.extracted_keys).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {Object.entries(service.extracted_keys).map(([k, v]) => (
                <span
                  key={k}
                  className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-700 rounded px-2 py-0.5 font-mono"
                >
                  <Key className="w-2.5 h-2.5" />
                  {k}: {v.length > 20 ? `${v.slice(0, 20)}…` : v}
                </span>
              ))}
            </div>
          )}

          {/* Probe summary */}
          {probes.length > 0 && (
            <p className="text-xs text-gray-500 mt-1.5">
              {probes.length} probe{probes.length !== 1 ? 's' : ''} —{' '}
              {probes.reduce((s, p) => s + p.data_fields_found.length, 0)} fields discovered
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Shield className="w-4 h-4 text-gray-400" />
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-gray-100 px-4 pb-4 pt-3 space-y-4 bg-gray-50">
          {/* Evidence */}
          {service.evidence.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                Detection evidence
              </p>
              <ul className="space-y-0.5">
                {service.evidence.map((e, i) => (
                  <li key={i} className="text-xs text-gray-600 truncate" title={e}>
                    • {e}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Probe results */}
          {probes.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                API probe results
              </p>
              <div className="space-y-3">
                {probes.map(probe => (
                  <ProbeResultPanel key={probe.id} probe={probe} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
