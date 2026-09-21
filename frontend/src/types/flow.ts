// @file frontend/src/types/flow.ts
// @brief Flow 与画布数据结构定义

export interface ActionSpec {
  type: string
  params?: Record<string, unknown>
}

export interface CheckSpec {
  type: string
  params?: Record<string, unknown>
}

export interface RetrySpec {
  attempts: number
  backoff_seconds: number
}

export interface StepSpec {
  id: string
  name?: string
  action: ActionSpec
  check?: CheckSpec
  retry?: RetrySpec
  output_var?: string
  for_each?: string
  for_item_var?: string
  condition?: string
  depends_on?: string[]
}

export interface HookSpec {
  on_success?: ActionSpec[]
  on_failure?: ActionSpec[]
}

export interface TriggerSpec {
  cron?: string
  webhook_enabled?: boolean
  webhook_token?: string
}

export interface FlowSpec {
  version: string
  name: string
  description?: string
  cron?: string
  trigger?: TriggerSpec
  steps: StepSpec[]
  hooks?: HookSpec
}

export type StepExecutionStatus = 'idle' | 'running' | 'success' | 'failed' | 'skipped'

export interface FlowNodeData {
  step: StepSpec
  index: number
  status: StepExecutionStatus
  duration_ms?: number
  check_passed?: boolean | null
  error?: string | null
  output?: unknown
}
