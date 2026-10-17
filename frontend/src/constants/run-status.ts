import { t } from '../i18n'
import type { RunStatus, RunStepStatus } from '../types/runs'

export const RUN_STATUS_META: Record<RunStatus, { color: string; readonly text: string }> = {
  success: {
    color: 'green',
    get text() {
      return t('status.success')
    },
  },
  failed: {
    color: 'red',
    get text() {
      return t('status.failed')
    },
  },
  running: {
    color: 'orange',
    get text() {
      return t('status.running')
    },
  },
}

export const STEP_STATUS_META: Record<RunStepStatus, { color: string; readonly text: string }> = {
  success: {
    color: 'green',
    get text() {
      return t('status.success')
    },
  },
  failed: {
    color: 'red',
    get text() {
      return t('status.failed')
    },
  },
  skipped: {
    color: 'orange',
    get text() {
      return t('status.skipped')
    },
  },
}
