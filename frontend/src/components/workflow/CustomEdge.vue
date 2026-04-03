<script setup lang="ts">
import { computed } from "vue";
import { useExecutionStore } from "../../stores/execution";
import { useDAGWorkflowStore } from "../../stores/dag-workflow";

const props = defineProps<{
  id?: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: string;
  targetPosition: string;
  data?: any;
}>();

const executionStore = useExecutionStore();
const dagStore = useDAGWorkflowStore();

const executionState = computed(() => {
  if (!props.id) return null;
  return executionStore.edges[props.id];
});

const isActive = computed(() => executionState.value?.status === "active");
const isSuccess = computed(() => executionState.value?.status === "success");
const isFailed = computed(() => executionState.value?.status === "failed");
const isSelected = computed(() =>
  props.id ? dagStore.selectedEdgeId === props.id : false,
);

const strokeColor = computed(() => {
  if (isSelected.value) return "#818cf8";
  if (isActive.value) return "#60a5fa";
  if (isSuccess.value) return "#34d399";
  if (isFailed.value) return "#f87171";
  return "#3d4a5c";
});

const strokeWidth = computed(() => {
  if (isSelected.value) return 2;
  if (isSuccess.value || isFailed.value || isActive.value) return 1.5;
  return 1.5;
});

const gradientId = computed(() =>
  props.id ? `flowGradient-${props.id}` : "flowGradient-default",
);
const maskId = computed(() =>
  props.id ? `flowMask-${props.id}` : "flowMask-default",
);

const getPathD = () => {
  const { sourceX, sourceY, targetX, targetY } = props;
  const dx = targetX - sourceX;
  const dy = targetY - sourceY;

  const isHorizontal = Math.abs(dx) > Math.abs(dy);

  if (isHorizontal && dx > 0) {
    const midX = sourceX + dx * 0.5;
    return `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`;
  }

  const controlPoint = Math.max(Math.abs(dx), Math.abs(dy)) * 0.45;
  return `M ${sourceX} ${sourceY} C ${sourceX + controlPoint} ${sourceY}, ${targetX - controlPoint} ${targetY}, ${targetX} ${targetY}`;
};
</script>

<template>
  <svg
    :style="{ position: 'absolute', width: 0, height: 0, overflow: 'visible' }"
  >
    <defs>
      <linearGradient :id="gradientId" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" :stop-color="strokeColor" stop-opacity="0" />
        <stop offset="10%" :stop-color="strokeColor" stop-opacity="1" />
        <stop offset="90%" :stop-color="strokeColor" stop-opacity="1" />
        <stop offset="100%" :stop-color="strokeColor" stop-opacity="0" />
      </linearGradient>
      <mask :id="maskId">
        <rect width="100%" height="100%" fill="white" />
        <path :d="getPathD()" stroke="black" stroke-width="6" fill="none" />
      </mask>
    </defs>
    <path
      :d="getPathD()"
      :stroke="strokeColor"
      :stroke-width="strokeWidth"
      fill="none"
      stroke-linecap="round"
      class="edge-path"
      :class="{
        'edge-shadow': isActive,
        'edge-selected': isSelected,
        'edge-pulse': isActive,
      }"
    />
    <path
      v-if="isActive"
      :d="getPathD()"
      :stroke="`url(#${gradientId})`"
      stroke-width="5"
      fill="none"
      stroke-linecap="round"
      stroke-dasharray="8 6"
      class="flow-animation"
    />
    <path
      v-if="isSuccess"
      :d="getPathD()"
      :stroke="strokeColor"
      stroke-width="2"
      fill="none"
      stroke-linecap="round"
      stroke-dasharray="6 3"
      opacity="0.35"
    />
  </svg>
</template>

<style scoped>
.edge-shadow {
  filter: drop-shadow(0 0 6px rgba(96, 165, 250, 0.4));
}

.edge-selected {
  filter: drop-shadow(0 0 8px rgba(129, 140, 248, 0.5));
}

.edge-pulse {
  animation: edgePulse 2s ease-in-out infinite;
}

@keyframes edgePulse {
  0%, 100% {
    filter: drop-shadow(0 0 4px rgba(96, 165, 250, 0.4));
  }
  50% {
    filter: drop-shadow(0 0 10px rgba(96, 165, 250, 0.65));
  }
}

.flow-animation {
  animation: flowAnimation 1.2s linear infinite;
}

@keyframes flowAnimation {
  0% { stroke-dashoffset: 28; }
  100% { stroke-dashoffset: 0; }
}
</style>
