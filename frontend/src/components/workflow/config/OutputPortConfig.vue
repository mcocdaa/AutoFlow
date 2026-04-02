<script setup lang="ts">
import { Input, Select, Button } from "ant-design-vue";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons-vue";
import type { OutputPort } from "../../../types/dag-workflow";

interface Props {
  ports: OutputPort[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:ports", ports: OutputPort[]): void;
  (e: "add-port"): void;
  (e: "remove-port", index: number): void;
}>();

const dataTypes = [
  { label: "any", value: "any" },
  { label: "string", value: "string" },
  { label: "number", value: "number" },
  { label: "boolean", value: "boolean" },
  { label: "object", value: "object" },
  { label: "array", value: "array" },
];

const handlePortNameChange = (index: number, value: string) => {
  const newPorts = [...props.ports];
  newPorts[index] = { ...newPorts[index], name: value };
  emit("update:ports", newPorts);
};

const handlePortTypeChange = (index: number, value: any) => {
  const newPorts = [...props.ports];
  newPorts[index] = { ...newPorts[index], type: value as any };
  emit("update:ports", newPorts);
};

const handlePortConditionChange = (index: number, value: any) => {
  const newPorts = [...props.ports];
  newPorts[index] = { ...newPorts[index], condition: value as string | null };
  emit("update:ports", newPorts);
};

const handleRemovePort = (index: number) => {
  emit("remove-port", index);
};

const handleAddPort = () => {
  emit("add-port");
};
</script>

<template>
  <div class="output-port-config">
    <div class="ports-header">
      <span class="ports-title">输出端口</span>
      <Button
        type="primary"
        size="small"
        :icon="h(PlusOutlined)"
        @click="handleAddPort"
      >
        添加端口
      </Button>
    </div>
    <div class="ports-list">
      <div
        v-for="(port, index) in ports"
        :key="port.id || index"
        class="port-item"
      >
        <div class="port-content">
          <div class="port-field">
            <label class="field-label">名称</label>
            <Input
              :value="port.name"
              @update:value="handlePortNameChange(index, $event)"
              placeholder="端口名称"
            />
          </div>
          <div class="port-field">
            <label class="field-label">类型</label>
            <Select
              :value="port.type"
              :options="dataTypes"
              @update:value="handlePortTypeChange(index, $event)"
              style="width: 100%"
            />
          </div>
          <div class="port-field condition-field">
            <label class="field-label">条件表达式</label>
            <Input
              :value="port.condition ?? undefined"
              @update:value="handlePortConditionChange(index, $event)"
              placeholder="条件表达式（可选）"
            />
          </div>
        </div>
        <Button
          type="text"
          danger
          size="small"
          :icon="h(DeleteOutlined)"
          @click="handleRemovePort(index)"
        />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { h } from "vue";
export default {
  methods: {
    h,
  },
};
</script>

<style scoped>
.output-port-config {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ports-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ports-title {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
}

.ports-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.port-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.port-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.condition-field {
  grid-column: span 2;
}

.port-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
}
</style>
