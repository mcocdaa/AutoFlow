<template>
  <div class="run-view">
    <div class="page-header">
      <div class="header-left">
        <PlayCircleOutlined class="title-icon" />
        <h2 class="page-title">Run Flow</h2>
      </div>
    </div>

    <a-row :gutter="24" class="main-content">
      <a-col :xs="24" :md="12">
        <YamlEditor
          :loading="store.loading"
          @execute="handleExecute"
        />
      </a-col>

      <a-col :xs="24" :md="12">
        <ResultsPanel
          :run="currentRun"
          :error="store.error"
        />
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PlayCircleOutlined } from '@ant-design/icons-vue'
import { useRunsStore } from '../stores/runs'
import YamlEditor from '../components/run/YamlEditor.vue'
import ResultsPanel from '../components/run/ResultsPanel.vue'

const store = useRunsStore()

const currentRun = computed(() => store.currentRun)

const handleExecute = async (yaml: string, isDryRun: boolean) => {
  const vars = isDryRun ? { dry_run: true } : {}
  await store.executeFlow(yaml, {}, vars)
}
</script>

<style scoped>
.run-view {
  max-width: 1400px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 24px;
  color: var(--flow-color-primary);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--flow-text-title);
  margin: 0;
}

.main-content {
  margin-bottom: 24px;
}
</style>
