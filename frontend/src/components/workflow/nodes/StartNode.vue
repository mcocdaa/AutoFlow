<script setup lang="ts">
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
  <div class="start-node-wrapper">
    <GenericNode
      :data="props.data"
      :selected="props.selected"
      :id="props.id"
      @node-click="handleNodeClick"
      @node-double-click="handleNodeDoubleClick"
      @port-hover="handlePortHover"
    />
  </div>
</template>

<style scoped>
.start-node-wrapper :deep(.node-container) {
  border-radius: 20px !important;
}

.start-node-wrapper :deep(.node-header) {
  background-color: #10b981 !important;
}
</style>
