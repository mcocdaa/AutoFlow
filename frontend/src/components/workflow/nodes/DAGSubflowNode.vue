<template>
  <GenericNode
    :data="data"
    :selected="selected"
    :dragging="dragging"
    :id="id"
    :class="{ 'node-expanded': isExpanded }"
  >
    <template #icon>
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    </template>
    <template #content>
      <div class="subflow-node-content">
        <div class="subflow-info">
          <span class="subflow-id">{{ subflowId }}</span>
        </div>
        <div class="subflow-status" @click.stop="toggleExpand">
          <span class="expand-icon">
            {{ isExpanded ? "▼" : "▶" }}
          </span>
          <span class="subflow-label">
            {{ isExpanded ? "点击折叠" : "点击预览" }}
          </span>
        </div>
      </div>
    </template>
  </GenericNode>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import GenericNode from "./GenericNode.vue";
import type { SubflowNodeData } from "../../../types/dag-workflow";

interface Props {
  data: SubflowNodeData;
  selected?: boolean;
  dragging?: boolean;
  id?: string;
}

const props = withDefaults(defineProps<Props>(), {
  selected: false,
  dragging: false,
});

const isExpanded = ref(false);

const subflowId = computed(() => {
  return props.data.config?.subflow_config?.subflow_id || "未选择";
});

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};
</script>

<style scoped>
.subflow-node-content {
  padding: 4px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.subflow-info {
  padding: 4px 8px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 4px;
  font-size: 12px;
  color: #10b981;
}

.subflow-id {
  font-weight: 500;
}

.subflow-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #10b981;
}

.subflow-status:hover {
  background: rgba(16, 185, 129, 0.2);
}

.expand-icon {
  font-size: 10px;
}

.node-expanded :deep(.node-body) {
  border-color: #10b981;
  box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.3);
}
</style>
