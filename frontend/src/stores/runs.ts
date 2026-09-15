import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  deleteRun as apiDeleteRun,
  executeFlow as apiExecuteFlow,
  fetchRun as apiFetchRun,
  fetchRuns as apiFetchRuns,
} from '../api/runs'
import { useAsyncState } from '../composables/useAsyncState'
import type { RunResult } from '../types/runs'

export const useRunsStore = defineStore('runs', () => {
  const currentRun = ref<RunResult | null>(null)
  const runs = ref<RunResult[]>([])

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

  const { loading: listLoading, error: listError, execute: fetchList } = useAsyncState(
    async () => {
      const data = await apiFetchRuns()
      runs.value = data
      return data
    },
  )

  const removeRun = async (runId: string) => {
    await apiDeleteRun(runId)
    runs.value = runs.value.filter((run) => run.run_id !== runId)
    if (currentRun.value?.run_id === runId) {
      currentRun.value = null
    }
  }

  const loading = computed(() => execLoading.value || fetchLoading.value || listLoading.value)
  const error = computed(() => execError.value ?? fetchError.value ?? listError.value)

  return {
    currentRun,
    runs,
    loading,
    error,
    executeFlow: execFlow,
    fetchRun: fetchOne,
    fetchRuns: fetchList,
    removeRun,
  }
})
