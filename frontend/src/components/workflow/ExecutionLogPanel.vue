<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { useExecutionStore } from "../../stores/execution";
import {
  Drawer,
  Select,
  Input,
  Button,
  Switch,
  Dropdown,
  Menu,
  message,
} from "ant-design-vue";
import {
  DownloadOutlined,
  DeleteOutlined,
  DownOutlined,
} from "@ant-design/icons-vue";

const executionStore = useExecutionStore();

const isOpen = ref(false);
const searchQuery = ref("");
const selectedLevel = ref<string | undefined>(undefined);
const selectedNode = ref<string | undefined>(undefined);
const selectedTimeRange = ref<string>("all");
const autoScroll = ref(true);
const logListRef = ref<HTMLElement | null>(null);

const levelOptions = [
  { label: "全部级别", value: undefined },
  { label: "Debug", value: "debug" },
  { label: "Info", value: "info" },
  { label: "Warn", value: "warn" },
  { label: "Error", value: "error" },
];

const timeRangeOptions = [
  { label: "全部", value: "all" },
  { label: "最近 5 分钟", value: "5m" },
  { label: "最近 30 分钟", value: "30m" },
  { label: "最近 1 小时", value: "1h" },
];

const nodeOptions = computed(() => {
  const nodes = new Map<string, string>();
  executionStore.logs.forEach((log) => {
    if (log.node_id) {
      const name = log.nodeName || log.node_id;
      nodes.set(log.node_id, name);
    }
  });
  const options = Array.from(nodes.entries()).map(([id, name]) => ({
    label: name,
    value: id,
  }));
  return [{ label: "全部节点", value: undefined }, ...options];
});

const filteredLogs = computed(() => {
  return executionStore.logs.filter((log) => {
    const matchesLevel =
      selectedLevel.value === undefined || log.level === selectedLevel.value;
    const matchesSearch =
      !searchQuery.value ||
      log.message.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (log.nodeName &&
        log.nodeName.toLowerCase().includes(searchQuery.value.toLowerCase()));
    const matchesNode =
      selectedNode.value === undefined || log.node_id === selectedNode.value;

    let matchesTime = true;
    if (selectedTimeRange.value !== "all") {
      const now = Date.now();
      const logTime = new Date(log.timestamp).getTime();
      const diff = now - logTime;

      switch (selectedTimeRange.value) {
        case "5m":
          matchesTime = diff <= 5 * 60 * 1000;
          break;
        case "30m":
          matchesTime = diff <= 30 * 60 * 1000;
          break;
        case "1h":
          matchesTime = diff <= 60 * 60 * 1000;
          break;
      }
    }

    return matchesLevel && matchesSearch && matchesNode && matchesTime;
  });
});

const getLevelIcon = (level: string) => {
  switch (level) {
    case "debug":
      return "🔍";
    case "info":
      return "ℹ️";
    case "warn":
      return "⚠️";
    case "error":
      return "❌";
    default:
      return "📝";
  }
};

const getLevelColor = (level: string) => {
  switch (level) {
    case "debug":
      return "#6B7280";
    case "info":
      return "#3B82F6";
    case "warn":
      return "#F59E0B";
    case "error":
      return "#EF4444";
    default:
      return "#6B7280";
  }
};

const formatTime = (date: Date) => {
  const d = new Date(date);
  return d.toLocaleTimeString("zh-CN", { hour12: false });
};

const formatFullTime = (date: Date) => {
  const d = new Date(date);
  return d.toLocaleString("zh-CN", { hour12: false });
};

const togglePanel = () => {
  isOpen.value = !isOpen.value;
  if (isOpen.value) {
    nextTick(() => scrollToBottom());
  }
};

const scrollToBottom = () => {
  if (logListRef.value) {
    logListRef.value.scrollTop = logListRef.value.scrollHeight;
  }
};

watch(
  () => executionStore.logs.length,
  () => {
    if (autoScroll.value && isOpen.value) {
      nextTick(() => scrollToBottom());
    }
  },
);

const clearLogs = () => {
  executionStore.clearLogs();
  message.success("日志已清空");
};

const exportLogs = (format: "txt" | "json") => {
  if (executionStore.logs.length === 0) {
    message.warning("没有日志可导出");
    return;
  }

  let content = "";
  let filename = "";
  let mimeType = "";

  if (format === "json") {
    content = JSON.stringify(
      executionStore.logs.map((log) => ({
        ...log,
        timestamp: new Date(log.timestamp).toISOString(),
      })),
      null,
      2,
    );
    filename = `execution_logs_${Date.now()}.json`;
    mimeType = "application/json";
  } else {
    content = executionStore.logs
      .map((log) => {
        const nodeInfo = log.nodeName ? ` [${log.nodeName}]` : "";
        return `[${formatFullTime(log.timestamp)}] [${log.level.toUpperCase()}]${nodeInfo} ${log.message}`;
      })
      .join("\n");
    filename = `execution_logs_${Date.now()}.txt`;
    mimeType = "text/plain";
  }

  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  message.success(`日志已导出为 ${format.toUpperCase()}`);
};

const exportMenuItems = [
  { key: "txt", label: "导出为 TXT" },
  { key: "json", label: "导出为 JSON" },
];

const handleExportMenuClick = (info: any) => {
  const key = String(info.key);
  exportLogs(key as "txt" | "json");
};
</script>

<template>
  <div>
    <button
      class="log-panel-toggle"
      @click="togglePanel"
      :class="{ 'has-logs': executionStore.logs.length > 0 }"
    >
      <span class="toggle-icon">📋</span>
      <span class="toggle-text">执行日志</span>
      <span v-if="executionStore.logs.length > 0" class="log-count">
        {{ executionStore.logs.length }}
      </span>
    </button>

    <Drawer
      :open="isOpen"
      placement="bottom"
      :height="450"
      @close="isOpen = false"
      :mask="true"
      :mask-closable="true"
      class="log-drawer"
    >
      <template #title>
        <div class="log-drawer-header">
          <div class="header-icon">
            <span>📋</span>
          </div>
          <div class="header-content">
            <h3 class="drawer-title">执行日志</h3>
            <p class="drawer-subtitle">
              共 {{ executionStore.logs.length }} 条日志
            </p>
          </div>
          <div class="header-actions">
            <Dropdown :trigger="['click']">
              <template #overlay>
                <Menu @click="handleExportMenuClick" :items="exportMenuItems" />
              </template>
              <Button type="default">
                <template #icon>
                  <DownloadOutlined />
                </template>
                导出
                <DownOutlined />
              </Button>
            </Dropdown>
            <Button type="default" danger @click="clearLogs">
              <template #icon>
                <DeleteOutlined />
              </template>
              清空
            </Button>
          </div>
        </div>
      </template>

      <div class="log-panel-content">
        <div class="log-filters">
          <div class="filter-row">
            <div class="filter-group">
              <Input
                v-model:value="searchQuery"
                placeholder="搜索日志..."
                prefix="🔍"
                class="search-input"
              />
            </div>
            <div class="filter-group">
              <Select
                v-model:value="selectedLevel"
                :options="levelOptions"
                style="width: 140px"
                class="level-select"
                placeholder="日志级别"
              />
            </div>
            <div class="filter-group">
              <Select
                v-model:value="selectedNode"
                :options="nodeOptions"
                style="width: 160px"
                class="node-select"
                placeholder="节点过滤"
                :disabled="nodeOptions.length <= 1"
              />
            </div>
            <div class="filter-group">
              <Select
                v-model:value="selectedTimeRange"
                :options="timeRangeOptions"
                style="width: 140px"
                class="time-select"
                placeholder="时间范围"
              />
            </div>
          </div>
          <div class="filter-row options-row">
            <div class="auto-scroll-toggle">
              <span class="toggle-label">自动滚动</span>
              <Switch v-model:checked="autoScroll" size="small" />
            </div>
          </div>
        </div>

        <div class="log-list" ref="logListRef">
          <div
            v-for="log in filteredLogs"
            :key="log.id || log.timestamp.getTime()"
            class="log-item"
            :style="{ borderLeftColor: getLevelColor(log.level) }"
          >
            <span class="log-icon">{{ getLevelIcon(log.level) }}</span>
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span v-if="log.nodeName" class="log-node"
              >[{{ log.nodeName }}]</span
            >
            <span class="log-message">{{ log.message }}</span>
          </div>

          <div v-if="filteredLogs.length === 0" class="no-logs">
            <div class="no-logs-icon">📭</div>
            <p>暂无日志记录</p>
          </div>
        </div>
      </div>
    </Drawer>
  </div>
</template>

<style scoped>
.log-panel-toggle {
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

.log-panel-toggle:hover {
  background: #e5e7eb;
}

.log-panel-toggle.has-logs {
  background: #dbeafe;
  border-color: #3b82f6;
}

.toggle-icon {
  font-size: 16px;
}

.toggle-text {
  font-weight: 500;
}

.log-count {
  background: #3b82f6;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.log-drawer {
  padding: 0;
}

:deep(.log-drawer .ant-drawer-content) {
  border-radius: 12px 12px 0 0;
  box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.08);
}

:deep(.log-drawer .ant-drawer-header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.log-drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.log-drawer-header .header-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border-radius: 10px;
  font-size: 20px;
}

.log-drawer-header .header-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.log-drawer-header .drawer-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.log-drawer-header .drawer-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.log-drawer-header .header-actions {
  display: flex;
  gap: 8px;
}

.log-panel-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0 24px 24px;
}

.log-filters {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
  padding-top: 20px;
}

.filter-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.options-row {
  justify-content: flex-end;
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

:deep(.level-select .ant-select-selector),
:deep(.node-select .ant-select-selector),
:deep(.time-select .ant-select-selector) {
  border-radius: 10px;
}

.auto-scroll-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.toggle-label {
  font-size: 13px;
  color: #64748b;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 4px;
}

.log-list::-webkit-scrollbar {
  width: 6px;
}

.log-list::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.log-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.log-list::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.log-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f8fafc;
  border-left: 3px solid #6b7280;
  border-radius: 8px;
  font-size: 13px;
  transition: all 0.2s ease;
}

.log-item:hover {
  background: #f1f5f9;
  transform: translateX(2px);
}

.log-icon {
  font-size: 16px;
}

.log-time {
  color: #6b7280;
  font-family: monospace;
  font-size: 12px;
  background: #e2e8f0;
  padding: 2px 8px;
  border-radius: 4px;
}

.log-node {
  color: #3b82f6;
  font-weight: 600;
  font-size: 12px;
}

.log-message {
  flex: 1;
  color: #1f2937;
  line-height: 1.5;
}

.no-logs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  gap: 12px;
}

.no-logs-icon {
  font-size: 64px;
  opacity: 0.4;
}

.no-logs p {
  margin: 0;
  color: #94a3b8;
  font-size: 15px;
}
</style>
