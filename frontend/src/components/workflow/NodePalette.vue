<script setup lang="ts">
import { ref, computed } from "vue";
import { useWorkflowStore } from "../../stores/workflow";
import { NODE_TEMPLATES } from "../../constants/node-templates";
import type {
  NodeTemplate,
  NodeCategory,
  NodeType,
} from "../../types/workflow";

interface CategoryGroup {
  id: NodeCategory;
  name: string;
  icon: string;
  nodes: NodeTemplate[];
}

const store = useWorkflowStore();

const searchQuery = ref("");
const expandedCategories = ref<Set<NodeCategory>>(new Set(["start", "core"]));

const CATEGORY_INFO: Record<NodeCategory, { name: string; icon: string }> = {
  start: { name: "开始/结束", icon: "🚀" },
  end: { name: "结束", icon: "🔚" },
  basic: { name: "基础节点", icon: "📦" },
  control: { name: "控制流", icon: "🔀" },
  data: { name: "数据处理", icon: "📊" },
  composite: { name: "组合节点", icon: "🧩" },
  core: { name: "核心节点", icon: "⚙️" },
  browser: { name: "浏览器", icon: "🌐" },
  tool: { name: "工具", icon: "🛠️" },
  other: { name: "其他", icon: "📦" },
};

const categories = computed<CategoryGroup[]>(() => {
  const groups: Record<NodeCategory, NodeTemplate[]> = {} as any;

  NODE_TEMPLATES.forEach((template) => {
    if (!groups[template.category]) {
      groups[template.category] = [];
    }
    groups[template.category].push(template);
  });

  return Object.entries(groups).map(([id, nodes]) => ({
    id: id as NodeCategory,
    name: CATEGORY_INFO[id as NodeCategory]?.name || id,
    icon: CATEGORY_INFO[id as NodeCategory]?.icon || "📦",
    nodes: nodes as NodeTemplate[],
  }));
});

const filteredCategories = computed<CategoryGroup[]>(() => {
  if (!searchQuery.value.trim()) {
    return categories.value;
  }

  const query = searchQuery.value.toLowerCase();
  return categories.value
    .map((category) => ({
      ...category,
      nodes: category.nodes.filter(
        (node) =>
          node.label.toLowerCase().includes(query) ||
          node.description.toLowerCase().includes(query) ||
          node.type.toLowerCase().includes(query),
      ),
    }))
    .filter((category) => category.nodes.length > 0);
});

const toggleCategory = (categoryId: NodeCategory) => {
  if (expandedCategories.value.has(categoryId)) {
    expandedCategories.value.delete(categoryId);
  } else {
    expandedCategories.value.add(categoryId);
  }
};

const isCategoryExpanded = (categoryId: NodeCategory): boolean => {
  return expandedCategories.value.has(categoryId);
};

const onDragStart = (event: DragEvent, template: NodeTemplate) => {
  if (!event.dataTransfer) return;

  event.dataTransfer.setData(
    "application/vueflow",
    JSON.stringify({ type: template.type, label: template.label }),
  );
  event.dataTransfer.effectAllowed = "move";
};

const addNodeToCenter = (template: NodeTemplate) => {
  const newNode = {
    id: crypto.randomUUID(),
    type: template.type as NodeType,
    position: {
      x: 300 + Math.random() * 100,
      y: 200 + Math.random() * 100,
    },
    data: {
      type: template.type,
      label: template.label,
      config: {},
    },
  };

  store.addNode(newNode);
  store.selectNode(newNode.id);
};
</script>

<template>
  <div class="node-palette">
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索节点..."
        class="search-input"
      />
    </div>

    <div class="category-list">
      <div
        v-for="category in filteredCategories"
        :key="category.id"
        class="category"
      >
        <div class="category-header" @click="toggleCategory(category.id)">
          <span class="category-icon">{{ category.icon }}</span>
          <span class="category-name">{{ category.name }}</span>
          <span
            class="category-arrow"
            :class="{ expanded: isCategoryExpanded(category.id) }"
          >
            ▶
          </span>
        </div>

        <div v-show="isCategoryExpanded(category.id)" class="category-content">
          <div
            v-for="template in category.nodes"
            :key="template.type"
            class="node-item"
            draggable="true"
            @dragstart="onDragStart($event, template)"
            @click="addNodeToCenter(template)"
          >
            <div
              class="node-item-icon"
              :style="{
                backgroundColor: template.color + '20',
                color: template.color,
              }"
            >
              {{ template.icon }}
            </div>
            <div class="node-item-content">
              <div class="node-item-label">{{ template.label }}</div>
              <div class="node-item-description">
                {{ template.description }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.node-palette {
  height: 100%;
  max-height: 600px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow:
    0 1px 3px 0 rgba(0, 0, 0, 0.1),
    0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

.search-bar {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.search-input {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  padding: 10px 14px;
  font-size: 14px;
  transition: all 0.2s;
  outline: none;
}

.search-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.category-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 0;
  max-height: calc(600px - 70px);
}

.category-list::-webkit-scrollbar {
  width: 6px;
}

.category-list::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.category-list::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.category-list::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.category {
  border-bottom: 1px solid #f1f5f9;
}

.category:last-child {
  border-bottom: none;
}

.category-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  color: #475569;
  transition: background 0.2s;
  user-select: none;
}

.category-header:hover {
  background: #f8fafc;
}

.category-icon {
  margin-right: 8px;
  font-size: 16px;
}

.category-name {
  flex: 1;
}

.category-arrow {
  transition: transform 0.2s;
  font-size: 10px;
  color: #94a3b8;
}

.category-arrow.expanded {
  transform: rotate(90deg);
}

.category-content {
  padding: 4px 8px 8px;
}

.node-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin: 4px 0;
  border-radius: 8px;
  cursor: grab;
  transition: all 0.2s;
  border: 2px solid transparent;
  background: white;
}

.node-item:hover {
  background: #f8fafc;
  border-color: #667eea;
  transform: translateX(4px);
}

.node-item:active {
  cursor: grabbing;
}

.node-item-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-right: 12px;
  flex-shrink: 0;
}

.node-item-content {
  flex: 1;
  min-width: 0;
}

.node-item-label {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
  margin-bottom: 2px;
}

.node-item-description {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
