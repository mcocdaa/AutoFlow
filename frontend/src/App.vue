<template>
  <a-config-provider :theme="FDS_THEME">
    <a-layout class="fds-layout">
      <div class="fds-header">
        <div class="fds-header-left">
          <div class="fds-logo" @click="goHome">
            <div class="fds-logo-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M12 2L2 7L12 12L22 7L12 2Z"
                  fill="white"
                  fill-opacity="0.9"
                />
                <path
                  d="M2 17L12 22L22 17"
                  stroke="white"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <path
                  d="M2 12L12 17L22 12"
                  stroke="white"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
            <div class="fds-logo-text-group">
              <span class="fds-logo-text">AutoFlow</span>
              <span class="fds-logo-subtitle">Workflow Automation</span>
            </div>
          </div>
        </div>
        <div class="fds-header-center"></div>
        <div class="fds-header-right">
          <a-button
            type="primary"
            class="create-flow-btn"
            @click="navigateToEditor"
          >
            <template #icon><PlusOutlined /></template>
            创建流程
          </a-button>
          <a-dropdown>
            <div class="user-info" @click.prevent>
              <a-avatar
                class="user-avatar"
                size="small"
                :style="{
                  background:
                    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                }"
                >U</a-avatar
              >
              <span class="user-name">User</span>
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item key="profile">个人设置</a-menu-item>
                <a-menu-item key="logout">退出登录</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </div>

      <a-layout style="margin-top: 68px">
        <a-layout-sider
          v-model:collapsed="collapsed"
          class="fds-sider"
          width="260"
          style="margin-top: 0"
        >
          <div class="sider-content">
            <a-menu
              v-model:selectedKeys="selectedKeys"
              mode="inline"
              :theme="'dark'"
              class="fds-menu"
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
          </div>
        </a-layout-sider>

        <a-layout-content class="fds-content">
          <router-view></router-view>
        </a-layout-content>
      </a-layout>
    </a-layout>
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
} from "@ant-design/icons-vue";
import { FDS_THEME } from "./theme/flow-design-theme";

const router = useRouter();
const route = useRoute();
const collapsed = ref(false);
const selectedKeys = ref<string[]>([route.path]);

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
.fds-layout {
  min-height: 100vh;
}

.fds-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
}

.fds-header-left {
  display: flex;
  align-items: center;
}

.fds-logo {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 14px;
  transition: transform 0.2s ease;
}

.fds-logo:hover {
  transform: scale(1.02);
}

.fds-logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.fds-logo-icon svg {
  width: 24px;
  height: 24px;
}

.fds-logo-text-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.fds-logo-text {
  font-size: 22px;
  font-weight: 700;
  color: white;
  letter-spacing: -0.3px;
}

.fds-logo-subtitle {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}

.fds-header-right {
  display: flex;
  align-items: center;
  gap: 18px;
}

.create-flow-btn {
  background: white;
  color: #667eea;
  border: none;
  font-weight: 600;
  height: 40px;
  border-radius: 10px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.create-flow-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  background: white !important;
  color: #667eea !important;
}

.create-flow-btn:active {
  transform: translateY(0);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  color: white;
  padding: 6px 12px;
  border-radius: 10px;
  transition: background 0.2s ease;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.15);
}

.user-name {
  font-weight: 500;
  font-size: 14px;
  color: white;
}

.fds-sider {
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  border-right: none;
}

.sider-content {
  padding-top: 20px;
}

.fds-menu {
  border-right: none;
  background: transparent;
}

.fds-menu :deep(.ant-menu-item) {
  margin: 4px 12px;
  border-radius: 10px;
  transition: all 0.2s ease;
  color: rgba(255, 255, 255, 0.7);
}

.fds-menu :deep(.ant-menu-item:hover) {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.fds-menu :deep(.ant-menu-item-selected) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.fds-menu :deep(.ant-menu-item .anticon) {
  font-size: 18px;
}

.fds-content {
  padding: 28px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  min-height: calc(100vh - 68px);
}
</style>
