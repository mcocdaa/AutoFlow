<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useDAGWorkflowStore } from "../../stores/dag-workflow";
import { NODE_TEMPLATES } from "../../constants/node-templates";
import { getDefaultPorts } from "../../utils/node-defaults";
import type {
  NodeTemplate,
  NodeCategory,
} from "../../types/workflow";

interface CategoryGroup {
  id: NodeCategory;
  name: string;
  icon: string;
  nodes: NodeTemplate[];
}

const props = defineProps<{
  collapsed?: boolean;
}>();

const store = useDAGWorkflowStore();

const searchQuery = ref("");
const expandedCategories = ref<Set<NodeCategory>>(new Set(["start", "core"]));
const activeCategory = ref<NodeCategory | null>(null);

watch(
  () => props.collapsed,
  (collapsed) => {
    if (collapsed) {
      expandedCategories.value.clear();
      activeCategory.value = null;
    } else {
      expandedCategories.value = new Set(["start", "core"]);
    }
  },
);

const CATEGORY_INFO: Record<NodeCategory, { name: string; icon: string }> = {
  start: { name: "入口/出口", icon: "▶" },
  end: { name: "结束", icon: "⏹" },
  basic: { name: "基础节点", icon: "📦" },
  control: { name: "控制流", icon: "🔀" },
  data: { name: "数据处理", icon: "📊" },
  composite: { name: "组合节点", icon: "🧩" },
  core: { name: "核心动作", icon: "⚙️" },
  browser: { name: "浏览器", icon: "🌐" },
  tool: { name: "工具", icon: "🔧" },
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
    icon: CATEGORY_INFO[id as NodeCategory]?.icon || "\u{1F4E6}",
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
    if (activeCategory.value === categoryId) {
      activeCategory.value = null;
    }
  } else {
    expandedCategories.value.add(categoryId);
    activeCategory.value = categoryId;
  }
};

const isCategoryExpanded = (categoryId: NodeCategory): boolean => {
  return expandedCategories.value.has(categoryId);
};

watch(searchQuery, () => {
  if (searchQuery.value.trim()) {
    categories.value.forEach((cat) => {
      expandedCategories.value.add(cat.id);
    });
  }
});

const onDragStart = (event: DragEvent, template: NodeTemplate) => {
  if (!event.dataTransfer) return;
  event.dataTransfer.setData(
    "application/vueflow",
    JSON.stringify({ type: template.type, label: template.label }),
  );
  event.dataTransfer.effectAllowed = "move";
};

const addNodeToCenter = (template: NodeTemplate) => {
  const nodeId = crypto.randomUUID();
  const { inputs, outputs, error_port } = getDefaultPorts(template.type);
  const newNode = {
    id: nodeId,
    name: template.label,
    type: template.type as any,
    config: template.type === "core.log" ? { action_type: "core.log" } : {},
    metadata: {
      x: 300 + Math.random() * 100,
      y: 200 + Math.random() * 100,
    },
    inputs,
    outputs,
    error_port,
  };
  store.addNode(newNode as any);
};
</script>

<template>
  <div class="node-palette" :class="{ collapsed: props.collapsed }">
    <div v-if="!props.collapsed" class="search-bar">
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
        :class="{ expanded: isCategoryExpanded(category.id) }"
      >
        <div
          v-if="!props.collapsed"
          class="category-header"
          @click="toggleCategory(category.id)"
        >
          <span class="category-arrow-wrap">
            <span
              class="category-arrow"
              :class="{ expanded: isCategoryExpanded(category.id) }"
            >&#x25B6;</span>
          </span>
          <span class="category-icon">{{ category.icon }}</span>
          <span class="category-name">{{ category.name }}</span>
          <span class="category-count">{{ category.nodes.length }}</span>
        </div>
        <div
          v-else
          class="category-header-collapsed"
          :title="category.name"
          @click="toggleCategory(category.id)"
        >
          <span class="category-icon">{{ category.icon }}</span>
        </div>

        <transition name="accordion">
          <div v-show="isCategoryExpanded(category.id) && !props.collapsed" class="category-content">
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
            <div v-if="category.nodes.length === 0" class="empty-hint">无匹配节点</div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.node-palette {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #0f172a;
  overflow: hidden;
}

.node-palette.collapsed .search-bar {
  display: none;
}

.search-bar {
  padding: 12px;
  border-bottom: 1px solid #1e293b;
  flex-shrink: 0;
}

.search-input {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #334155;
  padding: 8px 12px;
  font-size: 13px;
  transition: all 0.2s;
  outline: none;
  background: #1e293b;
  color: #e2e8f0;
}

.search-input:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
  background: #1e293b;
}

.search-input::placeholder {
  color: #64748b;
}

.category-list {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 2px 0;
}

.category-list::-webkit-scrollbar {
  width: 3px;
}

.category-list::-webkit-scrollbar-thumb {
  background: #334155;
  border-radius: 2px;
}

.category {
  border-bottom: 1px solid #1e293b;
}

.category:last-child {
  border-bottom: none;
}

.category-header {
  display: flex;
  align-items: center;
  padding: 10px 14px 10px 12px;
  cursor: pointer;
  font-weight: 600;
  font-size: 12px;
  color: #94a3b8;
  transition: all 0.15s ease;
  user-select: none;
  letter-spacing: 0.2px;
  gap: 8px;
}

.category-header:hover {
  background: #1e293b;
  color: #e2e8f0;
}

.category-header-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 4px;
  cursor: default;
}

.category-arrow-wrap {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.category-arrow {
  font-size: 8px;
  color: #64748b;
  transition: transform 0.2s ease;
  display: inline-block;
}

.category-arrow.expanded {
  transform: rotate(90deg);
}

.category-icon {
  font-size: 14px;
  flex-shrink: 0;
  line-height: 1;
}

.node-palette.collapsed .category-icon {
  margin-right: 0;
}

.category-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-palette.collapsed .category-name {
  display: none;
}

.category-count {
  font-size: 10px;
  color: #475569;
  background: #1e293b;
  padding: 1px 7px;
  border-radius: 9999px;
  font-weight: 600;
  min-width: 18px;
  text-align: center;
  flex-shrink: 0;
}

.node-palette.collapsed .category-count,
.node-palette.collapsed .category-arrow-wrap {
  display: none;
}

.category-content {
  padding: 2px 8px 8px 20px;
  overflow: hidden;
}

.accordion-enter-active,
.accordion-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}

.accordion-enter-from,
.accordion-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.accordion-enter-to,
.accordion-leave-from {
  opacity: 1;
  max-height: 600px;
}

.node-item {
  display: flex;
  align-items: center;
  padding: 10px;
  margin: 3px 0;
  border-radius: 8px;
  cursor: grab;
  transition: all 0.18s ease;
  border: 1px solid transparent;
  background: #1e293b;
}

.node-item:hover {
  background: #334155;
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateX(2px);
}

.node-item:active {
  cursor: grabbing;
}

.node-item-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-right: 10px;
  flex-shrink: 0;
}

.node-item-content {
  flex: 1;
  min-width: 0;
}

.node-item-label {
  font-weight: 600;
  font-size: 13px;
  color: #e2e8f0;
  margin-bottom: 1px;
}

.node-item-description {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-hint {
  text-align: center;
  padding: 8px 0;
  font-size: 11px;
  color: #475569;
}
</style>
