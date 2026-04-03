<template>
  <div class="workflow-yaml-editor">
    <div class="editor-toolbar">
      <a-button
        type="primary"
        @click="applyYaml"
        :disabled="hasErrors || isSyncing"
        :loading="isSyncing"
      >
        <template #icon><CheckOutlined /></template>
        应用 (Ctrl+Enter)
      </a-button>
      <a-button @click="resetToCurrent" :disabled="isSyncing">
        <template #icon><ReloadOutlined /></template>
        重置
      </a-button>
      <div class="spacer"></div>
      <a-tooltip v-if="hasErrors" title="发现错误，请修复后再应用">
        <ExclamationCircleFilled class="error-indicator" />
      </a-tooltip>
      <a-tooltip v-else-if="isDirty" title="有未保存的修改">
        <EditOutlined class="dirty-indicator" />
      </a-tooltip>
    </div>

    <div class="editor-container" ref="editorContainer"></div>

    <div v-if="validationErrors.length > 0" class="error-panel">
      <div class="error-panel-title">
        <ExclamationCircleOutlined />
        验证错误
      </div>
      <ul class="error-list">
        <li
          v-for="(error, index) in validationErrors"
          :key="index"
          class="error-item"
        >
          <span class="error-line" v-if="error.line">行 {{ error.line }}:</span>
          <span class="error-message">{{ error.message }}</span>
        </li>
      </ul>
    </div>

    <div v-if="validationWarnings.length > 0" class="warning-panel">
      <div class="warning-panel-title">
        <WarningOutlined />
        警告
      </div>
      <ul class="warning-list">
        <li
          v-for="(warning, index) in validationWarnings"
          :key="index"
          class="warning-item"
        >
          <span class="warning-line" v-if="warning.line"
            >行 {{ warning.line }}:</span
          >
          <span class="warning-message">{{ warning.message }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue";
import { message } from "ant-design-vue";
import {
  CheckOutlined,
  ReloadOutlined,
  ExclamationCircleFilled,
  EditOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons-vue";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { yaml } from "@codemirror/lang-yaml";
import { keymap } from "@codemirror/view";
import { indentWithTab } from "@codemirror/commands";
import jsYaml from "js-yaml";
import { useDAGWorkflowStore } from "../../stores/dag-workflow";
import type {
  DAGWorkflow,
  BaseNodeData,
  EdgeData,
} from "../../types/dag-workflow";

const dagStore = useDAGWorkflowStore();

const editorContainer = ref<HTMLDivElement | null>(null);
const editorView = ref<EditorView | null>(null);
const isSyncing = ref(false);
const isDirty = ref(false);
const validationErrors = ref<{ line?: number; message: string }[]>([]);
const validationWarnings = ref<{ line?: number; message: string }[]>([]);
let syncTimer: ReturnType<typeof setTimeout> | null = null;
let lastSyncedYaml = ref("");

const hasErrors = computed(() => validationErrors.value.length > 0);

const theme = EditorView.theme({
  "&": {
    height: "100%",
    fontSize: "14px",
    background: "#0f172a",
    color: "#e2e8f0",
  },
  ".cm-content": {
    fontFamily: "'Monaco', 'Menlo', 'Ubuntu Mono', monospace",
    minHeight: "100%",
    color: "#e2e8f0",
  },
  ".cm-scroller": {
    overflow: "auto",
    minHeight: "100%",
  },
  ".cm-gutters": {
    background: "#1e293b",
    color: "#64748b",
    borderRight: "1px solid #334155",
  },
  ".cm-activeLineGutter": {
    background: "#1e293b",
    color: "#e2e8f0",
  },
  ".cm-activeLine": {
    background: "#1e293b",
  },
  "&.cm-focused .cm-cursor": {
    borderLeftColor: "#6366f1",
  },
  "&.cm-focused .cm-selectionBackground": {
    backgroundColor: "rgba(99, 102, 241, 0.3)",
  },
  ".cm-selectionMatch": {
    backgroundColor: "rgba(99, 102, 241, 0.2)",
  },
});

function initEditor() {
  if (!editorContainer.value) return;

  const initialYaml = dagStore.exportToYAML();
  lastSyncedYaml.value = initialYaml;

  const updateListener = EditorView.updateListener.of((update) => {
    if (update.docChanged) {
      const newYaml = update.state.doc.toString();
      isDirty.value = newYaml !== lastSyncedYaml.value;
      debouncedValidate(newYaml);
    }
  });

  const applyKeymap = keymap.of([
    {
      key: "Ctrl-Enter",
      run: () => {
        applyYaml();
        return true;
      },
    },
    indentWithTab,
  ]);

  editorView.value = new EditorView({
    state: EditorState.create({
      doc: initialYaml,
      extensions: [
        basicSetup,
        yaml(),
        theme,
        updateListener,
        applyKeymap,
        EditorView.lineWrapping,
      ],
    }),
    parent: editorContainer.value,
  });
}

function debouncedValidate(yamlStr: string) {
  if (syncTimer) {
    clearTimeout(syncTimer);
  }
  syncTimer = setTimeout(() => {
    validateYaml(yamlStr);
  }, 300);
}

function validateYaml(yamlStr: string) {
  validationErrors.value = [];
  validationWarnings.value = [];

  try {
    const parsed = jsYaml.load(yamlStr) as DAGWorkflow;

    if (!parsed) {
      validationErrors.value.push({ message: "YAML 内容为空" });
      return;
    }

    if (!parsed.version) {
      validationErrors.value.push({ message: "缺少必需字段: version" });
    }

    if (!parsed.name) {
      validationWarnings.value.push({ message: "缺少字段: name" });
    }

    if (!parsed.nodes) {
      validationErrors.value.push({ message: "缺少必需字段: nodes" });
    } else {
      const nodeIds = Object.keys(parsed.nodes);

      if (nodeIds.length === 0) {
        validationWarnings.value.push({ message: "没有定义任何节点" });
      }

      const hasStart = nodeIds.some((id) => parsed.nodes[id]?.type === "start");
      if (!hasStart) {
        validationErrors.value.push({ message: "缺少 Start 节点" });
      }

      const hasEnd = nodeIds.some((id) => parsed.nodes[id]?.type === "end");
      if (!hasEnd) {
        validationErrors.value.push({ message: "缺少 End 节点" });
      }

      const cycle = detectCycle(parsed.nodes, parsed.edges || []);
      if (cycle) {
        validationErrors.value.push({
          message: `检测到循环依赖: ${cycle.join(" → ")}`,
        });
      }

      validatePorts(parsed.nodes, parsed.edges || []);
    }

    if (parsed.edges) {
      validateEdges(parsed.nodes || {}, parsed.edges);
    }
  } catch (e: any) {
    let line = undefined;
    const lineMatch = e.message?.match(/line (\d+)/);
    if (lineMatch) {
      line = parseInt(lineMatch[1]);
    }
    validationErrors.value.push({
      line,
      message: `YAML 语法错误: ${e.message}`,
    });
  }
}

function detectCycle(
  nodes: Record<string, BaseNodeData>,
  edges: EdgeData[],
): string[] | null {
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  const path: string[] = [];

  function dfs(nodeId: string): string[] | null {
    if (recursionStack.has(nodeId)) {
      const cycleStart = path.indexOf(nodeId);
      return path.slice(cycleStart);
    }
    if (visited.has(nodeId)) {
      return null;
    }

    visited.add(nodeId);
    recursionStack.add(nodeId);
    path.push(nodeId);

    for (const edge of edges) {
      const sourceNodeId = edge.source.split(".")[0];
      if (sourceNodeId === nodeId) {
        const targetNodeId = edge.target.split(".")[0];
        const cycle = dfs(targetNodeId);
        if (cycle) {
          return cycle;
        }
      }
    }

    recursionStack.delete(nodeId);
    path.pop();
    return null;
  }

  for (const nodeId of Object.keys(nodes)) {
    if (!visited.has(nodeId)) {
      const cycle = dfs(nodeId);
      if (cycle) {
        return cycle;
      }
    }
  }

  return null;
}

function validatePorts(nodes: Record<string, BaseNodeData>, edges: EdgeData[]) {
  for (const edge of edges) {
    const [sourceNodeId, sourcePortId] = edge.source.split(".");
    const [targetNodeId, targetPortId] = edge.target.split(".");

    const sourceNode = nodes[sourceNodeId];
    if (sourceNode) {
      const hasOutputPort =
        sourceNode.outputs?.some((p) => p.id === sourcePortId) ||
        sourcePortId === "error";
      if (!hasOutputPort) {
        validationWarnings.value.push({
          message: `节点 ${sourceNodeId} 没有输出端口 ${sourcePortId}`,
        });
      }
    }

    const targetNode = nodes[targetNodeId];
    if (targetNode) {
      const hasInputPort = targetNode.inputs?.some(
        (p) => p.id === targetPortId,
      );
      if (!hasInputPort) {
        validationWarnings.value.push({
          message: `节点 ${targetNodeId} 没有输入端口 ${targetPortId}`,
        });
      }
    }
  }
}

function validateEdges(nodes: Record<string, BaseNodeData>, edges: EdgeData[]) {
  const nodeIds = new Set(Object.keys(nodes));

  for (const edge of edges) {
    const sourceNodeId = edge.source.split(".")[0];
    const targetNodeId = edge.target.split(".")[0];

    if (!nodeIds.has(sourceNodeId)) {
      validationErrors.value.push({
        message: `连线引用了不存在的源节点: ${sourceNodeId}`,
      });
    }

    if (!nodeIds.has(targetNodeId)) {
      validationErrors.value.push({
        message: `连线引用了不存在的目标节点: ${targetNodeId}`,
      });
    }
  }
}

function applyYaml() {
  if (hasErrors.value) {
    message.error("请先修复所有错误");
    return;
  }

  if (!editorView.value) return;

  try {
    isSyncing.value = true;
    const yamlStr = editorView.value.state.doc.toString();

    dagStore.loadFromYAML(yamlStr);
    lastSyncedYaml.value = yamlStr;
    isDirty.value = false;

    message.success("YAML 已应用");
  } catch (e: any) {
    message.error(`应用失败: ${e.message}`);
  } finally {
    isSyncing.value = false;
  }
}

function resetToCurrent() {
  if (!editorView.value) return;

  const currentYaml = dagStore.exportToYAML();
  lastSyncedYaml.value = currentYaml;

  editorView.value.dispatch({
    changes: {
      from: 0,
      to: editorView.value.state.doc.length,
      insert: currentYaml,
    },
  });

  isDirty.value = false;
  validationErrors.value = [];
  validationWarnings.value = [];

  message.info("已重置为当前工作流");
}

function syncFromStore() {
  if (isSyncing.value) return;

  const currentYaml = dagStore.exportToYAML();
  if (currentYaml === lastSyncedYaml.value) return;

  if (!editorView.value) return;

  lastSyncedYaml.value = currentYaml;
  editorView.value.dispatch({
    changes: {
      from: 0,
      to: editorView.value.state.doc.length,
      insert: currentYaml,
    },
  });

  isDirty.value = false;
  validationErrors.value = [];
  validationWarnings.value = [];
}

let storeWatchTimer: ReturnType<typeof setTimeout> | null = null;

watch(
  () => [dagStore.nodes, dagStore.edges, dagStore.name],
  () => {
    if (storeWatchTimer) {
      clearTimeout(storeWatchTimer);
    }
    storeWatchTimer = setTimeout(() => {
      syncFromStore();
    }, 300);
  },
  { deep: true },
);

onMounted(() => {
  nextTick(() => {
    initEditor();
  });
});

onUnmounted(() => {
  if (syncTimer) clearTimeout(syncTimer);
  if (storeWatchTimer) clearTimeout(storeWatchTimer);
  if (editorView.value) {
    editorView.value.destroy();
  }
});
</script>

<style scoped>
.workflow-yaml-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0f172a;
  border-radius: 8px;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #334155;
  background: #1e293b;
}

.spacer {
  flex: 1;
}

.error-indicator {
  color: #ef4444;
  font-size: 18px;
}

.dirty-indicator {
  color: #f59e0b;
  font-size: 18px;
}

.editor-container {
  flex: 1;
  min-height: 0;
  border-bottom: 1px solid #334155;
}

.error-panel,
.warning-panel {
  padding: 12px 16px;
  border-top: 1px solid #334155;
}

.error-panel {
  background: rgba(239, 68, 68, 0.1);
}

.warning-panel {
  background: rgba(245, 158, 11, 0.1);
}

.error-panel-title,
.warning-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 8px;
}

.error-panel-title {
  color: #ef4444;
}

.warning-panel-title {
  color: #f59e0b;
}

.error-list,
.warning-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.error-item,
.warning-item {
  padding: 4px 0;
  display: flex;
  gap: 8px;
}

.error-line,
.warning-line {
  font-weight: 600;
  color: #94a3b8;
}

.error-message {
  color: #ef4444;
}

.warning-message {
  color: #f59e0b;
}
</style>
