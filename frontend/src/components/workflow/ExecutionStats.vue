<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useExecutionStore } from "../../stores/execution";
import { useWorkflowStore } from "../../stores/workflow";
import type { ExecutionStatus } from "../../types/dag-workflow";

const executionStore = useExecutionStore();
const workflowStore = useWorkflowStore();

const currentTime = ref(Date.now());
let timer: number | null = null;

const statusConfig: Record<
  ExecutionStatus,
  { label: string; color: string; dot: string }
> = {
  idle: { label: "空闲", color: "#64748b", dot: "#64748b" },
  running: { label: "运行中", color: "#3b82f6", dot: "#3b82f6" },
  paused: { label: "已暂停", color: "#f59e0b", dot: "#f59e0b" },
  completed: { label: "成功", color: "#10b981", dot: "#10b981" },
  failed: { label: "失败", color: "#ef4444", dot: "#ef4444" },
  stopped: { label: "已停止", color: "#6b7280", dot: "#6b7280" },
};

const currentStatus = computed(() => statusConfig[executionStore.status]);

const hasExecution = computed(() => executionStore.startTime !== null);

const currentDuration = computed(() => {
  if (!executionStore.startTime) return 0;
  return (
    executionStore.duration ||
    currentTime.value - executionStore.startTime.getTime()
  );
});

const durationDisplay = computed(() => {
  const ms = currentDuration.value;
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}:${String(minutes % 60).padStart(2, "0")}:${String(
      seconds % 60
    ).padStart(2, "0")}`;
  } else if (minutes > 0) {
    return `${minutes}:${String(seconds % 60).padStart(2, "0")}s`;
  } else {
    return `${seconds}.${String(Math.floor((ms % 1000) / 10)).padStart(
      2,
      "0"
    )}s`;
  }
});

const startTimer = () => {
  timer = window.setInterval(() => {
    currentTime.value = Date.now();
  }, 100);
};

const stopTimer = () => {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
};

onMounted(() => {
  startTimer();
});

onUnmounted(() => {
  stopTimer();
});
</script>

<template>
  <div class="status-bar">
    <div class="status-left">
      <span class="workflow-name">{{ workflowStore.name || 'hello-world' }}</span>
    </div>
    <div class="status-center">
      <span
        class="status-dot"
        :class="{ running: executionStore.status === 'running' }"
        :style="{ backgroundColor: currentStatus.dot }"
      ></span>
      <span
        class="status-label"
        :style="{ color: currentStatus.color }"
      >{{ currentStatus.label }}</span>
    </div>
    <div class="status-right">
      <template v-if="hasExecution">
        <span class="stat-item">
          <span class="stat-label">耗时</span>
          <span class="stat-value">{{ durationDisplay }}</span>
        </span>
        <span class="stat-divider"></span>
        <span class="stat-item">
          <span class="stat-label">节点</span>
          <span class="stat-value">{{ executionStore.progress.total }}</span>
        </span>
        <span class="stat-divider"></span>
        <span class="stat-item">
          <span class="stat-label success">完成</span>
          <span class="stat-value success">{{ executionStore.successCount }}</span>
        </span>
        <span class="stat-divider"></span>
        <span class="stat-item">
          <span class="stat-label error">失败</span>
          <span class="stat-value error">{{ executionStore.failedCount }}</span>
        </span>
      </template>
      <template v-else>
        <span class="stat-item">
          <span class="stat-label">就绪</span>
        </span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.status-bar {
  height: 40px;
  width: 100%;
  background: #1e293b;
  border-bottom: 1px solid #334155;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
}

.status-left {
  display: flex;
  align-items: center;
  min-width: 160px;
}

.workflow-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
}

.status-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: background-color 0.2s ease;
}

.status-dot.running {
  animation: breathe 2s ease-in-out infinite;
}

@keyframes breathe {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
  }
  50% {
    box-shadow: 0 0 8px 4px rgba(59, 130, 246, 0.15);
  }
}

.status-label {
  font-size: 13px;
  font-weight: 500;
}

.status-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
}

.stat-label.success {
  color: #10b981;
}

.stat-label.error {
  color: #ef4444;
}

.stat-value {
  font-size: 12px;
  font-weight: 600;
  color: #e2e8f0;
  font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
}

.stat-value.success {
  color: #10b981;
}

.stat-value.error {
  color: #ef4444;
}

.stat-divider {
  width: 1px;
  height: 16px;
  background: #334155;
}
</style>
