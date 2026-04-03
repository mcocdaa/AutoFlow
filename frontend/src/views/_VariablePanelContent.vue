<script setup lang="ts">
import { ref, computed } from "vue";
import { useExecutionStore } from "../stores/execution";
import { Input, Select, Tooltip } from "ant-design-vue";
import { CopyOutlined } from "@ant-design/icons-vue";

const executionStore = useExecutionStore();

const searchQuery = ref("");
const selectedType = ref<string | undefined>(undefined);

const typeOptions = [
  { label: "All Types", value: undefined as string | undefined },
  { label: "String", value: "string" },
  { label: "Number", value: "number" },
  { label: "Boolean", value: "boolean" },
  { label: "Object", value: "object" },
  { label: "Array", value: "array" },
];

const getVariableType = (value: any): string => {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
};

const filteredVariables = computed(() => {
  const entries = Object.entries(executionStore.variables);
  return entries.filter(([key]) => {
    return !searchQuery.value || key.toLowerCase().includes(searchQuery.value.toLowerCase());
  });
});

const formatValue = (value: any): string => {
  if (value === null) return "null";
  if (typeof value === "string") {
    return value.length > 80 ? value.slice(0, 80) + "..." : value;
  }
  if (typeof value === "object" || Array.isArray(value)) {
    try {
      const json = JSON.stringify(value, null, 2);
      return json.length > 300 ? json.slice(0, 300) + "\n..." : json;
    } catch {
      return "[Circular]";
    }
  }
  return String(value);
};

const copyToClipboard = async (_key: string, value: any) => {
  try {
    let text = String(value);
    if (typeof value === "object" || Array.isArray(value)) {
      text = JSON.stringify(value, null, 2);
    }
    await navigator.clipboard.writeText(text);
  } catch (e) {}
};

const getTypeColor = (type: string) => {
  switch (type) {
    case "string": return "#10b981";
    case "number": return "#3b82f6";
    case "boolean": return "#f59e0b";
    case "object": return "#a78bfa";
    case "array": return "#ec4899";
    default: return "#64748b";
  }
};
</script>

<template>
  <div class="panel-content">
    <div class="panel-filters">
      <Input v-model:value="searchQuery" placeholder="搜索变量..." size="small" class="filter-input" />
      <Select v-model:value="selectedType" :options="typeOptions" size="small" style="width:110px" />
    </div>

    <div class="variable-list">
      <div v-for="[key, value] in filteredVariables" :key="key" class="variable-item">
        <div class="variable-header">
          <span class="variable-name">{{ key }}</span>
          <span
            class="variable-type"
            :style="{ color: getTypeColor(getVariableType(value)) }"
          >{{ getVariableType(value) }}</span>
          <Tooltip title="复制值">
            <button class="copy-btn" @click="copyToClipboard(key, value)">
              <CopyOutlined />
            </button>
          </Tooltip>
        </div>
        <pre class="variable-value">{{ formatValue(value) }}</pre>
      </div>

      <div v-if="filteredVariables.length === 0" class="empty-state">
        <p>暂无变量</p>
      </div>
    </div>
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

.panel-filters {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid #334155;
  align-items: center;
}

.filter-input {
  flex: 1;
}

.variable-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
}

.variable-list::-webkit-scrollbar {
  width: 4px;
}

.variable-list::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 2px;
}

.variable-item {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 6px;
  overflow: hidden;
  transition: all 0.15s ease;
}

.variable-item:hover {
  border-color: #334155;
}

.variable-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #1e293b;
}

.variable-name {
  font-weight: 600;
  font-size: 13px;
  color: #e2e8f0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.variable-type {
  font-size: 11px;
  font-weight: 600;
  background: rgba(255,255,255,0.04);
  padding: 1px 7px;
  border-radius: 9999px;
  flex-shrink: 0;
}

.copy-btn {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  font-size: 12px;
  transition: color 0.15s;
  flex-shrink: 0;
}

.copy-btn:hover {
  color: #6366f1;
}

.variable-value {
  margin: 0;
  padding: 8px 12px;
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 11px;
  line-height: 1.5;
  color: #94a3b8;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 120px;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.empty-state p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
</style>
