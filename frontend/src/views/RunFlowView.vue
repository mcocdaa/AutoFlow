<template>
  <div class="af-page">
    <PageHeader
      title="运行流程"
      description="编辑或加载 Flow YAML，执行后查看每一步的结果"
      :icon="PlayCircleOutlined"
    />

    <a-row :gutter="[24, 24]">
      <a-col :xs="24" :lg="12">
        <YamlEditor :loading="store.loading" @execute="handleExecute" />
      </a-col>
      <a-col :xs="24" :lg="12">
        <ResultsPanel :run="currentRun" :error="store.error" />
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PlayCircleOutlined } from '@ant-design/icons-vue'
import { useRunsStore } from '../stores/runs'
import PageHeader from '../components/shared/PageHeader.vue'
import YamlEditor from '../components/run/YamlEditor.vue'
import ResultsPanel from '../components/run/ResultsPanel.vue'

const store = useRunsStore()

const currentRun = computed(() => store.currentRun)

const handleExecute = async (yaml: string, isDryRun: boolean) => {
  const vars = isDryRun ? { dry_run: true } : {}
  try {
    await store.executeFlow(yaml, {}, vars)
  } catch (err) {
    console.error('Flow execution failed:', err)
  }
}
</script>
