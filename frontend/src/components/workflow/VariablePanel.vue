<script setup lang="ts">
import { ref, computed } from "vue";
import { useExecutionStore } from "../../stores/execution";
import { Drawer, Select, Input, Button, Tooltip } from "ant-design-vue";
import {
  CopyOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
} from "@ant-design/icons-vue";

const executionStore = useExecutionStore();

const isOpen = ref(false);
const searchQuery = ref("");
const selectedType = ref<string | undefined>(undefined);
const expandedVariables = ref<Set<string>>(new Set());

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
  return entries.filter(([key, value]) => {
    const matchesSearch =
      !searchQuery.value ||
      key.toLowerCase().includes(searchQuery.value.toLowerCase());
    const varType = getVariableType(value);
    const matchesType =
      selectedType.value === undefined || varType === selectedType.value;
    return matchesSearch && matchesType;
  });
});

const formatValue = (value: any): string => {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (typeof value === "string") {
    return value.length > 100 ? value.slice(0, 100) + "..." : value;
  }
  if (typeof value === "object" || Array.isArray(value)) {
    try {
      const json = JSON.stringify(value, null, 2);
      return json.length > 500 ? json.slice(0, 500) + "\n..." : json;
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
  } catch (e) {
    console.error("Failed to copy:", e);
  }
};

const toggleVariableExpand = (key: string) => {
  if (expandedVariables.value.has(key)) {
    expandedVariables.value.delete(key);
  } else {
    expandedVariables.value.add(key);
  }
};

const togglePanel = () => {
  isOpen.value = !isOpen.value;
};

const getTypeColor = (type: string) => {
  switch (type) {
    case "string":
      return "#059669";
    case "number":
      return "#2563eb";
    case "boolean":
      return "#d97706";
    case "object":
      return "#7c3aed";
    case "array":
      return "#db2777";
    case "null":
      return "#6b7280";
    default:
      return "#6b7280";
  }
};

const getTypeIcon = (type: string) => {
  switch (type) {
    case "string":
      return "📝";
    case "number":
      return "🔢";
    case "boolean":
      return "⚡";
    case "object":
      return "📦";
    case "array":
      return "📋";
    case "null":
      return "∅";
    default:
      return "❓";
  }
};
</script>

<template>
  <div>
    <button
      class="variable-panel-toggle"
      @click="togglePanel"
      :class="{
        'has-variables': Object.keys(executionStore.variables).length > 0,
      }"
    >
      <span class="toggle-icon">📊</span>
      <span class="toggle-text">变量面板</span>
      <span
        v-if="Object.keys(executionStore.variables).length > 0"
        class="variable-count"
      >
        {{ Object.keys(executionStore.variables).length }}
      </span>
    </button>

    <Drawer
      :open="isOpen"
      placement="bottom"
      :height="500"
      @close="isOpen = false"
      :mask="true"
      :mask-closable="true"
      class="variable-drawer"
    >
      <template #title>
        <div class="variable-drawer-header">
          <div class="header-icon">
            <span>📊</span>
          </div>
          <div class="header-content">
            <h3 class="drawer-title">变量面板</h3>
            <p class="drawer-subtitle">
              共 {{ Object.keys(executionStore.variables).length }} 个变量
            </p>
          </div>
        </div>
      </template>

      <div class="variable-panel-content">
        <div class="variable-filters">
          <div class="filter-group">
            <Input
              v-model:value="searchQuery"
              placeholder="搜索变量..."
              prefix="🔍"
              class="search-input"
            />
          </div>
          <div class="filter-group">
            <Select
              v-model:value="selectedType"
              :options="typeOptions"
              style="width: 160px"
              class="type-select"
            />
          </div>
        </div>

        <div class="variable-list">
          <div
            v-for="[key, value] in filteredVariables"
            :key="key"
            class="variable-item"
          >
            <div class="variable-header">
              <div class="variable-info">
                <span class="variable-type-icon">{{
                  getTypeIcon(getVariableType(value))
                }}</span>
                <span class="variable-name">{{ key }}</span>
                <span
                  class="variable-type-badge"
                  :style="{
                    backgroundColor:
                      getTypeColor(getVariableType(value)) + '20',
                    color: getTypeColor(getVariableType(value)),
                  }"
                >
                  {{ getVariableType(value) }}
                </span>
              </div>
              <div class="variable-actions">
                <Tooltip title="复制值">
                  <Button
                    type="text"
                    size="small"
                    @click="copyToClipboard(key, value)"
                  >
                    <CopyOutlined />
                  </Button>
                </Tooltip>
                <Tooltip :title="expandedVariables.has(key) ? '收起' : '展开'">
                  <Button
                    type="text"
                    size="small"
                    @click="toggleVariableExpand(key)"
                  >
                    <EyeOutlined v-if="!expandedVariables.has(key)" />
                    <EyeInvisibleOutlined v-else />
                  </Button>
                </Tooltip>
              </div>
            </div>
            <div
              class="variable-value"
              :class="{ expanded: expandedVariables.has(key) }"
            >
              <pre>{{ formatValue(value) }}</pre>
            </div>
          </div>

          <div v-if="filteredVariables.length === 0" class="no-variables">
            <div class="no-variables-icon">📭</div>
            <p>暂无变量</p>
          </div>
        </div>
      </div>
    </Drawer>
  </div>
</template>

<style scoped>
.variable-panel-toggle {
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
}

.variable-panel-toggle:hover {
  background: #e5e7eb;
}

.variable-panel-toggle.has-variables {
  background: #dbeafe;
  border-color: #3b82f6;
}

.toggle-icon {
  font-size: 16px;
}

.toggle-text {
  font-weight: 500;
}

.variable-count {
  background: #3b82f6;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.variable-drawer {
  padding: 0;
}

:deep(.variable-drawer .ant-drawer-content) {
  border-radius: 12px 12px 0 0;
  box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.08);
}

:deep(.variable-drawer .ant-drawer-header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.variable-drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.variable-drawer-header .header-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  border-radius: 10px;
  font-size: 20px;
}

.variable-drawer-header .header-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.variable-drawer-header .drawer-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.variable-drawer-header .drawer-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.variable-panel-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0 24px 24px;
}

.variable-filters {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  padding-top: 20px;
}

.filter-group {
  display: flex;
  align-items: center;
}

.search-input {
  flex: 1;
  min-width: 200px;
}

:deep(.search-input .ant-input-wrapper) {
  border-radius: 10px;
}

:deep(.type-select .ant-select-selector) {
  border-radius: 10px;
}

.variable-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 4px;
}

.variable-list::-webkit-scrollbar {
  width: 6px;
}

.variable-list::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.variable-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.variable-list::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.variable-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.2s ease;
}

.variable-item:hover {
  border-color: #cbd5e1;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.variable-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #ffffff;
  border-bottom: 1px solid #f1f5f9;
}

.variable-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.variable-type-icon {
  font-size: 18px;
}

.variable-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
}

.variable-type-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.variable-actions {
  display: flex;
  gap: 4px;
}

.variable-value {
  padding: 12px 16px;
  max-height: 100px;
  overflow: hidden;
  transition: max-height 0.3s ease;
}

.variable-value.expanded {
  max-height: 400px;
  overflow-y: auto;
}

.variable-value pre {
  margin: 0;
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
  white-space: pre-wrap;
  word-break: break-all;
}

.no-variables {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  gap: 12px;
}

.no-variables-icon {
  font-size: 64px;
  opacity: 0.4;
}

.no-variables p {
  margin: 0;
  color: #94a3b8;
  font-size: 15px;
}
</style>
