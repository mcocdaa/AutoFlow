import type { HookResult, RunStepResult } from './runs'

export interface DebugStepInfo {
  id: string
  name: string | null
  for_each: string | null
  has_condition: boolean
  retry_attempts: number
  output_var: string | null
}

export interface DebugSessionSnapshot {
  session_id: string
  flow_name: string
  status: 'paused' | 'success' | 'failed'
  index: number
  total_steps: number
  run_id: string
  steps: DebugStepInfo[]
  results: RunStepResult[]
  hook_results: HookResult[]
  error: string | null
}
