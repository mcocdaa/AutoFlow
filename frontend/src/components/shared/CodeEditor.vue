<template>
  <div ref="host" class="code-editor"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { basicSetup, EditorView } from 'codemirror'
import { yaml } from '@codemirror/lang-yaml'
import { json } from '@codemirror/lang-json'

const props = withDefaults(defineProps<{
  modelValue: string
  minHeight?: number
  language?: 'yaml' | 'json'
}>(), {
  minHeight: 360,
  language: 'yaml',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const host = ref<HTMLDivElement | null>(null)
let view: EditorView | null = null

onMounted(() => {
  if (!host.value) return
  view = new EditorView({
    doc: props.modelValue,
    parent: host.value,
    extensions: [
      basicSetup,
      props.language === 'json' ? json() : yaml(),
      EditorView.lineWrapping,
      EditorView.theme({
        '&': {
          fontSize: '13px',
          backgroundColor: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '10px',
          overflow: 'hidden',
        },
        '&.cm-focused': {
          outline: 'none',
          borderColor: '#2563EB',
        },
        '.cm-scroller': {
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Monaco', 'Menlo', 'Consolas', monospace",
          lineHeight: '1.6',
          minHeight: `${props.minHeight}px`,
        },
        '.cm-gutters': {
          backgroundColor: '#F8FAFC',
          borderRight: '1px solid #E2E8F0',
          color: '#94A3B8',
        },
        '.cm-activeLine': {
          backgroundColor: '#F1F5F9',
        },
        '.cm-activeLineGutter': {
          backgroundColor: '#EEF2F7',
        },
        '.cm-content': {
          padding: '8px 0',
        },
        '.cm-cursor': {
          borderLeftColor: '#2563EB',
        },
      }, { dark: false }),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          emit('update:modelValue', update.state.doc.toString())
        }
      }),
    ],
  })
})

watch(() => props.modelValue, (value) => {
  if (!view) return
  const current = view.state.doc.toString()
  if (value !== current) {
    view.dispatch({ changes: { from: 0, to: current.length, insert: value } })
  }
})

onBeforeUnmount(() => {
  view?.destroy()
  view = null
})
</script>

<style scoped>
.code-editor {
  width: 100%;
}

.code-editor :deep(.cm-editor) {
  width: 100%;
}
</style>
