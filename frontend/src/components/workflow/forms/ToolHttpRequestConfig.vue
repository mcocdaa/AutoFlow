<script setup lang="ts">
import { computed } from "vue";
import { useWorkflowStore } from "../../../stores/workflow";
import { TextField, SelectField, NumberField, JsonEditor } from "../fields";

const store = useWorkflowStore();

const methodOptions = [
  { label: "GET", value: "GET" },
  { label: "POST", value: "POST" },
  { label: "PUT", value: "PUT" },
  { label: "DELETE", value: "DELETE" },
  { label: "PATCH", value: "PATCH" },
];

const headersString = computed(() => {
  const headers = store.selectedNode?.data.config?.headers;
  return headers ? JSON.stringify(headers, null, 2) : "";
});

const bodyString = computed(() => {
  const body = store.selectedNode?.data.config?.body;
  return body ? JSON.stringify(body, null, 2) : "";
});

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

const handleHeadersChange = (value: string) => {
  try {
    const parsed = value ? JSON.parse(value) : undefined;
    handleConfigChange("headers", parsed);
  } catch {
  }
};

const handleBodyChange = (value: string) => {
  try {
    const parsed = value ? JSON.parse(value) : undefined;
    handleConfigChange("body", parsed);
  } catch {
  }
};
</script>

<template>
  <div class="tool-http-request-config">
    <SelectField
      label="请求方法"
      :value="store.selectedNode?.data.config?.method || 'GET'"
      :options="methodOptions"
      @update:value="(v) => handleConfigChange('method', v)"
    />
    <TextField
      label="URL"
      :value="store.selectedNode?.data.config?.url"
      placeholder="https://api.example.com/endpoint"
      required
      @update:value="(v) => handleConfigChange('url', v)"
    />
    <JsonEditor
      label="请求头 (Headers)"
      :value="headersString"
      placeholder='{"Content-Type": "application/json"}'
      @update:value="handleHeadersChange"
    />
    <JsonEditor
      label="请求体 (Body)"
      :value="bodyString"
      placeholder='{"key": "value"}'
      @update:value="handleBodyChange"
    />
    <NumberField
      label="超时时间 (毫秒)"
      :value="store.selectedNode?.data.config?.timeout || 30000"
      :min="1000"
      :max="300000"
      :step="1000"
      @update:value="(v) => handleConfigChange('timeout', v)"
    />
    <TextField
      label="输出变量名"
      :value="store.selectedNode?.data.config?.outputVar"
      placeholder="response"
      @update:value="(v) => handleConfigChange('outputVar', v)"
    />
  </div>
</template>

<style scoped>
.tool-http-request-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
