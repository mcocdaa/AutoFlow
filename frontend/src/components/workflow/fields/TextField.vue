<script setup lang="ts">
import { Input } from "ant-design-vue";

interface Props {
  label?: string;
  value?: string;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:value", value: string): void;
}>();

const handleChange = (value: string) => {
  emit("update:value", value);
};
</script>

<template>
  <div class="text-field">
    <label v-if="label" class="field-label">
      {{ label }}
      <span v-if="required" class="required-mark">*</span>
    </label>
    <Input
      :value="value"
      :placeholder="placeholder"
      :disabled="disabled"
      @update:value="handleChange"
    />
  </div>
</template>

<style scoped>
.text-field {
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
</style>
