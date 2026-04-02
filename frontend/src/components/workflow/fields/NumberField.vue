<script setup lang="ts">
import { InputNumber } from "ant-design-vue";
import type { ValueType } from "ant-design-vue/es/input-number/src/utils/MiniDecimal";

interface Props {
  label?: string;
  value?: number;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  min?: number;
  max?: number;
  step?: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:value", value: ValueType): void;
}>();

const handleChange = (value: ValueType) => {
  emit("update:value", value);
};
</script>

<template>
  <div class="number-field">
    <label v-if="label" class="field-label">
      {{ label }}
      <span v-if="required" class="required-mark">*</span>
    </label>
    <InputNumber
      :value="value"
      :placeholder="placeholder"
      :disabled="disabled"
      :min="min"
      :max="max"
      :step="step"
      @update:value="handleChange"
      style="width: 100%"
    />
  </div>
</template>

<style scoped>
.number-field {
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
