<script setup lang="ts">
import { ref } from "vue";
import { useExecutionStore } from "../../stores/execution";
import {
  Drawer,
  Button,
  Tooltip,
  Input,
  Modal,
  Tabs,
  Switch,
} from "ant-design-vue";
import {
  PlayCircleOutlined,
  StopOutlined,
  StepForwardOutlined,
  StepBackwardOutlined,
  PlusOutlined,
  DeleteOutlined,
} from "@ant-design/icons-vue";

const executionStore = useExecutionStore();

const isOpen = ref(false);
const activeTab = ref("watches");
const newWatchName = ref("");
const newWatchExpression = ref("");
const showAddWatchModal = ref(false);

const togglePanel = () => {
  isOpen.value = !isOpen.value;
};

const handleAddWatch = () => {
  if (newWatchName.value && newWatchExpression.value) {
    executionStore.addVariableWatch(
      newWatchName.value,
      newWatchExpression.value,
    );
    newWatchName.value = "";
    newWatchExpression.value = "";
    showAddWatchModal.value = false;
  }
};

const handleRemoveWatch = (watchId: string) => {
  executionStore.removeVariableWatch(watchId);
};

const handleToggleBreakpoint = (breakpointId: string) => {
  executionStore.toggleBreakpoint(breakpointId);
};

const handleRemoveBreakpoint = (breakpointId: string) => {
  executionStore.removeBreakpoint(breakpointId);
};

const handleStepOver = () => {
  executionStore.stepOver();
};

const handleStepInto = () => {
  executionStore.stepInto();
};

const handleStepOut = () => {
  executionStore.stepOut();
};

const handleContinue = () => {
  executionStore.continueExecution();
};

const handleStop = () => {
  executionStore.stopExecution();
};

const formatValue = (value: any): string => {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (typeof value === "object" || Array.isArray(value)) {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return "[Circular]";
    }
  }
  return String(value);
};

const formatTime = (date: Date | undefined) => {
  if (!date) return "";
  return new Date(date).toLocaleTimeString();
};
</script>

<template>
  <div>
    <button
      class="debug-panel-toggle"
      @click="togglePanel"
      :class="{ active: executionStore.isDebugMode }"
    >
      <span class="toggle-icon">🔧</span>
      <span class="toggle-text">调试面板</span>
      <span v-if="executionStore.isDebugMode" class="debug-indicator">●</span>
    </button>

    <Drawer
      :open="isOpen"
      placement="bottom"
      :height="550"
      @close="isOpen = false"
      :mask="true"
      :mask-closable="true"
      class="debug-drawer"
    >
      <template #title>
        <div class="debug-drawer-header">
          <div class="header-icon">
            <span>🔧</span>
          </div>
          <div class="header-content">
            <h3 class="drawer-title">调试面板</h3>
            <p class="drawer-subtitle">
              模式: {{ executionStore.debugMode }} | 状态:
              {{ executionStore.status }}
            </p>
          </div>
        </div>
      </template>

      <div class="debug-panel-content">
        <div class="debug-controls">
          <div class="control-group">
            <Tooltip title="单步跳过">
              <Button
                type="primary"
                :disabled="!executionStore.isDebugMode"
                @click="handleStepOver"
              >
                <StepForwardOutlined />
                单步
              </Button>
            </Tooltip>
            <Tooltip title="进入">
              <Button
                :disabled="!executionStore.isDebugMode"
                @click="handleStepInto"
              >
                <StepBackwardOutlined />
                进入
              </Button>
            </Tooltip>
            <Tooltip title="跳出">
              <Button
                :disabled="!executionStore.isDebugMode"
                @click="handleStepOut"
              >
                <StepForwardOutlined />
                跳出
              </Button>
            </Tooltip>
          </div>
          <div class="control-group">
            <Tooltip title="继续执行">
              <Button
                type="primary"
                :disabled="!executionStore.isDebugMode"
                @click="handleContinue"
              >
                <PlayCircleOutlined />
                继续
              </Button>
            </Tooltip>
            <Tooltip title="停止">
              <Button
                danger
                :disabled="
                  !executionStore.isRunning && !executionStore.isPaused
                "
                @click="handleStop"
              >
                <StopOutlined />
                停止
              </Button>
            </Tooltip>
          </div>
        </div>

        <Tabs v-model:activeKey="activeTab" class="debug-tabs">
          <TabPane key="watches" tab="变量监视">
            <div class="tab-content">
              <div class="watch-header">
                <Button
                  type="primary"
                  size="small"
                  @click="showAddWatchModal = true"
                >
                  <PlusOutlined />
                  添加监视
                </Button>
              </div>
              <div class="watch-list">
                <div
                  v-for="watch in executionStore.variableWatches"
                  :key="watch.id"
                  class="watch-item"
                >
                  <div class="watch-info">
                    <span class="watch-name">{{ watch.name }}</span>
                    <span class="watch-expr">= {{ watch.expression }}</span>
                  </div>
                  <div class="watch-value">
                    <pre>{{ formatValue(watch.value) }}</pre>
                  </div>
                  <div class="watch-actions">
                    <span class="watch-time">{{
                      formatTime(watch.last_updated)
                    }}</span>
                    <Tooltip title="删除">
                      <Button
                        type="text"
                        size="small"
                        danger
                        @click="handleRemoveWatch(watch.id)"
                      >
                        <DeleteOutlined />
                      </Button>
                    </Tooltip>
                  </div>
                </div>
                <div
                  v-if="executionStore.variableWatches.length === 0"
                  class="empty-state"
                >
                  <span class="empty-icon">👁️</span>
                  <p>暂无监视变量</p>
                </div>
              </div>
            </div>
          </TabPane>

          <TabPane key="breakpoints" tab="断点列表">
            <div class="tab-content">
              <div class="breakpoint-list">
                <div
                  v-for="bp in executionStore.breakpoints"
                  :key="bp.id"
                  class="breakpoint-item"
                >
                  <div class="breakpoint-info">
                    <Switch
                      :checked="bp.enabled"
                      @change="handleToggleBreakpoint(bp.id)"
                      size="small"
                    />
                    <span class="breakpoint-node">节点: {{ bp.node_id }}</span>
                  </div>
                  <div class="breakpoint-condition" v-if="bp.condition">
                    条件: {{ bp.condition }}
                  </div>
                  <div class="breakpoint-actions">
                    <Tooltip title="删除">
                      <Button
                        type="text"
                        size="small"
                        danger
                        @click="handleRemoveBreakpoint(bp.id)"
                      >
                        <DeleteOutlined />
                      </Button>
                    </Tooltip>
                  </div>
                </div>
                <div
                  v-if="executionStore.breakpoints.length === 0"
                  class="empty-state"
                >
                  <span class="empty-icon">🎯</span>
                  <p>暂无断点</p>
                </div>
              </div>
            </div>
          </TabPane>

          <TabPane key="callstack" tab="调用堆栈">
            <div class="tab-content">
              <div class="callstack-list">
                <div
                  v-for="(nodeId, index) in executionStore.callStack"
                  :key="index"
                  class="callstack-item"
                >
                  <span class="callstack-index"
                    >#{{ executionStore.callStack.length - index }}</span
                  >
                  <span class="callstack-node">{{ nodeId }}</span>
                </div>
                <div
                  v-if="executionStore.callStack.length === 0"
                  class="empty-state"
                >
                  <span class="empty-icon">📚</span>
                  <p>调用堆栈为空</p>
                </div>
              </div>
            </div>
          </TabPane>

          <TabPane key="variables" tab="当前变量">
            <div class="tab-content">
              <div class="current-variables-list">
                <div
                  v-for="[key, value] in Object.entries(
                    executionStore.variables,
                  )"
                  :key="key"
                  class="current-variable-item"
                >
                  <span class="var-name">{{ key }}</span>
                  <span class="var-value">
                    <pre>{{ formatValue(value) }}</pre>
                  </span>
                </div>
                <div
                  v-if="Object.keys(executionStore.variables).length === 0"
                  class="empty-state"
                >
                  <span class="empty-icon">📊</span>
                  <p>暂无变量</p>
                </div>
              </div>
            </div>
          </TabPane>
        </Tabs>
      </div>
    </Drawer>

    <Modal
      v-model:open="showAddWatchModal"
      title="添加监视变量"
      @ok="handleAddWatch"
      @cancel="showAddWatchModal = false"
    >
      <div class="add-watch-form">
        <div class="form-item">
          <label>名称</label>
          <Input v-model:value="newWatchName" placeholder="变量名称" />
        </div>
        <div class="form-item">
          <label>表达式</label>
          <Input
            v-model:value="newWatchExpression"
            placeholder="变量名或表达式"
          />
        </div>
      </div>
    </Modal>
  </div>
</template>

<style scoped>
.debug-panel-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #374151;
  transition: all 0.2s ease;
  position: relative;
}

.debug-panel-toggle:hover {
  background: #e5e7eb;
}

.debug-panel-toggle.active {
  background: #fee2e2;
  border-color: #ef4444;
  color: #991b1b;
}

.toggle-icon {
  font-size: 16px;
}

.toggle-text {
  font-weight: 500;
}

.debug-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
  font-size: 8px;
  color: #ef4444;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.debug-drawer {
  padding: 0;
}

:deep(.debug-drawer .ant-drawer-content) {
  border-radius: 12px 12px 0 0;
  box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.08);
}

:deep(.debug-drawer .ant-drawer-header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.debug-drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.debug-drawer-header .header-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border-radius: 10px;
  font-size: 20px;
}

.debug-drawer-header .header-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.debug-drawer-header .drawer-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.debug-drawer-header .drawer-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.debug-panel-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0 24px 24px;
}

.debug-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 16px;
}

.control-group {
  display: flex;
  gap: 8px;
}

.debug-tabs {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

:deep(.debug-tabs .ant-tabs-content) {
  flex: 1;
  overflow: hidden;
}

:deep(.debug-tabs .ant-tabs-tabpane) {
  height: 100%;
  overflow: hidden;
}

.tab-content {
  height: 100%;
  overflow-y: auto;
  padding-right: 4px;
}

.tab-content::-webkit-scrollbar {
  width: 6px;
}

.tab-content::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.tab-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.watch-header {
  margin-bottom: 12px;
}

.watch-list,
.breakpoint-list,
.callstack-list,
.current-variables-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.watch-item,
.breakpoint-item,
.callstack-item,
.current-variable-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.watch-item {
  gap: 6px;
}

.watch-info,
.breakpoint-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.watch-name,
.breakpoint-node,
.callstack-node,
.var-name {
  font-weight: 600;
  color: #1e293b;
}

.watch-expr {
  color: #64748b;
  font-size: 13px;
}

.watch-value pre,
.var-value pre {
  margin: 0;
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 12px;
  color: #475569;
  white-space: pre-wrap;
  word-break: break-all;
  background: #ffffff;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.watch-actions,
.breakpoint-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.watch-time {
  font-size: 11px;
  color: #94a3b8;
}

.breakpoint-condition {
  font-size: 13px;
  color: #64748b;
  background: #ffffff;
  padding: 6px 10px;
  border-radius: 4px;
  border: 1px dashed #cbd5e1;
}

.callstack-item {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.callstack-index {
  background: #e0e7ff;
  color: #4338ca;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.current-variable-item {
  flex-direction: row;
  gap: 12px;
  align-items: flex-start;
}

.current-variable-item .var-name {
  min-width: 120px;
  flex-shrink: 0;
}

.current-variable-item .var-value {
  flex: 1;
  min-width: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  gap: 12px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.4;
}

.empty-state p {
  margin: 0;
  color: #94a3b8;
  font-size: 14px;
}

.add-watch-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}
</style>
