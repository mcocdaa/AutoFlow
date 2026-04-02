<script setup lang="ts">
import { computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { NODE_TEMPLATES } from "../../../constants/node-templates";
import { useExecutionStore } from "../../../stores/execution";
import type { BaseNodeData, Breakpoint } from "../../../types/dag-workflow";

const props = defineProps<{
  data: BaseNodeData;
  selected?: boolean;
  id?: string;
}>();

const emit = defineEmits<{
  (e: "node-click", nodeId: string): void;
  (e: "node-double-click", nodeId: string): void;
  (e: "port-hover", portId: string, isHovered: boolean): void;
  (e: "breakpoint-toggle", nodeId: string): void;
  (e: "breakpoint-disable", breakpointId: string): void;
}>();

const executionStore = useExecutionStore();

const getNodeTemplate = (type: string) => {
  return NODE_TEMPLATES.find((t) => t.type === type);
};

const template = computed(() => getNodeTemplate(props.data?.type || ""));
const nodeColor = computed(() => template.value?.color || "#6B7280");
const nodeIcon = computed(() => template.value?.icon || "📦");
const nodeLabel = computed(
  () => props.data?.name || template.value?.label || "Node",
);

const executionState = computed(() => {
  if (!props.id) return null;
  return executionStore.nodeStates[props.id];
});

const isPending = computed(
  () => executionState.value?.status === "pending" || !executionState.value,
);
const isRunning = computed(() => executionState.value?.status === "running");
const isCompleted = computed(
  () => executionState.value?.status === "completed",
);
const isFailed = computed(() => executionState.value?.status === "failed");
const isSkipped = computed(() => executionState.value?.status === "skipped");

const getStatusColor = () => {
  if (isRunning.value) return "#3B82F6";
  if (isCompleted.value) return "#10B981";
  if (isFailed.value) return "#EF4444";
  if (isSkipped.value) return "#F59E0B";
  if (isPending.value) return "#6B7280";
  return "#6B7280";
};

const getStatusIcon = () => {
  if (isRunning.value) return "⚡";
  if (isCompleted.value) return "✓";
  if (isFailed.value) return "✕";
  if (isSkipped.value) return "⏭";
  if (isPending.value) return "○";
  return "";
};

const getBorderColor = () => {
  if (isRunning.value) return "#3B82F6";
  if (isCompleted.value) return "#10B981";
  if (isFailed.value) return "#EF4444";
  if (isSkipped.value) return "#F59E0B";
  if (isPending.value) return "#9CA3AF";
  return "#ddd";
};

const getExecutionDuration = () => {
  if (!executionState.value) return null;
  if (
    isCompleted.value &&
    executionState.value.completed_at &&
    executionState.value.started_at
  ) {
    const duration =
      executionState.value.completed_at.getTime() -
      executionState.value.started_at.getTime();
    return `${duration}ms`;
  }
  if (isRunning.value && executionState.value.started_at) {
    const duration = Date.now() - executionState.value.started_at.getTime();
    return `${duration}ms`;
  }
  return null;
};

const getPortTypeIcon = (type: string) => {
  const icons: Record<string, string> = {
    any: "🔷",
    string: "📝",
    number: "🔢",
    boolean: "🔘",
    object: "📦",
    array: "📊",
  };
  return icons[type] || "🔷";
};

const isErrorPortVisible = computed(() => {
  return props.data.metadata?.showErrorPort || false;
});

const breakpoint = computed<Breakpoint | undefined>(() => {
  if (!props.id) return undefined;
  return executionStore.getBreakpoint(props.id);
});

const hasBreakpoint = computed(() => breakpoint.value !== undefined);
const isBreakpointEnabled = computed(() => breakpoint.value?.enabled ?? false);

const handleNodeClick = () => {
  if (props.id) {
    emit("node-click", props.id);
  }
};

const handleNodeDoubleClick = () => {
  if (props.id) {
    emit("node-double-click", props.id);
  }
};

const handlePortHover = (portId: string, isHovered: boolean) => {
  emit("port-hover", portId, isHovered);
};

const handleBreakpointClick = (event: MouseEvent) => {
  event.stopPropagation();
  if (!props.id) return;

  if (hasBreakpoint.value) {
    if (breakpoint.value) {
      executionStore.toggleBreakpoint(breakpoint.value.id);
    }
  } else {
    executionStore.addBreakpoint(props.id);
  }
};

const handleBreakpointRightClick = (event: MouseEvent) => {
  event.preventDefault();
  event.stopPropagation();
  if (!props.id || !breakpoint.value) return;

  executionStore.removeBreakpointByNodeId(props.id);
};
</script>

<template>
  <div
    class="node-container"
    :class="{
      'node-selected': selected,
      'node-pending': isPending,
      'node-running': isRunning,
      'node-completed': isCompleted,
      'node-failed': isFailed,
      'node-skipped': isSkipped,
    }"
    :style="{ borderColor: getBorderColor() }"
    @click="handleNodeClick"
    @dblclick="handleNodeDoubleClick"
  >
    <div class="input-ports">
      <div
        v-for="port in data.inputs"
        :key="port.id"
        class="port-container"
        @mouseenter="handlePortHover(port.id, true)"
        @mouseleave="handlePortHover(port.id, false)"
      >
        <Handle
          type="target"
          :position="Position.Left"
          :id="port.id"
          class="port-handle"
          :class="{ 'port-required': port.required }"
        />
        <span class="port-icon">{{ getPortTypeIcon(port.type) }}</span>
        <span class="port-label">{{ port.name }}</span>
      </div>
    </div>

    <div v-if="isFailed" class="error-badge">✕</div>

    <div class="node-header" :style="{ backgroundColor: nodeColor }">
      <div
        class="breakpoint-indicator"
        :class="{
          'breakpoint-active': hasBreakpoint,
          'breakpoint-enabled': isBreakpointEnabled,
          'breakpoint-disabled': hasBreakpoint && !isBreakpointEnabled,
        }"
        @click="handleBreakpointClick"
        @contextmenu="handleBreakpointRightClick"
      >
        <span v-if="!hasBreakpoint" class="breakpoint-placeholder"></span>
        <span v-else-if="isBreakpointEnabled" class="breakpoint-dot"></span>
        <span v-else class="breakpoint-disabled-dot"></span>
      </div>
      <span class="node-icon">{{ nodeIcon }}</span>
      <span class="node-title">{{ nodeLabel }}</span>
      <span
        class="status-indicator"
        :style="{ backgroundColor: getStatusColor() }"
      >
        {{ getStatusIcon() }}
      </span>
    </div>

    <div v-if="isFailed && executionState?.error" class="node-error-tooltip">
      <div class="tooltip-title">错误</div>
      <div class="tooltip-message">{{ executionState.error }}</div>
    </div>

    <div v-if="isFailed && executionState?.error" class="node-error">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ executionState.error }}</span>
    </div>

    <div v-if="getExecutionDuration()" class="node-duration">
      {{ getExecutionDuration() }}
    </div>

    <div class="output-ports">
      <div
        v-for="port in data.outputs"
        :key="port.id"
        class="port-container"
        @mouseenter="handlePortHover(port.id, true)"
        @mouseleave="handlePortHover(port.id, false)"
      >
        <span class="port-label">{{ port.name }}</span>
        <span class="port-icon">{{ getPortTypeIcon(port.type) }}</span>
        <Handle
          type="source"
          :position="Position.Right"
          :id="port.id"
          class="port-handle"
        />
        <span v-if="port.condition" class="port-condition">📋</span>
      </div>

      <div
        v-if="data.error_port && isErrorPortVisible"
        class="port-container error-port"
        @mouseenter="handlePortHover('error', true)"
        @mouseleave="handlePortHover('error', false)"
      >
        <span class="port-label">{{ data.error_port.name }}</span>
        <span class="port-icon">⚠️</span>
        <Handle
          type="source"
          :position="Position.Right"
          id="error"
          class="port-handle port-handle-error"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.node-container {
  min-width: 200px;
  max-width: 280px;
  border: 2px solid #ddd;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  transition: all 0.2s ease;
  position: relative;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.node-selected {
  border-color: #3b82f6;
  box-shadow:
    0 0 0 3px rgba(59, 130, 246, 0.2),
    0 4px 12px rgba(0, 0, 0, 0.15);
  transform: scale(1.02);
}

.node-pending {
  border-color: #9ca3af;
  background: #f9fafb;
}

.node-running {
  border-color: #3b82f6;
  background: #eff6ff;
  animation: pulse 1.5s infinite;
}

.node-completed {
  border-color: #10b981;
  background: #f0fdf4;
}

.node-failed {
  border-color: #ef4444;
  border-width: 3px;
  background: #fee2e2;
}

.node-skipped {
  border-color: #f59e0b;
  opacity: 0.6;
  background: #fffbeb;
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
  }
}

.error-badge {
  position: absolute;
  top: -10px;
  right: -10px;
  width: 26px;
  height: 26px;
  background: #ef4444;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.4);
  animation: badge-pulse 2s infinite;
}

@keyframes badge-pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.input-ports,
.output-ports {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 4px;
}

.input-ports {
  align-items: flex-start;
}

.output-ports {
  align-items: flex-end;
}

.port-container {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.port-container:hover {
  background-color: rgba(59, 130, 246, 0.1);
}

.port-icon {
  font-size: 14px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.port-label {
  font-size: 12px;
  color: #4b5563;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.port-handle {
  width: 12px;
  height: 12px;
  border: 2px solid #6b7280;
  background: white;
  border-radius: 50%;
  transition: all 0.2s ease;
  z-index: 5;
}

.port-handle:hover {
  width: 16px;
  height: 16px;
  border-color: #3b82f6;
  background: #3b82f6;
}

.port-required {
  border-color: #ef4444;
}

.port-required::after {
  content: "*";
  position: absolute;
  top: -8px;
  right: -6px;
  color: #ef4444;
  font-size: 12px;
  font-weight: bold;
}

.port-handle-error {
  border-color: #ef4444;
}

.port-handle-error:hover {
  border-color: #ef4444;
  background: #ef4444;
}

.port-condition {
  font-size: 12px;
}

.error-port {
  background: rgba(239, 68, 68, 0.1);
}

.node-header {
  height: 44px;
  color: white;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  font-weight: 600;
  font-size: 14px;
  padding: 0 12px;
  gap: 8px;
}

.breakpoint-indicator {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 50%;
}

.breakpoint-indicator:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.breakpoint-placeholder {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background-color: transparent;
}

.breakpoint-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background-color: #ef4444;
  border: 2px solid white;
  box-shadow: 0 0 4px rgba(239, 68, 68, 0.6);
  animation: breakpoint-pulse 2s infinite;
}

.breakpoint-disabled-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background-color: #9ca3af;
  border: 2px solid white;
  opacity: 0.6;
}

@keyframes breakpoint-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(239, 68, 68, 0);
  }
}

.node-icon {
  font-size: 18px;
}

.node-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-indicator {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: white;
  font-weight: bold;
  border: 2px solid white;
}

.node-error-tooltip {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: #1f2937;
  color: white;
  padding: 12px;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  z-index: 100;
  min-width: 220px;
  max-width: 300px;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
  margin-top: 8px;
}

.node-container:hover .node-error-tooltip {
  opacity: 1;
  visibility: visible;
}

.node-error-tooltip::before {
  content: "";
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 8px solid transparent;
  border-bottom-color: #1f2937;
}

.tooltip-title {
  font-weight: 600;
  font-size: 14px;
  color: #ef4444;
  margin-bottom: 4px;
}

.tooltip-message {
  font-size: 13px;
  color: #e5e7eb;
  line-height: 1.5;
  word-wrap: break-word;
}

.node-error {
  padding: 8px 12px;
  background: #fee2e2;
  border-top: 1px solid #fecaca;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #dc2626;
}

.error-icon {
  font-size: 14px;
}

.error-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-duration {
  padding: 4px 12px;
  background: #f0fdf4;
  border-top: 1px solid #bbf7d0;
  font-size: 11px;
  color: #166534;
  text-align: right;
}
</style>
