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
import { onMounted, onUnmounted, ref, computed } from "vue";
import type { NodeData } from "../../types/dag-workflow";
import { NODE_TEMPLATES } from "../../constants/node-templates";
import { getDefaultPorts, getDefaultConfig } from "../../utils/node-defaults";

const props = defineProps<{
  nodeTypes: Record<string, any>;
  edgeTypes?: Record<string, any>;
}>();

const store = useDAGWorkflowStore();
const isDragging = ref(false);
const spacePressed = ref(false);

const { fitView, setViewport } = useVueFlow();

const vueFlowNodes = computed(() =>
  Object.entries(store.nodes).map(([id, node]) => ({
    id,
    type: node.type,
    position: {
      x: node.metadata?.x ?? 0,
      y: node.metadata?.y ?? 0,
    },
    data: node,
    selected: store.selectedNodeId === id,
  })),
);

const vueFlowEdges = computed(() =>
  store.edges.map((edge) => ({
    id: edge.id,
    source: edge.source.split(".")[0],
    sourceHandle: edge.source.split(".")[1],
    target: edge.target.split(".")[0],
    targetHandle: edge.target.split(".")[1],
    selected: store.selectedEdgeId === edge.id,
    animated: true,
  })),
);

const NODE_COLOR_MAP = new Map(NODE_TEMPLATES.map((t) => [t.type, t.color]));
const getNodeColor = (type: string) => NODE_COLOR_MAP.get(type) ?? "#64748b";

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
    if (store.selectedNodeId) {
      store.removeNode(store.selectedNodeId);
      event.preventDefault();
    } else if (store.selectedEdgeId) {
      store.removeEdge(store.selectedEdgeId);
      event.preventDefault();
    }
  } else if (event.key === "Escape") {
    store.clearSelection();
    event.preventDefault();
  } else if (event.key.toLowerCase() === "f") {
    fitView({ padding: 0.2, duration: 300 });
    event.preventDefault();
  } else if (event.key.toLowerCase() === "r") {
    setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 });
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
        // Select all: select first node visually
        {
          const ids = Object.keys(store.nodes);
          if (ids.length > 0) store.selectNode(ids[0]);
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

const isValidConnection = (params: any): boolean => {
  const { source, target, targetHandle } = params;
  if (source === target) return false;

  const targetPortKey = `${target}.${targetHandle}`;
  if (store.edges.some((e) => e.target === targetPortKey)) return false;

  const hasPath = (start: string, end: string, visited = new Set<string>()): boolean => {
    if (start === end) return true;
    if (visited.has(start)) return false;
    visited.add(start);
    for (const edge of store.edges) {
      if (edge.source.startsWith(`${start}.`)) {
        if (hasPath(edge.target.split(".")[0], end, visited)) return true;
      }
    }
    return false;
  };

  if (hasPath(target, source)) return false;
  return true;
};

const onConnect = (params: any) => {
  if (!isValidConnection(params)) return;
  const id = crypto.randomUUID();
  const source = `${params.source}.${params.sourceHandle || "output"}`;
  const target = `${params.target}.${params.targetHandle || "input"}`;
  store.addEdge({ id, source, target });
};

const onNodeClick = (nodeMouseEvent: NodeMouseEvent) => {
  store.selectNode(nodeMouseEvent.node.id);
};

const onEdgeClick = (edgeMouseEvent: EdgeMouseEvent) => {
  store.selectEdge(edgeMouseEvent.edge.id);
};

const onPaneClick = () => {
  store.clearSelection();
};

const onNodeDragStop = ({ node }: { node: any }) => {
  if (!node || !store.nodes[node.id]) return;
  store.updateNode(node.id, {
    metadata: {
      ...store.nodes[node.id].metadata,
      x: node.position.x,
      y: node.position.y,
    },
  });
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
    const template = NODE_TEMPLATES.find((t) => t.type === type);
    const nodeId = crypto.randomUUID();
    const { inputs, outputs, error_port } = getDefaultPorts(type);

    const newNode: NodeData = {
      id: nodeId,
      name: label || template?.label || type,
      type: type as any,
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
</script>

<template>
  <div
    class="canvas-wrapper"
    :class="{ 'is-dragging': isDragging }"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <VueFlow
      :nodes="vueFlowNodes"
      :edges="vueFlowEdges"
      :node-types="props.nodeTypes"
      :edge-types="props.edgeTypes"
      :default-edge-options="{ type: 'custom', animated: true } as any"
      :snap-to-grid="true"
      :snap-grid="[20, 20]"
      :pan-on-scroll="!spacePressed"
      @connect="onConnect"
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @pane-click="onPaneClick"
      @node-drag-stop="onNodeDragStop"
      class="vue-flow-container"
    >
      <Background :gap="20" patternColor="#1e293b" :size="20" />
      <Controls class="controls" />
      <MiniMap
        :node-stroke-color="(node: any) => getNodeColor(node.type)"
        :node-color="(node: any) => getNodeColor(node.type) + '40'"
        :width="100"
        :height="70"
        class="minimap"
        :pannable="true"
        :zoomable="true"
        maskColor="rgba(15,23,42,0.7)"
      />
    </VueFlow>
  </div>
</template>

<style scoped>
.canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  border-radius: 0;
  overflow: hidden;
  border: 1px solid #1e293b;
  transition: border-color 0.2s ease;
  background: #0f172a;
}

.canvas-wrapper.is-dragging {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.03);
}

.vue-flow-container {
  width: 100%;
  height: 100%;
  background: #0f172a !important;
}

:deep(.vue-flow__background) {
  background-color: #0f172a !important;
}

:deep(.controls) {
  position: absolute !important;
  bottom: 16px !important;
  left: 16px !important;
  opacity: 0.5;
  transition: opacity 0.3s ease;
  background: #1e293b !important;
  border-radius: 8px !important;
  border: 1px solid #334155 !important;
  overflow: hidden;
}

:deep(.controls:hover) {
  opacity: 1;
}

:deep(.controls button) {
  width: 28px !important;
  height: 28px !important;
  background: transparent !important;
  border: none !important;
  color: #94a3b8 !important;
  fill: #94a3b8 !important;
}

:deep(.controls button:hover) {
  background: #334155 !important;
  color: #e2e8f0 !important;
  fill: #e2e8f0 !important;
}

:deep(.minimap) {
  left: auto !important;
  right: 16px !important;
  bottom: 16px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
  opacity: 0.7;
  padding: 0 !important;
  border-radius: 8px !important;
  border: 1px solid #334155 !important;
  overflow: hidden;
  transition: opacity 0.2s;
}

:deep(.minimap:hover) {
  opacity: 1;
}

:deep(.vue-flow__minimap) {
  background: #1e293b !important;
}

:deep(.vue-flow__minimap svg) {
  background: #1e293b !important;
}

:deep(.vue-flow__edge-path),
:deep(.vue-flow__connection-path) {
  stroke: #3d4a5c !important;
  stroke-width: 1.5 !important;
  transition: all 0.2s ease;
}

:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: #818cf8 !important;
  stroke-width: 2 !important;
}

:deep(.vue-flow__handle) {
  width: 10px !important;
  height: 10px !important;
  border-radius: 2px !important;
  transition: all 0.15s ease !important;
  z-index: 20 !important;
  cursor: crosshair !important;
}

:deep(.vue-flow__handle:hover) {
  width: 14px !important;
  height: 14px !important;
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.5) !important;
}

:deep(.vue-flow__handle.source) {
  background: #10b981 !important;
  border: 2px solid #065f46 !important;
  right: -5px !important;
}

:deep(.vue-flow__handle.source:hover) {
  background: #34d399 !important;
}

:deep(.vue-flow__handle.target) {
  background: #6366f1 !important;
  border: 2px solid #3730a3 !important;
  left: -5px !important;
}

:deep(.vue-flow__handle.target:hover) {
  background: #818cf8 !important;
}

:deep(.vue-flow__connection-line) {
  stroke: #6366f1 !important;
  stroke-width: 2 !important;
}
</style>
