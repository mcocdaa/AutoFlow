<script setup lang="ts">
import { ref } from "vue";
import GenericNode from "./GenericNode.vue";

const props = defineProps<{
  data: any;
  selected?: boolean;
  id?: string;
}>();

const emit = defineEmits<{
  (e: "node-click", nodeId: string): void;
  (e: "node-double-click", nodeId: string): void;
  (e: "port-hover", portId: string, isHovered: boolean): void;
}>();

const isExpanded = ref(false);

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

const handleNodeClick = (nodeId: string) => {
  emit("node-click", nodeId);
};

const handleNodeDoubleClick = (nodeId: string) => {
  emit("node-double-click", nodeId);
};

const handlePortHover = (portId: string, isHovered: boolean) => {
  emit("port-hover", portId, isHovered);
};
</script>

<template>
  <div class="for-node-wrapper">
    <GenericNode
      :data="props.data"
      :selected="props.selected"
      :id="props.id"
      @node-click="handleNodeClick"
      @node-double-click="handleNodeDoubleClick"
      @port-hover="handlePortHover"
    />
    <button class="expand-button" @click.stop="toggleExpand">
      {{ isExpanded ? "▼" : "▶" }}
    </button>
    <div v-if="isExpanded" class="subgraph-container">
      <div class="subgraph-placeholder">
        <div class="subgraph-label">子图区域</div>
        <div class="subgraph-hint">双击展开编辑</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.for-node-wrapper {
  position: relative;
}

.expand-button {
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid #3b82f6;
  background: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  z-index: 10;
  transition: all 0.2s ease;
}

.expand-button:hover {
  background: #3b82f6;
  color: white;
}

.subgraph-container {
  margin-top: 12px;
  border: 2px dashed #3b82f6;
  border-radius: 8px;
  padding: 16px;
  background: rgba(59, 130, 246, 0.05);
}

.subgraph-placeholder {
  min-height: 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}

.subgraph-label {
  font-weight: 600;
  margin-bottom: 4px;
}

.subgraph-hint {
  font-size: 12px;
}
</style>
