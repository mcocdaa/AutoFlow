<template>
  <a-config-provider :theme="FDS_THEME">
    <a-layout class="fds-layout">
      <a-layout-header class="fds-header">
        <div class="fds-header-left">
          <div class="fds-logo" @click="goHome">
            <div class="fds-logo-icon"></div>
            <span class="fds-logo-text">AutoFlow</span>
            <span class="fds-logo-subtitle">Workflow Automation</span>
          </div>
        </div>
        <div class="fds-header-center"></div>
        <div class="fds-header-right">
          <a-button type="primary" class="create-flow-btn" @click="navigateToRunFlow">
            <template #icon><PlusOutlined /></template>
            创建流程
          </a-button>
          <a-dropdown>
            <a class="user-info" @click.prevent>
              <a-avatar class="user-avatar" size="small">U</a-avatar>
              <span class="user-name">User</span>
            </a>
            <template #overlay>
              <a-menu>
                <a-menu-item key="profile">个人设置</a-menu-item>
                <a-menu-item key="logout">退出登录</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>

      <a-layout>
        <a-layout-sider v-model:collapsed="collapsed" class="fds-sider" width="240">
          <div class="sider-content">
            <a-menu
              v-model:selectedKeys="selectedKeys"
              mode="inline"
              :theme="'dark'"
              class="fds-menu"
            >
              <a-menu-item key="/" @click="router.push('/')">
                <template #icon><AppstoreOutlined /></template>
                <span>Plugins</span>
              </a-menu-item>
              <a-menu-item key="/run" @click="router.push('/run')">
                <template #icon><PlayCircleOutlined /></template>
                <span>Run Flow</span>
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
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  AppstoreOutlined,
  PlayCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons-vue'
import { FDS_THEME } from './theme/flow-design-theme'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const selectedKeys = ref<string[]>([route.path])

watch(() => route.path, (path) => {
  selectedKeys.value = [path]
}, { immediate: true })

const goHome = () => {
  router.push('/')
}

const navigateToRunFlow = () => {
  router.push('/run')
}
</script>

<style>
.fds-layout {
  min-height: 100vh;
}

.fds-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--flow-bg-card);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.fds-header-left {
  display: flex;
  align-items: center;
}

.fds-logo {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 12px;
}

.fds-logo-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--flow-gradient-autoflow);
}

.fds-logo-text {
  font-size: 20px;
  font-weight: 600;
  color: var(--flow-text-title);
}

.fds-logo-subtitle {
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.fds-header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.create-flow-btn {
  background: var(--flow-gradient-autoflow);
  border: none;
}

.create-flow-btn:hover {
  opacity: 0.9;
  background: var(--flow-gradient-autoflow) !important;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--flow-text-primary);
}

.user-avatar {
  background: var(--flow-color-primary);
}

.fds-sider {
  background: #1E293B;
}

.sider-content {
  padding-top: 16px;
}

.fds-menu {
  border-right: none;
}

.fds-content {
  padding: 24px;
  background: var(--flow-bg-page);
  min-height: calc(100vh - 64px);
}
</style>
