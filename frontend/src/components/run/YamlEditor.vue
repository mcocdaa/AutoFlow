<template>
  <a-card class="editor-card">
    <template #title>
      <div class="card-header">
        <div class="card-title">
          <FileTextOutlined class="card-icon" />
          Flow YAML
        </div>
        <a-select
          v-model:value="selectedExample"
          :placeholder="t('run.loadExample')"
          class="example-select"
          @change="handleLoadExample"
        >
          <a-select-option
            v-for="(example, key) in FLOW_EXAMPLES"
            :key="key"
            :value="key"
          >
            {{ getFlowExampleLabel(example) }}
          </a-select-option>
        </a-select>
      </div>
    </template>

    <CodeEditor v-model="yamlContent" :min-height="360" />

    <FlowParamsEditor
      v-model:input-text="inputText"
      v-model:vars-text="varsText"
      :hint="exampleHint"
    />

    <div class="editor-footer">
      <div class="dry-run">
        <a-checkbox v-model:checked="isDryRun">{{ t('run.dryRun') }}</a-checkbox>
        <span class="dry-run-hint">{{ t('run.dryRunHint') }}</span>
      </div>
      <a-button type="primary" :loading="loading" @click="handleExecute">
        <template #icon><ArrowRightOutlined /></template>
        {{ loading ? t('run.executing') : t('run.execute') }}
      </a-button>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowRightOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import {
  DEFAULT_FLOW_YAML_EN,
  DEFAULT_FLOW_YAML_ZH,
  FLOW_EXAMPLES,
  getDefaultFlowYaml,
  getFlowExampleHint,
  getFlowExampleLabel,
} from '../../constants/flow-examples'
import { useI18n } from '../../i18n'
import { parseJsonInput, parseJsonObject } from '../../utils/json'
import CodeEditor from '../shared/CodeEditor.vue'
import FlowParamsEditor from './FlowParamsEditor.vue'

const { t, locale } = useI18n()

defineProps<{
  loading: boolean
}>()

const emit = defineEmits<{
  execute: [
    yaml: string,
    isDryRun: boolean,
    input: unknown,
    vars: Record<string, unknown>,
  ]
}>()

const yamlContent = ref(getDefaultFlowYaml())
watch(locale, () => {
  const trimmed = yamlContent.value.trim()
  if (
    trimmed === DEFAULT_FLOW_YAML_ZH.trim() ||
    trimmed === DEFAULT_FLOW_YAML_EN.trim()
  ) {
    yamlContent.value = getDefaultFlowYaml()
  }
})
const selectedExample = ref<string>()
const isDryRun = ref(false)
const inputText = ref('{}')
const varsText = ref('{}')

const exampleHint = computed(() => {
  if (!selectedExample.value) return ''
  const example = FLOW_EXAMPLES[selectedExample.value as keyof typeof FLOW_EXAMPLES]
  return example ? getFlowExampleHint(example) : ''
})

const handleLoadExample = (key: string) => {
  const example = FLOW_EXAMPLES[key as keyof typeof FLOW_EXAMPLES]
  if (!example) return
  yamlContent.value = example.yaml
}

const handleExecute = () => {
  const input = parseJsonInput(inputText.value, 'input')
  if (!input.ok) return
  const vars = parseJsonObject(varsText.value, 'vars')
  if (!vars) return
  emit('execute', yamlContent.value, isDryRun.value, input.value, vars)
}
</script>

<style scoped>
.editor-card {
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.card-icon {
  color: var(--flow-color-primary);
}

.example-select {
  width: 190px;
}

.params-collapse {
  margin-top: 12px;
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
}

.dry-run {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.dry-run-hint {
  font-size: 12px;
  color: var(--flow-text-secondary);
}
</style>
