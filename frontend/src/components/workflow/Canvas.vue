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
import { NODE_TEMPLATES } from "../../constants/node-templates";

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
      return "#10b981";
    case "llm":
      return "#10b981";
    case "python":
      return "#f59e0b";
    case "api":
      return "#6366f1";
    case "condition":
    case "loop":
      return "#8b5cf6";
    default:
      return "#64748b";
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
    const template = NODE_TEMPLATES.find((t) => t.type === type);

    let inputs: any[] = [];
    let outputs: any[] = [];

    switch (type) {
      case "start":
        inputs = [];
        outputs = [{ id: "output", name: "Output", type: "any" }];
        break;
      case "end":
      case "output":
        inputs = [{ id: "input", name: "Input", type: "any", required: true }];
        outputs = [];
        break;
      case "if":
      case "switch":
      case "condition":
        inputs = [{ id: "input", name: "Input", type: "any", required: true }];
        outputs = [
          { id: "true", name: "True", type: "any" },
          { id: "false", name: "False", type: "any" },
        ];
        break;
      case "merge":
        inputs = [
          { id: "input1", name: "Input 1", type: "any", required: true },
          { id: "input2", name: "Input 2", type: "any" },
        ];
        outputs = [{ id: "output", name: "Output", type: "any" }];
        break;
      case "split":
        inputs = [{ id: "input", name: "Input", type: "any", required: true }];
        outputs = [
          { id: "output1", name: "Output 1", type: "any" },
          { id: "output2", name: "Output 2", type: "any" },
        ];
        break;
      case "for":
      case "while":
      case "loop":
        inputs = [{ id: "input", name: "Input", type: "any", required: true }];
        outputs = [{ id: "output", name: "Output", type: "any" }];
        break;
      default:
        inputs = [{ id: "input", name: "Input", type: "any", required: true }];
        outputs = [{ id: "output", name: "Output", type: "any" }];
    }

    const newNode: WorkflowNode = {
      id: crypto.randomUUID(),
      type: type as NodeType,
      position: {
        x: event.clientX - 300,
        y: event.clientY - 150,
      },
      data: {
        id: crypto.randomUUID(),
        name: label || template?.label || type,
        type: type,
        config: {},
        metadata: {},
        inputs,
        outputs,
        error_port:
          type !== "start" && type !== "end"
            ? { id: "error", name: "Error", type: "any" }
            : undefined,
      } as any,
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
      :default-edge-options="{ type: 'custom', animated: true } as any"
      :snap-to-grid="true"
      :snap-grid="[20, 20]"
      :pan-on-scroll="!spacePressed"
      @connect="onConnect"
      @node-click="onNodeClick"
      @edge-click="onEdgeClick"
      @pane-click="onPaneClick"
      class="vue-flow-container"
    >
      <Background :gap="20" patternColor="#1e293b" :size="20" />
      <Controls class="controls" />
      <MiniMap
        :node-stroke-color="(node) => getNodeColor(node.type as NodeType)"
        :node-color="(node) => getNodeColor(node.type as NodeType) + '40'"
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
  width: 8px !important;
  height: 8px !important;
  background: #3d4a5c !important;
  border: 2px solid #1a1f2e !important;
  border-radius: 50% !important;
  transition: all 0.15s ease !important;
  z-index: 10 !important;
}

:deep(.vue-flow__handle:hover) {
  width: 12px !important;
  height: 12px !important;
  background: #6366f1 !important;
  border-color: #818cf8 !important;
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.4) !important;
}

:deep(.vue-flow__handle.source) {
  background: #10b981 !important;
}

:deep(.vue-flow__handle.source:hover) {
  background: #34d399 !important;
}

:deep(.vue-flow__handle.target) {
  background: #f59e0b !important;
}

:deep(.vue-flow__handle.target:hover) {
  background: #fbbf24 !important;
}
</style>
