<template>
  <div class="page-header">
    <div class="header-left">
      <BranchesOutlined class="title-icon" />
      <a-input
        v-model:value="workflowName"
        class="workflow-name-input"
        placeholder="Untitled Workflow"
        @blur="handleNameChange"
      />
    </div>
    <div class="header-right">
      <a-button @click="handleLoadExample" size="small">
        <FileTextOutlined />
        导入示例
      </a-button>
      <a-button @click="handleSaveAsExample" size="small">
        <BookOutlined />
        保存为示例
      </a-button>
      <a-button @click="handleExportYaml" size="small">
        <DownloadOutlined />
        导出YAML
      </a-button>
      <a-button @click="handleSave" size="small">
        <SaveOutlined />
        保存
      </a-button>
      <a-button @click="handleReset" size="small">
        <ClearOutlined />
        重置
      </a-button>
      <a-button v-if="executionStore.isRunning" danger size="small" @click="handleStop">
        <StopOutlined />
        停止
      </a-button>
      <a-button v-if="executionStore.isRunning" size="small" @click="handlePause">
        <PauseCircleOutlined />
        暂停
      </a-button>
      <a-button
        v-if="executionStore.isPaused"
        type="primary"
        size="small"
        @click="handleResume"
      >
        <CaretRightOutlined />
        继续
      </a-button>
      <a-button
        v-if="!executionStore.isRunning && !executionStore.isPaused"
        type="primary"
        size="small"
        @click="handleExecute"
      >
        <PlayCircleOutlined />
        执行
      </a-button>
    </div>

    <SaveExampleModal
      v-model:visible="showSaveExampleModal"
      :yaml-content="currentYamlContent"
      :default-name="workflowName"
      @saved="handleExampleSaved"
    />
    <ExportYamlModal
      v-model:visible="showExportModal"
      :yaml-content="currentYamlContent"
      :file-name="workflowName"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  BranchesOutlined,
  SaveOutlined,
  ClearOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  StopOutlined,
  BookOutlined,
  DownloadOutlined,
  PauseCircleOutlined,
  CaretRightOutlined,
} from "@ant-design/icons-vue";
import { message } from "ant-design-vue";
import { useDAGWorkflowStore } from "../../stores/dag-workflow";
import { useExecutionStore } from "../../stores/execution";
import SaveExampleModal from "./SaveExampleModal.vue";
import ExportYamlModal from "./ExportYamlModal.vue";

const workflowStore = useDAGWorkflowStore();
const executionStore = useExecutionStore();

const workflowName = ref(workflowStore.name);
const showSaveExampleModal = ref(false);
const showExportModal = ref(false);

const currentYamlContent = computed(() => {
  return workflowStore.exportToYAML();
});

interface Emits {
  (e: "open-example-selector"): void;
}

const emit = defineEmits<Emits>();

const handleNameChange = () => {
  workflowStore.setName(workflowName.value);
};

const handleLoadExample = () => {
  emit("open-example-selector");
};

const handleSaveAsExample = () => {
  if (Object.keys(workflowStore.nodes).length === 0) {
    message.warning("请先添加节点再保存为示例");
    return;
  }
  showSaveExampleModal.value = true;
};

const handleExampleSaved = () => {
  message.success("示例保存成功！");
};

const handleExportYaml = () => {
  if (Object.keys(workflowStore.nodes).length === 0) {
    message.warning("请先添加节点再导出YAML");
    return;
  }
  showExportModal.value = true;
};

const handleSave = () => {
  workflowStore.saveToLocalStorage();
  message.success("工作流已保存");
};

const handleReset = () => {
  workflowStore.reset();
  workflowName.value = workflowStore.name;
  executionStore.resetExecution();
  message.info("工作流已重置");
};

const handleStop = () => {
  executionStore.stopExecution();
  message.info("执行已停止");
};

const handlePause = () => {
  executionStore.pauseExecution();
  message.info("执行已暂停");
};

const handleResume = () => {
  executionStore.resumeExecution();
  message.info("继续执行");
};

const waitIfPaused = async () => {
  return new Promise<void>((resolve) => {
    const check = () => {
      if (executionStore.isPaused) {
        setTimeout(check, 100);
      } else {
        resolve();
      }
    };
    check();
  });
};

const simulateExecution = async () => {
  const nodesRecord = workflowStore.nodes;
  const nodeIds = Object.keys(nodesRecord);
  const edges = workflowStore.edges;

  if (nodeIds.length === 0) {
    message.warning("请先添加节点");
    return;
  }

  const startNodeEntry = Object.entries(nodesRecord).find(([, n]) => n.type === "start");
  if (!startNodeEntry) {
    message.warning("请先添加开始节点");
    return;
  }
  const startNodeId = startNodeEntry[0];

  const inDegree = new Map<string, number>(nodeIds.map((id) => [id, 0]));
  const adjacencyList = new Map<string, string[]>(nodeIds.map((id) => [id, []]));
  const inputEdgesMap = new Map<string, string[]>(nodeIds.map((id) => [id, []]));
  const outputEdgesMap = new Map<string, string[]>(nodeIds.map((id) => [id, []]));

  edges.forEach((edge) => {
    const src = edge.source.split(".")[0];
    const tgt = edge.target.split(".")[0];
    adjacencyList.get(src)?.push(tgt);
    inDegree.set(tgt, (inDegree.get(tgt) || 0) + 1);
    inputEdgesMap.get(tgt)?.push(edge.id);
    outputEdgesMap.get(src)?.push(edge.id);
  });

  const queue: string[] = [];
  const topoOrder: string[] = [];

  inDegree.forEach((degree, nodeId) => {
    if (degree === 0 && nodeId === startNodeId) {
      queue.push(nodeId);
    }
  });

  while (queue.length > 0) {
    const current = queue.shift()!;
    topoOrder.push(current);
    const neighbors = adjacencyList.get(current) || [];
    for (const neighbor of neighbors) {
      const newDegree = (inDegree.get(neighbor) || 0) - 1;
      inDegree.set(neighbor, newDegree);
      if (newDegree === 0) queue.push(neighbor);
    }
  }

  if (topoOrder.length !== nodeIds.length) {
    message.error("检测到循环依赖，无法执行工作流");
    return;
  }

  executionStore.startExecution({ nodeIds });

  for (const nodeId of topoOrder) {
    if (!executionStore.isRunning && !executionStore.isPaused) break;

    await waitIfPaused();
    if (!executionStore.isRunning) break;

    const node = nodesRecord[nodeId];
    await new Promise((resolve) => setTimeout(resolve, 500));

    await waitIfPaused();
    if (!executionStore.isRunning) break;

    inputEdgesMap.get(nodeId)?.forEach((edgeId) => executionStore.activateEdge(edgeId));
    executionStore.startNode(node.id, node.name || node.type);

    await new Promise((resolve) => setTimeout(resolve, 1000 + Math.random() * 1000));

    await waitIfPaused();
    if (!executionStore.isRunning) break;

    if (node.type === "output") {
      executionStore.completeNode(node.id, node.name || node.type, {
        result: "执行完成",
        timestamp: new Date().toISOString(),
        data: { message: "Hello from AutoFlow!" },
      });
    } else {
      executionStore.completeNode(node.id, node.name || node.type);
    }

    outputEdgesMap.get(nodeId)?.forEach((edgeId) => executionStore.completeEdge(edgeId));
  }

  if (executionStore.isRunning) {
    executionStore.completeExecution();
    message.success("执行完成");
  }
};

const handleExecute = async () => {
  await simulateExecution();
};

watch(
  () => workflowStore.name,
  (newName) => {
    workflowName.value = newName;
  },
);
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  gap: 16px;
  flex-wrap: wrap;
  background: #1e293b;
  border-bottom: 1px solid #334155;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 200px;
}

.title-icon {
  font-size: 18px;
  color: #6366f1;
}

.workflow-name-input {
  font-size: 14px;
  font-weight: 500;
  border: none;
  box-shadow: none;
  padding: 4px 8px;
  background: transparent;
  color: #e2e8f0;
  width: auto;
}

.workflow-name-input:hover,
.workflow-name-input:focus {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
}

.header-right {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.header-right :deep(.ant-btn) {
  height: 30px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  border-color: #334155;
  color: #94a3b8;
  transition: all 0.2s;
  background: transparent;
}

.header-right :deep(.ant-btn:hover) {
  color: #e2e8f0;
  border-color: #475569;
  background: rgba(255, 255, 255, 0.04);
}

.header-right :deep(.ant-btn-primary) {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  border: none !important;
  color: white !important;
}

.header-right :deep(.ant-btn-primary:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
  background: linear-gradient(135deg, #5558e3, #7c3aed) !important;
  color: white !important;
}

.header-right :deep(.ant-btn-dangerous) {
  border-color: #7f1d1d;
  color: #ef4444;
}

.header-right :deep(.ant-btn-dangerous:hover) {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}
</style>
