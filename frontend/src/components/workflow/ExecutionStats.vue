<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useExecutionStore } from "../../stores/execution";
import type { ExecutionStatus } from "../../types/dag-workflow";

const executionStore = useExecutionStore();

const currentTime = ref(Date.now());
let timer: number | null = null;

const statusConfig: Record<
  ExecutionStatus,
  { label: string; color: string; icon: string }
> = {
  idle: { label: "空闲", color: "#9CA3AF", icon: "⏸️" },
  running: { label: "运行中", color: "#3B82F6", icon: "▶️" },
  paused: { label: "已暂停", color: "#F59E0B", icon: "⏯️" },
  completed: { label: "已完成", color: "#10B981", icon: "✅" },
  failed: { label: "失败", color: "#EF4444", icon: "❌" },
  stopped: { label: "已停止", color: "#6B7280", icon: "⏹️" },
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
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s ${ms % 1000}ms`;
  }
});

const successRate = computed(() => {
  const total = executionStore.successCount + executionStore.failedCount;
  if (total === 0) return 0;
  return Math.round((executionStore.successCount / total) * 100);
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
  <div class="execution-stats">
    <div class="status-section">
      <div class="status-item">
        <span class="status-icon">{{ currentStatus.icon }}</span>
        <span class="status-label">状态</span>
        <span class="status-value" :style="{ color: currentStatus.color }">{{
          currentStatus.label
        }}</span>
      </div>
      <div v-if="hasExecution" class="timer-item">
        <span class="timer-icon">⏱️</span>
        <span class="timer-label">执行时间</span>
        <span class="timer-value">{{ durationDisplay }}</span>
      </div>
    </div>
    <div v-if="hasExecution" class="stats-section">
      <div class="stat-item">
        <span class="stat-label">总节点数</span>
        <span class="stat-value">{{ executionStore.progress.total }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">已完成</span>
        <span class="stat-value success">{{
          executionStore.successCount
        }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">失败</span>
        <span class="stat-value error">{{ executionStore.failedCount }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">成功率</span>
        <span
          class="stat-value"
          :class="{
            success: successRate > 80,
            warning: successRate <= 80 && successRate >= 50,
            error: successRate < 50,
          }"
          >{{ successRate }}%</span
        >
      </div>
      <div class="stat-item">
        <span class="stat-label">进度</span>
        <span class="stat-value"
          >{{ executionStore.progress.percentage }}%</span
        >
      </div>
    </div>
  </div>
</template>

<style scoped>
.execution-stats {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.status-section {
  display: flex;
  gap: 32px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.status-item,
.timer-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-icon,
.timer-icon {
  font-size: 24px;
}

.status-label,
.timer-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
}

.status-value {
  font-size: 18px;
  font-weight: 700;
}

.timer-value {
  font-size: 20px;
  font-weight: 700;
  color: #60a5fa;
  font-family: "Courier New", monospace;
}

.stats-section {
  display: flex;
  gap: 28px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: white;
}

.stat-value.success {
  color: #4ade80;
}

.stat-value.warning {
  color: #fbbf24;
}

.stat-value.error {
  color: #f87171;
}
</style>
