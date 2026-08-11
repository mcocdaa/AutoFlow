import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { executeFlow as apiExecuteFlow, fetchRun as apiFetchRun } from '../api/runs'
import { useAsyncState } from '../composables/useAsyncState'
import type { RunResult } from '../types/runs'

export const useRunsStore = defineStore('runs', () => {
  const currentRun = ref<RunResult | null>(null)

  const { loading: execLoading, error: execError, execute: execFlow } = useAsyncState(
    async (flowYaml: string, input: unknown, vars: Record<string, unknown>) => {
      const data = await apiExecuteFlow(flowYaml, input, vars)
      currentRun.value = data
      return data
    },
  )

  const { loading: fetchLoading, error: fetchError, execute: fetchOne } = useAsyncState(
    async (runId: string) => {
      const data = await apiFetchRun(runId)
      currentRun.value = data
      return data
    },
  )

  const loading = computed(() => execLoading.value || fetchLoading.value)
  const error = computed(() => execError.value ?? fetchError.value)

  return { currentRun, loading, error, executeFlow: execFlow, fetchRun: fetchOne }
})
