<template>
  <div class="workflow-editor">
    <Toolbar @open-example-selector="showExampleSelector = true" />
    <ExecutionStats />

    <a-row :gutter="24" class="main-content">
      <a-col
        v-if="viewMode !== 'yaml'"
        :xs="24"
        :md="24"
        :lg="5"
        class="column-left"
      >
        <NodePalette />
      </a-col>

      <a-col
        :xs="24"
        :md="24"
        :lg="viewMode === 'split' ? 12 : 19"
        class="column-middle"
        v-show="viewMode !== 'yaml'"
      >
        <Canvas :node-types="nodeTypes" />
      </a-col>

      <a-col
        :xs="24"
        :md="24"
        :lg="viewMode === 'split' ? 7 : 19"
        class="column-yaml"
        v-show="viewMode !== 'visual'"
      >
        <WorkflowYamlEditor />
      </a-col>
    </a-row>

    <div class="view-mode-switcher">
      <a-radio-group v-model:value="viewMode" button-style="solid" size="small">
        <a-radio-button value="visual">
          <template #icon><EyeOutlined /></template>
          可视化
        </a-radio-button>
        <a-radio-button value="yaml">
          <template #icon><FileTextOutlined /></template>
          YAML
        </a-radio-button>
        <a-radio-button value="split">
          <template #icon><AppstoreOutlined /></template>
          分屏
        </a-radio-button>
      </a-radio-group>
      <div class="panel-toggles">
        <ExecutionLogPanel />
        <VariablePanel />
        <DebugPanel />
      </div>
      <div class="shortcuts-hint">
        <a-tag color="blue">Ctrl+Enter 应用 YAML</a-tag>
      </div>
    </div>

    <NodeConfigPanel />
    <ExampleSelectorModal
      v-model:visible="showExampleSelector"
      @import-example="handleImportExample"
    />

    <div v-if="runsStore.currentRun || runsStore.error" class="results-section">
      <ResultsPanel :run="runsStore.currentRun" :error="runsStore.error" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, markRaw } from "vue";
import { message, Modal } from "ant-design-vue";
import {
  Canvas,
  NodePalette,
  NodeConfigPanel,
  Toolbar,
  ExecutionLogPanel,
  ExecutionStats,
  ExampleSelectorModal,
  WorkflowYamlEditor,
  VariablePanel,
  DebugPanel,
} from "../components/workflow";
import {
  StartNode,
  EndNode,
  ActionNode,
  PassNode,
  IfNode,
  SwitchNode,
  ForNode,
  WhileNode,
  RetryNode,
  MergeNode,
  SplitNode,
  GroupNode,
  SubflowNode,
  OutputNode,
  LLMNode,
  PythonNode,
  APINode,
  ConditionNode,
  LoopNode,
  GenericNode,
} from "../components/workflow/nodes";
import {
  EyeOutlined,
  FileTextOutlined,
  AppstoreOutlined,
} from "@ant-design/icons-vue";
import ResultsPanel from "../components/run/ResultsPanel.vue";
import { useWorkflowStore } from "../stores/workflow";
import { useRunsStore } from "../stores/runs";
import { yamlToWorkflow } from "../utils/workflow-yaml";
import type { Example } from "../types/workflow";

type ViewMode = "visual" | "yaml" | "split";

const workflowStore = useWorkflowStore();
const runsStore = useRunsStore();

const viewMode = ref<ViewMode>("visual");
const showExampleSelector = ref(false);

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

const nodeTypes = {
  start: markRaw(StartNode),
  end: markRaw(EndNode),
  action: markRaw(ActionNode),
  pass: markRaw(PassNode),
  if: markRaw(IfNode),
  switch: markRaw(SwitchNode),
  for: markRaw(ForNode),
  while: markRaw(WhileNode),
  retry: markRaw(RetryNode),
  merge: markRaw(MergeNode),
  split: markRaw(SplitNode),
  group: markRaw(GroupNode),
  subflow: markRaw(SubflowNode),
  output: markRaw(OutputNode),
  llm: markRaw(LLMNode),
  python: markRaw(PythonNode),
  api: markRaw(APINode),
  condition: markRaw(ConditionNode),
  loop: markRaw(LoopNode),
  "core.log": markRaw(GenericNode),
  "core.set_var": markRaw(GenericNode),
  "core.wait": markRaw(GenericNode),
  "core.if": markRaw(GenericNode),
  "core.switch": markRaw(GenericNode),
  "core.loop": markRaw(GenericNode),
  "browser.navigate": markRaw(GenericNode),
  "browser.click": markRaw(GenericNode),
  "browser.type": markRaw(GenericNode),
  "browser.screenshot": markRaw(GenericNode),
  "browser.get_text": markRaw(GenericNode),
  "browser.get_attribute": markRaw(GenericNode),
  "browser.scroll": markRaw(GenericNode),
  "browser.wait_for": markRaw(GenericNode),
  "tool.http_request": markRaw(GenericNode),
  "tool.read_file": markRaw(GenericNode),
  "tool.write_file": markRaw(GenericNode),
  "tool.exec": markRaw(GenericNode),
  "tool.sleep": markRaw(GenericNode),
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
    if (workflowStore.isDirty) {
      workflowStore.saveToLocalStorage();
    }
  },
  { deep: true },
);

onMounted(() => {
  // 添加调试函数到 window
  (window as any).debugYamlToWorkflow = () => {
    const testYaml = `version: "1"
name: "demo-flow"
steps:
  - id: "hello"
    action:
      type: "core.log"
      params:
        message: "Hello AutoFlow!"
`;
    console.log("=== Debug yamlToWorkflow ===");
    console.log("Input YAML:", testYaml);
    const result = yamlToWorkflow(testYaml);
    console.log("Result:", result);
    console.log("Nodes:", result.nodes);
    console.log("Edges:", result.edges);
    return result;
  };
  (window as any).resetWorkflow = () => {
    localStorage.removeItem("autoflow_workflow");
    workflowStore.reset();
    console.log("Workflow reset!");
  };
  (window as any).loadTestWorkflow = () => {
    const testYaml = `version: "1"
name: "demo-flow"
steps:
  - id: "hello"
    action:
      type: "core.log"
      params:
        message: "Hello AutoFlow!"
`;
    console.log("Loading test workflow...");
    workflowStore.loadFromYAML(testYaml);
    console.log("Loaded! Nodes:", workflowStore.nodes);
    console.log("Loaded! Edges:", workflowStore.edges);
  };

  workflowStore.loadFromLocalStorage();
  window.addEventListener("keydown", handleGlobalKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleGlobalKeyDown);
});
</script>

<style scoped>
.workflow-editor {
  max-width: 1600px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.main-content {
  flex: 1;
  min-height: 0;
  margin-bottom: 24px;
}

.column-left,
.column-middle,
.column-yaml {
  height: 100%;
  min-height: 500px;
}

.column-yaml {
  height: 100%;
}

.view-mode-switcher {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
  gap: 12px;
}

.panel-toggles {
  display: flex;
  gap: 8px;
  align-items: center;
}

.shortcuts-hint {
  display: flex;
  gap: 8px;
}

.results-section {
  margin-top: 24px;
}
</style>
