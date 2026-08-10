import { defineStore } from 'pinia'
import apiClient from '../api'
import type { RunResult } from '../types/runs'

export const useRunsStore = defineStore('runs', {
  state: () => ({
    currentRun: null as RunResult | null,
    loading: false,
    error: null as string | null,
  }),
  actions: {
    async executeFlow(flowYaml: string, input: unknown = {}, vars: Record<string, unknown> = {}) {
      this.loading = true
      this.error = null
      try {
        const response = await apiClient.post<RunResult>('/runs/execute', {
          flow_yaml: flowYaml,
          input,
          vars,
        })
        this.currentRun = response.data
        return response.data
      } catch (error) {
        this.error =
          (error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
          (error instanceof Error ? error.message : String(error))
        throw error
      } finally {
        this.loading = false
      }
    },
    async fetchRun(runId: string) {
      this.loading = true
      try {
        const response = await apiClient.get<RunResult>(`/runs/${runId}`)
        this.currentRun = response.data
        return response.data
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
  },
})
