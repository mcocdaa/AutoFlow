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
      <a-button @click="handleLoadExample">
        <FileTextOutlined />
        导入示例
      </a-button>
      <a-button @click="handleSaveAsExample">
        <BookOutlined />
        保存为示例
      </a-button>
      <a-button @click="handleExportYaml">
        <DownloadOutlined />
        导出YAML
      </a-button>
      <a-button @click="handleSave">
        <SaveOutlined />
        保存
      </a-button>
      <a-button @click="handleReset">
        <ClearOutlined />
        重置
      </a-button>
      <a-button v-if="executionStore.isRunning" danger @click="handleStop">
        <StopOutlined />
        停止
      </a-button>
      <a-button v-if="executionStore.isRunning" @click="handlePause">
        <PauseCircleOutlined />
        暂停
      </a-button>
      <a-button
        v-if="executionStore.isPaused"
        type="primary"
        @click="handleResume"
      >
        <CaretRightOutlined />
        继续
      </a-button>
      <a-button
        v-if="!executionStore.isRunning && !executionStore.isPaused"
        type="primary"
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
import { useWorkflowStore } from "../../stores/workflow";
import { useExecutionStore } from "../../stores/execution";
import SaveExampleModal from "./SaveExampleModal.vue";
import ExportYamlModal from "./ExportYamlModal.vue";

const workflowStore = useWorkflowStore();
const executionStore = useExecutionStore();

const workflowName = ref(workflowStore.name);
const showSaveExampleModal = ref(false);
const showExportModal = ref(false);

const currentYamlContent = computed(() => {
  return workflowStore.toYAML();
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
  const nodes = workflowStore.nodes;
  if (nodes.length === 0) {
    message.warning("请先添加节点再保存为示例");
    return;
  }
  showSaveExampleModal.value = true;
};

const handleExampleSaved = () => {
  message.success("示例保存成功！");
};

const handleExportYaml = () => {
  const nodes = workflowStore.nodes;
  if (nodes.length === 0) {
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
  const nodes = workflowStore.nodes;
  const edges = workflowStore.edges;

  if (nodes.length === 0) {
    message.warning("请先添加节点");
    return;
  }

  const startNode = nodes.find((n) => n.type === "start");
  if (!startNode) {
    message.warning("请先添加开始节点");
    return;
  }

  const nodeMap = new Map<string, (typeof nodes)[0]>();
  nodes.forEach((node) => nodeMap.set(node.id, node));

  const inDegree = new Map<string, number>();
  nodes.forEach((node) => inDegree.set(node.id, 0));

  const adjacencyList = new Map<string, string[]>();
  nodes.forEach((node) => adjacencyList.set(node.id, []));

  const inputEdgesMap = new Map<string, string[]>();
  nodes.forEach((node) => inputEdgesMap.set(node.id, []));

  const outputEdgesMap = new Map<string, string[]>();
  nodes.forEach((node) => outputEdgesMap.set(node.id, []));

  edges.forEach((edge) => {
    adjacencyList.get(edge.source)?.push(edge.target);
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
    inputEdgesMap.get(edge.target)?.push(edge.id);
    outputEdgesMap.get(edge.source)?.push(edge.id);
  });

  const queue: string[] = [];
  const topoOrder: string[] = [];

  inDegree.forEach((degree, nodeId) => {
    if (degree === 0 && nodeId === startNode.id) {
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
      if (newDegree === 0) {
        queue.push(neighbor);
      }
    }
  }

  if (topoOrder.length !== nodes.length) {
    message.error("检测到循环依赖，无法执行工作流");
    return;
  }

  executionStore.startExecution({
    nodeIds: nodes.map((n) => n.id),
  });

  for (const nodeId of topoOrder) {
    if (!executionStore.isRunning && !executionStore.isPaused) break;

    await waitIfPaused();

    if (!executionStore.isRunning) break;

    const node = nodeMap.get(nodeId)!;

    await new Promise((resolve) => setTimeout(resolve, 500));

    await waitIfPaused();
    if (!executionStore.isRunning) break;

    const inputEdges = inputEdgesMap.get(nodeId) || [];
    inputEdges.forEach((edgeId) => {
      executionStore.activateEdge(edgeId);
    });

    executionStore.startNode(node.id, node.data.label || node.type);

    await new Promise((resolve) =>
      setTimeout(resolve, 1000 + Math.random() * 1000),
    );

    await waitIfPaused();
    if (!executionStore.isRunning) break;

    if (node.type === "output") {
      executionStore.completeNode(node.id, node.data.label || node.type, {
        result: "执行完成",
        timestamp: new Date().toISOString(),
        data: { message: "Hello from AutoFlow!" },
      });
    } else {
      executionStore.completeNode(node.id, node.data.label || node.type);
    }

    const outputEdges = outputEdgesMap.get(nodeId) || [];
    outputEdges.forEach((edgeId) => {
      executionStore.completeEdge(edgeId);
    });
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
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 200px;
}

.title-icon {
  font-size: 24px;
  color: var(--flow-color-primary);
}

.workflow-name-input {
  font-size: 20px;
  font-weight: 600;
  border: none;
  box-shadow: none;
  padding: 4px 8px;
  background: transparent;
}

.workflow-name-input:hover,
.workflow-name-input:focus {
  background: var(--flow-bg-layer);
  border-radius: 4px;
}

.header-right {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
