import type { RunStatus, RunStepStatus } from '../types/runs'

export const RUN_STATUS_META: Record<RunStatus, { color: string; text: string }> = {
  success: { color: 'green', text: '成功' },
  failed: { color: 'red', text: '失败' },
  running: { color: 'orange', text: '运行中' },
}

export const STEP_STATUS_META: Record<RunStepStatus, { color: string; text: string }> = {
  success: { color: 'green', text: '成功' },
  failed: { color: 'red', text: '失败' },
  skipped: { color: 'orange', text: '跳过' },
}
