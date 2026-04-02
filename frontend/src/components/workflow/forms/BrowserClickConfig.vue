<script setup lang="ts">
import { useWorkflowStore } from "../../../stores/workflow";
import { TextField, SelectField, NumberField, SwitchField } from "../fields";

const store = useWorkflowStore();

const selectorTypeOptions = [
  { label: "CSS Selector", value: "css" },
  { label: "XPath", value: "xpath" },
  { label: "Text", value: "text" },
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
  <div class="browser-click-config">
    <SelectField
      label="选择器类型"
      :value="store.selectedNode?.data.config?.selectorType || 'css'"
      :options="selectorTypeOptions"
      @update:value="(v) => handleConfigChange('selectorType', v)"
    />
    <TextField
      label="选择器值"
      :value="store.selectedNode?.data.config?.selector"
      placeholder=".button-class"
      required
      @update:value="(v) => handleConfigChange('selector', v)"
    />
    <NumberField
      label="超时时间 (毫秒)"
      :value="store.selectedNode?.data.config?.timeout || 10000"
      :min="1000"
      :max="60000"
      :step="1000"
      @update:value="(v) => handleConfigChange('timeout', v)"
    />
    <SwitchField
      label="等待元素可见"
      :value="store.selectedNode?.data.config?.waitVisible !== false"
      @update:value="(v) => handleConfigChange('waitVisible', v)"
    />
    <SwitchField
      label="多次尝试"
      :value="store.selectedNode?.data.config?.retry"
      @update:value="(v) => handleConfigChange('retry', v)"
    />
    <NumberField
      v-if="store.selectedNode?.data.config?.retry"
      label="尝试次数"
      :value="store.selectedNode?.data.config?.retryCount || 3"
      :min="1"
      :max="10"
      @update:value="(v) => handleConfigChange('retryCount', v)"
    />
  </div>
</template>

<style scoped>
.browser-click-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
