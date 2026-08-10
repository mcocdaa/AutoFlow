<template>
  <div class="section-header">
    <div class="section-title">
      <component :is="icon" class="title-icon" />
      {{ title }}
    </div>
    <a-input
      v-model:value="searchValue"
      :placeholder="searchPlaceholder"
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
        v-for="(items, pluginName) in groupedItems"
        :key="pluginName"
        :header="pluginName"
      >
        <div class="item-tags-group">
          <a-tag
            v-for="item in items"
            :key="item"
            :color="tagColor"
            class="item-tag"
            @click="$emit('copy', item)"
          >
            {{ item }}
          </a-tag>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </a-card>
</template>

<script setup lang="ts">
import { ref, computed, type Component } from 'vue'
import { SearchOutlined } from '@ant-design/icons-vue'

const props = defineProps<{
  title: string
  icon: Component
  items: string[]
  tagColor: string
  searchPlaceholder: string
}>()

defineEmits<{
  copy: [text: string]
}>()

const searchValue = ref('')

const groupedItems = computed(() => {
  const groups: Record<string, string[]> = {}
  props.items.forEach(item => {
    const pluginName = item.split('.')[0]
    if (!groups[pluginName]) {
      groups[pluginName] = []
    }
    if (item.toLowerCase().includes(searchValue.value.toLowerCase())) {
      groups[pluginName].push(item)
    }
  })
  return groups
})
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

.item-tags-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
}

.item-tag {
  font-size: 13px;
  cursor: pointer;
}

.item-tag:hover {
  opacity: 0.85;
}
</style>
