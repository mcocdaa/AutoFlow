<script setup lang="ts">
import { useWorkflowStore } from "../../../stores/workflow";

const workflowStore = useWorkflowStore();

const handleCodeChange = (event: Event) => {
  const target = event.target as HTMLTextAreaElement;
  if (workflowStore.selectedNode) {
    workflowStore.updateNode(workflowStore.selectedNode.id, {
      data: {
        ...workflowStore.selectedNode.data,
        config: {
          ...workflowStore.selectedNode.data.config,
          code: target.value,
        },
      },
    });
  }
};
</script>

<template>
  <div class="python-code-editor">
    <textarea
      v-if="workflowStore.selectedNode"
      :value="workflowStore.selectedNode.data.config?.code || ''"
      @input="handleCodeChange"
      class="code-editor"
    ></textarea>
  </div>
</template>

<style scoped>
.python-code-editor {
  width: 100%;
}

.code-editor {
  width: 100%;
  height: 300px;
  font-family: monospace;
  font-size: 14px;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: vertical;
}
</style>
