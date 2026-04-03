<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { useExecutionStore } from "../stores/execution";
import {
  Select,
  Input,
  Switch,
} from "ant-design-vue";

const executionStore = useExecutionStore();

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
    case "debug": return "\u{1F50D}";
    case "info": return "\u2139\uFE0F";
    case "warn": return "\u26A0\uFE0F";
    case "error": return "\u274C";
    default: return "\u{1F4DD}";
  }
};

const getLevelColor = (level: string) => {
  switch (level) {
    case "debug": return "#6B7280";
    case "info": return "#3B82F6";
    case "warn": return "#F59E0B";
    case "error": return "#EF4444";
    default: return "#6B7280";
  }
};

const formatTime = (date: Date) => {
  const d = new Date(date);
  return d.toLocaleTimeString("zh-CN", { hour12: false });
};

const scrollToBottom = () => {
  if (logListRef.value) {
    logListRef.value.scrollTop = logListRef.value.scrollHeight;
  }
};

watch(
  () => executionStore.logs.length,
  () => {
    if (autoScroll.value) {
      nextTick(() => scrollToBottom());
    }
  },
);


</script>

<template>
  <div class="panel-content">
    <div class="panel-filters">
      <Input v-model:value="searchQuery" placeholder="搜索日志..." size="small" class="filter-input" />
      <Select v-model:value="selectedLevel" :options="levelOptions" size="small" style="width:100px" placeholder="级别" />
      <Switch v-model:checked="autoScroll" size="small" checked-children="自动滚动" un-checked-children="手动" />
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
        <span v-if="log.nodeName" class="log-node">[{{ log.nodeName }}]</span>
        <span class="log-message">{{ log.message }}</span>
      </div>

      <div v-if="filteredLogs.length === 0" class="empty-state">
        <p>暂无日志记录</p>
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
  flex-wrap: wrap;
}

.filter-input {
  flex: 1;
  min-width: 120px;
}

.log-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
}

.log-list::-webkit-scrollbar {
  width: 4px;
}

.log-list::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 2px;
}

.log-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: #0f172a;
  border-left: 3px solid #6b7280;
  border-radius: 4px;
  font-size: 12px;
  color: #94a3b8;
  transition: all 0.15s ease;
}

.log-item:hover {
  background: #1e293b;
}

.log-icon {
  font-size: 12px;
  flex-shrink: 0;
}

.log-time {
  font-family: monospace;
  font-size: 11px;
  color: #64748b;
  flex-shrink: 0;
}

.log-node {
  color: #6366f1;
  font-weight: 500;
  font-size: 11px;
}

.log-message {
  flex: 1;
  color: #cbd5e1;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-state p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
</style>
