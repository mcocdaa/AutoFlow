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
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    </template>
    <template #content>
      <div class="group-node-content">
        <div class="group-status" @click.stop="toggleExpand">
          <span class="expand-icon">
            {{ isExpanded ? "▼" : "▶" }}
          </span>
          <span class="group-label">
            {{ isExpanded ? "点击折叠" : "点击展开" }}
          </span>
        </div>
      </div>
    </template>
  </GenericNode>
</template>

<script setup lang="ts">
import { ref } from "vue";
import GenericNode from "./GenericNode.vue";
import type { GroupNodeData } from "../../../types/dag-workflow";

interface Props {
  data: GroupNodeData;
  selected?: boolean;
  dragging?: boolean;
  id?: string;
}

const props = withDefaults(defineProps<Props>(), {
  selected: false,
  dragging: false,
});

const isExpanded = ref(false);

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};
</script>

<style scoped>
.group-node-content {
  padding: 4px 0;
}

.group-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #667eea;
}

.group-status:hover {
  background: rgba(102, 126, 234, 0.2);
}

.expand-icon {
  font-size: 10px;
}

.node-expanded :deep(.node-body) {
  border-color: #667eea;
  box-shadow: 0 0 0 1px rgba(102, 126, 234, 0.3);
}
</style>
