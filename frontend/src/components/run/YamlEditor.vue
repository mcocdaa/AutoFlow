<template>
  <a-card class="yaml-card">
    <template #title>
      <div class="card-header">
        <div class="card-title">
          <FileTextOutlined class="card-icon" />
          Flow YAML
        </div>
        <a-select
          v-model:value="selectedExample"
          placeholder="Load Example"
          @change="handleLoadExample"
          class="example-select"
        >
          <a-select-option label="Minimal Echo" value="echo" />
          <a-select-option label="Desktop Checkin" value="desktop" />
          <a-select-option label="Zhihu Digest" value="zhihu" />
        </a-select>
      </div>
    </template>
    <a-textarea
      v-model:value="yamlContent"
      :rows="15"
      placeholder="Paste your flow YAML here..."
      class="yaml-input"
    />
    <div class="action-buttons">
      <a-checkbox v-model:checked="isDryRun" class="dry-run-checkbox">
        <template #icon><CloudOutlined /></template>
        Dry Run
      </a-checkbox>
      <a-button
        type="primary"
        @click="$emit('execute', yamlContent, isDryRun)"
        :loading="loading"
        class="execute-button"
      >
        <template #icon><ArrowRightOutlined /></template>
        Execute
      </a-button>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  FileTextOutlined,
  CloudOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons-vue";
import {
  FLOW_EXAMPLES,
  DEFAULT_FLOW_YAML,
} from "../../constants/flow-examples";

const props = defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  execute: [yaml: string, isDryRun: boolean];
}>();

const yamlContent = ref(DEFAULT_FLOW_YAML);
const selectedExample = ref<string>();
const isDryRun = ref(false);

const handleLoadExample = (val: string) => {
  if (val && FLOW_EXAMPLES[val as keyof typeof FLOW_EXAMPLES]) {
    yamlContent.value = FLOW_EXAMPLES[val as keyof typeof FLOW_EXAMPLES];
  }
};

defineExpose({
  yamlContent,
});
</script>

<style scoped>
.yaml-card {
  border-radius: 12px;
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.card-icon {
  margin-right: 8px;
  color: var(--flow-color-primary);
}

.example-select {
  width: 200px;
}

.yaml-input {
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
}

.action-buttons {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  flex-wrap: wrap;
  gap: 12px;
}

.dry-run-checkbox {
  display: flex;
  align-items: center;
}

.execute-button {
  background: var(--flow-gradient-autoflow);
  border: none;
}

.execute-button:hover {
  opacity: 0.9;
  background: var(--flow-gradient-autoflow) !important;
}
</style>
