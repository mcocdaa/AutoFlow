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
          placeholder="加载示例"
          class="example-select"
          @change="handleLoadExample"
        >
          <a-select-option
            v-for="(example, key) in FLOW_EXAMPLES"
            :key="key"
            :value="key"
          >
            {{ example.label }}
          </a-select-option>
        </a-select>
      </div>
    </template>

    <CodeEditor v-model="yamlContent" :min-height="360" />

    <a-collapse v-model:activeKey="paramsOpen" ghost class="params-collapse">
      <a-collapse-panel key="params" header="高级参数（input / vars）">
        <p v-if="exampleHint" class="params-hint">{{ exampleHint }}</p>
        <div class="params-grid">
          <div class="param-block">
            <span class="param-label">input（JSON）</span>
            <CodeEditor v-model="inputText" language="json" :min-height="120" />
          </div>
          <div class="param-block">
            <span class="param-label">vars（JSON）</span>
            <CodeEditor v-model="varsText" language="json" :min-height="120" />
          </div>
        </div>
      </a-collapse-panel>
    </a-collapse>

    <div class="editor-footer">
      <div class="dry-run">
        <a-checkbox v-model:checked="isDryRun">模拟执行</a-checkbox>
        <span class="dry-run-hint">仅对实现了模拟模式的插件生效</span>
      </div>
      <a-button type="primary" :loading="loading" @click="handleExecute">
        <template #icon><ArrowRightOutlined /></template>
        {{ loading ? '执行中' : '执行' }}
      </a-button>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { ArrowRightOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import { DEFAULT_FLOW_YAML, FLOW_EXAMPLES } from '../../constants/flow-examples'
import CodeEditor from '../shared/CodeEditor.vue'

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

const yamlContent = ref(DEFAULT_FLOW_YAML)
const selectedExample = ref<string>()
const isDryRun = ref(false)
const inputText = ref('{}')
const varsText = ref('{}')
const paramsOpen = ref<string[]>([])
const exampleHint = ref('')

type JsonParseResult = { ok: true; value: unknown } | { ok: false }

const parseJson = (text: string, label: string): JsonParseResult => {
  const trimmed = text.trim()
  if (!trimmed) return { ok: true, value: {} }
  try {
    return { ok: true, value: JSON.parse(trimmed) }
  } catch (err) {
    message.error(`${label} 不是合法 JSON：${(err as Error).message}`)
    return { ok: false }
  }
}

const handleLoadExample = (key: string) => {
  const example = FLOW_EXAMPLES[key as keyof typeof FLOW_EXAMPLES]
  if (!example) return
  yamlContent.value = example.yaml
  exampleHint.value = example.hint ?? ''
  if (example.hint) {
    paramsOpen.value = ['params']
  }
}

const handleExecute = () => {
  const input = parseJson(inputText.value, 'input')
  if (!input.ok) return
  const vars = parseJson(varsText.value, 'vars')
  if (!vars.ok) return
  if (typeof vars.value !== 'object' || vars.value === null || Array.isArray(vars.value)) {
    message.error('vars 需要是 JSON 对象')
    return
  }
  emit('execute', yamlContent.value, isDryRun.value, input.value, vars.value as Record<string, unknown>)
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

.params-collapse :deep(.ant-collapse-header) {
  padding: 8px 0;
  font-size: 13px;
  color: var(--flow-text-secondary);
}

.params-collapse :deep(.ant-collapse-content-box) {
  padding: 4px 0 0;
}

.params-hint {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.param-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.param-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--flow-text-primary);
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
