<script setup lang="ts">
import { useWorkflowStore } from "../../../stores/workflow";
import { TextField, SelectField, SwitchField } from "../fields";

const store = useWorkflowStore();

const logLevelOptions = [
  { label: "Debug", value: "debug" },
  { label: "Info", value: "info" },
  { label: "Warn", value: "warn" },
  { label: "Error", value: "error" },
];

const handleConfigChange = (key: string, value: any) => {
  if (store.selectedNode) {
    store.updateNode(store.selectedNode.id, {
      data: {
        ...store.selectedNode.data,
        config: {
          ...store.selectedNode.data.config,
          [key]: value,
        },
      },
    });
  }
};
</script>

<template>
  <div class="core-log-config">
    <TextField
      label="消息"
      :value="store.selectedNode?.data.config?.message"
      placeholder="输入要输出的消息"
      @update:value="(v) => handleConfigChange('message', v)"
    />
    <SelectField
      label="日志级别"
      :value="store.selectedNode?.data.config?.level || 'info'"
      :options="logLevelOptions"
      @update:value="(v) => handleConfigChange('level', v)"
    />
    <SwitchField
      label="输出到控制台"
      :value="store.selectedNode?.data.config?.console !== false"
      @update:value="(v) => handleConfigChange('console', v)"
    />
  </div>
</template>

<style scoped>
.core-log-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
