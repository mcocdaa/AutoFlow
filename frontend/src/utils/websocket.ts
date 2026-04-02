import type {
  WebSocketConnectionStatus,
  WebSocketConnectionState,
  ExecutionStatus,
  NodeExecutionState,
  ExecutionLog,
  ExecutionError,
  VariableScope,
} from "../types/dag-workflow";

export interface WebSocketEvent {
  type: string;
  data: any;
  timestamp: string;
}

export interface WebSocketMessage {
  event: string;
  payload: any;
}

export interface WebSocketConfig {
  url: string;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
}

const DEFAULT_CONFIG: WebSocketConfig = {
  url: "",
  autoReconnect: true,
  maxReconnectAttempts: 5,
  reconnectInterval: 3000,
  heartbeatInterval: 30000,
};

type EventCallback = (data: any) => void;

export class WorkflowWebSocket {
  private config: WebSocketConfig;
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private eventHandlers: Map<string, Set<EventCallback>> = new Map();
  private reconnectAttempts: number = 0;
  private isManualClose: boolean = false;
  private connectionState: WebSocketConnectionState = {
    status: "disconnected",
    reconnect_attempts: 0,
  };

  public onStatusChange?: (state: WebSocketConnectionState) => void;
  public onExecutionStatusChange?: (status: ExecutionStatus) => void;
  public onNodeStateChange?: (
    nodeId: string,
    state: Partial<NodeExecutionState>,
  ) => void;
  public onLogReceived?: (log: ExecutionLog) => void;
  public onErrorReceived?: (error: ExecutionError) => void;
  public onVariablesUpdate?: (variables: VariableScope) => void;
  public onExecutionComplete?: (
    success: boolean,
    outputs?: Record<string, any>,
  ) => void;

  constructor(config: Partial<WebSocketConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  public connect(url?: string): void {
    if (url) {
      this.config.url = url;
    }

    if (!this.config.url) {
      console.error("WebSocket URL is required");
      return;
    }

    this.isManualClose = false;
    this.updateConnectionState("connecting");
    this.tryConnect();
  }

  private tryConnect(): void {
    try {
      this.ws = new WebSocket(this.config.url);

      this.ws.onopen = () => {
        this.onOpen();
      };

      this.ws.onmessage = (event) => {
        this.onMessage(event);
      };

      this.ws.onclose = (event) => {
        this.onClose(event);
      };

      this.ws.onerror = (error) => {
        this.onError(error);
      };
    } catch (error) {
      console.error("WebSocket connection error:", error);
      this.updateConnectionState("error", `Connection error: ${error}`);
      this.scheduleReconnect();
    }
  }

  private onOpen(): void {
    console.log("WebSocket connected");
    this.reconnectAttempts = 0;
    this.updateConnectionState("connected");
    this.startHeartbeat();
    this.emit("connected", { timestamp: new Date().toISOString() });
  }

  private onMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      this.handleMessage(message);
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error);
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    const { event, payload } = message;

    switch (event) {
      case "execution_status":
        this.handleExecutionStatus(payload);
        break;
      case "node_state":
        this.handleNodeState(payload);
        break;
      case "log":
        this.handleLog(payload);
        break;
      case "error":
        this.handleError(payload);
        break;
      case "variables":
        this.handleVariables(payload);
        break;
      case "execution_complete":
        this.handleExecutionComplete(payload);
        break;
      case "pong":
        break;
      default:
        this.emit(event, payload);
    }
  }

  private handleExecutionStatus(payload: any): void {
    if (this.onExecutionStatusChange) {
      this.onExecutionStatusChange(payload.status as ExecutionStatus);
    }
    this.emit("execution_status", payload);
  }

  private handleNodeState(payload: any): void {
    const { node_id, ...state } = payload;
    if (this.onNodeStateChange) {
      this.onNodeStateChange(node_id, state);
    }
    this.emit("node_state", payload);
  }

  private handleLog(payload: any): void {
    const log: ExecutionLog = {
      ...payload,
      timestamp: new Date(payload.timestamp),
    };
    if (this.onLogReceived) {
      this.onLogReceived(log);
    }
    this.emit("log", log);
  }

  private handleError(payload: any): void {
    const error: ExecutionError = {
      ...payload,
      timestamp: new Date(payload.timestamp),
    };
    if (this.onErrorReceived) {
      this.onErrorReceived(error);
    }
    this.emit("error", error);
  }

  private handleVariables(payload: any): void {
    if (this.onVariablesUpdate) {
      this.onVariablesUpdate(payload);
    }
    this.emit("variables", payload);
  }

  private handleExecutionComplete(payload: any): void {
    if (this.onExecutionComplete) {
      this.onExecutionComplete(payload.success, payload.outputs);
    }
    this.emit("execution_complete", payload);
  }

  private onClose(event: CloseEvent): void {
    console.log("WebSocket disconnected:", event.code, event.reason);
    this.stopHeartbeat();

    if (!this.isManualClose) {
      this.updateConnectionState("disconnected");
      this.scheduleReconnect();
    } else {
      this.updateConnectionState("disconnected");
    }

    this.emit("disconnected", { code: event.code, reason: event.reason });
  }

  private onError(error: Event): void {
    console.error("WebSocket error:", error);
    this.updateConnectionState("error", "WebSocket error occurred");
    this.emit("error", error);
  }

  private scheduleReconnect(): void {
    if (!this.config.autoReconnect || this.isManualClose) {
      return;
    }

    if (this.reconnectAttempts >= this.config.maxReconnectAttempts!) {
      console.error("Max reconnect attempts reached");
      this.updateConnectionState("error", "Max reconnect attempts reached");
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      console.log(
        `Reconnecting... Attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts}`,
      );
      this.updateConnectionState("connecting");
      this.tryConnect();
    }, this.config.reconnectInterval);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send({ event: "ping", payload: { timestamp: Date.now() } });
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  public send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket is not connected. Message not sent:", message);
    }
  }

  public subscribeToExecution(executionId: string): void {
    this.send({
      event: "subscribe",
      payload: { execution_id: executionId },
    });
  }

  public unsubscribeFromExecution(executionId: string): void {
    this.send({
      event: "unsubscribe",
      payload: { execution_id: executionId },
    });
  }

  public requestStateSync(): void {
    this.send({
      event: "request_state",
      payload: {},
    });
  }

  public pauseExecution(): void {
    this.send({
      event: "pause",
      payload: {},
    });
  }

  public resumeExecution(): void {
    this.send({
      event: "resume",
      payload: {},
    });
  }

  public stopExecution(): void {
    this.send({
      event: "stop",
      payload: {},
    });
  }

  public disconnect(): void {
    this.isManualClose = true;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.reconnectAttempts = 0;
  }

  public on(event: string, callback: EventCallback): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(callback);

    return () => {
      this.off(event, callback);
    };
  }

  public off(event: string, callback: EventCallback): void {
    if (this.eventHandlers.has(event)) {
      this.eventHandlers.get(event)!.delete(callback);
      if (this.eventHandlers.get(event)!.size === 0) {
        this.eventHandlers.delete(event);
      }
    }
  }

  private emit(event: string, data: any): void {
    if (this.eventHandlers.has(event)) {
      this.eventHandlers.get(event)!.forEach((callback) => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  private updateConnectionState(
    status: WebSocketConnectionStatus,
    error?: string,
  ): void {
    this.connectionState.status = status;

    if (error) {
      this.connectionState.last_error = error;
    }

    if (status === "connecting") {
      this.connectionState.reconnect_attempts = this.reconnectAttempts;
    } else if (status === "connected") {
      this.connectionState.reconnect_attempts = 0;
      this.connectionState.last_connected_at = new Date();
    } else if (status === "disconnected") {
      this.connectionState.last_disconnected_at = new Date();
    }

    if (this.onStatusChange) {
      this.onStatusChange(this.connectionState);
    }
  }

  public getConnectionState(): WebSocketConnectionState {
    return { ...this.connectionState };
  }

  public isConnected(): boolean {
    return this.connectionState.status === "connected";
  }

  public getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }
}

let globalWebSocket: WorkflowWebSocket | null = null;

export function getWebSocket(
  config?: Partial<WebSocketConfig>,
): WorkflowWebSocket {
  if (!globalWebSocket) {
    globalWebSocket = new WorkflowWebSocket(config);
  }
  return globalWebSocket;
}

export function createWebSocket(
  config?: Partial<WebSocketConfig>,
): WorkflowWebSocket {
  return new WorkflowWebSocket(config);
}
