export interface RunStep {
  step_id: string;
  status: string;
  error?: string;
  action_output: any;
  check_passed: boolean | null;
}

export interface RunResult {
  run_id: string;
  status: string;
  duration_ms: number;
  steps: RunStep[];
}

export interface RunsState {
  currentRun: RunResult | null;
  loading: boolean;
  error: string | null;
}
