import apiClient from './index'
import type { DebugSessionSnapshot } from '../types/debug'

export async function createDebugSession(
  flowYaml: string,
  input: unknown = {},
  vars: Record<string, unknown> = {},
): Promise<DebugSessionSnapshot> {
  const { data } = await apiClient.post<DebugSessionSnapshot>('/debug/sessions', {
    flow_yaml: flowYaml,
    input,
    vars,
  })
  return data
}

export async function fetchDebugSession(
  sessionId: string,
): Promise<DebugSessionSnapshot> {
  const { data } = await apiClient.get<DebugSessionSnapshot>(
    `/debug/sessions/${sessionId}`,
  )
  return data
}

export async function stepDebugSession(
  sessionId: string,
): Promise<DebugSessionSnapshot> {
  const { data } = await apiClient.post<DebugSessionSnapshot>(
    `/debug/sessions/${sessionId}/step`,
  )
  return data
}

export async function runDebugSession(
  sessionId: string,
): Promise<DebugSessionSnapshot> {
  const { data } = await apiClient.post<DebugSessionSnapshot>(
    `/debug/sessions/${sessionId}/run`,
  )
  return data
}

export async function deleteDebugSession(sessionId: string): Promise<void> {
  await apiClient.delete(`/debug/sessions/${sessionId}`)
}
