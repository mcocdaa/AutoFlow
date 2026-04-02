<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  StarOutlined,
  StarFilled,
  SearchOutlined,
  EyeOutlined,
  DeleteOutlined,
} from "@ant-design/icons-vue";
import { message } from "ant-design-vue";
import type { Example, ExampleDifficulty } from "../../types/workflow";
import {
  EXAMPLE_CATEGORIES,
  OFFICIAL_EXAMPLES,
  customExamplesStorage,
} from "../../constants/examples";

interface Props {
  visible: boolean;
}

interface Emits {
  (e: "update:visible", value: boolean): void;
  (e: "importExample", example: Example): void;
  (e: "toggleFavorite", exampleId: string): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const searchQuery = ref("");
const selectedCategory = ref<string>("all");
const selectedDifficulty = ref<string>("all");
const selectedExample = ref<Example | null>(null);
const examples = ref<Example[]>([]);

const loadExamples = () => {
  const custom = customExamplesStorage.getAll();
  examples.value = [...custom, ...OFFICIAL_EXAMPLES];
};

const CATEGORY_INFO = EXAMPLE_CATEGORIES;
const DIFFICULTY_MAP: Record<ExampleDifficulty, string> = {
  beginner: "入门",
  intermediate: "中级",
  advanced: "高级",
};

const DIFFICULTY_COLORS: Record<ExampleDifficulty, string> = {
  beginner: "#10B981",
  intermediate: "#F59E0B",
  advanced: "#EF4444",
};

const filteredExamples = computed(() => {
  let result = [...examples.value];

  if (selectedCategory.value !== "all") {
    result = result.filter((e) => e.category === selectedCategory.value);
  }

  if (selectedDifficulty.value !== "all") {
    result = result.filter((e) => e.difficulty === selectedDifficulty.value);
  }

  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(
      (e) =>
        e.name.toLowerCase().includes(query) ||
        e.description.toLowerCase().includes(query) ||
        e.tags.some((tag) => tag.toLowerCase().includes(query)),
    );
  }

  return result;
});

const handleClose = () => {
  emit("update:visible", false);
  searchQuery.value = "";
  selectedCategory.value = "all";
  selectedDifficulty.value = "all";
  selectedExample.value = null;
};

const handleImport = (example: Example) => {
  emit("importExample", example);
  handleClose();
};

const handleToggleFavorite = (e: Event, example: Example) => {
  e.stopPropagation();
  if (example.isOfficial) {
    emit("toggleFavorite", example.id);
  } else {
    customExamplesStorage.toggleFavorite(example.id);
    loadExamples();
  }
  const index = examples.value.findIndex((ex) => ex.id === example.id);
  if (index !== -1) {
    examples.value[index].isFavorite = !examples.value[index].isFavorite;
  }
};

const handleDeleteExample = (e: Event, example: Example) => {
  e.stopPropagation();
  if (!example.isOfficial) {
    customExamplesStorage.delete(example.id);
    loadExamples();
    message.success("示例已删除");
    if (selectedExample.value?.id === example.id) {
      selectedExample.value = null;
    }
  }
};

const showExampleDetail = (example: Example) => {
  selectedExample.value = example;
};

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      loadExamples();
    } else {
      selectedExample.value = null;
    }
  },
);
</script>

<template>
  <a-modal
    :open="visible"
    title="导入示例"
    :footer="null"
    width="900px"
    @cancel="handleClose"
    :mask-closable="true"
  >
    <div class="example-selector">
      <div class="left-sidebar">
        <div class="sidebar-header">
          <span class="sidebar-title">分类</span>
        </div>

        <div class="category-list">
          <div
            :class="['category-item', { active: selectedCategory === 'all' }]"
            @click="selectedCategory = 'all'"
          >
            <span class="category-icon">📁</span>
            <span class="category-name">全部示例</span>
            <span class="category-count">{{ examples.length }}</span>
          </div>

          <div
            v-for="(info, cat) in CATEGORY_INFO"
            :key="cat"
            :class="['category-item', { active: selectedCategory === cat }]"
            @click="selectedCategory = cat"
          >
            <span class="category-icon">{{ info.icon }}</span>
            <span class="category-name">{{ info.name }}</span>
            <span class="category-count">
              {{ examples.filter((e) => e.category === cat).length }}
            </span>
          </div>
        </div>

        <div class="divider"></div>

        <div class="sidebar-header">
          <span class="sidebar-title">难度</span>
        </div>

        <div class="difficulty-list">
          <div
            :class="[
              'difficulty-item',
              { active: selectedDifficulty === 'all' },
            ]"
            @click="selectedDifficulty = 'all'"
          >
            <span class="difficulty-name">全部</span>
          </div>

          <div
            v-for="(name, diff) in DIFFICULTY_MAP"
            :key="diff"
            :class="[
              'difficulty-item',
              { active: selectedDifficulty === diff },
            ]"
            @click="selectedDifficulty = diff"
          >
            <span
              class="difficulty-dot"
              :style="{
                backgroundColor: DIFFICULTY_COLORS[diff as ExampleDifficulty],
              }"
            ></span>
            <span class="difficulty-name">{{ name }}</span>
          </div>
        </div>
      </div>

      <div class="right-content">
        <div class="search-section">
          <a-input-search
            v-model:value="searchQuery"
            placeholder="搜索示例名称、描述、标签..."
            :prefix-icon="SearchOutlined"
            size="large"
            allow-clear
          />
        </div>

        <div class="examples-grid">
          <div
            v-for="example in filteredExamples"
            :key="example.id"
            class="example-card"
            @click="showExampleDetail(example)"
          >
            <div class="card-header">
              <div
                class="category-badge"
                :style="{
                  backgroundColor: CATEGORY_INFO[example.category].color + '20',
                  color: CATEGORY_INFO[example.category].color,
                }"
              >
                {{ CATEGORY_INFO[example.category].name }}
              </div>
              <div class="card-actions">
                <a-button
                  type="text"
                  :icon="example.isFavorite ? StarFilled : StarOutlined"
                  :class="['favorite-btn', { active: example.isFavorite }]"
                  @click="handleToggleFavorite($event, example)"
                />
                <a-button
                  v-if="!example.isOfficial"
                  type="text"
                  danger
                  :icon="DeleteOutlined"
                  class="delete-btn"
                  @click="handleDeleteExample($event, example)"
                />
              </div>
            </div>

            <div class="card-body">
              <h3 class="example-name">
                {{ example.name }}
                <a-tag
                  v-if="!example.isOfficial"
                  color="blue"
                  style="margin-left: 8px; font-size: 10px"
                  >自定义</a-tag
                >
              </h3>
              <p class="example-description">{{ example.description }}</p>

              <div class="tags">
                <span v-for="tag in example.tags" :key="tag" class="tag">
                  {{ tag }}
                </span>
              </div>
            </div>

            <div class="card-footer">
              <div class="difficulty">
                <span
                  class="diff-badge"
                  :style="{
                    backgroundColor:
                      DIFFICULTY_COLORS[example.difficulty] + '20',
                    color: DIFFICULTY_COLORS[example.difficulty],
                  }"
                >
                  {{ DIFFICULTY_MAP[example.difficulty] }}
                </span>
              </div>

              <div class="stats">
                <span class="stat">
                  <EyeOutlined />
                  {{ example.usageCount }}
                </span>
                <span class="stat">
                  ⭐
                  {{ example.rating.toFixed(1) }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="filteredExamples.length === 0" class="empty-state">
            <div class="empty-icon">🔍</div>
            <p class="empty-text">没有找到匹配的示例</p>
          </div>
        </div>
      </div>

      <a-drawer
        :open="!!selectedExample"
        title="示例详情"
        width="400px"
        placement="right"
        @close="selectedExample = null"
      >
        <div v-if="selectedExample" class="example-detail">
          <div class="detail-header">
            <div
              class="category-badge-large"
              :style="{
                backgroundColor:
                  CATEGORY_INFO[selectedExample.category].color + '20',
                color: CATEGORY_INFO[selectedExample.category].color,
              }"
            >
              {{ CATEGORY_INFO[selectedExample.category].icon }}
              {{ CATEGORY_INFO[selectedExample.category].name }}
            </div>
            <div class="detail-actions">
              <a-button
                type="text"
                :icon="selectedExample.isFavorite ? StarFilled : StarOutlined"
                :class="[
                  'favorite-btn',
                  { active: selectedExample.isFavorite },
                ]"
                @click="handleToggleFavorite($event, selectedExample)"
              />
              <a-button
                v-if="!selectedExample.isOfficial"
                type="text"
                danger
                :icon="DeleteOutlined"
                class="delete-btn"
                @click="handleDeleteExample($event, selectedExample)"
              />
            </div>
          </div>

          <h2 class="detail-name">
            {{ selectedExample.name }}
            <a-tag
              v-if="!selectedExample.isOfficial"
              color="blue"
              style="margin-left: 8px"
              >自定义</a-tag
            >
          </h2>
          <p class="detail-description">{{ selectedExample.description }}</p>

          <div class="detail-tags">
            <span
              v-for="tag in selectedExample.tags"
              :key="tag"
              class="detail-tag"
            >
              {{ tag }}
            </span>
          </div>

          <div class="divider"></div>

          <div class="info-section">
            <div class="info-row">
              <span class="info-label">难度</span>
              <span
                class="info-value diff-badge"
                :style="{
                  backgroundColor:
                    DIFFICULTY_COLORS[selectedExample.difficulty] + '20',
                  color: DIFFICULTY_COLORS[selectedExample.difficulty],
                }"
              >
                {{ DIFFICULTY_MAP[selectedExample.difficulty] }}
              </span>
            </div>

            <div class="info-row">
              <span class="info-label">作者</span>
              <span class="info-value">{{ selectedExample.author }}</span>
            </div>

            <div class="info-row">
              <span class="info-label">使用次数</span>
              <span class="info-value">{{ selectedExample.usageCount }}</span>
            </div>

            <div class="info-row">
              <span class="info-label">评分</span>
              <span class="info-value"
                >⭐ {{ selectedExample.rating.toFixed(1) }}</span
              >
            </div>

            <div class="info-row">
              <span class="info-label">更新时间</span>
              <span class="info-value">{{
                selectedExample.updatedAt.toLocaleDateString()
              }}</span>
            </div>
          </div>

          <div class="divider"></div>

          <div class="yaml-preview">
            <div class="yaml-header">
              <span>YAML 预览</span>
            </div>
            <pre class="yaml-content">{{ selectedExample.yamlContent }}</pre>
          </div>

          <div class="detail-actions">
            <a-button
              type="primary"
              size="large"
              block
              @click="handleImport(selectedExample)"
            >
              导入示例
            </a-button>
          </div>
        </div>
      </a-drawer>
    </div>
  </a-modal>
</template>

<style scoped>
.example-selector {
  display: flex;
  height: 600px;
  margin: -24px;
  overflow: hidden;
}

.left-sidebar {
  width: 220px;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  padding: 16px 0;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 8px 16px;
  font-weight: 600;
  font-size: 12px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.category-list,
.difficulty-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.category-item,
.difficulty-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.category-item:hover,
.difficulty-item:hover {
  background: #e2e8f0;
}

.category-item.active,
.difficulty-item.active {
  background: #dbeafe;
  color: #3b82f6;
  font-weight: 500;
}

.category-icon {
  font-size: 16px;
}

.category-name,
.difficulty-name {
  flex: 1;
  font-size: 14px;
}

.category-count {
  font-size: 12px;
  color: #94a3b8;
  background: #e2e8f0;
  padding: 2px 8px;
  border-radius: 10px;
}

.category-item.active .category-count,
.difficulty-item.active .difficulty-count {
  background: #3b82f6;
  color: white;
}

.difficulty-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.divider {
  height: 1px;
  background: #e2e8f0;
  margin: 16px 0;
}

.right-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  overflow: hidden;
}

.search-section {
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.examples-grid {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
  align-content: start;
}

.example-card {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.example-card:hover {
  border-color: #3b82f6;
  transform: translateY(-4px);
  box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px 8px;
}

.card-actions {
  display: flex;
  gap: 4px;
}

.category-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
}

.favorite-btn,
.delete-btn {
  padding: 4px;
  color: #94a3b8;
  font-size: 18px;
  transition: all 0.2s;
}

.favorite-btn:hover {
  color: #f59e0b;
  transform: scale(1.1);
}

.favorite-btn.active {
  color: #f59e0b;
}

.delete-btn:hover {
  color: #ef4444;
  transform: scale(1.1);
}

.card-body {
  padding: 0 16px 12px;
  flex: 1;
}

.example-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 6px;
  display: flex;
  align-items: center;
}

.example-description {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 10px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  font-size: 11px;
  color: #475569;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid #f1f5f9;
  background: #fafafa;
}

.diff-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 4px;
}

.stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
}

.stat {
  display: flex;
  align-items: center;
  gap: 4px;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #64748b;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 14px;
}

.example-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-actions {
  display: flex;
  gap: 4px;
}

.category-badge-large {
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-name {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  display: flex;
  align-items: center;
}

.detail-description {
  font-size: 14px;
  color: #64748b;
  margin: 0;
  line-height: 1.6;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-tag {
  font-size: 12px;
  color: #475569;
  background: #f1f5f9;
  padding: 4px 10px;
  border-radius: 6px;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 13px;
  color: #64748b;
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
}

.yaml-preview {
  background: #1e293b;
  border-radius: 8px;
  overflow: hidden;
}

.yaml-header {
  padding: 8px 12px;
  background: #334155;
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
}

.yaml-content {
  margin: 0;
  padding: 12px;
  font-size: 11px;
  color: #e2e8f0;
  overflow-x: auto;
  white-space: pre;
  line-height: 1.6;
}

.detail-actions {
  margin-top: auto;
}
</style>
