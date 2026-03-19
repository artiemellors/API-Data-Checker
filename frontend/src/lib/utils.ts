import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

export function formatDuration(start: string | null, end: string | null) {
  if (!start || !end) return null
  const ms = new Date(end).getTime() - new Date(start).getTime()
  if (ms < 60_000) return `${Math.round(ms / 1000)}s`
  return `${Math.round(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`
}

export function confidenceColor(confidence: number) {
  if (confidence >= 0.8) return 'text-green-600 bg-green-50 border-green-200'
  if (confidence >= 0.5) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
  return 'text-red-600 bg-red-50 border-red-200'
}

export const CATEGORY_COLORS: Record<string, string> = {
  search: 'bg-blue-100 text-blue-800',
  reviews: 'bg-purple-100 text-purple-800',
  recommendations: 'bg-pink-100 text-pink-800',
  analytics: 'bg-gray-100 text-gray-800',
  chat: 'bg-green-100 text-green-800',
  'ab-testing': 'bg-orange-100 text-orange-800',
  personalization: 'bg-indigo-100 text-indigo-800',
  loyalty: 'bg-yellow-100 text-yellow-800',
  cdn: 'bg-cyan-100 text-cyan-800',
  'customer-data': 'bg-teal-100 text-teal-800',
  payments: 'bg-emerald-100 text-emerald-800',
  'product-api': 'bg-blue-100 text-blue-800',
  'search-api': 'bg-sky-100 text-sky-800',
  'cart-api': 'bg-amber-100 text-amber-800',
  'reviews-api': 'bg-violet-100 text-violet-800',
  'graphql-api': 'bg-rose-100 text-rose-800',
  'unknown-api': 'bg-slate-100 text-slate-800',
}
