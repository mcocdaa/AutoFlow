<template>
  <a-config-provider :theme="FDS_THEME">
    <div class="app-shell">
      <header class="app-header">
        <div class="header-left">
          <div class="brand" @click="goHome">
            <div class="brand-mark">
              <svg viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 2L2 7L12 12L22 7L12 2Z"
                  fill="white"
                  fill-opacity="0.9"
                />
                <path
                  d="M2 17L12 22L22 17"
                  stroke="white"
                  stroke-width="1.8"
                  stroke-linecap="round"
                />
                <path
                  d="M2 12L12 17L22 12"
                  stroke="white"
                  stroke-width="1.8"
                  stroke-linecap="round"
                />
              </svg>
            </div>
            <div class="brand-text">
              <span class="brand-name">AutoFlow</span>
              <span class="brand-sub">Workflow Automation</span>
            </div>
          </div>
        </div>

        <div class="header-center"></div>

        <div class="header-right">
          <a-button type="primary" class="btn-create" @click="navigateToEditor">
            <template #icon><PlusOutlined /></template>
            创建流程
          </a-button>
          <a-dropdown>
            <div class="user-chip">
              <a-avatar :size="28" class="user-avatar">U</a-avatar>
              <span class="user-label">User</span>
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item key="profile">个人设置</a-menu-item>
                <a-menu-item key="logout">退出登录</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </header>

      <div class="app-body">
        <aside
          class="app-sidebar"
          :class="{ collapsed: sidebarCollapsed }"
          @mouseenter="handleSidebarEnter"
          @mouseleave="handleSidebarLeave"
        >
          <button
            class="sidebar-collapse-btn"
            @click="sidebarCollapsed = !sidebarCollapsed"
          >
            <MenuFoldOutlined v-if="!sidebarCollapsed" />
            <MenuUnfoldOutlined v-else />
          </button>

          <nav class="sidebar-nav">
            <a-menu
              v-model:selectedKeys="selectedKeys"
              mode="inline"
              theme="dark"
              class="side-menu"
            >
              <a-menu-item key="/" @click="router.push('/')">
                <template #icon><AppstoreOutlined /></template>
                <span>插件管理</span>
              </a-menu-item>
              <a-menu-item key="/editor" @click="router.push('/editor')">
                <template #icon><BranchesOutlined /></template>
                <span>可视化编辑器</span>
              </a-menu-item>
              <a-menu-item key="/run" @click="router.push('/run')">
                <template #icon><PlayCircleOutlined /></template>
                <span>YAML 编辑器</span>
              </a-menu-item>
            </a-menu>
          </nav>
        </aside>

        <main class="app-main">
          <router-view />
        </main>
      </div>
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  AppstoreOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  BranchesOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from "@ant-design/icons-vue";
import { FDS_THEME } from "./theme/flow-design-theme";

const router = useRouter();
const route = useRoute();
const sidebarCollapsed = ref(false);
const selectedKeys = ref<string[]>([route.path]);

let collapseTimer: number | null = null;

const handleSidebarEnter = () => {
  if (collapseTimer) {
    clearTimeout(collapseTimer);
    collapseTimer = null;
  }
  sidebarCollapsed.value = false;
};

const handleSidebarLeave = () => {
  collapseTimer = window.setTimeout(() => {
    sidebarCollapsed.value = true;
  }, 300);
};

watch(
  () => route.path,
  (path) => {
    selectedKeys.value = [path];
  },
  { immediate: true },
);

const goHome = () => {
  router.push("/");
};

const navigateToEditor = () => {
  router.push("/editor");
};
</script>

<style>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0f172a;
}

.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #0f172a;
  border-bottom: 1px solid #1e293b;
}

.header-left {
  display: flex;
  align-items: center;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.brand:hover {
  opacity: 0.9;
}

.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
}

.brand-mark svg {
  width: 20px;
  height: 20px;
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: -0.3px;
}

.brand-sub {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.header-center {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.btn-create {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  border: none !important;
  font-weight: 600;
  height: 36px;
  border-radius: 8px;
  font-size: 13px;
  transition: all 0.25s;
}

.btn-create:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35) !important;
  background: linear-gradient(135deg, #5558e3, #7c3aed) !important;
  color: white !important;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 10px 4px 4px;
  border-radius: 9999px;
  transition: background 0.2s;
}

.user-chip:hover {
  background: rgba(255, 255, 255, 0.06);
}

.user-avatar {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  font-size: 12px !important;
  font-weight: 600;
}

.user-label {
  font-size: 13px;
  font-weight: 500;
  color: #cbd5e1;
}

.app-body {
  margin-top: 56px;
  display: flex;
  flex: 1;
  min-height: calc(100vh - 56px);
}

.app-sidebar {
  position: fixed;
  left: 0;
  top: 56px;
  bottom: 0;
  width: 220px;
  background: #0f172a;
  border-right: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  transition: width 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 800;
  overflow: hidden;
}

.app-sidebar.collapsed {
  width: 64px;
}

.sidebar-collapse-btn {
  position: absolute;
  top: 12px;
  right: 10px;
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(255, 255, 255, 0.06);
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  z-index: 10;
}

.sidebar-collapse-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #e2e8f0;
}

.sidebar-nav {
  padding-top: 48px;
  flex: 1;
  overflow-y: auto;
}

.side-menu {
  border-right: none !important;
  background: transparent !important;
}

.side-menu :deep(.ant-menu-item) {
  margin: 3px 10px !important;
  border-radius: 8px !important;
  height: 40px !important;
  line-height: 40px !important;
  color: #94a3b8 !important;
  font-size: 13px !important;
  transition: all 0.2s !important;
}

.side-menu :deep(.ant-menu-item:hover) {
  color: #e2e8f0 !important;
  background: rgba(255, 255, 255, 0.04) !important;
}

.side-menu :deep(.ant-menu-item-selected) {
  background: #334155 !important;
  color: #e2e8f0 !important;
  box-shadow: 0 2px 12px rgba(99, 102, 241, 0.15) !important;
}

.side-menu :deep(.ant-menu-item .anticon) {
  font-size: 16px !important;
}

.app-main {
  flex: 1;
  margin-left: 220px;
  min-height: calc(100vh - 56px);
  transition: margin-left 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  display: flex;
  flex-direction: column;
}

.app-sidebar.collapsed ~ .app-main {
  margin-left: 64px;
}
</style>
