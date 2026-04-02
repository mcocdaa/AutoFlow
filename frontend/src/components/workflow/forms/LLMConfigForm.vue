<script setup lang="ts">
import { useWorkflowStore } from "../../../stores/workflow";
import { Input, InputNumber, Textarea } from "ant-design-vue";

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
  <div class="llm-config-form">
    <div class="form-item">
      <Input
        :value="store.selectedNode?.data.config?.model"
        @update:value="(v) => handleConfigChange('model', v)"
        placeholder="Model Name"
      />
    </div>
    <div class="form-item">
      <Textarea
        :value="store.selectedNode?.data.config?.prompt"
        @update:value="(v) => handleConfigChange('prompt', v)"
        placeholder="Prompt"
        :rows="6"
      />
    </div>
    <div class="form-item">
      <InputNumber
        :value="store.selectedNode?.data.config?.temperature"
        @update:value="(v) => handleConfigChange('temperature', v)"
        :min="0"
        :max="2"
        :step="0.1"
        placeholder="Temperature"
        style="width: 100%"
      />
    </div>
  </div>
</template>

<style scoped>
.llm-config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item {
  width: 100%;
}
</style>
