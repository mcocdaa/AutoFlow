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
  <div class="subflow-node-wrapper">
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
        <div class="subgraph-label">子工作流预览</div>
        <div class="subgraph-hint">（只读）</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.subflow-node-wrapper {
  position: relative;
}

.expand-button {
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid #ec4899;
  background: #1a1f2e;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #94a3b8;
  z-index: 10;
  transition: all 0.2s ease;
}

.expand-button:hover {
  background: #ec4899;
  color: white;
}

.subgraph-container {
  margin-top: 12px;
  border: 1.5px dashed rgba(236, 72, 153, 0.4);
  border-radius: 8px;
  padding: 16px;
  background: rgba(236, 72, 153, 0.04);
}

.subgraph-placeholder {
  min-height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
}

.subgraph-label {
  font-weight: 600;
  margin-bottom: 4px;
}

.subgraph-hint {
  font-size: 12px;
}
</style>
