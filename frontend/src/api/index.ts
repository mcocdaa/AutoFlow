import axios from 'axios'

interface AutoflowBridge {
  apiBase?: string
}
const bridge = (window as unknown as { autoflow?: AutoflowBridge }).autoflow
const baseURL = bridge?.apiBase ? `${bridge.apiBase}/api/v1` : '/api/v1'

export const API_BASE_URL = baseURL

export function buildApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

export function buildArtifactUrl(runId: string, artifactPath: string): string {
  const encodedPath = artifactPath.split('/').map(encodeURIComponent).join('/')
  return buildApiUrl(`/runs/${encodeURIComponent(runId)}/artifacts/${encodedPath}`)
}

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail
    if (detail !== undefined && detail !== null) {
      error.message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    return Promise.reject(error)
  },
)

export default apiClient
