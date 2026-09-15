export function formatOutput(output: unknown): string {
  if (output === undefined || output === null) return '—'
  if (typeof output === 'string') return output
  return JSON.stringify(output, null, 2)
}

export function formatInline(value: unknown): string {
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

export function formatTime(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

export function formatSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
