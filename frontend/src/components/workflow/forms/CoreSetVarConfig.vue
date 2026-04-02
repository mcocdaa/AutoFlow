<script setup lang="ts">
import { useWorkflowStore } from "../../../stores/workflow";
import { TextField, SelectField, SwitchField, JsonEditor } from "../fields";

const store = useWorkflowStore();

const typeOptions = [
  { label: "String", value: "string" },
  { label: "Number", value: "number" },
  { label: "Boolean", value: "boolean" },
  { label: "Object", value: "object" },
  { label: "Array", value: "array" },
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
  <div class="core-set-var-config">
    <TextField
      label="变量名"
      :value="store.selectedNode?.data.config?.varName"
      placeholder="输入变量名称"
      required
      @update:value="(v) => handleConfigChange('varName', v)"
    />
    <SelectField
      label="类型"
      :value="store.selectedNode?.data.config?.type || 'string'"
      :options="typeOptions"
      @update:value="(v) => handleConfigChange('type', v)"
    />
    <TextField
      v-if="
        store.selectedNode?.data.config?.type !== 'object' &&
        store.selectedNode?.data.config?.type !== 'array'
      "
      label="变量值"
      :value="store.selectedNode?.data.config?.value"
      placeholder="输入变量值"
      @update:value="(v) => handleConfigChange('value', v)"
    />
    <JsonEditor
      v-else
      label="变量值"
      :value="store.selectedNode?.data.config?.value"
      placeholder="{}"
      @update:value="(v) => handleConfigChange('value', v)"
    />
    <SwitchField
      label="覆盖已有变量"
      :value="store.selectedNode?.data.config?.overwrite !== false"
      @update:value="(v) => handleConfigChange('overwrite', v)"
    />
  </div>
</template>

<style scoped>
.core-set-var-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
