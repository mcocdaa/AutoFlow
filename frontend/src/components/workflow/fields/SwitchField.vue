<script setup lang="ts">
import { Switch } from "ant-design-vue";

interface Props {
  label?: string;
  value?: boolean;
  disabled?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:value", value: any): void;
}>();

const handleChange = (checked: any) => {
  emit("update:value", checked);
};
</script>

<template>
  <div class="switch-field">
    <div class="switch-wrapper">
      <span v-if="label" class="field-label">{{ label }}</span>
      <Switch
        :checked="value"
        :disabled="disabled"
        @update:checked="handleChange"
      />
    </div>
  </div>
</template>

<style scoped>
.switch-field {
  display: flex;
  flex-direction: column;
}

.switch-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-label {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}
</style>
