<script setup lang="ts">
import { ref, computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { NODE_TEMPLATES } from "../../../constants/node-templates";
import { useExecutionStore } from "../../../stores/execution";
import { useDAGWorkflowStore } from "../../../stores/dag-workflow";
import { generateId } from "../../../utils/id";
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
const dagStore = useDAGWorkflowStore();
const showDetail = ref(true);

const getNodeTemplate = (type: string) => {
  return NODE_TEMPLATES.find((t) => t.type === type);
};

const template = computed(() => getNodeTemplate(props.data?.type || ""));
const nodeIcon = computed(() => template.value?.icon || "\u{1F4E6}");
const nodeLabel = computed(
  () => props.data?.name || template.value?.label || "Node",
);
const inputPorts = computed(() => props.data.inputs || []);
const outputPorts = computed(() => props.data.outputs || []);

const addInputPort = (event: MouseEvent) => {
  event.stopPropagation();
  if (!props.id) return;
  const node = dagStore.nodes[props.id];
  if (!node) return;
  const newPort = { id: generateId(), name: `in_${(node.inputs || []).length + 1}`, type: "any" as const, required: false };
  dagStore.updateNode(props.id, { inputs: [...(node.inputs || []), newPort] });
};

const addOutputPort = (event: MouseEvent) => {
  event.stopPropagation();
  if (!props.id) return;
  const node = dagStore.nodes[props.id];
  if (!node) return;
  const newPort = { id: generateId(), name: `out_${(node.outputs || []).length + 1}`, type: "any" as const };
  dagStore.updateNode(props.id, { outputs: [...(node.outputs || []), newPort] });
};

const removeInputPort = (event: MouseEvent, portId: string) => {
  event.stopPropagation();
  if (!props.id) return;
  const node = dagStore.nodes[props.id];
  if (!node) return;
  dagStore.updateNode(props.id, { inputs: (node.inputs || []).filter((p) => p.id !== portId) });
};

const removeOutputPort = (event: MouseEvent, portId: string) => {
  event.stopPropagation();
  if (!props.id) return;
  const node = dagStore.nodes[props.id];
  if (!node) return;
  dagStore.updateNode(props.id, { outputs: (node.outputs || []).filter((p) => p.id !== portId) });
};

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

const getStatusIcon = () => {
  if (isRunning.value) return "\u26A1";
  if (isCompleted.value) return "\u2713";
  if (isFailed.value) return "\u2715";
  if (isSkipped.value) return "\u23ED";
  if (isPending.value) return "\u25CB";
  return "";
};

const getBorderColor = () => {
  if (isRunning.value) return "#3b82f6";
  if (isCompleted.value) return "#10b981";
  if (isFailed.value) return "#ef4444";
  if (isSkipped.value) return "#f59e0b";
  if (isPending.value) return "#334155";
  return "#334155";
};

const getBoxShadow = () => {
  if (isCompleted.value) return "0 0 8px rgba(16,185,129,0.35)";
  if (isRunning.value) return "0 0 12px rgba(59,130,246,0.25)";
  if (isFailed.value) return "0 0 8px rgba(239,68,68,0.35)";
  return "0 2px 4px rgba(0,0,0,0.2)";
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

const isErrorPortVisible = computed(() => {
  return !!(props.data.metadata?.showErrorPort || false) && !!props.data.error_port;
});

const breakpoint = computed<Breakpoint | undefined>(() => {
  if (!props.id) return undefined;
  return executionStore.getBreakpoint(props.id);
});

const hasBreakpoint = computed(() => breakpoint.value !== undefined);
const isBreakpointEnabled = computed(() => breakpoint.value?.enabled ?? false);

const toggleDetail = (event: MouseEvent) => {
  event.stopPropagation();
  showDetail.value = !showDetail.value;
};

const handleNodeClick = () => {
  if (props.id) emit("node-click", props.id);
};

const handleNodeDoubleClick = () => {
  if (props.id) emit("node-double-click", props.id);
};

const handleTitleClick = (event: MouseEvent) => {
  event.stopPropagation();
  if (props.id) dagStore.openConfig(props.id);
};

const handlePortHover = (portId: string, isHovered: boolean) => {
  emit("port-hover", portId, isHovered);
};

const handleBreakpointClick = (event: MouseEvent) => {
  event.stopPropagation();
  if (!props.id) return;
  if (hasBreakpoint.value && breakpoint.value) {
    executionStore.toggleBreakpoint(breakpoint.value.id);
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
    class="browser-node"
    :class="{
      'node-selected': selected,
      'node-pending': isPending,
      'node-running': isRunning,
      'node-completed': isCompleted,
      'node-failed': isFailed,
      'node-skipped': isSkipped,
      'expanded-detail': showDetail,
    }"
    :style="{ borderColor: getBorderColor(), boxShadow: getBoxShadow() }"
    @click="handleNodeClick"
    @dblclick="handleNodeDoubleClick"
  >
    <div class="input-ports">
      <div
        v-for="port in (data.inputs || [])"
        :key="port.id"
        class="port-container port-container-input"
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
        <span class="port-label port-label-input">{{ port.name }}</span>
      </div>
    </div>

    <div class="browser-titlebar" :class="{ 'titlebar-rounded-bottom': !showDetail }">
      <div class="titlebar-left">
        <span class="node-icon">{{ nodeIcon }}</span>
        <span class="node-title" :title="template?.description" @click="handleTitleClick">{{ nodeLabel }}</span>
      </div>
      <div class="titlebar-right">
        <span
          class="status-indicator"
          :class="{
            'status-running': isRunning,
            'status-completed': isCompleted && !isFailed,
            'status-failed': isFailed,
            'status-skipped': isSkipped,
          }"
          :title="isRunning ? '运行中' : isCompleted ? '已完成' : isFailed ? '失败' : isSkipped ? '已跳过' : '等待'"
        >{{ getStatusIcon() }}</span>
        <span
          class="breakpoint-dot-wrap"
          :class="{
            active: hasBreakpoint,
            enabled: isBreakpointEnabled,
            disabled: hasBreakpoint && !isBreakpointEnabled,
          }"
          :title="hasBreakpoint ? (isBreakpointEnabled ? '断点已启用（右键删除）' : '断点已禁用') : '添加断点'"
          @click="handleBreakpointClick"
          @contextmenu="handleBreakpointRightClick"
        ></span>
        <button class="more-btn" @click="toggleDetail" :title="showDetail ? '收起' : '展开'">
          {{ showDetail ? '\u25B2' : '\u25BC' }}
        </button>
      </div>
    </div>

    <div class="browser-content" v-show="showDetail">
      <div v-if="inputPorts.length > 0 || outputPorts.length > 0" class="ports-section">
        <div v-if="inputPorts.length > 0" class="port-group">
          <div class="port-group-label">输入</div>
          <div class="content-row" v-for="port in inputPorts" :key="port.id">
            <span class="row-label row-input">{{ port.name }}</span>
            <span class="row-value">{{ port.type }}</span>
            <span class="port-remove-btn" @click="removeInputPort($event, port.id)" title="删除端口">×</span>
          </div>
          <div class="add-port-btn" @click="addInputPort($event)" title="添加输入端口">+ 输入</div>
        </div>
        <div v-if="outputPorts.length > 0" class="port-group">
          <div class="port-group-label">输出</div>
          <div class="content-row" v-for="port in outputPorts" :key="port.id">
            <span class="row-label row-output">{{ port.name }}</span>
            <span class="row-value">{{ port.type }}</span>
            <span class="port-remove-btn" @click="removeOutputPort($event, port.id)" title="删除端口">×</span>
          </div>
          <div class="add-port-btn" @click="addOutputPort($event)" title="添加输出端口">+ 输出</div>
        </div>
      </div>
      <div v-else class="add-ports-row">
        <div class="add-port-btn" @click="addInputPort($event)">+ 输入</div>
        <div class="add-port-btn" @click="addOutputPort($event)">+ 输出</div>
      </div>

      <div v-if="isFailed && executionState?.error" class="error-row">
        <span class="row-label">错误</span>
        <span class="row-error">{{ executionState.error }}</span>
      </div>

      <div v-if="getExecutionDuration()" class="duration-row">
        <span class="row-label">耗时</span>
        <span class="row-duration">{{ getExecutionDuration() }}</span>
      </div>
    </div>

    <div class="output-ports">
      <div
        v-for="port in (data.outputs || [])"
        :key="port.id"
        class="port-container port-container-output"
        @mouseenter="handlePortHover(port.id, true)"
        @mouseleave="handlePortHover(port.id, false)"
      >
        <span class="port-label port-label-output">{{ port.name }}</span>
        <Handle
          type="source"
          :position="Position.Right"
          :id="port.id"
          class="port-handle"
        />
      </div>
      <div
        v-if="data.error_port && isErrorPortVisible"
        class="port-container port-container-output error-port"
        @mouseenter="handlePortHover('error', true)"
        @mouseleave="handlePortHover('error', false)"
      >
        <span class="port-label port-label-output">Error</span>
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
.browser-node {
  min-width: 200px;
  max-width: 280px;
  border: 1px solid #2a2d37;
  border-radius: 4px;
  background: #1a1b1f;
  transition: all 0.15s ease;
  position: relative;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.node-selected {
  border-color: #4a90d9 !important;
  box-shadow: 0 0 0 1px #4a90d9, 0 2px 12px rgba(74, 144, 217, 0.3) !important;
  z-index: 10;
}

.node-running {
  border-color: #4a90d9;
  animation: pulse-border 2s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4); }
  50% { box-shadow: 0 0 0 1px #4a90d9, 0 2px 12px rgba(74, 144, 217, 0.4); }
}

.node-completed {
  border-color: #3a925a;
}
.node-failed {
  border-color: #d94a4a;
  border-width: 1px;
}
.node-skipped { opacity: 0.6; }

.input-ports,
.output-ports {
  display: flex;
  flex-direction: column;
  gap: 0px;
  padding: 2px 2px;
  position: absolute;
  top: 28px;
}
.input-ports {
  left: 0;
  align-items: flex-start;
}
.output-ports {
  right: 0;
  align-items: flex-end;
}

.port-container {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 0;
  border-radius: 2px;
  transition: background-color 0.1s ease;
  position: relative;
}
.port-container-input {
  flex-direction: row;
  padding-left: 2px;
}
.port-container-output {
  flex-direction: row-reverse;
  padding-right: 2px;
}
.port-container:hover {
  background-color: rgba(74, 144, 217, 0.1);
}

.port-label {
  opacity: 0;
  transition: opacity 0.15s;
  white-space: nowrap;
  font-size: 10px;
  color: #94a3b8;
  pointer-events: none;
  user-select: none;
  line-height: 1;
}
.port-container:hover .port-label {
  opacity: 1;
}

.port-handle {
  width: 12px;
  height: 12px;
  border: 2px solid #5a5f6e;
  background: #1a1b1f;
  border-radius: 3px;
  transition: all 0.1s ease;
  z-index: 5;
  flex-shrink: 0;
}
.port-handle:hover {
  border-color: #4a90d9;
  background: #4a90d9;
  box-shadow: 0 0 6px rgba(74, 144, 217, 0.6);
}
.port-required {
  border-color: #d94a4a;
}
.port-handle-error {
  border-color: #d94a4a;
}
.port-handle-error:hover {
  border-color: #d94a4a;
  background: #d94a4a;
}
.error-port {
  background: rgba(217, 74, 74, 0.08);
}

.browser-titlebar {
  height: 28px;
  color: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  gap: 6px;
  user-select: none;
  cursor: default;
  position: relative;
  background: #2a2d37;
  border-bottom: 1px solid #1f2128;
  border-radius: 4px 4px 0 0;
}
.browser-titlebar.titlebar-rounded-bottom {
  border-radius: 4px;
  border-bottom: none;
}

.titlebar-left {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.node-icon {
  font-size: 11px;
  flex-shrink: 0;
}

.node-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  font-size: 11px;
  letter-spacing: 0.2px;
  cursor: pointer;
}
.node-title:hover {
  color: #6366f1;
  text-decoration: underline dotted;
}

.titlebar-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.breakpoint-dot-wrap {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  border: 1.5px solid #5a5f6e;
  background: transparent;
  cursor: pointer;
  transition: all 0.1s;
  flex-shrink: 0;
}
.breakpoint-dot-wrap.active.enabled {
  background: #d94a4a;
  border-color: #d94a4a;
}
.breakpoint-dot-wrap.active.disabled {
  background: #5a5f6e;
  border-color: #5a5f6e;
  opacity: 0.5;
}
.breakpoint-dot-wrap:hover {
  border-color: #8a8f9e;
}

.status-indicator {
  width: 14px;
  height: 14px;
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  color: #1a1b1f;
  font-weight: bold;
  flex-shrink: 0;
  background: #3a3d47;
  cursor: default;
}
.status-indicator.status-running {
  background: #3b82f6;
  animation: status-blink 1s ease-in-out infinite;
}
.status-indicator.status-completed {
  background: #10b981;
}
.status-indicator.status-failed {
  background: #ef4444;
}
.status-indicator.status-skipped {
  background: #f59e0b;
}

@keyframes status-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.more-btn {
  width: 16px;
  height: 16px;
  border: none;
  background: transparent;
  color: #8a8f9e;
  border-radius: 2px;
  cursor: pointer;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.1s;
  line-height: 1;
  flex-shrink: 0;
}
.more-btn:hover {
  background: #3a3d47;
  color: #e0e0e0;
}

.browser-content {
  padding: 4px 6px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: #1a1b1f;
  max-height: 160px;
  overflow-y: auto;
  border-radius: 0 0 4px 4px;
}

.browser-content::-webkit-scrollbar {
  width: 4px;
}
.browser-content::-webkit-scrollbar-thumb {
  background: #3a3d47;
  border-radius: 2px;
}
.browser-content::-webkit-scrollbar-track {
  background: #1a1b1f;
}

.ports-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.port-group {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.port-group-label {
  font-size: 9px;
  color: #5a5f6e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 2px 3px 0;
}

.add-port-btn {
  font-size: 10px;
  color: #5a5f6e;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px dashed #3a3d47;
  text-align: center;
  margin-top: 2px;
  transition: all 0.15s;
  user-select: none;
}
.add-port-btn:hover {
  color: #6366f1;
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
}

.add-ports-row {
  display: flex;
  gap: 4px;
}
.add-ports-row .add-port-btn {
  flex: 1;
}

.port-remove-btn {
  font-size: 10px;
  color: #5a5f6e;
  cursor: pointer;
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
  flex-shrink: 0;
  transition: all 0.1s;
  line-height: 1;
}
.port-remove-btn:hover {
  color: #d94a4a;
  background: rgba(217, 74, 74, 0.12);
}

.content-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 3px;
  border-radius: 2px;
  transition: background 0.1s;
}
.content-row:hover {
  background: #2a2d37;
}

.row-label {
  font-size: 10px;
  color: #7a7f8e;
  font-weight: 500;
  min-width: 34px;
  flex-shrink: 0;
  text-align: right;
}
.row-value {
  font-size: 10px;
  color: #c0c0c0;
  font-family: "Consolas", "Monaco", monospace;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row-input {
  color: #6aa0d9;
}
.row-output {
  color: #6ad98a;
}

.error-row {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 3px 3px;
  border-top: 1px solid #2a2d37;
  margin-top: 1px;
}
.row-error {
  font-size: 9px;
  color: #d96a6a;
  word-break: break-all;
  line-height: 1.3;
}

.duration-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 3px;
  border-top: 1px solid #2a2d37;
  margin-top: 1px;
}
.row-duration {
  font-size: 9px;
  color: #6ad98a;
  font-family: "Consolas", "Monaco", monospace;
  font-weight: 500;
}
</style>
