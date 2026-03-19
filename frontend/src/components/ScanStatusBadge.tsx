import { cn } from '../lib/utils'

interface Props {
  status: string
  className?: string
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700 border-gray-200',
  running: 'bg-blue-100 text-blue-700 border-blue-200 animate-pulse',
  completed: 'bg-green-100 text-green-700 border-green-200',
  failed: 'bg-red-100 text-red-700 border-red-200',
}

const STATUS_DOTS: Record<string, string> = {
  pending: 'bg-gray-400',
  running: 'bg-blue-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
}

export function ScanStatusBadge({ status, className }: Props) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending
  const dot = STATUS_DOTS[status] ?? STATUS_DOTS.pending

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border',
        style,
        className
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full', dot)} />
      {status}
    </span>
  )
}
