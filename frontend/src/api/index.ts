import axios from 'axios'

interface AutoflowBridge {
  apiBase?: string
}
const bridge = (window as unknown as { autoflow?: AutoflowBridge }).autoflow
const baseURL = bridge?.apiBase ? `${bridge.apiBase}/api/v1` : '/api/v1'

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 统一错误标准化:优先提取后端返回的 response.data.detail
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
