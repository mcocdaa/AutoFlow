import apiClient from './index'
import type { RunResult } from '../types/runs'

export async function fetchRuns(): Promise<RunResult[]> {
  const { data } = await apiClient.get<RunResult[]>('/runs')
  return data
}

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

export async function deleteRun(runId: string): Promise<void> {
  await apiClient.delete(`/runs/${runId}`)
}

export async function replayRun(runId: string): Promise<RunResult> {
  const { data } = await apiClient.post<RunResult>(`/runs/${runId}/replay`)
  return data
}
