<script setup lang="ts">
import { message } from "ant-design-vue";
import { CopyOutlined, DownloadOutlined } from "@ant-design/icons-vue";

interface Props {
  visible: boolean;
  yamlContent: string;
  fileName?: string;
}

interface Emits {
  (e: "update:visible", value: boolean): void;
}

const props = withDefaults(defineProps<Props>(), {
  fileName: "workflow",
});

const emit = defineEmits<Emits>();

const handleClose = () => {
  emit("update:visible", false);
};

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(props.yamlContent);
    message.success("YAML已复制到剪贴板");
  } catch (error) {
    message.error("复制失败");
  }
};

const handleDownload = () => {
  try {
    const blob = new Blob([props.yamlContent], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${props.fileName}.yaml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    message.success("YAML文件已下载");
  } catch (error) {
    message.error("下载失败");
  }
};
</script>

<template>
  <a-modal
    :open="visible"
    title="导出 YAML"
    width="700px"
    @cancel="handleClose"
    :footer="null"
  >
    <div class="export-yaml-modal">
      <div class="yaml-container">
        <pre class="yaml-content">{{ yamlContent }}</pre>
      </div>
      <div class="modal-actions">
        <a-button @click="handleClose">取消</a-button>
        <a-button @click="handleCopy">
          <template #icon><CopyOutlined /></template>
          复制
        </a-button>
        <a-button type="primary" @click="handleDownload">
          <template #icon><DownloadOutlined /></template>
          下载
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
.export-yaml-modal {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.yaml-container {
  background: #1e293b;
  border-radius: 8px;
  overflow: hidden;
  max-height: 500px;
  overflow-y: auto;
}

.yaml-content {
  margin: 0;
  padding: 16px;
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 13px;
  color: #e2e8f0;
  overflow-x: auto;
  white-space: pre;
  line-height: 1.6;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
