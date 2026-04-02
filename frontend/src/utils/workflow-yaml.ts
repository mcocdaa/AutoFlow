import jsYAML from "js-yaml";
import type {
  WorkflowNode,
  WorkflowEdge,
  NodeType,
  NodeData,
} from "../types/workflow";

export interface FlowYAML {
  version: string;
  name: string;
  steps: FlowStep[];
  hooks?: any;
}

export interface FlowStep {
  id: string;
  name?: string;
  action: {
    type: string;
    params: Record<string, any>;
  };
  check?: any;
  retry?: any;
  output_var?: string;
  for_each?: string;
  for_item_var?: string;
  condition?: string;
}

export function workflowToYAML(
  name: string,
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
): string {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const inDegree = new Map(nodes.map((n) => [n.id, 0]));
  const adjacency = new Map(nodes.map((n) => [n.id, [] as string[]]));

  for (const edge of edges) {
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
    adjacency.get(edge.source)?.push(edge.target);
  }

  const order: string[] = [];
  const queue = [...inDegree.entries()]
    .filter(([_, d]) => d === 0)
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

  const steps: FlowStep[] = order
    .filter((nodeId) => {
      const node = nodeMap.get(nodeId);
      return node && node.type !== "start" && node.type !== "end";
    })
    .map((nodeId) => {
      const node = nodeMap.get(nodeId)!;
      return nodeToStep(node);
    });

  const yamlObj: FlowYAML = {
    version: "1.0",
    name,
    steps,
  };

  return jsYAML.dump(yamlObj);
}

function nodeToStep(node: WorkflowNode): FlowStep {
  const config = node.data.config || {};

  switch (node.type) {
    case "llm":
      return {
        id: node.id,
        name: node.data.label || "LLM Call",
        action: {
          type: "ai_deepseek.chat",
          params: {
            prompt: config.prompt || "",
            model: config.model || "deepseek-chat",
            temperature: config.temperature ?? 0.7,
          },
        },
        output_var: `${node.id}_output`,
      };

    case "python":
      return {
        id: node.id,
        name: node.data.label || "Python Script",
        action: {
          type: "dummy.python_exec",
          params: {
            code: config.code || "",
          },
        },
        output_var: `${node.id}_output`,
      };

    case "api":
      return {
        id: node.id,
        name: node.data.label || "API Call",
        action: {
          type: "dummy.http_request",
          params: {
            url: config.url || "",
            method: config.method || "GET",
            headers: config.headers || {},
            body: config.body || "",
          },
        },
        output_var: `${node.id}_output`,
      };

    case "condition":
      return {
        id: node.id,
        name: node.data.label || "Condition",
        action: {
          type: "dummy.noop",
          params: {},
        },
        condition: config.condition || "",
      };

    case "loop":
      return {
        id: node.id,
        name: node.data.label || "Loop",
        action: {
          type: "dummy.noop",
          params: {},
        },
        for_each: config.forEach ? String(config.forEach) : "",
        for_item_var: config.forItemVar || "item",
      };

    case "core.log":
      return {
        id: node.id,
        name: node.data.label || "Log",
        action: {
          type: "core.log",
          params: {
            message: config.message || "",
          },
        },
      };

    case "core.set_var":
      return {
        id: node.id,
        name: node.data.label || "Set Variable",
        action: {
          type: "core.set_var",
          params: {
            name: config.name || "",
            value: config.value || "",
          },
        },
      };

    case "core.wait":
      return {
        id: node.id,
        name: node.data.label || "Wait",
        action: {
          type: "core.wait",
          params: {
            seconds: config.seconds || 1,
          },
        },
      };

    case "output":
      return {
        id: node.id,
        name: node.data.label || "Output",
        action: {
          type: "dummy.noop",
          params: {},
        },
      };

    case "start":
    case "end":
    default:
      return {
        id: node.id,
        name: node.data.label || "Start",
        action: {
          type: "dummy.noop",
          params: {},
        },
      };
  }
}

export function yamlToWorkflow(yaml: string): {
  name: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
} {
  const parsed = jsYAML.load(yaml) as FlowYAML;

  const nodes: WorkflowNode[] = [];
  const edges: WorkflowEdge[] = [];

  // 1. 添加 Start 节点
  nodes.push({
    id: "start",
    type: "start",
    position: { x: 100, y: 200 },
    data: {
      type: "start",
      label: "Start",
      config: {},
    },
  });

  // 2. 根据步骤创建中间节点
  parsed.steps.forEach((step, index) => {
    // 确定节点类型
    let nodeType: NodeType = "python"; // 默认类型

    if (step.action.type === "core.log") {
      nodeType = "core.log";
    } else if (step.action.type === "core.set_var") {
      nodeType = "core.set_var";
    } else if (step.action.type === "core.wait") {
      nodeType = "core.wait";
    } else if (step.action.type.includes("browser.navigate")) {
      nodeType = "browser.navigate";
    } else if (step.action.type.includes("browser.click")) {
      nodeType = "browser.click";
    } else if (step.action.type.includes("browser.type")) {
      nodeType = "browser.type";
    } else if (step.action.type.includes("browser.screenshot")) {
      nodeType = "browser.screenshot";
    } else if (step.action.type.includes("browser.get_text")) {
      nodeType = "browser.get_text";
    } else if (step.action.type.includes("browser.get_attribute")) {
      nodeType = "browser.get_attribute";
    } else if (step.action.type.includes("browser.scroll")) {
      nodeType = "browser.scroll";
    } else if (step.action.type.includes("browser.wait_for")) {
      nodeType = "browser.wait_for";
    } else if (step.action.type.includes("tool.http_request")) {
      nodeType = "tool.http_request";
    } else if (step.action.type.includes("tool.read_file")) {
      nodeType = "tool.read_file";
    } else if (step.action.type.includes("tool.write_file")) {
      nodeType = "tool.write_file";
    } else if (step.action.type.includes("tool.exec")) {
      nodeType = "tool.exec";
    } else if (step.action.type.includes("tool.sleep")) {
      nodeType = "tool.sleep";
    } else if (
      step.action.type.includes("llm") ||
      step.action.type.includes("chat") ||
      step.action.type.includes("ai_")
    ) {
      nodeType = "llm";
    } else if (
      step.action.type.includes("http") ||
      step.action.type.includes("api")
    ) {
      nodeType = "api";
    } else if (step.condition) {
      nodeType = "condition";
    } else if (step.for_each) {
      nodeType = "loop";
    }

    // 创建节点数据
    const nodeData: NodeData = {
      type: nodeType,
      label: step.name || step.id,
      config: {
        // 根据节点类型设置配置
        ...(nodeType === "python" && {
          code: `# ${step.name || step.id}\n# Action: ${step.action.type}\n\nprint(${JSON.stringify(step.action.params)})`,
        }),
        ...(nodeType === "llm" && {
          model: step.action.params.model || "deepseek-chat",
          prompt: step.action.params.prompt || "",
          temperature: step.action.params.temperature ?? 0.7,
        }),
        ...(nodeType === "api" && {
          url: step.action.params.url || "",
          method: step.action.params.method || "GET",
          headers: step.action.params.headers || {},
          body: step.action.params.body || "",
        }),
        ...(nodeType === "condition" && {
          condition: step.condition || "",
        }),
        ...(nodeType === "loop" && {
          forEach: step.for_each || "",
          forItemVar: step.for_item_var || "item",
        }),
        // 核心节点配置
        ...(nodeType === "core.log" && {
          message: step.action.params.message || "",
        }),
        ...(nodeType === "core.set_var" && {
          name: step.action.params.name || "",
          value: step.action.params.value || "",
        }),
        ...(nodeType === "core.wait" && {
          seconds: step.action.params.seconds || 1,
        }),
      },
    };

    // 计算节点位置（横向排列，从 start 后面开始）
    const position = {
      x: 100 + (index + 1) * 250,
      y: 200,
    };

    nodes.push({
      id: step.id,
      type: nodeType,
      position,
      data: nodeData,
    });
  });

  // 3. 添加 End 节点
  const endNodeX = 100 + (parsed.steps.length + 1) * 250;
  nodes.push({
    id: "end",
    type: "end",
    position: { x: endNodeX, y: 200 },
    data: {
      type: "end",
      label: "End",
      config: {},
    },
  });

  // 4. 创建连线
  // start -> 第一个节点
  if (parsed.steps.length > 0) {
    edges.push({
      id: "edge-start-" + parsed.steps[0].id,
      source: "start",
      target: parsed.steps[0].id,
      animated: true,
    });
  }

  // 中间节点之间的连线
  parsed.steps.forEach((step, index) => {
    if (index < parsed.steps.length - 1) {
      edges.push({
        id: `edge-${step.id}-${parsed.steps[index + 1].id}`,
        source: step.id,
        target: parsed.steps[index + 1].id,
        animated: true,
      });
    }
  });

  // 最后一个节点 -> end
  if (parsed.steps.length > 0) {
    edges.push({
      id: "edge-" + parsed.steps[parsed.steps.length - 1].id + "-end",
      source: parsed.steps[parsed.steps.length - 1].id,
      target: "end",
      animated: true,
    });
  }

  // 如果没有步骤，直接连接 start -> end
  if (parsed.steps.length === 0) {
    edges.push({
      id: "edge-start-end",
      source: "start",
      target: "end",
      animated: true,
    });
  }

  return {
    name: parsed.name || "Untitled Workflow",
    nodes,
    edges,
  };
}
