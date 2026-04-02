<script setup lang="ts">
import { ref, watch } from "vue";

interface Props {
  label?: string;
  value?: string;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  rows?: number;
}

const props = withDefaults(defineProps<Props>(), {
  rows: 10,
});

const emit = defineEmits<{
  (e: "update:value", value: string): void;
  (e: "error", error: string | null): void;
}>();

const internalValue = ref(props.value || "");
const errorMessage = ref<string | null>(null);

const validateJson = (value: string) => {
  if (!value.trim()) {
    errorMessage.value = null;
    emit("error", null);
    return true;
  }
  try {
    JSON.parse(value);
    errorMessage.value = null;
    emit("error", null);
    return true;
  } catch (e) {
    errorMessage.value = (e as Error).message;
    emit("error", errorMessage.value);
    return false;
  }
};

const handleInput = (event: Event) => {
  const target = event.target as HTMLTextAreaElement;
  internalValue.value = target.value;
  validateJson(target.value);
  emit("update:value", target.value);
};

const formatJson = () => {
  try {
    const parsed = JSON.parse(internalValue.value);
    const formatted = JSON.stringify(parsed, null, 2);
    internalValue.value = formatted;
    emit("update:value", formatted);
    errorMessage.value = null;
  } catch (e) {
    errorMessage.value = "Invalid JSON, cannot format";
  }
};

watch(
  () => props.value,
  (newValue) => {
    internalValue.value = newValue || "";
    validateJson(newValue || "");
  },
);
</script>

<template>
  <div class="json-editor-field">
    <div class="field-header">
      <label v-if="label" class="field-label">
        {{ label }}
        <span v-if="required" class="required-mark">*</span>
      </label>
      <button
        v-if="!disabled"
        type="button"
        @click="formatJson"
        class="format-btn"
      >
        格式化
      </button>
    </div>
    <textarea
      :value="internalValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :rows="rows"
      @input="handleInput"
      class="json-editor"
      :class="{ 'has-error': errorMessage }"
    ></textarea>
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<style scoped>
.json-editor-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.format-btn {
  font-size: 12px;
  padding: 4px 8px;
  background-color: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
  color: #374151;
}

.format-btn:hover {
  background-color: #e5e7eb;
}

.json-editor {
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

.json-editor:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.json-editor.has-error {
  border-color: #ef4444;
}

.json-editor:disabled {
  background-color: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}

.error-message {
  font-size: 12px;
  color: #ef4444;
}
</style>
