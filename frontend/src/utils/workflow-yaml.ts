import jsYAML from "js-yaml";
import type {
  WorkflowNode,
  WorkflowEdge,
  NodeType,
  NodeData,
} from "../types/workflow";

const YAML_VERSION = "1.0";
const DEFAULT_WORKFLOW_NAME = "Untitled Workflow";
const START_NODE_TYPE = "start";
const END_NODE_TYPE = "end";
const NODE_POSITION_OFFSET_X = 250;
const NODE_POSITION_START_X = 100;
const NODE_POSITION_Y = 200;

export interface FlowYAML {
  version: string;
  name: string;
  steps: FlowStep[];
  hooks?: unknown;
}

export interface FlowStep {
  id: string;
  name?: string;
  action: {
    type: string;
    params: Record<string, unknown>;
  };
  check?: unknown;
  retry?: unknown;
  output_var?: string;
  for_each?: string;
  for_item_var?: string;
  condition?: string;
}

interface NodeTypeConfig {
  actionType: string;
  defaultLabel: string;
  getParams: (config: Record<string, unknown>) => Record<string, unknown>;
  outputVar?: boolean;
}

const NODE_TYPE_CONFIGS: Record<string, NodeTypeConfig> = {
  llm: {
    actionType: "ai_deepseek.chat",
    defaultLabel: "LLM Call",
    getParams: (config) => ({
      prompt: config.prompt || "",
      model: config.model || "deepseek-chat",
      temperature: config.temperature ?? 0.7,
    }),
    outputVar: true,
  },
  python: {
    actionType: "dummy.python_exec",
    defaultLabel: "Python Script",
    getParams: (config) => ({
      code: config.code || "",
    }),
    outputVar: true,
  },
  api: {
    actionType: "dummy.http_request",
    defaultLabel: "API Call",
    getParams: (config) => ({
      url: config.url || "",
      method: config.method || "GET",
      headers: config.headers || {},
      body: config.body || "",
    }),
    outputVar: true,
  },
  condition: {
    actionType: "dummy.noop",
    defaultLabel: "Condition",
    getParams: () => ({}),
  },
  loop: {
    actionType: "dummy.noop",
    defaultLabel: "Loop",
    getParams: () => ({}),
  },
  "core.log": {
    actionType: "core.log",
    defaultLabel: "Log",
    getParams: (config) => ({
      message: config.message || "",
    }),
  },
  "core.set_var": {
    actionType: "core.set_var",
    defaultLabel: "Set Variable",
    getParams: (config) => ({
      name: config.name || "",
      value: config.value || "",
    }),
  },
  "core.wait": {
    actionType: "core.wait",
    defaultLabel: "Wait",
    getParams: (config) => ({
      seconds: config.seconds || 1,
    }),
  },
  output: {
    actionType: "dummy.noop",
    defaultLabel: "Output",
    getParams: () => ({}),
  },
};

const NODE_TYPE_MAPPINGS: Record<string, NodeType> = {
  "core.log": "core.log",
  "core.set_var": "core.set_var",
  "core.wait": "core.wait",
  "browser.navigate": "browser.navigate",
  "browser.click": "browser.click",
  "browser.type": "browser.type",
  "browser.screenshot": "browser.screenshot",
  "browser.get_text": "browser.get_text",
  "browser.get_attribute": "browser.get_attribute",
  "browser.scroll": "browser.scroll",
  "browser.wait_for": "browser.wait_for",
  "tool.http_request": "tool.http_request",
  "tool.read_file": "tool.read_file",
  "tool.write_file": "tool.write_file",
  "tool.exec": "tool.exec",
  "tool.sleep": "tool.sleep",
};

function buildTopologicalOrder(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
): string[] {
  const inDegree = new Map(nodes.map((n) => [n.id, 0]));
  const adjacency = new Map(nodes.map((n) => [n.id, [] as string[]]));

  for (const edge of edges) {
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
    adjacency.get(edge.source)?.push(edge.target);
  }

  const order: string[] = [];
  const queue = [...inDegree.entries()]
    .filter(([_, degree]) => degree === 0)
    .map(([id]) => id);

  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    order.push(nodeId);
    for (const next of adjacency.get(nodeId) || []) {
      inDegree.set(next, inDegree.get(next)! - 1);
      if (inDegree.get(next) === 0) {
        queue.push(next);
      }
    }
  }

  return order;
}

function nodeToStep(node: WorkflowNode): FlowStep {
  const config = node.data.config || {};
  const nodeType = node.type;
  const configEntry = NODE_TYPE_CONFIGS[nodeType];

  if (configEntry) {
    const step: FlowStep = {
      id: node.id,
      name: node.data.label || configEntry.defaultLabel,
      action: {
        type: configEntry.actionType,
        params: configEntry.getParams(config),
      },
    };

    if (configEntry.outputVar) {
      step.output_var = `${node.id}_output`;
    }

    if (nodeType === "condition") {
      step.condition = config.condition || "";
    } else if (nodeType === "loop") {
      step.for_each = config.forEach ? String(config.forEach) : "";
      step.for_item_var = config.forItemVar || "item";
    }

    return step;
  }

  return {
    id: node.id,
    name: node.data.label || "Start",
    action: {
      type: "dummy.noop",
      params: {},
    },
  };
}

function determineNodeType(step: FlowStep): NodeType {
  const actionType = step.action.type;

  if (NODE_TYPE_MAPPINGS[actionType]) {
    return NODE_TYPE_MAPPINGS[actionType];
  }

  if (
    actionType.includes("llm") ||
    actionType.includes("chat") ||
    actionType.includes("ai_")
  ) {
    return "llm";
  }

  if (actionType.includes("http") || actionType.includes("api")) {
    return "api";
  }

  if (step.condition) {
    return "condition";
  }

  if (step.for_each) {
    return "loop";
  }

  return "python";
}

function buildNodeData(step: FlowStep, nodeType: NodeType): NodeData {
  const config: Record<string, unknown> = {};
  const params = step.action.params;

  switch (nodeType) {
    case "python":
      config.code = `# ${step.name || step.id}\n# Action: ${step.action.type}\n\nprint(${JSON.stringify(params)})`;
      break;
    case "llm":
      config.model = params.model || "deepseek-chat";
      config.prompt = params.prompt || "";
      config.temperature = params.temperature ?? 0.7;
      break;
    case "api":
      config.url = params.url || "";
      config.method = params.method || "GET";
      config.headers = params.headers || {};
      config.body = params.body || "";
      break;
    case "condition":
      config.condition = step.condition || "";
      break;
    case "loop":
      config.forEach = step.for_each || "";
      config.forItemVar = step.for_item_var || "item";
      break;
    case "core.log":
      config.message = params.message || "";
      break;
    case "core.set_var":
      config.name = params.name || "";
      config.value = params.value || "";
      break;
    case "core.wait":
      config.seconds = params.seconds || 1;
      break;
  }

  return {
    type: nodeType,
    label: step.name || step.id,
    config,
  };
}

function buildNodesAndEdges(parsed: FlowYAML): {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
} {
  const nodes: WorkflowNode[] = [];
  const edges: WorkflowEdge[] = [];
  const stepCount = parsed.steps.length;

  nodes.push({
    id: "start",
    type: START_NODE_TYPE,
    position: { x: NODE_POSITION_START_X, y: NODE_POSITION_Y },
    data: {
      type: START_NODE_TYPE,
      label: "Start",
      config: {},
    },
  });

  parsed.steps.forEach((step, index) => {
    const nodeType = determineNodeType(step);
    nodes.push({
      id: step.id,
      type: nodeType,
      position: {
        x: NODE_POSITION_START_X + (index + 1) * NODE_POSITION_OFFSET_X,
        y: NODE_POSITION_Y,
      },
      data: buildNodeData(step, nodeType),
    });
  });

  const endNodeX = NODE_POSITION_START_X + (stepCount + 1) * NODE_POSITION_OFFSET_X;
  nodes.push({
    id: "end",
    type: END_NODE_TYPE,
    position: { x: endNodeX, y: NODE_POSITION_Y },
    data: {
      type: END_NODE_TYPE,
      label: "End",
      config: {},
    },
  });

  if (stepCount > 0) {
    edges.push({
      id: "edge-start-" + parsed.steps[0].id,
      source: "start",
      target: parsed.steps[0].id,
      animated: true,
    });

    parsed.steps.forEach((step, index) => {
      if (index < stepCount - 1) {
        edges.push({
          id: `edge-${step.id}-${parsed.steps[index + 1].id}`,
          source: step.id,
          target: parsed.steps[index + 1].id,
          animated: true,
        });
      }
    });

    edges.push({
      id: "edge-" + parsed.steps[stepCount - 1].id + "-end",
      source: parsed.steps[stepCount - 1].id,
      target: "end",
      animated: true,
    });
  } else {
    edges.push({
      id: "edge-start-end",
      source: "start",
      target: "end",
      animated: true,
    });
  }

  return { nodes, edges };
}

export function workflowToYAML(
  name: string,
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
): string {
  const order = buildTopologicalOrder(nodes, edges);
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  const steps: FlowStep[] = order
    .filter((nodeId) => {
      const node = nodeMap.get(nodeId);
      return node && node.type !== START_NODE_TYPE && node.type !== END_NODE_TYPE;
    })
    .map((nodeId) => nodeToStep(nodeMap.get(nodeId)!));

  const yamlObj: FlowYAML = {
    version: YAML_VERSION,
    name,
    steps,
  };

  return jsYAML.dump(yamlObj);
}

export function yamlToWorkflow(yaml: string): {
  name: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
} {
  const parsed = jsYAML.load(yaml) as FlowYAML;
  const { nodes, edges } = buildNodesAndEdges(parsed);

  return {
    name: parsed.name || DEFAULT_WORKFLOW_NAME,
    nodes,
    edges,
  };
}
