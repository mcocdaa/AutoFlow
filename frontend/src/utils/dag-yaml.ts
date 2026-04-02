import jsYAML from "js-yaml";
import type {
  DAGWorkflow,
  BaseNodeData,
  NodeData,
  EdgeData,
  InputPort,
  OutputPort,
} from "../types/dag-workflow";

export interface DAGYAML {
  version: string;
  name: string;
  description?: string;
  inputs?: Record<string, any>;
  nodes: Record<string, NodeYAML>;
  edges: EdgeYAML[];
}

export interface NodeYAML {
  type: string;
  name: string;
  retry?: {
    attempts?: number;
    backoff_seconds?: number;
  };
  config?: Record<string, any>;
  inputs?: InputPort[];
  outputs?: OutputPort[];
  metadata?: Record<string, any>;
  inner_nodes?: Record<string, NodeYAML>;
  inner_edges?: EdgeYAML[];
  port_mapping?: {
    inputs?: Array<{
      external_port_id: string;
      internal_node_id: string;
      internal_port_id: string;
    }>;
    outputs?: Array<{
      external_port_id: string;
      internal_node_id: string;
      internal_port_id: string;
    }>;
  };
  subflow_id?: string;
  subflow_version?: string;
}

export interface EdgeYAML {
  id?: string;
  source: string;
  target: string;
}

export const SUPPORTED_VERSION = "2.0";

export class DAGYAMLLoaderError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DAGYAMLLoaderError";
  }
}

export function dagToYAML(workflow: DAGWorkflow): string {
  const yamlData: DAGYAML = {
    version: SUPPORTED_VERSION,
    name: workflow.name,
    description: workflow.description,
    inputs: workflow.inputs,
    nodes: {},
    edges: [],
  };

  for (const [nodeId, nodeData] of Object.entries(workflow.nodes)) {
    yamlData.nodes[nodeId] = nodeToYAML(nodeData);
  }

  for (const edge of workflow.edges) {
    yamlData.edges.push({
      id: edge.id,
      source: edge.source,
      target: edge.target,
    });
  }

  return jsYAML.dump(yamlData, {
    sortKeys: false,
    indent: 2,
  });
}

function nodeToYAML(node: BaseNodeData): NodeYAML {
  const yamlNode: NodeYAML = {
    type: node.type,
    name: node.name,
  };

  if (
    node.retry &&
    (node.retry.attempts > 0 || node.retry.backoff_seconds > 0)
  ) {
    yamlNode.retry = {
      attempts: node.retry.attempts,
      backoff_seconds: node.retry.backoff_seconds,
    };
  }

  if (node.config && Object.keys(node.config).length > 0) {
    yamlNode.config = node.config;
  }

  if (node.inputs && node.inputs.length > 0) {
    yamlNode.inputs = node.inputs;
  }

  if (node.outputs && node.outputs.length > 0) {
    yamlNode.outputs = node.outputs;
  }

  if (node.metadata && Object.keys(node.metadata).length > 0) {
    yamlNode.metadata = node.metadata;
  }

  if (node.type === "group" || node.type === "subflow") {
    const config = node.config as any;
    if (node.type === "group" && config?.group_config) {
      const groupConfig = config.group_config;
      if (groupConfig.internal_subgraph?.nodes) {
        yamlNode.inner_nodes = {};
        for (const [innerNodeId, innerNode] of Object.entries(
          groupConfig.internal_subgraph.nodes as Record<string, BaseNodeData>,
        )) {
          yamlNode.inner_nodes[innerNodeId] = nodeToYAML(innerNode);
        }
      }
      if (groupConfig.internal_subgraph?.edges) {
        yamlNode.inner_edges = (
          groupConfig.internal_subgraph.edges as EdgeData[]
        ).map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
        }));
      }
      if (groupConfig.input_mappings || groupConfig.output_mappings) {
        yamlNode.port_mapping = {
          inputs: groupConfig.input_mappings,
          outputs: groupConfig.output_mappings,
        };
      }
    } else if (node.type === "subflow" && config?.subflow_config) {
      const subflowConfig = config.subflow_config;
      yamlNode.subflow_id = subflowConfig.subflow_id;
      if (subflowConfig.subflow_version) {
        yamlNode.subflow_version = subflowConfig.subflow_version;
      }
      if (subflowConfig.input_mappings || subflowConfig.output_mappings) {
        yamlNode.port_mapping = {
          inputs: subflowConfig.input_mappings,
          outputs: subflowConfig.output_mappings,
        };
      }
    }
  }

  return yamlNode;
}

export function yamlToDAG(yamlStr: string): DAGWorkflow {
  let parsed: DAGYAML;
  try {
    parsed = jsYAML.load(yamlStr) as DAGYAML;
  } catch (e) {
    throw new DAGYAMLLoaderError(`YAML parse error: ${e}`);
  }

  if (!parsed.version) {
    throw new DAGYAMLLoaderError("Missing required field: version");
  }
  if (parsed.version !== SUPPORTED_VERSION) {
    throw new DAGYAMLLoaderError(
      `Unsupported version: ${parsed.version}, expected: ${SUPPORTED_VERSION}`,
    );
  }
  if (!parsed.name) {
    throw new DAGYAMLLoaderError("Missing required field: name");
  }
  if (!parsed.nodes) {
    throw new DAGYAMLLoaderError("Missing required field: nodes");
  }
  if (!parsed.edges) {
    throw new DAGYAMLLoaderError("Missing required field: edges");
  }

  const nodes: Record<string, BaseNodeData> = {};
  for (const [nodeId, nodeYAML] of Object.entries(parsed.nodes)) {
    nodes[nodeId] = yamlToNode(nodeYAML, nodeId);
  }

  const edges: EdgeData[] = parsed.edges.map((e, i) => ({
    id: e.id || `edge-${i}`,
    source: e.source,
    target: e.target,
    animated: true,
  }));

  validateDAG(nodes, edges);

  return {
    version: parsed.version,
    name: parsed.name,
    description: parsed.description || "",
    inputs: parsed.inputs || {},
    nodes: nodes as Record<string, NodeData>,
    edges,
  };
}

function yamlToNode(nodeYAML: NodeYAML, nodeId: string): BaseNodeData {
  const node: BaseNodeData = {
    id: nodeId,
    type: nodeYAML.type,
    name: nodeYAML.name,
    retry: nodeYAML.retry
      ? {
          attempts: nodeYAML.retry.attempts || 0,
          backoff_seconds: nodeYAML.retry.backoff_seconds || 0,
        }
      : undefined,
    config: nodeYAML.config || {},
    inputs: nodeYAML.inputs || [],
    outputs: nodeYAML.outputs || [],
    metadata: nodeYAML.metadata || {},
  };

  if (nodeYAML.inner_nodes || nodeYAML.inner_edges || nodeYAML.port_mapping) {
    const config = node.config as any;
    if (node.type === "group") {
      config.group_config = {
        internal_subgraph: {
          nodes: nodeYAML.inner_nodes
            ? Object.fromEntries(
                Object.entries(nodeYAML.inner_nodes).map(([id, n]) => [
                  id,
                  yamlToNode(n, id),
                ]),
              )
            : {},
          edges: nodeYAML.inner_edges
            ? nodeYAML.inner_edges.map((e, i) => ({
                id: e.id || `inner-edge-${i}`,
                source: e.source,
                target: e.target,
              }))
            : [],
        },
        input_mappings: nodeYAML.port_mapping?.inputs || [],
        output_mappings: nodeYAML.port_mapping?.outputs || [],
      };
    } else if (node.type === "subflow") {
      config.subflow_config = {
        subflow_id: nodeYAML.subflow_id || "",
        subflow_version: nodeYAML.subflow_version,
        input_mappings: nodeYAML.port_mapping?.inputs || [],
        output_mappings: nodeYAML.port_mapping?.outputs || [],
      };
    }
  }

  return node;
}

function validateDAG(nodes: Record<string, BaseNodeData>, edges: EdgeData[]) {
  const hasStart = Object.values(nodes).some((n) => n.type === "start");
  const hasEnd = Object.values(nodes).some((n) => n.type === "end");

  if (!hasStart) {
    throw new DAGYAMLLoaderError("Workflow must have a Start node");
  }
  if (!hasEnd) {
    throw new DAGYAMLLoaderError("Workflow must have an End node");
  }

  const visited = new Set<string>();
  const recursionStack = new Set<string>();

  function dfs(nodeId: string): boolean {
    if (recursionStack.has(nodeId)) {
      return true;
    }
    if (visited.has(nodeId)) {
      return false;
    }

    visited.add(nodeId);
    recursionStack.add(nodeId);

    for (const edge of edges) {
      const sourceNodeId = edge.source.split(".")[0];
      if (sourceNodeId === nodeId) {
        const targetNodeId = edge.target.split(".")[0];
        if (dfs(targetNodeId)) {
          return true;
        }
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }

  for (const nodeId of Object.keys(nodes)) {
    if (dfs(nodeId)) {
      throw new DAGYAMLLoaderError("Workflow contains a cycle");
    }
  }

  for (const edge of edges) {
    const [sourceNodeId, sourcePortId] = edge.source.split(".");
    const [targetNodeId, targetPortId] = edge.target.split(".");

    if (!nodes[sourceNodeId]) {
      throw new DAGYAMLLoaderError(`Source node not found: ${sourceNodeId}`);
    }
    if (!nodes[targetNodeId]) {
      throw new DAGYAMLLoaderError(`Target node not found: ${targetNodeId}`);
    }

    const sourcePortExists = nodes[sourceNodeId].outputs?.some(
      (p: any) => p.id === sourcePortId,
    );
    if (!sourcePortExists) {
      throw new DAGYAMLLoaderError(`Source port not found: ${edge.source}`);
    }

    const targetPortExists = nodes[targetNodeId].inputs?.some(
      (p: any) => p.id === targetPortId,
    );
    if (!targetPortExists) {
      throw new DAGYAMLLoaderError(`Target port not found: ${edge.target}`);
    }
  }
}
