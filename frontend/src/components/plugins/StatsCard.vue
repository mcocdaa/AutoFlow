<template>
  <a-card class="stats-card" :bordered="false">
    <a-row :gutter="20" class="stats-row">
      <a-col :xs="24" :sm="24" :md="8">
        <div class="stat-item">
          <AppstoreOutlined class="stat-icon" />
          <div class="stat-number">{{ plugins.length }}</div>
          <div class="stat-label">Total Plugins</div>
        </div>
      </a-col>
      <a-col :xs="24" :sm="24" :md="8">
        <div class="stat-item">
          <ThunderboltOutlined class="stat-icon" />
          <div class="stat-number">{{ actions.length }}</div>
          <div class="stat-label">Actions</div>
        </div>
      </a-col>
      <a-col :xs="24" :sm="24" :md="8">
        <div class="stat-item">
          <CheckCircleOutlined class="stat-icon" />
          <div class="stat-number">{{ checks.length }}</div>
          <div class="stat-label">Checks</div>
        </div>
      </a-col>
    </a-row>
  </a-card>
</template>

<script setup lang="ts">
import {
  AppstoreOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons-vue'

defineProps<{
  plugins: any[]
  actions: string[]
  checks: string[]
}>()
</script>

<style scoped>
.stats-card {
  margin-bottom: 24px;
  background: var(--flow-gradient-autoflow);
  border-radius: 12px;
  box-shadow: var(--flow-shadow-medium);
}

.stats-card :deep(.ant-card-body) {
  padding: 0;
}

.stats-row {
  padding: 24px 0;
}

.stat-item {
  text-align: center;
  padding: 24px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: white;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.stat-icon {
  font-size: 24px;
}

.stat-number {
  font-size: 36px;
  font-weight: 700;
  color: #ffffff;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}
</style>
