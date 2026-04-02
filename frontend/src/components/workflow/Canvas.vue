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
import { useWorkflowStore } from "../../stores/workflow";
import { onMounted, onUnmounted, ref } from "vue";
import type { NodeType, WorkflowNode } from "../../types/workflow";

const props = defineProps<{
  nodeTypes: Record<string, any>;
  edgeTypes?: Record<string, any>;
}>();

const store = useWorkflowStore();
const isDragging = ref(false);
const spacePressed = ref(false);

const { fitView, setViewport } = useVueFlow();

const getNodeColor = (type: NodeType) => {
  switch (type) {
    case "start":
    case "output":
      return "#2563EB";
    case "llm":
      return "#10B981";
    case "python":
      return "#F59E0B";
    case "api":
      return "#3B82F6";
    case "condition":
    case "loop":
      return "#8B5CF6";
    default:
      return "#64748B";
  }
};

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
    if (store.hasSelectedNodes) {
      store.deleteSelectedNodes();
      event.preventDefault();
    } else if (store.selectedEdgeId) {
      store.deleteEdge(store.selectedEdgeId);
      event.preventDefault();
    }
  } else if (event.key.toLowerCase() === "f") {
    fitView({ padding: 0.2, duration: 300 });
    event.preventDefault();
  } else if (event.key.toLowerCase() === "r") {
    setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 300 });
    event.preventDefault();
  } else if (event.ctrlKey || event.metaKey) {
    switch (event.key.toLowerCase()) {
      case "c":
        if (store.hasSelectedNodes) {
          store.copySelectedNodes();
          event.preventDefault();
        }
        break;
      case "v":
        store.pasteNodes();
        event.preventDefault();
        break;
      case "x":
        if (store.hasSelectedNodes) {
          store.copySelectedNodes();
          store.deleteSelectedNodes();
          event.preventDefault();
        }
        break;
      case "d":
        if (store.selectedNode) {
          store.duplicateSelectedNode();
          event.preventDefault();
        }
        break;
      case "a":
        store.selectAllNodes();
        event.preventDefault();
        break;
      case "s":
        store.saveToLocalStorage();
        event.preventDefault();
        break;
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
  const id = crypto.randomUUID();
  store.addEdge({
    id,
    source: params.source,
    target: params.target,
    animated: true,
  });
};

const onNodeClick = (nodeMouseEvent: NodeMouseEvent) => {
  const addToSelection =
    nodeMouseEvent.event.ctrlKey || nodeMouseEvent.event.metaKey;
  store.selectNode(nodeMouseEvent.node.id, addToSelection);
};

const onEdgeClick = (edgeMouseEvent: EdgeMouseEvent) => {
  store.selectEdge(edgeMouseEvent.edge.id);
};

const onPaneClick = () => {
  store.clearSelection();
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

    const newNode: WorkflowNode = {
      id: crypto.randomUUID(),
      type: type as NodeType,
      position: {
        x: event.clientX - 300,
        y: event.clientY - 150,
      },
      data: {
        type: type,
        label: label || type,
        config: {},
      },
    };

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
      v-model:nodes="store.nodes"
      v-model:edges="store.edges"
      :node-types="props.nodeTypes"
      :edge-types="props.edgeTypes"
      :default-edge-options="{ type: 'smoothstep', animated: true }"
      :snap-to-grid="true"
      :snap-grid="[10, 10]"
      :pan-on-scroll="!spacePressed"
      @connect="onConnect"
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @pane-click="onPaneClick"
      class="vue-flow-container"
    >
      <Background :gap="16" class="background" />
      <Controls class="controls" />
      <MiniMap
        :node-stroke-color="(node) => getNodeColor(node.type as NodeType)"
        :node-color="(node) => getNodeColor(node.type as NodeType) + '40'"
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
.canvas-wrapper {
  width: 100%;
  height: 600px;
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid transparent;
  transition: border-color 0.2s ease;
}

.canvas-wrapper.is-dragging {
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

/* 连线点样式 - 精致美观 */
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

/* 连线拖拽时的临时连线样式 */
:deep(.vue-flow__edge-path) {
  stroke: #9ca3af !important;
  stroke-width: 2 !important;
}

:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: #3b82f6 !important;
  stroke-width: 3 !important;
}
</style>
