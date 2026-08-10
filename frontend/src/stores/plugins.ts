import { defineStore } from 'pinia'
import apiClient from '../api'
import type { Plugin, PluginError } from '../types/plugins'

interface PluginsResponse {
  plugins: Plugin[]
  actions: string[]
  checks: string[]
  errors: PluginError[]
}

export const usePluginsStore = defineStore('plugins', {
  state: () => ({
    plugins: [] as Plugin[],
    actions: [] as string[],
    checks: [] as string[],
    errors: [] as PluginError[],
    loading: false,
    error: null as string | null,
  }),
  actions: {
    async fetchPlugins() {
      this.loading = true
      this.error = null
      try {
        const response = await apiClient.get<PluginsResponse>('/plugins')
        this.plugins = response.data.plugins
        this.actions = response.data.actions
        this.checks = response.data.checks
        this.errors = response.data.errors || []
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
        console.error('Failed to fetch plugins:', error)
      } finally {
        this.loading = false
      }
    },
  },
})
