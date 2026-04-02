<script setup lang="ts">
import { Select } from "ant-design-vue";
import type { SelectValue } from "ant-design-vue/es/select";

interface Option {
  label: string;
  value: string | number;
}

interface Props {
  label?: string;
  value?: string | number;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  options: Option[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:value", value: SelectValue): void;
}>();

const handleChange = (value: SelectValue) => {
  emit("update:value", value);
};
</script>

<template>
  <div class="select-field">
    <label v-if="label" class="field-label">
      {{ label }}
      <span v-if="required" class="required-mark">*</span>
    </label>
    <Select
      :value="value"
      :placeholder="placeholder"
      :disabled="disabled"
      :options="options"
      @update:value="handleChange"
      style="width: 100%"
    />
  </div>
</template>

<style scoped>
.select-field {
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
