<script setup lang="ts">
import { useWorkflowStore } from "../../../stores/workflow";

const workflowStore = useWorkflowStore();

const handleConfigChange = (key: string, value: any) => {
  if (workflowStore.selectedNode) {
    const updatedConfig = {
      ...workflowStore.selectedNode.data.config,
      [key]: value,
    };
    workflowStore.updateNode(workflowStore.selectedNode.id, {
      data: {
        ...workflowStore.selectedNode.data,
        config: updatedConfig,
      },
    });
  }
};
</script>

<template>
  <div v-if="workflowStore.selectedNode" class="api-config-form">
    <a-form layout="vertical">
      <a-form-item label="URL">
        <a-input
          v-model:value="workflowStore.selectedNode.data.config.url"
          placeholder="请输入API URL"
          @update:value="handleConfigChange('url', $event)"
        />
      </a-form-item>
      <a-form-item label="Method">
        <a-select
          v-model:value="workflowStore.selectedNode.data.config.method"
          placeholder="请选择HTTP方法"
          @update:value="handleConfigChange('method', $event)"
        >
          <a-select-option value="GET">GET</a-select-option>
          <a-select-option value="POST">POST</a-select-option>
          <a-select-option value="PUT">PUT</a-select-option>
          <a-select-option value="DELETE">DELETE</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="Headers">
        <a-textarea
          v-model:value="workflowStore.selectedNode.data.config.headers"
          placeholder="请输入Headers (JSON格式)"
          :rows="4"
          @update:value="handleConfigChange('headers', $event)"
        />
      </a-form-item>
      <a-form-item label="Body">
        <a-textarea
          v-model:value="workflowStore.selectedNode.data.config.body"
          placeholder="请输入Body (JSON格式)"
          :rows="4"
          @update:value="handleConfigChange('body', $event)"
        />
      </a-form-item>
    </a-form>
  </div>
</template>

<style scoped>
.api-config-form {
  padding: 16px;
}
</style>
