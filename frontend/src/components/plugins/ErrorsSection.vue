<template>
  <div class="errors-section">
    <h3 class="section-title">
      <WarningOutlined class="title-icon" />
      {{ t('plugins.errorsTitle') }}
    </h3>
    <a-card>
      <a-table :data-source="errors" :pagination="false" :scroll="{ x: 640 }">
        <a-table-column :title="t('plugins.colPluginId')" data-index="plugin_id" width="180" />
        <a-table-column :title="t('plugins.colFilePath')" data-index="file_path" />
        <a-table-column :title="t('plugins.colError')" data-index="error" />
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { WarningOutlined } from '@ant-design/icons-vue'
import { useI18n } from '../../i18n'
import type { PluginError } from '../../types/plugins'

const { t } = useI18n()

defineProps<{
  errors: PluginError[]
}>()
</script>

<style scoped>
.errors-section {
  margin-top: 32px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.title-icon {
  color: var(--flow-color-warning);
}
</style>
