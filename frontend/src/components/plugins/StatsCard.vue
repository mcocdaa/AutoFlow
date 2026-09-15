<template>
  <a-card class="stats-card">
    <div class="stats-row">
      <div v-for="stat in stats" :key="stat.label" class="stat-item">
        <span class="stat-icon" :class="stat.tone">
          <component :is="stat.icon" />
        </span>
        <div class="stat-body">
          <div class="stat-number">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  AppstoreOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import type { Plugin } from '../../types/plugins'

const props = defineProps<{
  plugins: Plugin[]
  actions: string[]
  checks: string[]
}>()

const stats = computed(() => [
  {
    label: '插件',
    value: props.plugins.length,
    icon: AppstoreOutlined,
    tone: 'is-primary',
  },
  {
    label: 'Action',
    value: props.actions.length,
    icon: ThunderboltOutlined,
    tone: 'is-success',
  },
  {
    label: 'Check',
    value: props.checks.length,
    icon: CheckCircleOutlined,
    tone: 'is-warning',
  },
])
</script>

<style scoped>
.stats-card {
  margin-bottom: 24px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 24px;
  border-right: 1px solid var(--flow-border-color-soft);
}

.stat-item:first-child {
  padding-left: 0;
}

.stat-item:last-child {
  padding-right: 0;
  border-right: none;
}

.stat-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 42px;
  height: 42px;
  font-size: 20px;
  border-radius: 10px;
}

.stat-icon.is-primary {
  color: var(--flow-color-primary);
  background: var(--flow-color-primary-soft);
}

.stat-icon.is-success {
  color: var(--flow-color-success);
  background: var(--flow-color-success-soft);
}

.stat-icon.is-warning {
  color: var(--flow-color-warning);
  background: var(--flow-color-warning-soft);
}

.stat-body {
  min-width: 0;
}

.stat-number {
  font-size: 28px;
  font-weight: 650;
  line-height: 1.1;
  color: var(--flow-text-title);
}

.stat-label {
  margin-top: 2px;
  font-size: 13px;
  color: var(--flow-text-secondary);
}

@media (max-width: 767px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .stat-item {
    padding: 12px 0;
    border-right: none;
    border-bottom: 1px solid var(--flow-border-color-soft);
  }

  .stat-item:last-child {
    border-bottom: none;
  }
}
</style>
