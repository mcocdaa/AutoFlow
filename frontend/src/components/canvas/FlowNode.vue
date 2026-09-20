<template>
  <div
    class="flow-node"
    :class="[
      `status-${data.status || 'idle'}`,
      { 'is-selected': selected }
    ]"
  >
    <Handle type="target" :position="Position.Top" class="flow-handle handle-top" />

    <div class="node-header">
      <div class="step-badge">{{ (data.index ?? 0) + 1 }}</div>
      <div class="node-title-group">
        <div class="node-id af-mono">{{ data.step.id }}</div>
        <div v-if="data.step.name" class="node-name">{{ data.step.name }}</div>
      </div>
      <div class="node-status-indicator" :class="`indicator-${data.status || 'idle'}`">
        <span v-if="data.status === 'running'" class="pulse-dot"></span>
        <span v-else-if="data.status === 'success'" class="icon-success">✓</span>
        <span v-else-if="data.status === 'failed'" class="icon-failed">✕</span>
      </div>
    </div>

    <div class="node-body">
      <div class="action-tag" :class="actionCategoryClass">
        <span class="action-icon">{{ actionCategoryIcon }}</span>
        <span class="action-type af-mono">{{ data.step.action.type }}</span>
      </div>

      <div v-if="data.step.check" class="check-tag">
        <span class="check-icon">🛡️</span>
        <span class="check-type af-mono">{{ data.step.check.type }}</span>
      </div>

      <div class="extra-badges">
        <span v-if="data.step.condition" class="badge-tag badge-condition" title="执行条件">
          ⚡ if
        </span>
        <span v-if="data.step.for_each" class="badge-tag badge-loop" title="循环遍历">
          🔁 loop
        </span>
        <span v-if="data.step.retry && data.step.retry.attempts > 0" class="badge-tag badge-retry" title="重试策略">
          🔄 x{{ data.step.retry.attempts }}
        </span>
        <span v-if="data.step.output_var" class="badge-tag badge-var" title="导出变量">
          📦 ${{ data.step.output_var }}
        </span>
      </div>

      <div v-if="data.duration_ms !== undefined" class="node-metrics">
        <span class="metric-duration">{{ data.duration_ms }} ms</span>
        <span v-if="data.check_passed !== undefined && data.check_passed !== null" class="metric-check" :class="data.check_passed ? 'check-pass' : 'check-fail'">
          Check: {{ data.check_passed ? 'PASS' : 'FAIL' }}
        </span>
      </div>
    </div>

    <Handle type="source" :position="Position.Bottom" class="flow-handle handle-bottom" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import type { FlowNodeData } from '../../types/flow'

const props = defineProps<{
  id: string
  data: FlowNodeData
  selected?: boolean
}>()

const actionCategoryClass = computed(() => {
  const type = props.data.step.action.type || ''
  if (type.startsWith('core.')) return 'cat-core'
  if (type.startsWith('dummy.')) return 'cat-dummy'
  if (type.startsWith('ai.') || type.includes('deepseek')) return 'cat-ai'
  if (type.startsWith('zhihu.') || type.startsWith('openclaw.')) return 'cat-scraper'
  if (type.startsWith('desktop.')) return 'cat-desktop'
  return 'cat-other'
})

const actionCategoryIcon = computed(() => {
  const type = props.data.step.action.type || ''
  if (type.startsWith('core.log')) return '📝'
  if (type.startsWith('core.')) return '⚙️'
  if (type.startsWith('dummy.')) return '📦'
  if (type.startsWith('ai.') || type.includes('deepseek')) return '🤖'
  if (type.startsWith('zhihu.') || type.startsWith('openclaw.')) return '🕷️'
  if (type.startsWith('desktop.')) return '🖥️'
  return '⚡'
})
</script>

<style scoped>
.flow-node {
  position: relative;
  width: 260px;
  background: #ffffff;
  border-radius: 12px;
  border: 1.5px solid #e2e8f0;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  user-select: none;
}

.flow-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.09);
  border-color: #cbd5e1;
}

.flow-node.is-selected {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2), 0 8px 20px rgba(37, 99, 235, 0.12);
}

/* 节点动态状态光效 */

/* 1. 运行中呼吸灯 */
.flow-node.status-running {
  border-color: #3b82f6;
  box-shadow: 0 0 16px rgba(59, 130, 246, 0.55);
  animation: breathing-glow 1.6s infinite ease-in-out alternate;
}

@keyframes breathing-glow {
  0% {
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.35);
    border-color: #60a5fa;
  }
  100% {
    box-shadow: 0 0 24px rgba(37, 99, 235, 0.75), 0 0 8px rgba(96, 165, 250, 0.9);
    border-color: #2563eb;
  }
}

/* 2. 成功翡翠绿光圈 */
.flow-node.status-success {
  border-color: #10b981;
  box-shadow: 0 0 14px rgba(16, 185, 129, 0.38);
}

/* 3. 失败绯红抖动与光晕 */
.flow-node.status-failed {
  border-color: #ef4444;
  box-shadow: 0 0 18px rgba(239, 68, 68, 0.45);
  animation: failure-shake 0.35s ease;
}

@keyframes failure-shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-4px); }
  40%, 80% { transform: translateX(4px); }
}

/* 4. 跳过 */
.flow-node.status-skipped {
  border-color: #f59e0b;
  opacity: 0.85;
}

/* 内部结构 */
.node-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #f8fafc;
  border-top-left-radius: 10px;
  border-top-right-radius: 10px;
  border-bottom: 1px solid #f1f5f9;
}

.step-badge {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  border-radius: 6px;
}

.status-running .step-badge {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-success .step-badge {
  background: #d1fae5;
  color: #065f46;
}

.status-failed .step-badge {
  background: #fee2e2;
  color: #991b1b;
}

.node-title-group {
  flex: 1;
  min-width: 0;
}

.node-id {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-name {
  font-size: 11px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  font-size: 11px;
  font-weight: bold;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3b82f6;
  box-shadow: 0 0 6px #3b82f6;
  animation: pulse-dot-anim 1s infinite;
}

@keyframes pulse-dot-anim {
  0% { transform: scale(0.8); opacity: 0.6; }
  50% { transform: scale(1.3); opacity: 1; }
  100% { transform: scale(0.8); opacity: 0.6; }
}

.icon-success {
  color: #10b981;
}

.icon-failed {
  color: #ef4444;
}

.node-body {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12px;
}

.action-icon {
  font-size: 13px;
}

.action-type {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 分类颜色 */
.cat-core { background: #eff6ff; color: #1e40af; }
.cat-dummy { background: #f0fdf4; color: #166534; }
.cat-ai { background: #faf5ff; color: #6b21a8; }
.cat-scraper { background: #fff7ed; color: #9a3412; }
.cat-desktop { background: #ecfeff; color: #155e75; }
.cat-other { background: #f1f5f9; color: #334155; }

.check-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #fdf2f8;
  color: #9d174d;
  border-radius: 6px;
  font-size: 11px;
}

.check-type {
  font-weight: 500;
}

.extra-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.badge-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-condition { background: #fef3c7; color: #92400e; }
.badge-loop { background: #e0e7ff; color: #3730a3; }
.badge-retry { background: #f1f5f9; color: #475569; }
.badge-var { background: #f3e8ff; color: #6b21a8; }

.node-metrics {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
  font-size: 11px;
}

.metric-duration {
  color: #64748b;
  font-family: monospace;
}

.metric-check {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
}

.check-pass { background: #d1fae5; color: #065f46; }
.check-fail { background: #fee2e2; color: #991b1b; }

/* Handles */
.flow-handle {
  width: 10px !important;
  height: 10px !important;
  border-radius: 50% !important;
  background: #94a3b8 !important;
  border: 2px solid #ffffff !important;
  transition: all 0.2s;
}

.flow-handle:hover {
  background: #2563eb !important;
  transform: scale(1.2);
}
</style>
