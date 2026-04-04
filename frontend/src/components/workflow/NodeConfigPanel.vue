<script setup lang="ts">
import { useDAGWorkflowStore } from "../../stores/dag-workflow";
import { useExecutionStore } from "../../stores/execution";
import { Input, Drawer, Button, InputNumber, Select } from "ant-design-vue";
import {
  CloseOutlined,
  ReloadOutlined,
  ForwardOutlined,
  ClockCircleOutlined,
  CodeOutlined,
  AlertOutlined,
} from "@ant-design/icons-vue";
import { InputPortConfig, OutputPortConfig } from "./config";
import { computed } from "vue";
import { generateId } from "../../utils";
import type { InputPort, OutputPort } from "../../types/dag-workflow";

const store = useDAGWorkflowStore();
const executionStore = useExecutionStore();

const selectedNode = computed(() => store.configNode as any);

const mergeStrategies = [
  { label: "列表拼接", value: "list_concat" },
  { label: "对象合并", value: "object_merge" },
  { label: "自定义", value: "custom" },
];

const splitStrategies = [
  { label: "按索引", value: "by_index" },
  { label: "按字段", value: "by_field" },
  { label: "自定义", value: "custom" },
];

const handleNameChange = (value: string) => {
  if (selectedNode.value) {
    store.updateNode(selectedNode.value.id, {
      name: value,
    });
  }
};

const handleRetryAttemptsChange = (value: any) => {
  if (selectedNode.value && value !== null && value !== undefined) {
    store.updateNode(selectedNode.value.id, {
      retry: {
        ...selectedNode.value.retry,
        attempts: Number(value),
      },
    });
  }
};

const handleRetryBackoffChange = (value: any) => {
  if (selectedNode.value && value !== null && value !== undefined) {
    store.updateNode(selectedNode.value.id, {
      retry: {
        ...selectedNode.value.retry,
        backoff_seconds: Number(value),
      },
    });
  }
};

const handleClose = () => {
  store.closeConfig();
};

const getNodeError = computed(() => {
  if (!selectedNode.value) return null;
  return executionStore.nodes[selectedNode.value.id]?.error;
});

const handleRetry = () => {
  if (!selectedNode.value) return;
  executionStore.retryNode(selectedNode.value.id);
};

const handleSkip = () => {
  if (!selectedNode.value) return;
  executionStore.skipNode(selectedNode.value.id);
};

const handleInputPortsUpdate = (ports: InputPort[]) => {
  if (selectedNode.value) {
    store.updateNode(selectedNode.value.id, { inputs: ports });
  }
};

const handleOutputPortsUpdate = (ports: OutputPort[]) => {
  if (selectedNode.value) {
    store.updateNode(selectedNode.value.id, { outputs: ports });
  }
};

const handleAddInputPort = () => {
  if (selectedNode.value) {
    const newPort: InputPort = {
      id: generateId(),
      name: "input_" + (selectedNode.value.inputs.length + 1),
      type: "any",
      required: true,
    };
    store.updateNode(selectedNode.value.id, {
      inputs: [...selectedNode.value.inputs, newPort],
    });
  }
};

const handleAddOutputPort = () => {
  if (selectedNode.value) {
    const newPort: OutputPort = {
      id: generateId(),
      name: "output_" + (selectedNode.value.outputs.length + 1),
      type: "any",
    };
    store.updateNode(selectedNode.value.id, {
      outputs: [...selectedNode.value.outputs, newPort],
    });
  }
};

const handleRemoveInputPort = (index: number) => {
  if (selectedNode.value) {
    const newPorts = [...selectedNode.value.inputs];
    newPorts.splice(index, 1);
    store.updateNode(selectedNode.value.id, { inputs: newPorts });
  }
};

const handleRemoveOutputPort = (index: number) => {
  if (selectedNode.value) {
    const newPorts = [...selectedNode.value.outputs];
    newPorts.splice(index, 1);
    store.updateNode(selectedNode.value.id, { outputs: newPorts });
  }
};

const handleActionTypeChange = (value: any) => {
  if (selectedNode.value && selectedNode.value.type === "action") {
    store.updateNode(selectedNode.value.id, {
      config: { ...selectedNode.value.config, action_type: value as string },
    });
  }
};

const handleMergeStrategyChange = (value: any) => {
  if (selectedNode.value && selectedNode.value.type === "merge") {
    store.updateNode(selectedNode.value.id, {
      config: { ...selectedNode.value.config, strategy: value as string },
    });
  }
};

const handleSplitStrategyChange = (value: any) => {
  if (selectedNode.value && selectedNode.value.type === "split") {
    store.updateNode(selectedNode.value.id, {
      config: { ...selectedNode.value.config, strategy: value as string },
    });
  }
};

const handleCustomStrategyChange = (value: string) => {
  if (selectedNode.value) {
    store.updateNode(selectedNode.value.id, {
      config: { ...selectedNode.value.config, custom_strategy: value },
    });
  }
};

const handlePassTransformChange = (value: string) => {
  if (selectedNode.value && selectedNode.value.type === "pass") {
    store.updateNode(selectedNode.value.id, {
      config: { ...selectedNode.value.config, transform: value },
    });
  }
};

const handleForIterableSourceChange = (value: string) => {
  if (selectedNode.value && selectedNode.value.type === "for") {
    store.updateNode(selectedNode.value.id, {
      config: { ...selectedNode.value.config, iterable_source: value },
    });
  }
};

const handleWhileConditionChange = (value: string) => {
  if (selectedNode.value && selectedNode.value.type === "while") {
    store.updateNode(selectedNode.value.id, {
      config: { ...selectedNode.value.config, condition: value },
    });
  }
};

const handleSubflowIdChange = (value: string) => {
  if (selectedNode.value && selectedNode.value.type === "subflow") {
    store.updateNode(selectedNode.value.id, {
      config: { ...selectedNode.value.config, subflow_id: value },
    });
  }
};
</script>

<template>
  <Drawer
    :open="!!selectedNode"
    placement="right"
    :width="400"
    @close="handleClose"
    :mask="true"
    :mask-closable="true"
    class="config-drawer"
  >
    <template #title>
      <div class="drawer-header">
        <div class="header-icon">
          <span>⚙️</span>
        </div>
        <div class="header-content">
          <h3 class="drawer-title">节点配置</h3>
          <p class="drawer-subtitle">
            {{ selectedNode?.name || selectedNode?.type }}
          </p>
        </div>
        <button class="close-button" @click="handleClose">
          <CloseOutlined />
        </button>
      </div>
    </template>

    <div class="config-content">
      <div v-if="getNodeError" class="error-detail-section">
        <div class="error-header">
          <div class="error-title">
            <AlertOutlined class="error-icon" />
            <span class="error-type">{{ getNodeError.type }}</span>
          </div>
          <div class="error-timestamp">
            <ClockCircleOutlined class="timestamp-icon" />
            <span>{{ getNodeError.timestamp.toLocaleString() }}</span>
          </div>
        </div>

        <div class="error-message">
          {{ getNodeError.message }}
        </div>

        <div v-if="getNodeError.stack" class="error-stack-container">
          <div class="stack-header">
            <CodeOutlined class="stack-icon" />
            <span>错误堆栈</span>
          </div>
          <pre class="error-stack">{{ getNodeError.stack }}</pre>
        </div>

        <div class="error-actions">
          <Button
            type="primary"
            :icon="h(ReloadOutlined)"
            @click="handleRetry"
            class="action-button retry-button"
          >
            重试
          </Button>
          <Button
            :icon="h(ForwardOutlined)"
            @click="handleSkip"
            class="action-button skip-button"
          >
            跳过
          </Button>
        </div>
      </div>

      <div class="config-section">
        <label class="section-label">节点名称</label>
        <Input
          :value="selectedNode?.name"
          @update:value="handleNameChange"
          placeholder="输入节点名称"
          class="config-input"
        />
      </div>

      <div class="config-section">
        <label class="section-label">重试配置</label>
        <div class="retry-config-container">
          <div class="retry-config-item">
            <label class="retry-config-label">重试次数</label>
            <InputNumber
              :value="selectedNode?.retry?.attempts ?? 0"
              @update:value="handleRetryAttemptsChange"
              :min="0"
              :step="1"
              class="config-input-number"
              style="width: 100%"
            />
          </div>
          <div class="retry-config-item">
            <label class="retry-config-label">退避时间 (秒)</label>
            <InputNumber
              :value="selectedNode?.retry?.backoff_seconds ?? 0"
              @update:value="handleRetryBackoffChange"
              :min="0"
              :step="1"
              class="config-input-number"
              style="width: 100%"
            />
          </div>
        </div>
      </div>

      <div class="config-section">
        <label class="section-label">节点配置</label>
        <div class="form-container">
          <div
            v-if="selectedNode?.type === 'start'"
            class="type-specific-config"
          >
            <OutputPortConfig
              :ports="selectedNode.outputs"
              @update:ports="handleOutputPortsUpdate"
              @add-port="handleAddOutputPort"
              @remove-port="handleRemoveOutputPort"
            />
          </div>

          <div
            v-else-if="selectedNode?.type === 'end'"
            class="type-specific-config"
          >
            <InputPortConfig
              :ports="selectedNode.inputs"
              @update:ports="handleInputPortsUpdate"
              @add-port="handleAddInputPort"
              @remove-port="handleRemoveInputPort"
            />
          </div>

          <div
            v-else-if="selectedNode?.type === 'action'"
            class="type-specific-config"
          >
            <div class="config-field">
              <label class="field-label">Action 类型</label>
              <Select
                :value="selectedNode.config?.action_type"
                :options="[]"
                placeholder="选择 action 类型"
                @update:value="handleActionTypeChange"
                style="width: 100%"
              />
            </div>
            <div class="ports-section">
              <InputPortConfig
                :ports="selectedNode.inputs"
                @update:ports="handleInputPortsUpdate"
                @add-port="handleAddInputPort"
                @remove-port="handleRemoveInputPort"
              />
            </div>
            <div class="ports-section">
              <OutputPortConfig
                :ports="selectedNode.outputs"
                @update:ports="handleOutputPortsUpdate"
                @add-port="handleAddOutputPort"
                @remove-port="handleRemoveOutputPort"
              />
            </div>
          </div>

          <div
            v-else-if="selectedNode?.type === 'pass'"
            class="type-specific-config"
          >
            <div class="config-field">
              <label class="field-label">数据转换表达式</label>
              <Input
                :value="selectedNode.config?.transform"
                @update:value="handlePassTransformChange"
                placeholder="转换表达式（可选）"
              />
            </div>
            <div class="ports-section">
              <InputPortConfig
                :ports="selectedNode.inputs"
                @update:ports="handleInputPortsUpdate"
                @add-port="handleAddInputPort"
                @remove-port="handleRemoveInputPort"
              />
            </div>
            <div class="ports-section">
              <OutputPortConfig
                :ports="selectedNode.outputs"
                @update:ports="handleOutputPortsUpdate"
                @add-port="handleAddOutputPort"
                @remove-port="handleRemoveOutputPort"
              />
            </div>
          </div>

          <div
            v-else-if="selectedNode?.type === 'if'"
            class="type-specific-config"
          >
            <OutputPortConfig
              :ports="selectedNode.outputs"
              @update:ports="handleOutputPortsUpdate"
              @add-port="handleAddOutputPort"
              @remove-port="handleRemoveOutputPort"
            />
          </div>

          <div
            v-else-if="selectedNode?.type === 'switch'"
            class="type-specific-config"
          >
            <OutputPortConfig
              :ports="selectedNode.outputs"
              @update:ports="handleOutputPortsUpdate"
              @add-port="handleAddOutputPort"
              @remove-port="handleRemoveOutputPort"
            />
          </div>

          <div
            v-else-if="selectedNode?.type === 'for'"
            class="type-specific-config"
          >
            <div class="config-field">
              <label class="field-label">迭代源</label>
              <Input
                :value="selectedNode.config?.iterable_source"
                @update:value="handleForIterableSourceChange"
                placeholder="迭代源"
              />
            </div>
            <div class="config-notice">子画布编辑将在后续版本中支持</div>
          </div>

          <div
            v-else-if="selectedNode?.type === 'while'"
            class="type-specific-config"
          >
            <div class="config-field">
              <label class="field-label">循环条件</label>
              <Input
                :value="selectedNode.config?.condition"
                @update:value="handleWhileConditionChange"
                placeholder="循环条件表达式"
              />
            </div>
            <div class="config-notice">子画布编辑将在后续版本中支持</div>
          </div>

          <div
            v-else-if="selectedNode?.type === 'retry'"
            class="type-specific-config"
          >
            <div class="config-notice">Retry 节点配置将在后续版本中支持</div>
          </div>

          <div
            v-else-if="selectedNode?.type === 'merge'"
            class="type-specific-config"
          >
            <div class="config-field">
              <label class="field-label">合并策略</label>
              <Select
                :value="selectedNode.config?.strategy"
                :options="mergeStrategies"
                @update:value="handleMergeStrategyChange"
                style="width: 100%"
              />
            </div>
            <div
              v-if="selectedNode.config?.strategy === 'custom'"
              class="config-field"
            >
              <label class="field-label">自定义策略</label>
              <Input
                :value="selectedNode.config?.custom_strategy"
                @update:value="handleCustomStrategyChange"
                placeholder="自定义策略表达式"
              />
            </div>
            <InputPortConfig
              :ports="selectedNode.inputs"
              @update:ports="handleInputPortsUpdate"
              @add-port="handleAddInputPort"
              @remove-port="handleRemoveInputPort"
            />
          </div>

          <div
            v-else-if="selectedNode?.type === 'split'"
            class="type-specific-config"
          >
            <div class="config-field">
              <label class="field-label">拆分策略</label>
              <Select
                :value="selectedNode.config?.strategy"
                :options="splitStrategies"
                @update:value="handleSplitStrategyChange"
                style="width: 100%"
              />
            </div>
            <div
              v-if="selectedNode.config?.strategy === 'custom'"
              class="config-field"
            >
              <label class="field-label">自定义策略</label>
              <Input
                :value="selectedNode.config?.custom_strategy"
                @update:value="handleCustomStrategyChange"
                placeholder="自定义策略表达式"
              />
            </div>
            <OutputPortConfig
              :ports="selectedNode.outputs"
              @update:ports="handleOutputPortsUpdate"
              @add-port="handleAddOutputPort"
              @remove-port="handleRemoveOutputPort"
            />
          </div>

          <div
            v-else-if="selectedNode?.type === 'group'"
            class="type-specific-config"
          >
            <div class="config-notice">
              Group 节点端口映射配置将在后续版本中支持
            </div>
          </div>

          <div
            v-else-if="selectedNode?.type === 'subflow'"
            class="type-specific-config"
          >
            <div class="config-field">
              <label class="field-label">子工作流 ID</label>
              <Input
                :value="selectedNode.config?.subflow_id"
                @update:value="handleSubflowIdChange"
                placeholder="子工作流 ID"
              />
            </div>
            <div class="config-notice">
              子工作流选择和端口映射将在后续版本中支持
            </div>
          </div>

          <div
            v-else-if="selectedNode?.type === 'input'"
            class="type-specific-config"
          >
            <div class="config-field">
              <label class="field-label">输入模式</label>
              <a-select
                :value="selectedNode.config?.mode || 'api'"
                @change="(v: string) => store.updateNode(selectedNode!.id, { config: { ...selectedNode!.config, mode: v } })"
                style="width: 100%"
              >
                <a-select-option value="api">API 注入</a-select-option>
                <a-select-option value="webhook">Webhook</a-select-option>
                <a-select-option value="form">表单</a-select-option>
                <a-select-option value="watch">监听文件</a-select-option>
              </a-select>
            </div>
            <div class="config-field">
              <label class="field-label">超时（秒）</label>
              <a-input-number
                :value="selectedNode.config?.timeout_seconds ?? 300"
                :min="1"
                :max="86400"
                @change="(v: number) => store.updateNode(selectedNode!.id, { config: { ...selectedNode!.config, timeout_seconds: v } })"
                style="width: 100%"
              />
            </div>
            <div class="config-notice input-node-notice">
              运行时工作流在此节点暂停，等待通过 API 提交数据后继续
            </div>
          </div>

          <div v-else class="config-placeholder">
            <div class="placeholder-icon">📝</div>
            <p>该节点类型暂无配置表单</p>
            <span class="node-type-tag">{{ selectedNode?.type }}</span>
          </div>
        </div>
      </div>
    </div>
  </Drawer>
</template>

<script lang="ts">
import { h } from "vue";
export default {
  methods: {
    h,
  },
};
</script>

<style scoped>
.config-drawer {
  padding: 0;
}

:deep(.ant-drawer-content) {
  border-radius: 12px 0 0 12px;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.4);
  background: #1e293b;
}

:deep(.ant-drawer-body) {
  background: #1e293b;
  padding: 0;
}

:deep(.ant-drawer-header) {
  padding: 20px 24px;
  border-bottom: 1px solid #334155;
  background: #1e293b;
}

:deep(.ant-drawer-close) {
  color: #64748b;
}
:deep(.ant-drawer-close:hover) {
  color: #e2e8f0;
  background: rgba(255,255,255,0.08);
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.header-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  font-size: 20px;
}

.header-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.drawer-title {
  font-size: 18px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
}

.drawer-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.close-button {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: #334155;
  border-radius: 8px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s ease;
}

.close-button:hover {
  background: #475569;
  color: #e2e8f0;
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
}

.error-detail-section {
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 12px;
  padding: 20px;
}

.error-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.error-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #991b1b;
  font-size: 14px;
}

.error-icon {
  font-size: 18px;
  color: #dc2626;
}

.error-timestamp {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #7f1d1d;
  opacity: 0.8;
}

.timestamp-icon {
  font-size: 14px;
}

.error-message {
  background: #1e293b;
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  color: #fca5a5;
  font-size: 14px;
  line-height: 1.6;
}

.error-stack-container {
  margin-bottom: 16px;
}

.stack-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #7f1d1d;
  margin-bottom: 8px;
}

.stack-icon {
  font-size: 14px;
}

.error-stack {
  background: #1f2937;
  color: #e5e7eb;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 11px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 150px;
  overflow-y: auto;
  margin: 0;
  font-family: "Menlo", "Monaco", "Courier New", monospace;
}

.error-actions {
  display: flex;
  gap: 10px;
}

.action-button {
  flex: 1;
  height: 36px;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.retry-button {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  border: none;
}

.retry-button:hover {
  background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.skip-button {
  background: #334155;
  border: 1px solid #475569;
  color: #94a3b8;
}

.skip-button:hover {
  border-color: #6366f1;
  background: #3d4a5c;
  color: #e2e8f0;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-label {
  font-size: 14px;
  font-weight: 600;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-label::before {
  content: "";
  width: 4px;
  height: 16px;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
}

.config-input {
  border-radius: 8px;
}

:deep(.config-input .ant-input) {
  padding: 10px 14px;
  border-radius: 8px;
}

.retry-config-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.retry-config-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.retry-config-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

:deep(.config-input-number .ant-input-number-input-wrap) {
  padding: 10px 14px;
  border-radius: 8px;
}

:deep(.config-input-number) {
  border-radius: 8px;
}

.form-container {
  background: #0f172a;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #334155;
}

.config-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  gap: 12px;
}

.placeholder-icon {
  font-size: 48px;
  opacity: 0.5;
}

.config-placeholder p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.node-type-tag {
  display: inline-block;
  padding: 4px 12px;
  background: #334155;
  border-radius: 20px;
  font-size: 12px;
  color: #94a3b8;
  font-family: monospace;
}

.type-specific-config {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-field .field-label {
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
}

.ports-section {
  margin-top: 4px;
}

.config-notice {
  padding: 12px;
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: 8px;
  color: #fbbf24;
  font-size: 13px;
}

.input-node-notice {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.3);
  color: #818cf8;
}

.config-field .field-label {
  font-size: 13px;
  font-weight: 500;
  color: #94a3b8;
}
</style>
