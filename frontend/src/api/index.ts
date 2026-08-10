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

export default apiClient
