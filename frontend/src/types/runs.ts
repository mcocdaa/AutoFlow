// Backend model alignment:
// - RunIteration / RunStepResult / RunResult mirror backend/app/runtime/models/models.py
// - RunStatus / RunStepStatus literal match StepStatus/RunStatus in the backend

export type RunStepStatus = 'success' | 'failed' | 'skipped'
export type RunStatus = 'success' | 'failed' | 'running'

export interface RunIteration {
  item: unknown
  output: unknown
  error: string | null
  check_passed: boolean | null
  duration_ms: number
  vars_snapshot?: Record<string, unknown>
}

export interface RunStepResult {
  step_id: string
  status: RunStepStatus
  started_at: string
  finished_at: string
  duration_ms: number
  action_output: unknown
  check_passed: boolean | null
  error: string | null
  iterations: RunIteration[] | null
}

export type HookPhase = 'on_success' | 'on_failure'
export type HookStatus = 'success' | 'failed'

export interface HookResult {
  hook: HookPhase
  action_type: string
  status: HookStatus
  started_at: string
  finished_at: string
  duration_ms: number
  output: unknown
  error: string | null
}

export interface RunResult {
  run_id: string
  flow_name: string
  status: RunStatus
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  steps: RunStepResult[]
  hook_results: HookResult[]
  error: string | null
  parent_run_id: string | null
  fork_step_index: number | null
}

export interface RunDiffSummary {
  run_id: string
  flow_name: string
  status: RunStatus
  started_at: string
  duration_ms: number | null
}

export interface OutputDiffEntry {
  path: string
  base: unknown
  target: unknown
}

export interface RunStepDiff {
  step_id: string
  base_index: number | null
  target_index: number | null
  base_status: RunStepStatus | null
  target_status: RunStepStatus | null
  status_changed: boolean
  base_check_passed: boolean | null
  target_check_passed: boolean | null
  check_changed: boolean
  base_error: string | null
  target_error: string | null
  output_changed: boolean
  output_diff: OutputDiffEntry[]
}

export interface RunDiff {
  base: RunDiffSummary
  target: RunDiffSummary
  steps: RunStepDiff[]
}

export interface ArtifactRef {
  path: string
  sha256: string
  size: number
}
