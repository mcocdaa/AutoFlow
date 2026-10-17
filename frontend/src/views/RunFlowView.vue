<template>
  <div class="af-page">
    <PageHeader
      :title="t('run.title')"
      :description="t('run.desc')"
      :icon="PlayCircleOutlined"
    />

    <a-row :gutter="[20, 20]">
      <a-col :xs="24" :md="12">
        <YamlEditor :loading="store.loading" @execute="handleExecute" />
      </a-col>
      <a-col :xs="24" :md="12">
        <ResultsPanel :run="currentRun" :error="store.error" />
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PlayCircleOutlined } from '@ant-design/icons-vue'
import { useI18n } from '../i18n'
import { useRunsStore } from '../stores/runs'
import PageHeader from '../components/shared/PageHeader.vue'
import YamlEditor from '../components/run/YamlEditor.vue'
import ResultsPanel from '../components/run/ResultsPanel.vue'

const { t } = useI18n()
const store = useRunsStore()

const currentRun = computed(() => store.currentRun)

const handleExecute = async (
  yaml: string,
  isDryRun: boolean,
  input: unknown,
  vars: Record<string, unknown>,
) => {
  const runtimeVars = isDryRun ? { ...vars, dry_run: true } : vars
  try {
    await store.executeFlow(yaml, input, runtimeVars)
  } catch (err) {
    console.error('Flow execution failed:', err)
  }
}
</script>
