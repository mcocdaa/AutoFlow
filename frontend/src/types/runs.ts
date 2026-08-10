// Backend model alignment:
// - StepResult / RunResult mirror backend/app/runtime/models/models.py
// - RunStatus literal matches StepStatus/RunStatus in the backend

export type RunStepStatus = 'success' | 'failed' | 'skipped'
export type RunStatus = 'success' | 'failed' | 'running'

export interface RunStepResult {
  step_id: string
  status: RunStepStatus
  started_at: string
  finished_at: string
  duration_ms: number
  action_output: unknown
  check_passed: boolean | null
  error: string | null
  iterations: unknown[] | null
}

export interface RunResult {
  run_id: string
  flow_name: string
  status: RunStatus
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  steps: RunStepResult[]
  error: string | null
}
