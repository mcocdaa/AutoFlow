import { defineStore } from 'pinia'
import apiClient from '../api'

export const useRunsStore = defineStore('runs', {
  state: () => ({
    currentRun: null as any,
    loading: false,
    error: null as string | null,
  }),
  actions: {
    async executeFlow(flowYaml: string, input: any = {}, vars: any = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await apiClient.post('/runs/execute', {
          flow_yaml: flowYaml,
          input,
          vars
        })
        this.currentRun = response.data
        return response.data
      } catch (error: any) {
        this.error = error.response?.data?.detail || error.message
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchRun(runId: string) {
      this.loading = true
      try {
        const response = await apiClient.get(`/runs/${runId}`)
        this.currentRun = response.data
        return response.data
      } catch (error: any) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    }
  }
})
