<template>
  <div class="tag-section">
    <div class="section-header">
      <h3 class="af-section-title">
        <component :is="icon" />
        {{ title }}
        <span class="items-count">{{ items.length }}</span>
      </h3>
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
    <a-card>
      <div v-if="groups.length > 0" class="groups">
        <div v-for="group in groups" :key="group.name" class="tag-group">
          <div class="tag-group-title">
            {{ group.name }}
            <span class="tag-group-count">{{ group.items.length }}</span>
          </div>
          <div class="tag-list">
            <a-tag
              v-for="item in group.items"
              :key="item"
              :color="tagColor"
              class="item-tag"
              title="点击复制"
              @click="emit('copy', item)"
            >
              {{ item }}
            </a-tag>
          </div>
        </div>
      </div>
      <a-empty v-else description="没有匹配项" :image="emptyImage" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, type Component } from 'vue'
import { Empty } from 'ant-design-vue'
import { SearchOutlined } from '@ant-design/icons-vue'

const props = defineProps<{
  title: string
  icon: Component
  items: string[]
  tagColor: string
  searchPlaceholder: string
}>()

const emit = defineEmits<{
  copy: [text: string]
}>()

const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE
const searchValue = ref('')

const groups = computed(() => {
  const keyword = searchValue.value.trim().toLowerCase()
  const buckets = new Map<string, string[]>()
  for (const item of props.items) {
    if (keyword && !item.toLowerCase().includes(keyword)) continue
    const group = item.split('.')[0]
    const list = buckets.get(group) ?? []
    list.push(item)
    buckets.set(group, list)
  }
  return [...buckets.entries()].map(([name, items]) => ({ name, items }))
})
</script>

<style scoped>
.tag-section {
  margin-top: 32px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.section-header .af-section-title {
  margin-bottom: 0;
}

.items-count {
  padding: 1px 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--flow-text-secondary);
  background: var(--flow-bg-layer);
  border-radius: 9999px;
}

.search-input {
  width: 220px;
}

.groups {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.tag-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--flow-text-primary);
}

.tag-group-count {
  font-size: 12px;
  font-weight: 500;
  color: var(--flow-text-disabled);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.item-tag {
  margin-inline-end: 0;
  font-size: 13px;
  cursor: pointer;
}
</style>
