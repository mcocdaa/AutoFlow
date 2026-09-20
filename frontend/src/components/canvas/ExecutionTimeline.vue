<template>
  <div v-if="run && run.steps.length > 0" class="timeline-container">
    <div class="timeline-header">
      <div class="header-left">
        <span class="title-icon">📊</span>
        <span class="title-text">执行瀑布流甘特图 (Execution Timeline)</span>
        <a-tag :color="statusColor" class="status-tag">{{ run.status.toUpperCase() }}</a-tag>
      </div>
      <div class="header-right">
        <span class="meta-label">总耗时:</span>
        <span class="meta-value af-mono">{{ run.duration_ms ?? 0 }} ms</span>
        <span class="meta-label" style="margin-left: 12px">步骤数:</span>
        <span class="meta-value af-mono">{{ run.steps.length }}</span>
      </div>
    </div>

    <div class="waterfall-chart">
      <div
        v-for="(step, idx) in processedSteps"
        :key="step.step_id"
        class="waterfall-row"
        :class="{ 'is-bottleneck': step.isBottleneck }"
      >
        <div class="row-label">
          <span class="step-idx">{{ idx + 1 }}.</span>
          <span class="step-id af-mono">{{ step.step_id }}</span>
          <span v-if="step.isBottleneck" class="bottleneck-tag" title="当前执行链路中最耗时步骤">
            ⚡ 耗时瓶颈 ({{ step.percentOfTotal }}%)
          </span>
        </div>

        <div class="row-track">
          <!-- 背景刻度标线 -->
          <div class="grid-line" style="left: 25%"></div>
          <div class="grid-line" style="left: 50%"></div>
          <div class="grid-line" style="left: 75%"></div>

          <!-- 时间轴条形 -->
          <div
            class="waterfall-bar"
            :class="`bar-${step.status}`"
            :style="{
              left: `${step.leftPercent}%`,
              width: `${Math.max(step.widthPercent, 1.5)}%`,
            }"
          >
            <span class="bar-duration">{{ step.duration_ms }}ms</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else-if="run" class="timeline-empty">
    <span>暂无步骤执行数据</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RunResult } from '../../types/runs'

const props = defineProps<{
  run: RunResult | null
}>()

const statusColor = computed(() => {
  if (!props.run) return 'default'
  if (props.run.status === 'success') return 'success'
  if (props.run.status === 'failed') return 'error'
  return 'processing'
})

const processedSteps = computed(() => {
  if (!props.run || !props.run.steps || props.run.steps.length === 0) return []

  const steps = props.run.steps
  const totalDuration = Math.max(props.run.duration_ms ?? 1, 1)

  // 找到耗时最长的有效步骤作为瓶颈
  let maxDuration = -1
  let bottleneckStepId = ''
  steps.forEach((s) => {
    if (s.duration_ms > maxDuration) {
      maxDuration = s.duration_ms
      bottleneckStepId = s.step_id
    }
  })

  // 计算相对时间偏移
  const firstStartTime = new Date(steps[0].started_at).getTime()

  return steps.map((s) => {
    const sStart = new Date(s.started_at).getTime()
    const offsetMs = Math.max(0, sStart - firstStartTime)
    const leftPercent = Math.min(100, Math.max(0, (offsetMs / totalDuration) * 100))
    const widthPercent = Math.min(100 - leftPercent, Math.max(1, (s.duration_ms / totalDuration) * 100))
    const percentOfTotal = Math.round((s.duration_ms / totalDuration) * 100)

    return {
      ...s,
      leftPercent,
      widthPercent,
      percentOfTotal,
      isBottleneck: s.step_id === bottleneckStepId && s.duration_ms > 0,
    }
  })
})
</script>

<style scoped>
.timeline-container {
  padding: 12px 16px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.03);
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  font-size: 15px;
}

.title-text {
  font-size: 13px;
  font-weight: 650;
  color: #1e293b;
}

.status-tag {
  font-size: 10.5px;
  font-weight: 700;
  margin-left: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.meta-label {
  color: #64748b;
}

.meta-value {
  color: #0f172a;
  font-weight: 600;
}

.waterfall-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.waterfall-row {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 28px;
}

.waterfall-row.is-bottleneck .step-id {
  color: #dc2626;
  font-weight: 700;
}

.row-label {
  width: 220px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-idx {
  font-size: 11px;
  color: #94a3b8;
  width: 16px;
}

.step-id {
  font-size: 12px;
  color: #334155;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bottleneck-tag {
  font-size: 10px;
  font-weight: 700;
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 1px 5px;
  border-radius: 4px;
  flex: none;
}

.row-track {
  flex: 1;
  position: relative;
  height: 20px;
  background: #f8fafc;
  border-radius: 4px;
  border: 1px solid #f1f5f9;
  overflow: hidden;
}

.grid-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #e2e8f0;
  z-index: 1;
}

.waterfall-bar {
  position: absolute;
  top: 2px;
  bottom: 2px;
  border-radius: 4px;
  z-index: 2;
  display: flex;
  align-items: center;
  padding: 0 6px;
  transition: all 0.3s ease;
  min-width: 24px;
}

.bar-duration {
  font-size: 10px;
  font-weight: 600;
  color: #ffffff;
  white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.bar-success {
  background: linear-gradient(90deg, #10b981, #059669);
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
}

.bar-failed {
  background: linear-gradient(90deg, #ef4444, #dc2626);
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.3);
}

.bar-skipped {
  background: #94a3b8;
}

.is-bottleneck .bar-success {
  background: linear-gradient(90deg, #f59e0b, #d97706);
  box-shadow: 0 2px 6px rgba(245, 158, 11, 0.4);
}

.timeline-empty {
  padding: 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
}
</style>
