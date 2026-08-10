import apiClient from './index'
import type { RunResult } from '../types/runs'

export async function executeFlow(
  flowYaml: string,
  input: unknown = {},
  vars: Record<string, unknown> = {},
): Promise<RunResult> {
  const { data } = await apiClient.post<RunResult>('/runs/execute', {
    flow_yaml: flowYaml,
    input,
    vars,
  })
  return data
}

export async function fetchRun(runId: string): Promise<RunResult> {
  const { data } = await apiClient.get<RunResult>(`/runs/${runId}`)
  return data
}
