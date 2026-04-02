<script setup lang="ts">
import { ref, reactive, watch } from "vue";
import { message } from "ant-design-vue";
import type {
  Example,
  ExampleCategory,
  ExampleDifficulty,
} from "../../types/workflow";
import {
  EXAMPLE_CATEGORIES,
  EXAMPLE_DIFFICULTIES,
  customExamplesStorage,
} from "../../constants/examples";

interface Props {
  visible: boolean;
  yamlContent: string;
  defaultName?: string;
}

interface Emits {
  (e: "update:visible", value: boolean): void;
  (e: "saved", example: Example): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const formState = reactive({
  name: "",
  description: "",
  category: "tutorial" as ExampleCategory,
  difficulty: "beginner" as ExampleDifficulty,
  tags: [] as string[],
});

const tagInput = ref("");

const resetForm = () => {
  formState.name = props.defaultName || "";
  formState.description = "";
  formState.category = "tutorial";
  formState.difficulty = "beginner";
  formState.tags = [];
  tagInput.value = "";
};

const handleAddTag = () => {
  const tag = tagInput.value.trim();
  if (tag && !formState.tags.includes(tag)) {
    formState.tags.push(tag);
    tagInput.value = "";
  }
};

const handleRemoveTag = (tagToRemove: string) => {
  formState.tags = formState.tags.filter((tag) => tag !== tagToRemove);
};

const handleSave = () => {
  if (!formState.name.trim()) {
    message.error("请输入示例名称");
    return;
  }

  if (!formState.description.trim()) {
    message.error("请输入示例描述");
    return;
  }

  const example = customExamplesStorage.save({
    name: formState.name.trim(),
    description: formState.description.trim(),
    category: formState.category,
    difficulty: formState.difficulty,
    tags: [...formState.tags],
    author: "Me",
    yamlContent: props.yamlContent,
  });

  message.success("示例保存成功！");
  emit("saved", example);
  handleClose();
};

const handleClose = () => {
  emit("update:visible", false);
  resetForm();
};

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      resetForm();
    }
  },
);
</script>

<template>
  <a-modal
    :open="visible"
    title="保存为示例"
    width="600px"
    @cancel="handleClose"
    :footer="null"
  >
    <div class="save-example-form">
      <a-form layout="vertical">
        <a-form-item label="示例名称" required>
          <a-input
            v-model:value="formState.name"
            placeholder="请输入示例名称"
            :maxlength="100"
            show-count
          />
        </a-form-item>

        <a-form-item label="示例描述" required>
          <a-textarea
            v-model:value="formState.description"
            placeholder="请输入示例描述"
            :rows="3"
            :maxlength="500"
            show-count
          />
        </a-form-item>

        <a-form-item label="分类">
          <a-select v-model:value="formState.category" placeholder="请选择分类">
            <a-select-option
              v-for="(info, category) in EXAMPLE_CATEGORIES"
              :key="category"
              :value="category"
            >
              <span style="margin-right: 8px">{{ info.icon }}</span>
              {{ info.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="难度">
          <a-select
            v-model:value="formState.difficulty"
            placeholder="请选择难度"
          >
            <a-select-option
              v-for="(info, difficulty) in EXAMPLE_DIFFICULTIES"
              :key="difficulty"
              :value="difficulty"
            >
              {{ info.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="标签">
          <div class="tags-input-container">
            <div class="tags-list">
              <a-tag
                v-for="tag in formState.tags"
                :key="tag"
                closable
                @close="handleRemoveTag(tag)"
              >
                {{ tag }}
              </a-tag>
            </div>
            <a-input
              v-model:value="tagInput"
              placeholder="输入标签后按回车添加"
              @press-enter="handleAddTag"
              style="margin-top: 8px"
            />
          </div>
        </a-form-item>
      </a-form>

      <div class="form-actions">
        <a-button @click="handleClose">取消</a-button>
        <a-button type="primary" @click="handleSave">保存</a-button>
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
.save-example-form {
  padding: 8px 0;
}

.tags-input-container {
  width: 100%;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
