export type NodeType =
  | "start"
  | "end"
  | "input"
  | "action"
  | "pass"
  | "if"
  | "switch"
  | "for"
  | "while"
  | "retry"
  | "merge"
  | "split"
  | "group"
  | "subflow"
  | "core.log"
  | "core.set_var"
  | "core.wait"
  | "core.if"
  | "core.switch"
  | "core.loop"
  | "browser.navigate"
  | "browser.click"
  | "browser.type"
  | "browser.screenshot"
  | "browser.get_text"
  | "browser.get_attribute"
  | "browser.scroll"
  | "browser.wait_for"
  | "tool.http_request"
  | "tool.read_file"
  | "tool.write_file"
  | "tool.exec"
  | "tool.sleep"
  | "llm"
  | "python"
  | "api"
  | "condition"
  | "loop"
  | "output";

export type NodeCategory =
  | "start"
  | "end"
  | "io"
  | "basic"
  | "control"
  | "data"
  | "composite"
  | "core"
  | "browser"
  | "tool"
  | "other";

export type NodeExecutionStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "paused";

export type EdgeExecutionStatus = "pending" | "active" | "success" | "failed";

export interface InputField {
  name: string;
  type: string;
  default?: any;
  required: boolean;
}

export interface NodeConfig {
  [key: string]: any;
  inputFields?: InputField[];
  model?: string;
  prompt?: string;
  temperature?: number;
  code?: string;
  url?: string;
  method?: string;
  headers?: Record<string, string>;
  body?: any;
  condition?: string;
  forEach?: any[] | string;
  forItemVar?: string;
  outputVar?: string;
}

export interface NodeData {
  type?: NodeType;
  label: string;
  config: NodeConfig;
  executionStatus?: NodeExecutionStatus;
  error?: string;
  output?: any;
}

export interface WorkflowNode {
  id: string;
  type: NodeType;
  position: { x: number; y: number };
  data: NodeData;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
  executionStatus?: EdgeExecutionStatus;
}

export interface WorkflowState {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  selectedNodeId: string | null;
  selectedEdgeId: string | null;
  isDirty: boolean;
  name: string;
}

export interface NodeTemplate {
  type: NodeType;
  category: NodeCategory;
  label: string;
  description: string;
  icon: string;
  color: string;
}

export type ExampleCategory =
  | "tutorial"
  | "browser"
  | "data"
  | "api"
  | "control"
  | "comprehensive";

export type ExampleDifficulty = "beginner" | "intermediate" | "advanced";

export interface Example {
  id: string;
  name: string;
  description: string;
  category: ExampleCategory;
  tags: string[];
  difficulty: ExampleDifficulty;
  author: string;
  createdAt: Date;
  updatedAt: Date;
  isOfficial: boolean;
  isFavorite: boolean;
  usageCount: number;
  rating: number;
  thumbnail?: string;
  previewNodes?: WorkflowNode[];
  yamlContent: string;
}

export type OverallExecutionStatus =
  | "idle"
  | "running"
  | "paused"
  | "completed"
  | "failed"
  | "stopped";

export interface NodeExecutionState {
  status: NodeExecutionStatus;
  startTime: Date | null;
  endTime: Date | null;
  duration: number;
  output: any;
  error: ExecutionError | null;
}

export interface EdgeExecutionState {
  status: EdgeExecutionStatus;
  data: any;
}

export interface ExecutionLog {
  id: string;
  timestamp: Date;
  level: "debug" | "info" | "warn" | "error";
  nodeId: string | null;
  nodeName: string | null;
  message: string;
  data?: any;
}

export interface ExecutionError {
  id: string;
  nodeId: string;
  nodeName: string;
  message: string;
  stack?: string;
  timestamp: Date;
  type: string;
}

export interface ExecutionState {
  overall: OverallExecutionStatus;
  nodes: Record<string, NodeExecutionState>;
  edges: Record<string, EdgeExecutionState>;
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  logs: ExecutionLog[];
  variables: Record<string, any>;
  errors: ExecutionError[];
  startTime: Date | null;
  endTime: Date | null;
  duration: number;
}
