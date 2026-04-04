<template>
  <div class="workflow-editor">
    <Toolbar
      :view-mode="viewMode"
      @open-example-selector="showExampleSelector = true"
      @view-change="(mode) => (viewMode = mode as ViewMode)"
    />

    <div class="editor-body">
      <aside class="editor-sidebar" :class="{ collapsed: paletteCollapsed }">
        <div class="palette-container">
          <NodePalette :collapsed="paletteCollapsed" />
        </div>

        <div class="sidebar-bottom-section">
          <div class="sidebar-panels">
            <div
              v-for="panel in sidePanels"
              :key="panel.key"
              class="side-tab"
              :class="{ active: activeSidePanel === panel.key }"
              @click="activeSidePanel = activeSidePanel === panel.key ? '' : panel.key"
              :title="panel.label"
            >
              <span class="tab-icon">
                <component :is="panel.icon" />
              </span>
              <span class="tab-label">{{ panel.label }}</span>
              <span v-if="panel.badge > 0" class="tab-badge">{{ panel.badge }}</span>
            </div>
          </div>

          <transition name="slide-down">
            <div v-if="activeSidePanel && !paletteCollapsed" class="side-panel-content">
              <div class="panel-header">
                <span class="panel-title">{{ activeSidePanel === 'logs' ? '执行日志' : activeSidePanel === 'variables' ? '变量面板' : '调试面板' }}</span>
                <CloseOutlined class="panel-close" @click="activeSidePanel = ''" />
              </div>
              <div class="panel-body">
                <ExecutionLogPanelContent v-if="activeSidePanel === 'logs'" />
                <VariablePanelContent v-if="activeSidePanel === 'variables'" />
                <DebugPanelContent v-if="activeSidePanel === 'debug'" />
              </div>
            </div>
          </transition>
        </div>

      </aside>

      <button
        class="palette-toggle"
        @click="paletteCollapsed = !paletteCollapsed"
        :title="paletteCollapsed ? '展开节点库' : '折叠节点库'"
      >
        <LeftOutlined v-if="!paletteCollapsed" />
        <RightOutlined v-else />
      </button>

      <main class="editor-main">
        <div v-show="viewMode !== 'yaml'" class="canvas-area">
          <Canvas :node-types="nodeTypes" :edge-types="edgeTypes" />
        </div>

        <div v-show="viewMode !== 'visual'" class="yaml-area">
          <WorkflowYamlEditor />
        </div>


      </main>
    </div>

    <NodeConfigPanel />
    <ExampleSelectorModal
      v-model:visible="showExampleSelector"
      @import-example="handleImportExample"
    />

    <ExecutionStats />

    <div v-if="runsStore.currentRun || runsStore.error" class="results-section">
      <ResultsPanel :run="runsStore.currentRun" :error="runsStore.error" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, markRaw, computed } from "vue";
import { message, Modal } from "ant-design-vue";
import {
  Canvas,
  NodePalette,
  NodeConfigPanel,
  Toolbar,
  ExampleSelectorModal,
  WorkflowYamlEditor,
  ExecutionStats,
  CustomEdge,
} from "../components/workflow";
import { GenericNode } from "../components/workflow/nodes";
import {
  LeftOutlined,
  RightOutlined,
  CloseOutlined,
  FileTextOutlined as LogIcon,
  BarChartOutlined as VarIcon,
  ToolOutlined as DebugIcon,
} from "@ant-design/icons-vue";
const LOG_ICON = markRaw(LogIcon);
const VAR_ICON = markRaw(VarIcon);
const DEBUG_ICON = markRaw(DebugIcon);
import ResultsPanel from "../components/run/ResultsPanel.vue";
import { useDAGWorkflowStore } from "../stores/dag-workflow";
import { useRunsStore } from "../stores/runs";
import { useExecutionStore } from "../stores/execution";
import { useNodeMetaStore } from "../stores/node-meta";
import type { Example } from "../types/workflow";
import ExecutionLogPanelContent from "./_ExecutionLogPanelContent.vue";
import VariablePanelContent from "./_VariablePanelContent.vue";
import DebugPanelContent from "./_DebugPanelPanelContent.vue";

type ViewMode = "visual" | "yaml" | "split";

const workflowStore = useDAGWorkflowStore();
const runsStore = useRunsStore();
const executionStore = useExecutionStore();
const nodeMetaStore = useNodeMetaStore();

const viewMode = ref<ViewMode>("visual");
const showExampleSelector = ref(false);
const paletteCollapsed = ref(false);
const activeSidePanel = ref("");

const sidePanels = computed(() => [
  {
    key: "logs",
    label: "执行日志",
    icon: LOG_ICON,
    badge: executionStore.logs.length,
  },
  {
    key: "variables",
    label: "变量面板",
    icon: VAR_ICON,
    badge: Object.keys(executionStore.variables).length,
  },
  {
    key: "debug",
    label: "调试面板",
    icon: DEBUG_ICON,
    badge: executionStore.isDebugMode ? 1 : 0,
  },
]);

const handleGlobalKeyDown = (event: KeyboardEvent) => {
  if (
    (event.ctrlKey || event.metaKey) &&
    event.shiftKey &&
    event.key.toLowerCase() === "i"
  ) {
    showExampleSelector.value = true;
    event.preventDefault();
  }
};

const edgeTypes = {
  custom: markRaw(CustomEdge),
};

// All node types render as GenericNode — the card reads node.data for display.
// Plugin-provided action types (not in this map) also fall back to GenericNode
// via VueFlow's default node type.
const GenericNodeRaw = markRaw(GenericNode);
const nodeTypes: Record<string, any> = {
  start: GenericNodeRaw,
  end: GenericNodeRaw,
  input: GenericNodeRaw,
  action: GenericNodeRaw,
  pass: GenericNodeRaw,
  if: GenericNodeRaw,
  switch: GenericNodeRaw,
  for: GenericNodeRaw,
  while: GenericNodeRaw,
  retry: GenericNodeRaw,
  merge: GenericNodeRaw,
  split: GenericNodeRaw,
  group: GenericNodeRaw,
  subflow: GenericNodeRaw,
  "core.log": GenericNodeRaw,
};

const handleImportExample = (example: Example) => {
  Modal.confirm({
    title: "导入示例",
    content: "请选择导入方式：",
    okText: "覆盖当前",
    cancelText: "追加到当前",
    onOk: () => {
      workflowStore.loadFromExample(example.yamlContent, "overwrite");
      message.success("示例已导入（覆盖模式）");
    },
    onCancel: () => {
      workflowStore.loadFromExample(example.yamlContent, "append");
      message.success("示例已追加到当前工作流");
    },
  });
};

watch(
  () => [workflowStore.nodes, workflowStore.edges],
  () => {
    workflowStore.saveToLocalStorage();
  },
  { deep: true },
);

onMounted(() => {
  nodeMetaStore.fetchMetas();
  workflowStore.loadFromLocalStorage();
  window.addEventListener("keydown", handleGlobalKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleGlobalKeyDown);
});
</script>

<style scoped>
.workflow-editor {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: #0f172a;
}

.editor-body {
  display: flex;
  height: calc(100% - 40px);
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.editor-sidebar {
  width: 280px;
  min-width: 280px;
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 100;
  background: #0f172a;
  overflow: hidden;
}

.editor-sidebar.collapsed {
  width: 60px;
  min-width: 60px;
}

.palette-container {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-bottom-section {
  flex: 0 0 108px;
  display: flex;
  flex-direction: column;
  height: 108px;
  max-height: 108px;
  overflow: hidden;
  border-top: 1px solid #334155;
}

.palette-toggle {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  left: 266px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: #334155;
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  font-size: 12px;
  transition: left 0.2s ease, background 0.2s ease, color 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.editor-sidebar.collapsed ~ .palette-toggle {
  left: 46px;
}

.palette-toggle:hover {
  background: #475569;
  color: #e2e8f0;
}

.sidebar-panels {
  border-top: 1px solid #334155;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.side-tab {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  height: 36px;
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  user-select: none;
}

.side-tab:hover {
  background: #1e293b;
  color: #e2e8f0;
}

.side-tab.active {
  background: #334155;
  color: #e2e8f0;
  border-left: 3px solid #6366f1;
  padding-left: 13px;
}

.tab-icon {
  display: flex;
  align-items: center;
  font-size: 14px;
}

.tab-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-badge {
  background: #6366f1;
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 9999px;
  min-width: 18px;
  text-align: center;
}

.editor-sidebar.collapsed .tab-label,
.editor-sidebar.collapsed .tab-badge {
  display: none;
}

.editor-sidebar.collapsed .side-tab {
  justify-content: center;
  padding: 0;
}

.side-panel-content {
  flex: 1;
  background: #1e293b;
  border-top: 1px solid #334155;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #334155;
  flex-shrink: 0;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.panel-close {
  color: #64748b;
  cursor: pointer;
  font-size: 14px;
  transition: color 0.15s;
  padding: 4px;
}

.panel-close:hover {
  color: #ef4444;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
}

.slide-down-enter-to,
.slide-down-leave-from {
  opacity: 1;
  max-height: 250px;
}

.editor-main {
  flex: 1;
  display: flex;
  min-width: 0;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.canvas-area {
  flex: 1;
  min-height: 0;
  position: relative;
}

.yaml-area {
  flex: 1;
  min-height: 0;
  border-left: 1px solid #334155;
  overflow: auto;
}


.results-section {
  margin-top: 20px;
}
</style>
