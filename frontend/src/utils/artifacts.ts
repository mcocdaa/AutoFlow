import type { ArtifactRef } from '../types/runs'

export function collectArtifacts(
  value: unknown,
  found: ArtifactRef[] = [],
): ArtifactRef[] {
  if (Array.isArray(value)) {
    value.forEach((item) => collectArtifacts(item, found))
    return found
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    const artifact = record.__artifact__
    if (artifact && typeof artifact === 'object') {
      const ref = artifact as Record<string, unknown>
      if (typeof ref.path === 'string') {
        found.push({
          path: ref.path,
          sha256: typeof ref.sha256 === 'string' ? ref.sha256 : '',
          size: typeof ref.size === 'number' ? ref.size : 0,
        })
      }
    }
    Object.values(record).forEach((item) => collectArtifacts(item, found))
  }
  return found
}

export function uniqueArtifacts(refs: ArtifactRef[]): ArtifactRef[] {
  return [...new Map(refs.map((ref) => [ref.path, ref])).values()]
}

export function artifactsOfValue(value: unknown): ArtifactRef[] {
  return uniqueArtifacts(collectArtifacts(value))
}
