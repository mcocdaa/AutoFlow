<template>
  <div class="section-header">
    <div class="section-title">
      <ThunderboltOutlined class="title-icon" />
      Registered Actions
    </div>
    <a-input
      v-model:value="searchValue"
      placeholder="搜索 Actions"
      allow-clear
      class="search-input"
    >
      <template #prefix>
        <SearchOutlined />
      </template>
    </a-input>
  </div>
  <a-card class="tags-card">
    <a-collapse>
      <a-collapse-panel
        v-for="(actions, pluginName) in groupedActions"
        :key="pluginName"
        :header="pluginName"
      >
        <div class="action-tags-group">
          <a-tag
            v-for="action in actions"
            :key="action"
            color="blue"
            class="action-tag"
            @click="$emit('copy', action)"
          >
            {{ action }}
          </a-tag>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { ThunderboltOutlined, SearchOutlined } from "@ant-design/icons-vue";

const props = defineProps<{
  actions: string[];
}>();

defineEmits<{
  copy: [text: string];
}>();

const searchValue = ref("");

const groupedActions = computed(() => {
  const groups: Record<string, string[]> = {};
  props.actions.forEach((action) => {
    const pluginName = action.split(".")[0];
    if (!groups[pluginName]) {
      groups[pluginName] = [];
    }
    if (action.toLowerCase().includes(searchValue.value.toLowerCase())) {
      groups[pluginName].push(action);
    }
  });
  return groups;
});
</script>

<style scoped>
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 32px;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.title-icon {
  margin-right: 8px;
  color: var(--flow-color-primary);
  font-size: 20px;
}

.search-input {
  width: 200px;
}

.tags-card {
  border-radius: 12px;
}

.action-tags-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
}

.action-tag {
  font-size: 13px;
  cursor: pointer;
}

.action-tag:hover {
  opacity: 0.85;
}
</style>
