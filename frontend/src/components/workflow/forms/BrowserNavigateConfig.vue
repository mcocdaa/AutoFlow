<script setup lang="ts">
import { useWorkflowStore } from "../../../stores/workflow";
import { TextField, NumberField, SwitchField } from "../fields";

const store = useWorkflowStore();

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
  <div class="browser-navigate-config">
    <TextField
      label="URL"
      :value="store.selectedNode?.data.config?.url"
      placeholder="https://example.com"
      required
      @update:value="(v) => handleConfigChange('url', v)"
    />
    <NumberField
      label="超时时间 (毫秒)"
      :value="store.selectedNode?.data.config?.timeout || 30000"
      :min="1000"
      :max="300000"
      :step="1000"
      @update:value="(v) => handleConfigChange('timeout', v)"
    />
    <SwitchField
      label="等待页面加载完成"
      :value="store.selectedNode?.data.config?.waitForLoad !== false"
      @update:value="(v) => handleConfigChange('waitForLoad', v)"
    />
  </div>
</template>

<style scoped>
.browser-navigate-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
