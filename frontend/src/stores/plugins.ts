import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchPlugins as apiFetchPlugins } from '../api/plugins'
import { useAsyncState } from '../composables/useAsyncState'
import type { Plugin, PluginError } from '../types/plugins'

export const usePluginsStore = defineStore('plugins', () => {
  const plugins = ref<Plugin[]>([])
  const actions = ref<string[]>([])
  const checks = ref<string[]>([])
  const errors = ref<PluginError[]>([])

  const { loading, error, execute } = useAsyncState(async () => {
    const data = await apiFetchPlugins()
    plugins.value = data.plugins
    actions.value = data.actions
    checks.value = data.checks
    errors.value = data.errors || []
    return data
  })

  return { plugins, actions, checks, errors, loading, error, fetchPlugins: execute }
})
