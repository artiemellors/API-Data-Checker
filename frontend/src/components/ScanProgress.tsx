import { useEffect, useRef } from 'react'
import { CheckCircle, AlertCircle, Loader2, Radio } from 'lucide-react'
import type { ScanProgressEvent } from '../api/client'
import { cn } from '../lib/utils'

interface Props {
  events: ScanProgressEvent[]
  running: boolean
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  progress: <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500 shrink-0" />,
  service_found: <Radio className="w-3.5 h-3.5 text-green-500 shrink-0" />,
  probe_complete: <CheckCircle className="w-3.5 h-3.5 text-blue-500 shrink-0" />,
  error: <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />,
  done: <CheckCircle className="w-3.5 h-3.5 text-green-600 shrink-0" />,
}

export function ScanProgress({ events, running }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  if (events.length === 0 && !running) return null

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
        Live progress
      </p>
      <div className="space-y-1.5 max-h-48 overflow-y-auto text-sm">
        {events.map((ev, i) => (
          <div key={i} className="flex items-start gap-2">
            {EVENT_ICONS[ev.event] ?? null}
            <span
              className={cn(
                'text-xs leading-snug',
                ev.event === 'error' ? 'text-red-600' :
                ev.event === 'done' ? 'text-green-700 font-medium' :
                ev.event === 'service_found' ? 'text-green-700' :
                'text-gray-600'
              )}
            >
              {ev.message || ev.service_name || ev.event}
              {ev.step !== undefined && ev.total !== undefined && (
                <span className="text-gray-400 ml-1">
                  ({ev.step}/{ev.total})
                </span>
              )}
            </span>
          </div>
        ))}
        {running && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Scanning…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
