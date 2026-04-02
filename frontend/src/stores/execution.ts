import { defineStore } from "pinia";
import type {
  ExecutionStatus,
  NodeExecutionState,
  NodeExecutionStatus,
  ExecutionLog,
  ExecutionError,
  Breakpoint,
  VariableWatch,
  DebugMode,
  WebSocketConnectionStatus,
  WebSocketConnectionState,
  EdgeExecutionState,
} from "../types/dag-workflow";

function generateId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export const useExecutionStore = defineStore("execution", {
  state: () => ({
    runId: null as string | null,
    workflowId: null as string | null,
    status: "idle" as ExecutionStatus,
    nodeStates: {} as Record<string, NodeExecutionState>,
    nodes: {} as Record<string, any>,
    edges: {} as Record<string, EdgeExecutionState>,
    logs: [] as ExecutionLog[],
    variables: {} as Record<string, any>,
    errors: [] as ExecutionError[],
    startTime: null as Date | null,
    endTime: null as Date | null,
    duration: 0,
    progress: { current: 0, total: 0, percentage: 0 },
    successCount: 0,
    failedCount: 0,

    breakpoints: [] as Breakpoint[],
    variableWatches: [] as VariableWatch[],
    debugMode: "idle" as DebugMode,
    currentBreakpointNodeId: null as string | null,
    callStack: [] as string[],

    websocket: {
      status: "disconnected" as WebSocketConnectionStatus,
      last_error: undefined,
      reconnect_attempts: 0,
      last_connected_at: undefined,
      last_disconnected_at: undefined,
    } as WebSocketConnectionState,
  }),

  getters: {
    isRunning: (state): boolean => state.status === "running",
    isPaused: (state): boolean => state.status === "paused",
    isCompleted: (state): boolean => state.status === "completed",
    isFailed: (state): boolean => state.status === "failed",
    isStopped: (state): boolean => state.status === "stopped",
    getNodeState:
      (state) =>
      (nodeId: string): NodeExecutionState | undefined =>
        state.nodeStates[nodeId],
    successRate: (state): number => {
      const total = state.successCount + state.failedCount;
      return total === 0 ? 0 : state.successCount / total;
    },

    isDebugMode: (state): boolean => state.debugMode !== "idle",
    hasBreakpoint:
      (state) =>
      (nodeId: string): boolean =>
        state.breakpoints.some((bp) => bp.node_id === nodeId && bp.enabled),
    getBreakpoint:
      (state) =>
      (nodeId: string): Breakpoint | undefined =>
        state.breakpoints.find((bp) => bp.node_id === nodeId),
    getVariableWatch:
      (state) =>
      (watchId: string): VariableWatch | undefined =>
        state.variableWatches.find((w) => w.id === watchId),
    isWebSocketConnected: (state): boolean =>
      state.websocket.status === "connected",
  },

  actions: {
    startExecution(options?: {
      runId?: string;
      workflowId?: string;
      nodeIds?: string[];
    }) {
      this.runId = options?.runId || null;
      this.workflowId = options?.workflowId || null;
      this.status = "running";
      this.startTime = new Date();
      this.endTime = null;
      this.duration = 0;
      this.nodeStates = {};
      this.logs = [];
      this.variables = {};
      this.errors = [];
      this.successCount = 0;
      this.failedCount = 0;
      this.debugMode = "idle";
      this.currentBreakpointNodeId = null;
      this.callStack = [];

      if (options?.nodeIds) {
        options.nodeIds.forEach((nodeId) => {
          this.nodeStates[nodeId] = {
            node_id: nodeId,
            status: "pending" as NodeExecutionStatus,
          };
        });
      }

      this.addLog({ level: "info", message: "Workflow execution started" });
    },

    cancelExecution() {
      this.status = "stopped";
      this.endTime = new Date();
      if (this.startTime) {
        this.duration = this.endTime.getTime() - this.startTime.getTime();
      }
      this.debugMode = "idle";
      this.currentBreakpointNodeId = null;
      this.callStack = [];

      this.addLog({ level: "warn", message: "Workflow execution cancelled" });
    },

    pauseExecution() {
      if (this.status === "running") {
        this.status = "paused";
        this.addLog({ level: "info", message: "Workflow execution paused" });
      }
    },

    resumeExecution() {
      if (this.status === "paused") {
        this.status = "running";
        this.debugMode = "idle";
        this.currentBreakpointNodeId = null;
        this.addLog({ level: "info", message: "Workflow execution resumed" });
      }
    },

    clearExecution() {
      this.runId = null;
      this.workflowId = null;
      this.status = "idle";
      this.nodeStates = {};
      this.logs = [];
      this.variables = {};
      this.errors = [];
      this.startTime = null;
      this.endTime = null;
      this.duration = 0;
      this.successCount = 0;
      this.failedCount = 0;
      this.debugMode = "idle";
      this.currentBreakpointNodeId = null;
      this.callStack = [];
    },

    updateNodeState(nodeId: string, state: Partial<NodeExecutionState>) {
      if (!this.nodeStates[nodeId]) {
        this.nodeStates[nodeId] = {
          node_id: nodeId,
          status: "pending",
        };
      }
      this.nodeStates[nodeId] = { ...this.nodeStates[nodeId], ...state };

      if (state.status) {
        this.handleNodeStatusChange(nodeId, state.status);
      }
    },

    handleNodeStatusChange(nodeId: string, status: NodeExecutionStatus) {
      switch (status) {
        case "failed":
          this.addLog({
            level: "error",
            message: `Node ${nodeId} failed`,
            node_id: nodeId,
          });
          this.failedCount++;
          break;
        case "completed":
          this.addLog({
            level: "info",
            message: `Node ${nodeId} completed`,
            node_id: nodeId,
          });
          this.successCount++;
          break;
        case "running":
          this.nodeStates[nodeId].started_at = new Date();
          this.addLog({
            level: "info",
            message: `Node ${nodeId} started`,
            node_id: nodeId,
          });
          break;
      }
    },

    addLog(log: Omit<ExecutionLog, "timestamp">) {
      this.logs.push({
        timestamp: new Date(),
        ...log,
      });
    },

    setVariable(key: string, value: any) {
      this.variables[key] = value;

      this.variableWatches.forEach((watch) => {
        try {
          if (watch.expression === key) {
            watch.value = value;
            watch.last_updated = new Date();
          }
        } catch (e) {
          console.error(
            `Error evaluating watch expression ${watch.expression}:`,
            e,
          );
        }
      });
    },

    addError(error: Omit<ExecutionError, "timestamp">) {
      const executionError: ExecutionError = {
        ...error,
        timestamp: new Date(),
      };
      this.errors.push(executionError);
      this.addLog({
        level: "error",
        message: error.error,
        node_id: error.node_id,
      });
    },

    completeExecution(success: boolean = true) {
      this.status = success ? "completed" : "failed";
      this.endTime = new Date();
      if (this.startTime) {
        this.duration = this.endTime.getTime() - this.startTime.getTime();
      }
      this.debugMode = "idle";
      this.currentBreakpointNodeId = null;
      this.callStack = [];

      this.addLog({
        level: success ? "info" : "error",
        message: `Workflow execution ${success ? "completed" : "failed"} in ${this.duration}ms`,
      });
    },

    resetExecution() {
      this.clearExecution();
    },

    stopExecution() {
      this.cancelExecution();
    },

    retryNode(nodeId: string) {
      this.updateNodeState(nodeId, { status: "pending", error: undefined });
    },

    skipNode(nodeId: string) {
      this.updateNodeState(nodeId, { status: "skipped" });
    },

    activateEdge(edgeId: string) {
      this.edges[edgeId] = {
        status: "active",
        started_at: new Date(),
      };
    },

    startNode(nodeId: string, nodeName?: string) {
      this.updateNodeState(nodeId, { status: "running", node_name: nodeName });
    },

    completeNode(nodeId: string, nodeName?: string, result?: any) {
      this.updateNodeState(nodeId, {
        status: "completed",
        node_name: nodeName,
        result,
      });
      if (result) {
        this.setVariable(`${nodeId}_result`, result);
      }
    },

    completeEdge(edgeId: string, success: boolean = true) {
      if (this.edges[edgeId]) {
        this.edges[edgeId].status = success ? "success" : "failed";
        this.edges[edgeId].completed_at = new Date();
      }
    },

    addBreakpoint(nodeId: string, condition?: string): Breakpoint {
      const breakpoint: Breakpoint = {
        id: generateId("bp"),
        node_id: nodeId,
        enabled: true,
        condition,
      };
      this.breakpoints.push(breakpoint);
      this.addLog({
        level: "debug",
        message: `Breakpoint added for node ${nodeId}`,
        node_id: nodeId,
      });
      return breakpoint;
    },

    removeBreakpoint(breakpointId: string) {
      const index = this.breakpoints.findIndex((bp) => bp.id === breakpointId);
      if (index !== -1) {
        const bp = this.breakpoints[index];
        this.breakpoints.splice(index, 1);
        this.addLog({
          level: "debug",
          message: `Breakpoint removed for node ${bp.node_id}`,
          node_id: bp.node_id,
        });
      }
    },

    removeBreakpointByNodeId(nodeId: string) {
      const index = this.breakpoints.findIndex((bp) => bp.node_id === nodeId);
      if (index !== -1) {
        const bp = this.breakpoints[index];
        this.breakpoints.splice(index, 1);
        this.addLog({
          level: "debug",
          message: `Breakpoint removed for node ${bp.node_id}`,
          node_id: bp.node_id,
        });
      }
    },

    toggleBreakpoint(breakpointId: string) {
      const breakpoint = this.breakpoints.find((bp) => bp.id === breakpointId);
      if (breakpoint) {
        breakpoint.enabled = !breakpoint.enabled;
        this.addLog({
          level: "debug",
          message: `Breakpoint ${breakpoint.enabled ? "enabled" : "disabled"} for node ${breakpoint.node_id}`,
          node_id: breakpoint.node_id,
        });
      }
    },

    updateBreakpointCondition(breakpointId: string, condition?: string) {
      const breakpoint = this.breakpoints.find((bp) => bp.id === breakpointId);
      if (breakpoint) {
        breakpoint.condition = condition;
        this.addLog({
          level: "debug",
          message: `Breakpoint condition updated for node ${breakpoint.node_id}`,
          node_id: breakpoint.node_id,
        });
      }
    },

    clearAllBreakpoints() {
      this.breakpoints = [];
      this.addLog({ level: "debug", message: "All breakpoints cleared" });
    },

    addVariableWatch(name: string, expression: string): VariableWatch {
      const watch: VariableWatch = {
        id: generateId("vw"),
        name,
        expression,
      };
      this.variableWatches.push(watch);
      this.evaluateVariableWatch(watch.id);
      return watch;
    },

    removeVariableWatch(watchId: string) {
      const index = this.variableWatches.findIndex((w) => w.id === watchId);
      if (index !== -1) {
        this.variableWatches.splice(index, 1);
      }
    },

    updateVariableWatch(watchId: string, name?: string, expression?: string) {
      const watch = this.variableWatches.find((w) => w.id === watchId);
      if (watch) {
        if (name) watch.name = name;
        if (expression) watch.expression = expression;
        this.evaluateVariableWatch(watchId);
      }
    },

    evaluateVariableWatch(watchId: string) {
      const watch = this.variableWatches.find((w) => w.id === watchId);
      if (watch) {
        try {
          watch.value = this.variables[watch.expression];
          watch.last_updated = new Date();
        } catch (e) {
          console.error(
            `Error evaluating watch expression ${watch.expression}:`,
            e,
          );
          watch.value = undefined;
        }
      }
    },

    evaluateAllVariableWatches() {
      this.variableWatches.forEach((watch) => {
        this.evaluateVariableWatch(watch.id);
      });
    },

    clearAllVariableWatches() {
      this.variableWatches = [];
    },

    setDebugMode(mode: DebugMode) {
      this.debugMode = mode;
    },

    triggerBreakpoint(nodeId: string) {
      this.status = "paused";
      this.debugMode = "breakpoint";
      this.currentBreakpointNodeId = nodeId;
      this.callStack.push(nodeId);
      this.addLog({
        level: "info",
        message: `Execution paused at breakpoint in node ${nodeId}`,
        node_id: nodeId,
      });
    },

    stepOver() {
      if (this.debugMode === "breakpoint") {
        this.debugMode = "stepping";
        this.addLog({ level: "debug", message: "Stepping over" });
      }
    },

    stepInto() {
      if (this.debugMode === "breakpoint") {
        this.debugMode = "stepping";
        this.addLog({ level: "debug", message: "Stepping into" });
      }
    },

    stepOut() {
      if (this.callStack.length > 0) {
        this.callStack.pop();
        if (this.callStack.length === 0) {
          this.resumeExecution();
        }
      }
    },

    continueExecution() {
      this.resumeExecution();
    },

    updateWebSocketStatus(status: WebSocketConnectionStatus, error?: string) {
      const previousStatus = this.websocket.status;
      this.websocket.status = status;

      if (error) {
        this.websocket.last_error = error;
      }

      if (status === "connected") {
        this.websocket.last_connected_at = new Date();
        this.websocket.reconnect_attempts = 0;
      } else if (status === "disconnected" && previousStatus === "connected") {
        this.websocket.last_disconnected_at = new Date();
      } else if (status === "connecting") {
        this.websocket.reconnect_attempts++;
      }
    },

    resetWebSocketState() {
      this.websocket = {
        status: "disconnected",
        last_error: undefined,
        reconnect_attempts: 0,
        last_connected_at: undefined,
        last_disconnected_at: undefined,
      };
    },

    clearLogs() {
      this.logs = [];
    },
  },
});
