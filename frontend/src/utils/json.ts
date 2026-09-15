import { message } from 'ant-design-vue'

export type JsonParseResult = { ok: true; value: unknown } | { ok: false }

export function parseJsonInput(text: string, label: string): JsonParseResult {
  const trimmed = text.trim()
  if (!trimmed) return { ok: true, value: {} }
  try {
    return { ok: true, value: JSON.parse(trimmed) }
  } catch (err) {
    message.error(`${label} 不是合法 JSON：${(err as Error).message}`)
    return { ok: false }
  }
}

export function parseJsonObject(
  text: string,
  label: string,
): Record<string, unknown> | null {
  const result = parseJsonInput(text, label)
  if (!result.ok) return null
  if (
    typeof result.value !== 'object' ||
    result.value === null ||
    Array.isArray(result.value)
  ) {
    message.error(`${label} 需要是 JSON 对象`)
    return null
  }
  return result.value as Record<string, unknown>
}
