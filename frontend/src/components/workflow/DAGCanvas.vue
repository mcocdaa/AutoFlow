<script setup lang="ts">
import {
  VueFlow,
  NodeMouseEvent,
  EdgeMouseEvent,
  useVueFlow,
} from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import { MiniMap } from "@vue-flow/minimap";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/controls/dist/style.css";
import "@vue-flow/minimap/dist/style.css";
import { useDAGWorkflowStore } from "../../stores/dag-workflow";
import { useNodeMetaStore } from "../../stores/node-meta";
import { onMounted, onUnmounted, ref, computed } from "vue";
import type { NodeData } from "../../types/dag-workflow";
import {
  DAGStartNode,
  DAGEndNode,
  DAGActionNode,
  DAGPassNode,
  DAGIfNode,
  DAGSwitchNode,
  DAGForNode,
  DAGWhileNode,
  DAGRetryNode,
  DAGMergeNode,
  DAGSplitNode,
  DAGGroupNode,
  DAGSubflowNode,
} from "./nodes";
import { getDefaultConfig } from "../../utils/node-defaults";

const nodeTypes: any = {
  start: DAGStartNode,
  end: DAGEndNode,
  action: DAGActionNode,
  pass: DAGPassNode,
  if: DAGIfNode,
  switch: DAGSwitchNode,
  for: DAGForNode,
  while: DAGWhileNode,
  retry: DAGRetryNode,
  merge: DAGMergeNode,
  split: DAGSplitNode,
  group: DAGGroupNode,
  subflow: DAGSubflowNode,
};

const props = defineProps<{
  edgeTypes?: Record<string, any>;
}>();

const store = useDAGWorkflowStore();
const nodeMetaStore = useNodeMetaStore();
const isDragging = ref(false);
const spacePressed = ref(false);
const selectedNodeIds = ref<string[]>([]);

const { fitView, setViewport } = useVueFlow();

const vueFlowNodes = computed(() => {
  return Object.entries(store.nodes).map(([id, node]) => ({
    id,
    type: node.type,
    position: {
      x: node.metadata.x || 0,
      y: node.metadata.y || 0,
    },
    data: node,
    selected: store.selectedNodeId === id || selectedNodeIds.value.includes(id),
  }));
});

const vueFlowEdges = computed(() => {
  return store.edges.map((edge) => ({
    id: edge.id,
    source: edge.source.split(".")[0],
    sourceHandle: edge.source.split(".")[1],
    target: edge.target.split(".")[0],
    targetHandle: edge.target.split(".")[1],
    selected: store.selectedEdgeId === edge.id,
    animated: true,
  }));
});

const getNodeColor = (type: string) => nodeMetaStore.colorMap.get(type) ?? "#6B7280";

const handleKeyDown = (event: KeyboardEvent) => {
  const target = event.target as HTMLElement;
  const isInputElement =
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.contentEditable === "true";

  if (
    isInputElement &&
    !["Delete", "Backspace", "Escape"].includes(event.key)
  ) {
    return;
  }

  if (event.key === " ") {
    spacePressed.value = true;
    event.preventDefault();
  }

  if (event.key === "Delete" || event.key === "Backspace") {
    if (selectedNodeIds.value.length > 0) {
      selectedNodeIds.value.forEach((id) => store.removeNode(id));
      selectedNodeIds.value = [];
      store.clearSelection();
      event.preventDefault();
    } else if (store.selectedNodeId) {
      store.removeNode(store.selectedNodeId);
      event.preventDefault();
    } else if (store.selectedEdgeId) {
      store.removeEdge(store.selectedEdgeId);
      event.preventDefault();
    }
  } else if (event.key.toLowerCase() === "f") {
    fitView({ padding: 0.2, duration: 300 });
    event.preventDefault();
  } else if (event.key.toLowerCase() === "r") {
    setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 });
    event.preventDefault();
  } else if (event.key === "Escape") {
    store.clearSelection();
    selectedNodeIds.value = [];
    event.preventDefault();
  } else if (event.ctrlKey || event.metaKey) {
    switch (event.key.toLowerCase()) {
      case "z":
        if (event.shiftKey) {
          store.redo();
        } else {
          store.undo();
        }
        event.preventDefault();
        break;
      case "y":
        store.redo();
        event.preventDefault();
        break;
      case "a":
        selectedNodeIds.value = Object.keys(store.nodes);
        if (selectedNodeIds.value.length > 0) {
          store.selectNode(selectedNodeIds.value[0]);
        }
        event.preventDefault();
        break;
    }
  }
};

const handleKeyUp = (event: KeyboardEvent) => {
  if (event.key === " ") {
    spacePressed.value = false;
  }
};

onMounted(() => {
  window.addEventListener("keydown", handleKeyDown);
  window.addEventListener("keyup", handleKeyUp);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown);
  window.removeEventListener("keyup", handleKeyUp);
});

const onConnect = (params: any) => {
  if (!isValidConnection(params)) {
    return;
  }
  const id = crypto.randomUUID();
  const source = `${params.source}.${params.sourceHandle}`;
  const target = `${params.target}.${params.targetHandle}`;
  store.addEdge({ id, source, target });
};

const onNodeClick = (nodeMouseEvent: NodeMouseEvent) => {
  const addToSelection =
    nodeMouseEvent.event.shiftKey ||
    nodeMouseEvent.event.ctrlKey ||
    nodeMouseEvent.event.metaKey;
  const nodeId = nodeMouseEvent.node.id;

  if (addToSelection) {
    const index = selectedNodeIds.value.indexOf(nodeId);
    if (index === -1) {
      selectedNodeIds.value.push(nodeId);
    } else {
      selectedNodeIds.value.splice(index, 1);
    }
    if (selectedNodeIds.value.length > 0) {
      store.selectNode(nodeId);
    } else {
      store.selectNode(null);
    }
  } else {
    selectedNodeIds.value = [nodeId];
    store.selectNode(nodeId);
  }
};

const onEdgeClick = (edgeMouseEvent: EdgeMouseEvent) => {
  store.selectEdge(edgeMouseEvent.edge.id);
};

const onPaneClick = () => {
  store.clearSelection();
  selectedNodeIds.value = [];
};

const isValidConnection = (params: any): boolean => {
  const { source, target, targetHandle } = params;

  if (source === target) {
    return false;
  }

  const targetInputPort = `${target}.${targetHandle}`;
  const isAlreadyConnected = store.edges.some(
    (edge) => edge.target === targetInputPort,
  );
  if (isAlreadyConnected) {
    return false;
  }

  const hasPath = (
    start: string,
    end: string,
    visited = new Set<string>(),
  ): boolean => {
    if (start === end) return true;
    if (visited.has(start)) return false;
    visited.add(start);

    const outgoingEdges = store.edges.filter((edge) =>
      edge.source.startsWith(`${start}.`),
    );
    for (const edge of outgoingEdges) {
      const nextNode = edge.target.split(".")[0];
      if (hasPath(nextNode, end, visited)) {
        return true;
      }
    }
    return false;
  };

  if (hasPath(target, source)) {
    return false;
  }

  return true;
};

const onDragOver = (event: DragEvent) => {
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
  isDragging.value = true;
};

const onDragLeave = () => {
  isDragging.value = false;
};

const onDrop = (event: DragEvent) => {
  event.preventDefault();
  isDragging.value = false;

  if (!event.dataTransfer) return;

  const data = event.dataTransfer.getData("application/vueflow");
  if (!data) return;

  try {
    const { type, label } = JSON.parse(data);
    const nodeId = crypto.randomUUID();
    const { inputs, outputs, error_port } = nodeMetaStore.getPortsForType(type);

    const newNode: NodeData = {
      id: nodeId,
      name: label || nodeMetaStore.getMeta(type)?.label || type,
      type: type as any,
      retry: { attempts: 0, backoff_seconds: 0 },
      config: getDefaultConfig(type),
      metadata: {
        x: event.clientX - 300,
        y: event.clientY - 150,
      },
      inputs,
      outputs,
      error_port,
    } as any;

    store.addNode(newNode);
  } catch (error) {
    console.error("Failed to add node:", error);
  }
};

const onNodeDragStop = (event: any) => {
  const { node, position } = event;
  store.updateNode(node.id, {
    metadata: {
      ...store.nodes[node.id]?.metadata,
      x: position.x,
      y: position.y,
    },
  });
};

const autoLayout = () => {
  store.autoLayout();
};

defineExpose({
  autoLayout,
});
</script>

<template>
  <div
    class="dag-canvas-wrapper"
    :class="{ 'is-dragging': isDragging }"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <VueFlow
      :nodes="vueFlowNodes"
      :edges="vueFlowEdges"
      :node-types="nodeTypes as any"
      :edge-types="props.edgeTypes"
      :default-edge-options="{ type: 'smoothstep', animated: true }"
      :snap-to-grid="true"
      :snap-grid="[10, 10]"
      :pan-on-scroll="!spacePressed"
      @connect="onConnect"
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @pane-click="onPaneClick"
      @node-drag-stop="onNodeDragStop"
      class="vue-flow-container"
    >
      <Background :gap="16" class="background" />
      <Controls class="controls" />
      <MiniMap
        :node-stroke-color="(node: any) => getNodeColor(node.type)"
        :node-color="(node: any) => getNodeColor(node.type) + '40'"
        :width="80"
        :height="60"
        class="minimap"
        :pannable="true"
        :zoomable="true"
      />
    </VueFlow>
  </div>
</template>

<style scoped>
.dag-canvas-wrapper {
  width: 100%;
  height: 600px;
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid transparent;
  transition: border-color 0.2s ease;
}

.dag-canvas-wrapper.is-dragging {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.05);
}

.vue-flow-container {
  width: 100%;
  height: 100%;
}

:deep(.controls) {
  position: absolute;
  bottom: 100px;
  left: 10px;
  opacity: 0.7;
  transition: opacity 0.3s ease;
}

:deep(.controls:hover) {
  opacity: 1;
}

:deep(.minimap) {
  left: auto !important;
  right: 10px;
  bottom: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  opacity: 0.9;
  padding: 0;
  margin: 0;
  line-height: normal;
}

:deep(.vue-flow__minimap) {
  background: transparent !important;
  padding: 0 !important;
  margin: 0 !important;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

:deep(.vue-flow__minimap svg) {
  background: white !important;
  display: block;
}

.background {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
}

:deep(.vue-flow__background) {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
}

:deep(.vue-flow__handle) {
  width: 10px !important;
  height: 10px !important;
  background: #d1d5db !important;
  border: 2px solid white !important;
  border-radius: 50% !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
  z-index: 10 !important;
}

:deep(.vue-flow__handle:hover) {
  width: 14px !important;
  height: 14px !important;
  background: #6366f1 !important;
  box-shadow: 0 0 0 6px rgba(99, 102, 241, 0.15) !important;
  border-width: 2px !important;
}

:deep(.vue-flow__handle:active) {
  transform: scale(0.95) !important;
}

:deep(.vue-flow__handle.source) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
}

:deep(.vue-flow__handle.source:hover) {
  background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.15) !important;
}

:deep(.vue-flow__handle.target) {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
}

:deep(.vue-flow__handle.target:hover) {
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%) !important;
  box-shadow: 0 0 0 6px rgba(245, 158, 11, 0.15) !important;
}

:deep(.vue-flow__edge-path) {
  stroke: #9ca3af !important;
  stroke-width: 2 !important;
}

:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: #3b82f6 !important;
  stroke-width: 3 !important;
}
</style>
