<script setup lang="ts">
interface Props {
  label?: string;
  value?: string;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  rows?: number;
  language?: string;
}

const props = withDefaults(defineProps<Props>(), {
  rows: 10,
  language: "text",
});

const emit = defineEmits<{
  (e: "update:value", value: string): void;
}>();

const handleInput = (event: Event) => {
  const target = event.target as HTMLTextAreaElement;
  emit("update:value", target.value);
};
</script>

<template>
  <div class="code-editor-field">
    <label v-if="label" class="field-label">
      {{ label }}
      <span v-if="required" class="required-mark">*</span>
    </label>
    <textarea
      :value="value"
      :placeholder="placeholder"
      :disabled="disabled"
      :rows="rows"
      @input="handleInput"
      class="code-editor"
    ></textarea>
  </div>
</template>

<style scoped>
.code-editor-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.required-mark {
  color: #ef4444;
  margin-left: 2px;
}

.code-editor {
  width: 100%;
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 13px;
  line-height: 1.5;
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  resize: vertical;
  background-color: #f9fafb;
  color: #1f2937;
}

.code-editor:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.code-editor:disabled {
  background-color: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}
</style>
