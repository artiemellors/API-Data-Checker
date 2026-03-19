/**
 * Typed API client for the Retailer API Checker backend.
 */

export interface ScanResponse {
  scan_id: string
  url: string
  domain: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  max_pages: number
  probe: boolean
  started_at: string | null
  completed_at: string | null
  endpoints_discovered: number
  services_found: number
  probes_completed: number
  errors: string[]
}

export interface ServiceResponse {
  id: number
  scan_id: string
  service_name: string
  category: string
  confidence: number
  evidence: string[]
  extracted_keys: Record<string, string>
}

export interface ProbeResponse {
  id: number
  scan_id: string
  service_id: number | null
  service_name: string | null
  probe_url: string
  probe_method: string
  probe_payload: Record<string, unknown> | null
  response_status: number | null
  data_fields_found: string[]
  sample_records: Record<string, unknown>[]
  probed_at: string
  error: string | null
}

export interface ScanProgressEvent {
  event: 'progress' | 'service_found' | 'probe_complete' | 'error' | 'done'
  message: string
  service_name?: string
  category?: string
  fields_found?: number
  services_found?: number
  step?: number
  total?: number
}

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status} ${text}`)
  }
  return res.json() as Promise<T>
}

// ── Scans ─────────────────────────────────────────────────────────────────────

export const api = {
  createScan: (url: string, maxPages = 10, probe = true) =>
    request<ScanResponse>('/scans', {
      method: 'POST',
      body: JSON.stringify({ url, max_pages: maxPages, probe }),
    }),

  createBatchScan: (urls: string[], maxPages = 10, probe = true) =>
    request<{ scan_ids: string[]; submitted: number }>('/scans/batch', {
      method: 'POST',
      body: JSON.stringify({ urls, max_pages: maxPages, probe }),
    }),

  listScans: () => request<ScanResponse[]>('/scans'),

  getScan: (scanId: string) => request<ScanResponse>(`/scans/${scanId}`),

  getServices: (scanId: string) =>
    request<ServiceResponse[]>(`/scans/${scanId}/services`),

  getProbes: (scanId: string) =>
    request<ProbeResponse[]>(`/scans/${scanId}/probes`),

  exportJsonUrl: (scanId: string) => `${BASE}/scans/${scanId}/export.json`,
  exportCsvUrl: (scanId: string) => `${BASE}/scans/${scanId}/export.csv`,

  streamEvents: (scanId: string, onEvent: (e: ScanProgressEvent) => void): () => void => {
    const es = new EventSource(`${BASE}/scans/${scanId}/events`)
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as ScanProgressEvent
        onEvent(data)
        if (data.event === 'done' || data.event === 'error') {
          es.close()
        }
      } catch {
        // ignore parse errors
      }
    }
    es.onerror = () => es.close()
    return () => es.close()
  },
}
