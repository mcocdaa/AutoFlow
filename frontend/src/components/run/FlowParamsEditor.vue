<template>
  <a-collapse v-model:activeKey="activeKey" ghost class="params-collapse">
    <a-collapse-panel key="params" header="高级参数（input / vars）">
      <p v-if="hint" class="params-hint">{{ hint }}</p>
      <div class="params-grid">
        <div class="param-block">
          <span class="param-label">input（JSON）</span>
          <CodeEditor
            :model-value="inputText"
            language="json"
            :min-height="120"
            @update:model-value="emit('update:inputText', $event)"
          />
        </div>
        <div class="param-block">
          <span class="param-label">vars（JSON）</span>
          <CodeEditor
            :model-value="varsText"
            language="json"
            :min-height="120"
            @update:model-value="emit('update:varsText', $event)"
          />
        </div>
      </div>
    </a-collapse-panel>
  </a-collapse>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import CodeEditor from '../shared/CodeEditor.vue'

const props = withDefaults(
  defineProps<{
    inputText: string
    varsText: string
    hint?: string
  }>(),
  {
    hint: '',
  },
)

const emit = defineEmits<{
  'update:inputText': [value: string]
  'update:varsText': [value: string]
}>()

const activeKey = ref<string[]>([])

watch(
  () => props.hint,
  (hint) => {
    if (hint) {
      activeKey.value = ['params']
    }
  },
)
</script>

<style scoped>
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
</style>
