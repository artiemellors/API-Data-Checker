import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Download, RefreshCw } from 'lucide-react'
import { api, type ProbeResponse, type ScanProgressEvent, type ScanResponse, type ServiceResponse } from '../api/client'
import { ScanStatusBadge } from '../components/ScanStatusBadge'
import { ScanProgress } from '../components/ScanProgress'
import { ServiceCard } from '../components/ServiceCard'
import { formatDate, formatDuration } from '../lib/utils'

export function ScanDetail() {
  const { scanId } = useParams<{ scanId: string }>()
  const [scan, setScan] = useState<ScanResponse | null>(null)
  const [services, setServices] = useState<ServiceResponse[]>([])
  const [probes, setProbes] = useState<ProbeResponse[]>([])
  const [events, setEvents] = useState<ScanProgressEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const stopStreamRef = useRef<(() => void) | null>(null)

  const fetchResults = async (id: string) => {
    const [scanData, servicesData, probesData] = await Promise.all([
      api.getScan(id),
      api.getServices(id),
      api.getProbes(id),
    ])
    setScan(scanData)
    setServices(servicesData)
    setProbes(probesData)
  }

  useEffect(() => {
    if (!scanId) return
    setLoading(true)

    fetchResults(scanId)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [scanId])

  // Start SSE stream when scan is pending/running
  useEffect(() => {
    if (!scanId || !scan) return
    if (scan.status !== 'pending' && scan.status !== 'running') return

    stopStreamRef.current?.()

    const stop = api.streamEvents(scanId, (ev) => {
      setEvents(prev => [...prev, ev])
      if (ev.event === 'done' || ev.event === 'error') {
        // Re-fetch final results
        fetchResults(scanId).catch(() => {})
      }
    })
    stopStreamRef.current = stop

    return () => stop()
  }, [scanId, scan?.status])

  // Poll for status changes while running
  useEffect(() => {
    if (!scanId || !scan) return
    if (scan.status !== 'pending' && scan.status !== 'running') return

    const interval = setInterval(() => {
      fetchResults(scanId).catch(() => {})
    }, 3000)
    return () => clearInterval(interval)
  }, [scanId, scan?.status])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center text-gray-400">
        Loading scan…
      </div>
    )
  }

  if (error || !scan) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <p className="text-red-600">{error || 'Scan not found'}</p>
        <Link to="/scans" className="text-blue-600 hover:underline text-sm mt-2 inline-block">
          ← Back to scans
        </Link>
      </div>
    )
  }

  const probesBySvc: Record<number, ProbeResponse[]> = {}
  for (const p of probes) {
    if (p.service_id != null) {
      probesBySvc[p.service_id] = [...(probesBySvc[p.service_id] ?? []), p]
    }
  }

  const isRunning = scan.status === 'pending' || scan.status === 'running'

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Back nav */}
      <Link
        to="/scans"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900"
      >
        <ArrowLeft className="w-4 h-4" /> All scans
      </Link>

      {/* Scan header */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-xl font-bold text-gray-900">{scan.domain}</h1>
              <ScanStatusBadge status={scan.status} />
            </div>
            <p className="text-sm text-gray-500 break-all">{scan.url}</p>
          </div>

          {/* Export buttons */}
          {scan.status === 'completed' && (
            <div className="flex gap-2 shrink-0">
              <a
                href={api.exportJsonUrl(scan.scan_id)}
                download
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium"
              >
                <Download className="w-3.5 h-3.5" /> JSON
              </a>
              <a
                href={api.exportCsvUrl(scan.scan_id)}
                download
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium"
              >
                <Download className="w-3.5 h-3.5" /> CSV
              </a>
            </div>
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          {[
            { label: 'Services found', value: scan.services_found },
            { label: 'Endpoints', value: scan.endpoints_discovered },
            { label: 'Probes run', value: scan.probes_completed },
            { label: 'Duration', value: formatDuration(scan.started_at, scan.completed_at) ?? '—' },
          ].map(stat => (
            <div key={stat.label} className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2">
              <p className="text-xs text-gray-500">{stat.label}</p>
              <p className="text-lg font-bold text-gray-900 mt-0.5">{stat.value}</p>
            </div>
          ))}
        </div>

        {scan.started_at && (
          <p className="text-xs text-gray-400 mt-3">
            Started {formatDate(scan.started_at)}
            {scan.completed_at && ` · Completed ${formatDate(scan.completed_at)}`}
          </p>
        )}

        {/* Errors */}
        {scan.errors.length > 0 && (
          <div className="mt-3 rounded-lg bg-red-50 border border-red-200 p-3">
            <p className="text-xs font-semibold text-red-700 mb-1">Errors ({scan.errors.length})</p>
            {scan.errors.map((e, i) => (
              <p key={i} className="text-xs text-red-600">{e}</p>
            ))}
          </div>
        )}
      </div>

      {/* Live progress */}
      {(isRunning || events.length > 0) && (
        <ScanProgress events={events} running={isRunning} />
      )}

      {/* Services */}
      {services.length > 0 ? (
        <div>
          <h2 className="text-base font-semibold text-gray-900 mb-3">
            Discovered services ({services.length})
          </h2>
          <div className="space-y-3">
            {services
              .sort((a, b) => b.confidence - a.confidence)
              .map(svc => (
                <ServiceCard
                  key={svc.id}
                  service={svc}
                  probes={probesBySvc[svc.id] ?? []}
                />
              ))}
          </div>
        </div>
      ) : scan.status === 'completed' ? (
        <div className="text-center py-10 text-gray-400">
          No third-party services detected on this site.
        </div>
      ) : null}
    </div>
  )
}
