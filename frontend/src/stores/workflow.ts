import { defineStore } from "pinia";
import type {
  WorkflowState,
  WorkflowNode,
  WorkflowEdge,
} from "../types/workflow";
import { workflowToYAML, yamlToWorkflow } from "../utils/workflow-yaml";

const STORAGE_KEY = "autoflow_workflow";
const MAX_HISTORY = 50;

interface HistoryItem {
  type:
    | "add_node"
    | "delete_node"
    | "update_node"
    | "add_edge"
    | "delete_edge"
    | "reset";
  before: any;
  after: any;
}

interface ClipboardData {
  nodes: WorkflowNode[];
}

export const useWorkflowStore = defineStore("workflow", {
  state: (): WorkflowState & {
    history: HistoryItem[];
    historyIndex: number;
    clipboard: ClipboardData | null;
    selectedNodeIds: string[];
    selectedEdgeId: string | null;
  } => ({
    nodes: [],
    edges: [],
    selectedNodeId: null,
    selectedEdgeId: null,
    isDirty: false,
    name: "Untitled Workflow",
    history: [],
    historyIndex: -1,
    clipboard: null,
    selectedNodeIds: [],
  }),
  getters: {
    selectedNode: (state): WorkflowNode | undefined => {
      return state.nodes.find((node) => node.id === state.selectedNodeId);
    },
    selectedNodes: (state): WorkflowNode[] => {
      return state.nodes.filter((node) =>
        state.selectedNodeIds.includes(node.id),
      );
    },
    canUndo: (state): boolean => {
      return state.historyIndex >= 0;
    },
    canRedo: (state): boolean => {
      return state.historyIndex < state.history.length - 1;
    },
    hasSelectedNodes: (state): boolean => {
      return state.selectedNodeIds.length > 0;
    },
  },
  actions: {
    pushHistory(item: HistoryItem) {
      this.history = this.history.slice(0, this.historyIndex + 1);
      this.history.push(item);
      if (this.history.length > MAX_HISTORY) {
        this.history.shift();
      } else {
        this.historyIndex++;
      }
    },
    undo() {
      if (!this.canUndo) return;
      const item = this.history[this.historyIndex];
      this.historyIndex--;

      switch (item.type) {
        case "add_node":
          this.nodes = item.before.nodes;
          this.edges = item.before.edges;
          break;
        case "delete_node":
          this.nodes = item.before.nodes;
          this.edges = item.before.edges;
          break;
        case "update_node":
          this.nodes = item.before.nodes;
          break;
        case "add_edge":
          this.edges = item.before.edges;
          break;
        case "delete_edge":
          this.edges = item.before.edges;
          break;
        case "reset":
          this.nodes = item.before.nodes;
          this.edges = item.before.edges;
          this.name = item.before.name;
          break;
      }
      this.isDirty = true;
    },
    redo() {
      if (!this.canRedo) return;
      this.historyIndex++;
      const item = this.history[this.historyIndex];

      switch (item.type) {
        case "add_node":
          this.nodes = item.after.nodes;
          this.edges = item.after.edges;
          break;
        case "delete_node":
          this.nodes = item.after.nodes;
          this.edges = item.after.edges;
          break;
        case "update_node":
          this.nodes = item.after.nodes;
          break;
        case "add_edge":
          this.edges = item.after.edges;
          break;
        case "delete_edge":
          this.edges = item.after.edges;
          break;
        case "reset":
          this.nodes = item.after.nodes;
          this.edges = item.after.edges;
          this.name = item.after.name;
          break;
      }
      this.isDirty = true;
    },
    copySelectedNode() {
      if (!this.selectedNode) return;
      this.clipboard = {
        nodes: [JSON.parse(JSON.stringify(this.selectedNode))],
      };
    },
    pasteNodes() {
      if (!this.clipboard) return;
      const before = { nodes: [...this.nodes], edges: [...this.edges] };

      this.clipboard.nodes.forEach((node, index) => {
        const newNode: WorkflowNode = {
          ...node,
          id: crypto.randomUUID(),
          position: {
            x: node.position.x + 50 + index * 20,
            y: node.position.y + 50 + index * 20,
          },
        };
        this.nodes.push(newNode);
      });

      this.pushHistory({
        type: "add_node",
        before,
        after: { nodes: [...this.nodes], edges: [...this.edges] },
      });
      this.isDirty = true;
    },
    setName(name: string) {
      this.name = name;
      this.isDirty = true;
    },
    addNode(node: WorkflowNode) {
      const before = { nodes: [...this.nodes], edges: [...this.edges] };
      this.nodes.push(node);
      this.pushHistory({
        type: "add_node",
        before,
        after: { nodes: [...this.nodes], edges: [...this.edges] },
      });
      this.isDirty = true;
    },
    updateNode(id: string, updates: Partial<WorkflowNode>) {
      const before = { nodes: [...this.nodes] };
      const index = this.nodes.findIndex((node) => node.id === id);
      if (index !== -1) {
        this.nodes[index] = { ...this.nodes[index], ...updates };
        this.pushHistory({
          type: "update_node",
          before,
          after: { nodes: [...this.nodes] },
        });
        this.isDirty = true;
      }
    },
    deleteNode(id: string) {
      const before = { nodes: [...this.nodes], edges: [...this.edges] };
      this.nodes = this.nodes.filter((node) => node.id !== id);
      this.edges = this.edges.filter(
        (edge) => edge.source !== id && edge.target !== id,
      );
      if (this.selectedNodeId === id) {
        this.selectedNodeId = null;
      }
      this.pushHistory({
        type: "delete_node",
        before,
        after: { nodes: [...this.nodes], edges: [...this.edges] },
      });
      this.isDirty = true;
    },
    addEdge(edge: WorkflowEdge) {
      const before = { edges: [...this.edges] };
      this.edges.push(edge);
      this.pushHistory({
        type: "add_edge",
        before,
        after: { edges: [...this.edges] },
      });
      this.isDirty = true;
    },
    updateEdge(id: string, updates: Partial<WorkflowEdge>) {
      const index = this.edges.findIndex((edge) => edge.id === id);
      if (index !== -1) {
        this.edges[index] = { ...this.edges[index], ...updates };
        this.isDirty = true;
      }
    },
    deleteEdge(id: string) {
      const before = { edges: [...this.edges] };
      this.edges = this.edges.filter((edge) => edge.id !== id);
      if (this.selectedEdgeId === id) {
        this.selectedEdgeId = null;
      }
      this.pushHistory({
        type: "delete_edge",
        before,
        after: { edges: [...this.edges] },
      });
      this.isDirty = true;
    },
    selectNode(id: string | null, addToSelection: boolean = false) {
      this.selectedEdgeId = null;
      if (addToSelection && id) {
        if (!this.selectedNodeIds.includes(id)) {
          this.selectedNodeIds.push(id);
        }
        this.selectedNodeId = id;
      } else {
        this.selectedNodeId = id;
        this.selectedNodeIds = id ? [id] : [];
      }
    },
    selectEdge(id: string) {
      this.selectedNodeId = null;
      this.selectedNodeIds = [];
      this.selectedEdgeId = id;
    },
    selectAllNodes() {
      this.selectedEdgeId = null;
      this.selectedNodeIds = this.nodes.map((node) => node.id);
      if (this.selectedNodeIds.length > 0) {
        this.selectedNodeId = this.selectedNodeIds[0];
      }
    },
    clearSelection() {
      this.selectedNodeId = null;
      this.selectedNodeIds = [];
      this.selectedEdgeId = null;
    },
    deleteSelectedNodes() {
      if (this.selectedNodeIds.length === 0) return;
      const before = { nodes: [...this.nodes], edges: [...this.edges] };

      const idsToDelete = new Set(this.selectedNodeIds);
      this.nodes = this.nodes.filter((node) => !idsToDelete.has(node.id));
      this.edges = this.edges.filter(
        (edge) =>
          !idsToDelete.has(edge.source) && !idsToDelete.has(edge.target),
      );

      this.selectedNodeId = null;
      this.selectedNodeIds = [];

      this.pushHistory({
        type: "delete_node",
        before,
        after: { nodes: [...this.nodes], edges: [...this.edges] },
      });
      this.isDirty = true;
    },
    copySelectedNodes() {
      if (this.selectedNodeIds.length === 0) return;
      this.clipboard = {
        nodes: JSON.parse(JSON.stringify(this.selectedNodes)),
      };
    },
    duplicateSelectedNode() {
      if (!this.selectedNode) return;
      const before = { nodes: [...this.nodes], edges: [...this.edges] };

      const newNode: WorkflowNode = {
        ...this.selectedNode,
        id: crypto.randomUUID(),
        position: {
          x: this.selectedNode.position.x + 50,
          y: this.selectedNode.position.y + 50,
        },
      };
      this.nodes.push(newNode);

      this.pushHistory({
        type: "add_node",
        before,
        after: { nodes: [...this.nodes], edges: [...this.edges] },
      });
      this.isDirty = true;

      this.selectNode(newNode.id);
    },
    setNodes(nodes: WorkflowNode[]) {
      this.nodes = nodes;
      this.isDirty = true;
    },
    setEdges(edges: WorkflowEdge[]) {
      this.edges = edges;
      this.isDirty = true;
    },
    reset() {
      const before = {
        nodes: [...this.nodes],
        edges: [...this.edges],
        name: this.name,
      };
      this.nodes = [];
      this.edges = [];
      this.selectedNodeId = null;
      this.isDirty = false;
      this.name = "Untitled Workflow";
      this.history = [];
      this.historyIndex = -1;
      localStorage.removeItem(STORAGE_KEY);
      this.pushHistory({
        type: "reset",
        before,
        after: { nodes: [], edges: [], name: "Untitled Workflow" },
      });
    },
    markClean() {
      this.isDirty = false;
    },
    toYAML(): string {
      return workflowToYAML(this.name, this.nodes, this.edges);
    },
    loadFromYAML(yaml: string) {
      const { name, nodes, edges } = yamlToWorkflow(yaml);
      this.name = name;
      this.nodes = nodes;
      this.edges = edges;
      this.selectedNodeId = null;
      this.isDirty = true;
      this.history = [];
      this.historyIndex = -1;
    },
    saveToLocalStorage() {
      const data = {
        name: this.name,
        nodes: this.nodes,
        edges: this.edges,
        savedAt: new Date().toISOString(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      this.markClean();
    },
    loadFromLocalStorage(): boolean {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        return false;
      }
      try {
        const data = JSON.parse(stored);
        this.name = data.name || "Untitled Workflow";
        this.nodes = data.nodes || [];
        this.edges = data.edges || [];
        this.selectedNodeId = null;
        this.isDirty = false;
        this.history = [];
        this.historyIndex = -1;
        return true;
      } catch {
        return false;
      }
    },
    loadFromExample(yaml: string, mode: "overwrite" | "append" = "overwrite") {
      const { name, nodes, edges } = yamlToWorkflow(yaml);

      if (mode === "overwrite") {
        const before = {
          nodes: [...this.nodes],
          edges: [...this.edges],
          name: this.name,
        };
        this.name = name;
        this.nodes = nodes;
        this.edges = edges;
        this.selectedNodeId = null;
        this.isDirty = true;
        this.history = [];
        this.historyIndex = -1;
        this.pushHistory({
          type: "reset",
          before,
          after: { nodes, edges, name },
        });
      } else {
        const before = { nodes: [...this.nodes], edges: [...this.edges] };

        const maxX =
          this.nodes.length > 0
            ? Math.max(...this.nodes.map((n) => n.position.x))
            : 0;

        const offsetX = maxX + 300;

        const newNodes = nodes.map((node) => ({
          ...node,
          id: crypto.randomUUID(),
          position: {
            x: node.position.x + offsetX,
            y: node.position.y,
          },
        }));

        const nodeIdMap = new Map<string, string>();
        nodes.forEach((oldNode, index) => {
          nodeIdMap.set(oldNode.id, newNodes[index].id);
        });

        const newEdges = edges.map((edge) => ({
          ...edge,
          id: crypto.randomUUID(),
          source: nodeIdMap.get(edge.source) || edge.source,
          target: nodeIdMap.get(edge.target) || edge.target,
        }));

        this.nodes = [...this.nodes, ...newNodes];
        this.edges = [...this.edges, ...newEdges];
        this.selectedNodeId = null;
        this.isDirty = true;

        this.pushHistory({
          type: "add_node",
          before,
          after: { nodes: [...this.nodes], edges: [...this.edges] },
        });
      }
    },
  },
});
