/**
 * 节点元数据 Store
 *
 * 从后端 GET /v2/nodes 拉取节点类型的端口定义、图标、颜色和配置 schema，
 * 替代 node-defaults.ts 和 node-templates.ts 中的硬编码内容。
 *
 * 插件注册的自定义节点类型自动包含在结果中，无需修改任何前端代码。
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import apiClient from "../api";
import type { InputPort, OutputPort } from "../types/dag-workflow";
import { NODE_TEMPLATES } from "../constants/node-templates";
import { getDefaultPorts } from "../utils/node-defaults";

// ─── 类型定义（与后端 node_registry.py 保持一致）────────────────────────────

export interface PortMeta {
  id: string;
  name: string;
  type: string;
  required: boolean;
}

export interface NodeMeta {
  type: string;
  label: string;
  category: string;
  icon: string;
  color: string;
  inputs: PortMeta[];
  outputs: PortMeta[];
  error_port: PortMeta | null;
  config_schema: Record<string, unknown>;
}

// NodeTemplate 用于 NodePalette 和 Canvas 颜色 Map
export interface NodeTemplate {
  type: string;
  label: string;
  category: string;
  icon: string;
  color: string;
  description: string;
}

// ─── Store ────────────────────────────────────────────────────────────────

export const useNodeMetaStore = defineStore("node-meta", () => {
  const metas = ref<NodeMeta[]>([]);
  const loaded = ref(false);
  const loading = ref(false);
  const error = ref<string | null>(null);

  /**
   * 从后端拉取节点元数据，只执行一次（后续调用直接返回缓存）。
   * 后端不可用时，降级到 node-defaults.ts 本地定义。
   */
  async function fetchMetas() {
    if (loaded.value || loading.value) return;
    loading.value = true;
    error.value = null;
    try {
      const res = await apiClient.get("/v2/nodes");
      metas.value = res.data as NodeMeta[];
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      error.value = msg;
      // 降级：使用本地硬编码数据（离线或后端不可用时）
      metas.value = buildLocalFallback();
    } finally {
      loaded.value = true;
      loading.value = false;
    }
  }

  /**
   * 获取指定节点类型的端口定义，替代 getDefaultPorts()。
   */
  function getPortsForType(type: string): {
    inputs: InputPort[];
    outputs: OutputPort[];
    error_port: OutputPort | undefined;
  } {
    const meta = metas.value.find((m) => m.type === type);
    if (!meta) {
      // 降级到本地定义
      return getDefaultPorts(type);
    }
    return {
      inputs: meta.inputs.map((p) => ({
        id: p.id,
        name: p.name,
        type: p.type as InputPort["type"],
        required: p.required,
      })),
      outputs: meta.outputs.map((p) => ({
        id: p.id,
        name: p.name,
        type: p.type as OutputPort["type"],
      })),
      error_port: meta.error_port
        ? {
            id: meta.error_port.id,
            name: meta.error_port.name,
            type: meta.error_port.type as OutputPort["type"],
          }
        : undefined,
    };
  }

  /**
   * 获取指定节点类型的元数据。
   */
  function getMeta(type: string): NodeMeta | undefined {
    return metas.value.find((m) => m.type === type);
  }

  /**
   * 替代 NODE_TEMPLATES 常量，用于 NodePalette 和颜色 Map。
   */
  const templates = computed<NodeTemplate[]>(() =>
    metas.value.map((m) => ({
      type: m.type,
      label: m.label,
      category: m.category,
      icon: m.icon,
      color: m.color,
      description: "",
    })),
  );

  /**
   * 颜色 Map，替代 Canvas.vue 中的 NODE_COLOR_MAP。
   */
  const colorMap = computed<Map<string, string>>(
    () => new Map(metas.value.map((m) => [m.type, m.color])),
  );

  return {
    metas,
    loaded,
    loading,
    error,
    fetchMetas,
    getPortsForType,
    getMeta,
    templates,
    colorMap,
  };
});

// ─── 本地降级数据（当后端不可用时使用）──────────────────────────────────────

function buildLocalFallback(): NodeMeta[] {
  return NODE_TEMPLATES.map((t) => {
    const ports = getDefaultPorts(t.type);
    return {
      type: t.type,
      label: t.label,
      category: t.category,
      icon: t.icon,
      color: t.color,
      inputs: ports.inputs.map((p) => ({
        id: p.id,
        name: p.name,
        type: p.type,
        required: (p as InputPort).required ?? false,
      })),
      outputs: ports.outputs.map((p) => ({
        id: p.id,
        name: p.name,
        type: p.type,
        required: false,
      })),
      error_port: ports.error_port
        ? { id: ports.error_port.id, name: ports.error_port.name, type: ports.error_port.type, required: false }
        : null,
      config_schema: {},
    } satisfies NodeMeta;
  });
}
