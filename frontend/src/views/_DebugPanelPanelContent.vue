<script setup lang="ts">
import { ref } from "vue";
import { useExecutionStore } from "../stores/execution";
import { Button, Tabs, Switch } from "ant-design-vue";
const TabPane = Tabs.TabPane;
import {
  PlayCircleOutlined,
  StopOutlined,
  StepForwardOutlined,
  StepBackwardOutlined,
  PlusOutlined,
  DeleteOutlined,
} from "@ant-design/icons-vue";

const executionStore = useExecutionStore();

const activeTab = ref("watches");

const handleRemoveWatch = (watchId: string) => {
  executionStore.removeVariableWatch(watchId);
};

const handleStepOver = () => executionStore.stepOver();
const handleStepInto = () => executionStore.stepInto();
const handleStepOut = () => executionStore.stepOut();
const handleContinue = () => executionStore.continueExecution();
const handleStop = () => executionStore.stopExecution();

const formatValue = (value: any): string => {
  if (value === null) return "null";
  if (typeof value === "object" || Array.isArray(value)) {
    try { return JSON.stringify(value, null, 2); } catch { return "[Circular]"; }
  }
  return String(value);
};
</script>

<template>
  <div class="panel-content">
    <div class="debug-controls">
      <Button size="small" :disabled="!executionStore.isDebugMode" @click="handleStepOver">
        <StepForwardOutlined /> 单步
      </Button>
      <Button size="small" :disabled="!executionStore.isDebugMode" @click="handleStepInto">
        <StepBackwardOutlined /> 进入
      </Button>
      <Button size="small" :disabled="!executionStore.isDebugMode" @click="handleStepOut">
        <StepForwardOutlined /> 跳出
      </Button>
      <Button size="small" type="primary" :disabled="!executionStore.isDebugMode" @click="handleContinue">
        <PlayCircleOutlined /> 继续
      </Button>
      <Button size="small" danger :disabled="!executionStore.isRunning && !executionStore.isPaused" @click="handleStop">
        <StopOutlined /> 停止
      </Button>
    </div>

    <Tabs v-model:activeKey="activeTab" size="small" class="debug-tabs">
      <TabPane key="watches" tab="监视">
        <div class="tab-scroll">
          <Button size="small" type="primary" style="margin-bottom:8px" disabled>
            <PlusOutlined /> 添加监视
          </Button>
          <div v-for="watch in executionStore.variableWatches" :key="watch.id" class="watch-item">
            <div class="watch-info">
              <span class="watch-name">{{ watch.name }}</span>
              <span class="watch-expr">= {{ watch.expression }}</span>
            </div>
            <pre class="watch-value">{{ formatValue(watch.value) }}</pre>
            <Button type="text" size="small" danger @click="handleRemoveWatch(watch.id)">
              <DeleteOutlined />
            </Button>
          </div>
          <p v-if="executionStore.variableWatches.length === 0" class="empty-hint">暂无监视变量</p>
        </div>
      </TabPane>

      <TabPane key="breakpoints" tab="断点">
        <div class="tab-scroll">
          <div v-for="bp in executionStore.breakpoints" :key="bp.id" class="bp-item">
            <Switch :checked="bp.enabled" @change="executionStore.toggleBreakpoint(bp.id)" size="small" />
            <span>节点: {{ bp.node_id }}</span>
            <Button type="text" size="small" danger @click="executionStore.removeBreakpoint(bp.id)">
              <DeleteOutlined />
            </Button>
          </div>
          <p v-if="executionStore.breakpoints.length === 0" class="empty-hint">暂无断点</p>
        </div>
      </TabPane>

      <TabPane key="variables" tab="变量">
        <div class="tab-scroll">
          <div v-for="[key, value] in Object.entries(executionStore.variables)" :key="key" class="var-item">
            <span class="var-key">{{ key }}</span>
            <pre class="var-val">{{ formatValue(value) }}</pre>
          </div>
          <p v-if="Object.keys(executionStore.variables).length === 0" class="empty-hint">暂无变量</p>
        </div>
      </TabPane>
    </Tabs>
  </div>
</template>

<style scoped>
.panel-content {
  display: flex;
  flex-direction: column;
  height: 0;
  flex: 1;
  overflow: hidden;
}

.debug-controls {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  border-bottom: 1px solid #334155;
  flex-wrap: wrap;
}

.debug-tabs {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.debug-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 0 !important;
  padding: 0 12px;
  background: #0f172a;
}

.debug-tabs :deep(.ant-tabs-tab) {
  padding: 6px 12px !important;
  font-size: 12px !important;
  color: #64748b !important;
}

.debug-tabs :deep(.ant-tabs-tab-active .ant-tabs-tab-btn) {
  color: #e2e8f0 !important;
}

.debug-tabs :deep(.ant-tabs-content-holder) {
  flex: 1;
  overflow: hidden;
}

.debug-tabs :deep(.ant-tabs-content) {
  height: 100%;
}

.debug-tabs :deep(.ant-tabs-tabpane) {
  height: 100%;
  overflow: hidden;
}

.tab-scroll {
  height: 100%;
  overflow-y: auto;
  padding: 8px 12px;
}

.tab-scroll::-webkit-scrollbar {
  width: 4px;
}

.tab-scroll::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 2px;
}

.watch-item, .bp-item, .var-item {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.watch-info, .bp-item {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.watch-name {
  font-weight: 600;
  color: #e2e8f0;
}

.watch-expr {
  color: #64748b;
}

.watch-value, .var-val {
  margin: 0;
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 11px;
  color: #94a3b8;
  white-space: pre-wrap;
  word-break: break-all;
  background: rgba(0,0,0,0.2);
  padding: 6px 8px;
  border-radius: 4px;
}

.var-item {
  flex-direction: row;
  align-items: flex-start;
  gap: 8px;
}

.var-key {
  font-weight: 600;
  color: #e2e8f0;
  min-width: 80px;
  flex-shrink: 0;
}

.var-val {
  flex: 1;
  min-width: 0;
}

.empty-hint {
  text-align: center;
  color: #64748b;
  font-size: 12px;
  padding: 20px 0;
  margin: 0;
}
</style>
