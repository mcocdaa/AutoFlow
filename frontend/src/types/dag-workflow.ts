export type PortDataType =
  | "any"
  | "string"
  | "number"
  | "boolean"
  | "object"
  | "array";

export interface Port {
  id: string;
  name: string;
  type: PortDataType;
}

export interface InputPort extends Port {
  required: boolean;
  default?: any;
}

export interface OutputPort extends Port {
  condition?: string | null;
  case?: any;
  index?: number;
  field?: string;
}

export interface RetrySpec {
  attempts: number;
  backoff_seconds: number;
}

export interface InputMapping {
  external_port_id: string;
  internal_node_id: string;
  internal_port_id: string;
}

export interface OutputMapping {
  external_port_id: string;
  internal_node_id: string;
  internal_port_id: string;
}

export interface InternalSubgraph {
  nodes: Record<string, BaseNodeData>;
  edges: EdgeData[];
}

export interface GroupConfig {
  internal_subgraph: InternalSubgraph;
  input_mappings: InputMapping[];
  output_mappings: OutputMapping[];
}

export interface SubflowConfig {
  subflow_id: string;
  subflow_version?: string;
  input_mappings: InputMapping[];
  output_mappings: OutputMapping[];
}

export interface BaseNodeData {
  id: string;
  name: string;
  type: string;
  retry?: RetrySpec;
  config: Record<string, any>;
  metadata: Record<string, any>;
  inputs: InputPort[];
  outputs: OutputPort[];
  error_port?: OutputPort;
}

export interface StartNodeData extends BaseNodeData {
  type: "start";
}

export interface EndNodeData extends BaseNodeData {
  type: "end";
}

export interface ActionNodeData extends BaseNodeData {
  type: "action";
  config: {
    action_type: string;
    [key: string]: any;
  };
}

export interface PassNodeData extends BaseNodeData {
  type: "pass";
  config: {
    transform?: string;
  };
}

export interface IfNodeData extends BaseNodeData {
  type: "if";
  config: {
    condition: string;
  };
}

export interface SwitchNodeData extends BaseNodeData {
  type: "switch";
  config: {
    cases: Array<{
      value: any;
      label: string;
    }>;
    has_default: boolean;
  };
}

export interface ForNodeData extends BaseNodeData {
  type: "for";
  config: {
    iterable_source: string;
  };
}

export interface WhileNodeData extends BaseNodeData {
  type: "while";
  config: {
    condition: string;
  };
}

export interface RetryNodeData extends BaseNodeData {
  type: "retry";
  config: {
    max_attempts: number;
    backoff_seconds: number;
  };
}

export interface MergeNodeData extends BaseNodeData {
  type: "merge";
  config: {
    strategy: "list_concat" | "object_merge" | "custom";
    custom_strategy?: string;
  };
}

export interface SplitNodeData extends BaseNodeData {
  type: "split";
  config: {
    strategy: "by_index" | "by_field" | "custom";
    custom_strategy?: string;
  };
}

export interface GroupNodeData extends BaseNodeData {
  type: "group";
  config: {
    group_config: GroupConfig;
  };
}

export interface SubflowNodeData extends BaseNodeData {
  type: "subflow";
  config: {
    subflow_config: SubflowConfig;
  };
}

export type NodeData =
  | StartNodeData
  | EndNodeData
  | ActionNodeData
  | PassNodeData
  | IfNodeData
  | SwitchNodeData
  | ForNodeData
  | WhileNodeData
  | RetryNodeData
  | MergeNodeData
  | SplitNodeData
  | GroupNodeData
  | SubflowNodeData;

export interface EdgeData {
  id: string;
  source: string;
  target: string;
}

export interface MessageMetadata {
  timestamp: string;
  source_node: string;
  source_port: string;
}

export interface Message {
  success: boolean;
  data?: any;
  error?: string | null;
  metadata: MessageMetadata;
}

export interface DAGWorkflow {
  version: string;
  name: string;
  description?: string;
  inputs: Record<string, any>;
  nodes: Record<string, NodeData>;
  edges: EdgeData[];
}

export type NodeExecutionStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export interface NodeExecutionState {
  node_id: string;
  status: NodeExecutionStatus;
  started_at?: Date;
  completed_at?: Date;
  error?: string;
  outputs?: Record<string, any>;
  node_name?: string;
  result?: any;
}

export interface EdgeExecutionState {
  status: "pending" | "active" | "success" | "failed";
  started_at?: Date;
  completed_at?: Date;
}

export interface ExecutionLog {
  timestamp: Date;
  level: "info" | "warn" | "error" | "debug";
  message: string;
  node_id?: string;
  nodeName?: string;
  id?: string;
}

export interface ExecutionError {
  node_id?: string;
  error: string;
  timestamp: Date;
}

export type ExecutionStatus =
  | "idle"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "stopped";

export interface VariableScope {
  variables: Record<string, any>;
  parent?: VariableScope;
}

export interface ExecutionHistoryEntry {
  id: string;
  execution_id: string;
  workflow_id?: string;
  started_at: Date;
  completed_at?: Date;
  status: ExecutionStatus;
  node_states: Record<string, NodeExecutionState>;
  error?: ExecutionError;
  logs: ExecutionLog[];
  inputs: Record<string, any>;
  outputs?: Record<string, any>;
}

export interface WorkflowExecutionState {
  id: string;
  status: ExecutionStatus;
  started_at?: Date;
  completed_at?: Date;
  node_states: Record<string, NodeExecutionState>;
  logs: ExecutionLog[];
  variables: VariableScope;
  error?: ExecutionError;
  inputs: Record<string, any>;
  outputs?: Record<string, any>;
}

export interface WorkflowState {
  nodes: Record<string, NodeData>;
  edges: EdgeData[];
  timestamp: Date;
}

export interface Breakpoint {
  node_id: string;
  enabled: boolean;
  condition?: string;
  id: string;
}

export interface VariableWatch {
  id: string;
  name: string;
  expression: string;
  value?: any;
  last_updated?: Date;
}

export type DebugMode = "idle" | "stepping" | "breakpoint";

export type WebSocketConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

export interface WebSocketConnectionState {
  status: WebSocketConnectionStatus;
  last_error?: string;
  reconnect_attempts: number;
  last_connected_at?: Date;
  last_disconnected_at?: Date;
}
