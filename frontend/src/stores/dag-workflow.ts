import { defineStore } from "pinia";
import jsYaml from "js-yaml";
import type {
  DAGWorkflow,
  NodeData,
  EdgeData,
  WorkflowState,
} from "../types/dag-workflow";

const MAX_HISTORY = 50;

const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;
const HORIZONTAL_SPACING = 60;
const VERTICAL_SPACING = 60;
const CANVAS_WIDTH = 800;
const INITIAL_Y = 50;

export const useDAGWorkflowStore = defineStore("dag-workflow", {
  state: () => ({
    nodes: {} as Record<string, NodeData>,
    edges: [] as EdgeData[],
    selectedNodeId: null as string | null,
    selectedEdgeId: null as string | null,
    history: [] as WorkflowState[],
    future: [] as WorkflowState[],
    name: "Untitled DAG Workflow",
  }),

  getters: {
    getNode:
      (state) =>
      (id: string): NodeData | undefined =>
        state.nodes[id],
    getEdge:
      (state) =>
      (id: string): EdgeData | undefined =>
        state.edges.find((edge) => edge.id === id),
    selectedNode: (state): NodeData | undefined =>
      state.selectedNodeId ? state.nodes[state.selectedNodeId] : undefined,
    getSelectedNode: (state): NodeData | undefined =>
      state.selectedNodeId ? state.nodes[state.selectedNodeId] : undefined,
    getSelectedEdge: (state): EdgeData | undefined =>
      state.selectedEdgeId
        ? state.edges.find((edge) => edge.id === state.selectedEdgeId)
        : undefined,
    canUndo: (state): boolean => state.history.length > 0,
    canRedo: (state): boolean => state.future.length > 0,
  },

  actions: {
    saveHistory() {
      const state: WorkflowState = {
        nodes: JSON.parse(JSON.stringify(this.nodes)),
        edges: JSON.parse(JSON.stringify(this.edges)),
        timestamp: new Date(),
      };
      this.history.push(state);
      this.future = [];
      if (this.history.length > MAX_HISTORY) {
        this.history.shift();
      }
    },

    undo() {
      if (!this.canUndo) return;
      const currentState = this.createSnapshot();
      this.future.push(currentState);
      const previousState = this.history.pop()!;
      this.restoreSnapshot(previousState);
    },

    redo() {
      if (!this.canRedo) return;
      const currentState = this.createSnapshot();
      this.history.push(currentState);
      const nextState = this.future.pop()!;
      this.restoreSnapshot(nextState);
    },

    createSnapshot(): WorkflowState {
      return {
        nodes: JSON.parse(JSON.stringify(this.nodes)),
        edges: JSON.parse(JSON.stringify(this.edges)),
        timestamp: new Date(),
      };
    },

    restoreSnapshot(snapshot: WorkflowState) {
      this.nodes = snapshot.nodes;
      this.edges = snapshot.edges;
    },

    setName(name: string) {
      this.saveHistory();
      this.name = name;
    },

    addNode(node: NodeData) {
      this.saveHistory();
      this.nodes[node.id] = node;
    },

    updateNode(id: string, updates: Partial<NodeData>) {
      if (this.nodes[id]) {
        this.saveHistory();
        this.nodes[id] = { ...this.nodes[id], ...updates } as NodeData;
      }
    },

    removeNode(id: string) {
      if (!this.nodes[id]) return;
      this.saveHistory();
      const { [id]: _, ...remainingNodes } = this.nodes;
      this.nodes = remainingNodes;
      this.edges = this.edges.filter(
        (edge) =>
          !edge.source.startsWith(`${id}.`) &&
          !edge.target.startsWith(`${id}.`),
      );
      if (this.selectedNodeId === id) {
        this.selectedNodeId = null;
      }
    },

    addEdge(edge: EdgeData) {
      this.saveHistory();
      this.edges.push(edge);
    },

    updateEdge(id: string, updates: Partial<EdgeData>) {
      const index = this.edges.findIndex((edge) => edge.id === id);
      if (index !== -1) {
        this.saveHistory();
        this.edges[index] = { ...this.edges[index], ...updates };
      }
    },

    removeEdge(id: string) {
      const index = this.edges.findIndex((edge) => edge.id === id);
      if (index === -1) return;
      this.saveHistory();
      this.edges = this.edges.filter((edge) => edge.id !== id);
      if (this.selectedEdgeId === id) {
        this.selectedEdgeId = null;
      }
    },

    selectNode(id: string | null) {
      this.selectedEdgeId = null;
      this.selectedNodeId = id;
    },

    selectEdge(id: string | null) {
      this.selectedNodeId = null;
      this.selectedEdgeId = id;
    },

    clearSelection() {
      this.selectedNodeId = null;
      this.selectedEdgeId = null;
    },

    reset() {
      this.saveHistory();
      this.nodes = {};
      this.edges = [];
      this.selectedNodeId = null;
      this.selectedEdgeId = null;
      this.name = "Untitled DAG Workflow";
      this.history = [];
      this.future = [];
    },

    toDAGWorkflow(): DAGWorkflow {
      return {
        version: "2.0",
        name: this.name,
        description: undefined,
        inputs: {},
        nodes: { ...this.nodes },
        edges: [...this.edges],
      };
    },

    loadFromDAGWorkflow(workflow: DAGWorkflow) {
      this.saveHistory();
      this.name = workflow.name;
      this.nodes = { ...workflow.nodes };
      this.edges = [...workflow.edges];
      this.selectedNodeId = null;
      this.selectedEdgeId = null;
      this.history = [];
      this.future = [];
    },

    exportToYAML(): string {
      const workflow = this.toDAGWorkflow();
      return jsYaml.dump(workflow, {
        indent: 2,
        lineWidth: -1,
      });
    },

    loadFromYAML(yamlString: string) {
      const workflow = jsYaml.load(yamlString) as DAGWorkflow;
      this.loadFromDAGWorkflow(workflow);
    },

    autoLayout() {
      this.saveHistory();

      const nodeIds = Object.keys(this.nodes);
      if (nodeIds.length === 0) return;

      const layers = this.calculateTopologicalLayers(nodeIds);
      this.applyLayerLayout(layers);
    },

    calculateTopologicalLayers(nodeIds: string[]): string[][] {
      const visited = new Set<string>();
      const layers: string[][] = [];

      const inDegree = this.calculateInDegrees(nodeIds);
      const queue = nodeIds.filter((id) => inDegree.get(id) === 0);

      while (queue.length > 0) {
        const layer: string[] = [];
        const levelSize = queue.length;

        for (let i = 0; i < levelSize; i++) {
          const nodeId = queue.shift()!;
          if (!visited.has(nodeId)) {
            visited.add(nodeId);
            layer.push(nodeId);
            this.processNodeOutgoingEdges(nodeId, inDegree, queue);
          }
        }

        if (layer.length > 0) {
          layers.push(layer);
        }
      }

      const remainingNodes = nodeIds.filter((id) => !visited.has(id));
      if (remainingNodes.length > 0) {
        layers.push(remainingNodes);
      }

      return layers;
    },

    calculateInDegrees(nodeIds: string[]): Map<string, number> {
      const inDegree = new Map<string, number>();
      nodeIds.forEach((id) => inDegree.set(id, 0));

      this.edges.forEach((edge) => {
        const targetNodeId = edge.target.split(".")[0];
        const current = inDegree.get(targetNodeId) || 0;
        inDegree.set(targetNodeId, current + 1);
      });

      return inDegree;
    },

    processNodeOutgoingEdges(
      nodeId: string,
      inDegree: Map<string, number>,
      queue: string[],
    ) {
      this.edges.forEach((edge) => {
        const targetNodeId = edge.target.split(".")[0];

        if (edge.source.startsWith(`${nodeId}.`)) {
          const current = inDegree.get(targetNodeId)! - 1;
          inDegree.set(targetNodeId, current);
          if (current === 0) {
            queue.push(targetNodeId);
          }
        }
      });
    },

    applyLayerLayout(layers: string[][]) {
      let currentY = INITIAL_Y;
      layers.forEach((layer) => {
        const layerWidth = this.calculateLayerWidth(layer.length);
        const startX = (CANVAS_WIDTH - layerWidth) / 2;

        layer.forEach((nodeId, index) => {
          this.updateNodePosition(
            nodeId,
            startX + index * (NODE_WIDTH + HORIZONTAL_SPACING),
            currentY,
          );
        });

        currentY += NODE_HEIGHT + VERTICAL_SPACING;
      });
    },

    calculateLayerWidth(nodeCount: number): number {
      return nodeCount * NODE_WIDTH + (nodeCount - 1) * HORIZONTAL_SPACING;
    },

    updateNodePosition(nodeId: string, x: number, y: number) {
      const node = this.nodes[nodeId];
      if (node) {
        this.nodes[nodeId] = {
          ...node,
          metadata: {
            ...node.metadata,
            x,
            y,
          },
        };
      }
    },
  },
});
